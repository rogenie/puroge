#!/usr/bin/env python3
"""Generate images for one video file with fal.ai (Nano Banana edit, product photos as references).

Usage:  FAL_KEY=... python3 engine/generate.py engine/runs/<date>/<video>.json [--group-only] [--only <look slug or "group">]
  --only   regenerate just one image (after a failed quality check); other candidates are kept

Writes candidates to images/candidates/<video id>/:
  group-<n>.jpg        all models together, 9:16, for the video (2 candidates)
  <look slug>.jpg      one model per look, 3:4, for the look page and the video close-ups
  manifest.json        prompts, references and costs, for the quality check
Pairs mode (video file has "mode": "pairs"): one 3:4 image per look with two people side by side,
each wearing one tier ("cast": [{"model": "T", "tier": "heirloom"}, {"model": "R", "tier": "everyday"}]).
People with reference photos ("refs" in engine/models.json) are matched to those photos.
Nothing goes live until a candidate is approved with engine/approve.py.
Cost at fal's listed price (about $0.04 per image): about $0.20 per three-look video.
"""
import io
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENDPOINT = "fal-ai/nano-banana/edit"
PRICE_PER_IMAGE = 0.0398


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def pieces_for(look, tier):
    out = []
    for p in look["pieces"]:
        v = p[tier]
        out.append({"item": p["item"], "name": v["name"], "material": v.get("material", ""), "ref": v.get("ref_image")})
    return out


def describe(pieces):
    out = []
    for p in pieces:
        color, item = p["name"].split(",")[-1].strip().lower(), p["item"].lower()
        words = [w for w in color.split() if w not in item.split()]
        out.append(f'{" ".join(words + [item]).strip()} ({p["material"]})')
    return ", ".join(out)


def save_jpeg(url, dest, max_w=1080):
    from PIL import Image
    with urllib.request.urlopen(url, timeout=120) as r:
        im = Image.open(io.BytesIO(r.read())).convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=86, optimize=True)


def call(prompt, refs, aspect, n):
    import fal_client
    res = fal_client.subscribe(ENDPOINT, arguments={
        "prompt": prompt, "image_urls": refs, "num_images": n,
        "aspect_ratio": aspect, "output_format": "png", "limit_generations": n == 1})
    return [img["url"] for img in res["images"]]


def person_refs(model):
    """Reference photos of a real person: URLs as given, local files uploaded to fal storage."""
    import fal_client
    base = Path(os.environ.get("PEOPLE_DIR", ROOT))
    out = []
    for r in model.get("refs", []):
        if r.startswith("http"):
            out.append(r)
        elif (base / r).exists():
            out.append(fal_client.upload_file(str(base / r)))
        else:
            print(f"::warning title=generate.py::reference photo not found: {r}")
    return out


def model_desc(cast, key):
    m = cast["models"][key]
    return m["description"] if isinstance(m, dict) else m


def main_pairs(video, cast, outdir, only):
    looks = [load_json(ROOT / "data" / "looks" / f"{s}.json") for s in video["looks"]]
    sides = ["On the left", "On the right"]
    people = video["cast"]
    face_refs = {p["model"]: person_refs(cast["models"][p["model"]]) for p in people}
    manifest = {"video": video["id"], "endpoint": ENDPOINT, "mode": "pairs", "images": []}
    old = outdir / "manifest.json"
    if only and old.exists():
        manifest["images"] = [i for i in json.loads(old.read_text())["images"] if i.get("look") != only]
    made = 0
    for look in looks:
        if only and only != look["slug"]:
            continue
        lines, refs = [], []
        for side, p in zip(sides, people):
            ps = pieces_for(look, p["tier"])
            lines.append(f"{side}: {model_desc(cast, p['model'])}, wearing {describe(ps)}.")
            refs += [x["ref"] for x in ps if x["ref"]]
        persons = [u for p in people for u in face_refs[p["model"]]]
        refs = list(dict.fromkeys(persons + refs))
        prompt = (f"{cast['style']} Vertical 3:4. Two women standing side by side, both full length, head to toe visible, "
                  f"same outfit idea in two versions. " + " ".join(lines) + f" {cast.get('scale_note', '')} "
                  f"Setting: {cast['set']}. {cast['reference_note']}")
        for u in call(prompt, refs, "3:4", 1):
            dest = outdir / f"{look['slug']}.jpg"
            save_jpeg(u, dest)
            made += 1
            manifest["images"].append({"file": dest.name, "kind": "look", "look": look["slug"],
                                       "prompt": prompt, "person_refs": len(persons)})
    outdir.mkdir(parents=True, exist_ok=True)
    manifest["estimated_cost_usd"] = round(made * PRICE_PER_IMAGE, 2)
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{made} images in {outdir}, about ${manifest['estimated_cost_usd']}")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    os.environ["FAL_KEY"] = os.environ.get("FAL_KEY", "").strip().strip('"').strip("'").strip()
    if not os.environ.get("FAL_KEY"):
        sys.exit("FAL_KEY is not set. Add it as a repository secret named FAL_KEY.")
    video = load_json(sys.argv[1])
    cast = load_json(ROOT / "engine" / "models.json")
    tier = video.get("tier_shown", "everyday")
    looks = [load_json(ROOT / "data" / "looks" / f"{s}.json") for s in video["looks"]]
    order = cast["positions"].get(str(len(looks)), [])
    outdir = Path(os.environ.get("CANDIDATES_DIR", ROOT / "images" / "candidates")) / video["id"]
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    if video.get("mode") == "pairs":
        return main_pairs(video, cast, outdir, only)
    old = outdir / "manifest.json"
    manifest = {"video": video["id"], "endpoint": ENDPOINT, "tier": tier, "images": []}
    if only and old.exists():
        prev = json.loads(old.read_text())
        keep = (lambda i: i["kind"] != "group") if only == "group" else (lambda i: i.get("look") != only)
        manifest["images"] = [i for i in prev["images"] if keep(i)]
        manifest["history_cost_usd"] = prev.get("estimated_cost_usd", 0) + prev.get("history_cost_usd", 0)

    # Group image for the video: every model, every reference.
    lines, refs = [], []
    for pos, (model_key, look) in enumerate(zip(order, looks)):
        side = ["On the left", "In the center", "On the right"][pos if len(looks) == 3 else (0 if pos == 0 else 2)]
        ps = pieces_for(look, tier)
        lines.append(f"{side}: {model_desc(cast, model_key)}, wearing {describe(ps)}.")
        refs += [p["ref"] for p in ps if p["ref"]]
    refs = list(dict.fromkeys(refs))
    group_prompt = (f"{cast['style']} Vertical 9:16. {len(looks)} women standing side by side, full length, head to toe visible. "
                    + " ".join(lines) + f" Setting: {cast['set']}. {cast['reference_note']}")
    urls = call(group_prompt, refs, "9:16", 2) if only in (None, "group") else []
    for i, u in enumerate(urls, 1):
        dest = outdir / f"group-{i}.jpg"
        save_jpeg(u, dest)
        manifest["images"].append({"file": str(dest.relative_to(ROOT)), "kind": "group", "prompt": group_prompt, "refs": refs})

    # One image per look for the site.
    if "--group-only" not in sys.argv and only != "group":
        for model_key, look in zip(order, looks):
            if only and only != look["slug"]:
                continue
            ps = pieces_for(look, tier)
            look_refs = [p["ref"] for p in ps if p["ref"]]
            prompt = (f"{cast['style']} Vertical 3:4. One woman, full length, head to toe visible: {model_desc(cast, model_key)}, "
                      f"wearing {describe(ps)}. Setting: {cast['set']}. {cast['reference_note']}")
            for u in call(prompt, look_refs, "3:4", 1):
                dest = outdir / f"{look['slug']}.jpg"
                save_jpeg(u, dest)
                manifest["images"].append({"file": str(dest.relative_to(ROOT)), "kind": "look", "look": look["slug"],
                                           "prompt": prompt, "refs": look_refs})

    outdir.mkdir(parents=True, exist_ok=True)
    new = len(urls) + sum(1 for i in manifest["images"] if i["kind"] == "look" and (not only or i.get("look") == only))
    manifest["estimated_cost_usd"] = round(new * PRICE_PER_IMAGE, 2)
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len(manifest['images'])} images in {outdir.relative_to(ROOT)}, about ${manifest['estimated_cost_usd']}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as ex:
        if ex.code not in (0, None):
            print(f"::error title=generate.py::{ex.code}")
        raise
    except Exception as ex:
        import traceback
        detail = "".join(traceback.format_exception_only(type(ex), ex)).strip().replace("\n", " | ")
        print(f"::error title=generate.py::{detail[:900]}")
        raise
