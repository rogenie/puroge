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
PRICES = {"fal-ai/nano-banana/edit": 0.0398, "fal-ai/nano-banana-pro/edit": 0.15, "fal-ai/nano-banana-2/edit": 0.08}
PRICE_PER_IMAGE = PRICES[ENDPOINT]


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


MAX_REFS = 10  # fal nano-banana/edit accepts at most 10 image URLs


def person_refs(model, limit=None):
    """Reference photos of a real person, best first: URLs as given, local files uploaded to fal storage."""
    import fal_client
    base = Path(os.environ.get("PEOPLE_DIR", ROOT))
    out = []
    for r in model.get("refs", [])[:limit]:
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


def local_ref(path):
    """Upload one local file (in this repo or PEOPLE_DIR) to fal storage; URLs pass through."""
    import fal_client
    if path.startswith("http"):
        return path
    for base in (ROOT, Path(os.environ.get("PEOPLE_DIR", ROOT))):
        if (base / path).exists():
            return fal_client.upload_file(str(base / path))
    print(f"::warning title=generate.py::reference not found: {path}")
    return None


def main_assets(video, outdir, only):
    """Reusable assets (character sheets, empty set plates): "jobs": [{file, prompt, refs, aspect, n}]."""
    manifest = {"video": video["id"], "endpoint": ENDPOINT, "mode": "assets", "images": []}
    made = 0
    for job in video["jobs"]:
        if only and only != job["file"]:
            continue
        refs = [u for u in (local_ref(r) for r in job.get("refs", [])) if u]
        n = job.get("n", 1)
        for i, u in enumerate(call(job["prompt"], refs, job.get("aspect", "3:4"), n), 1):
            dest = outdir / (f"{job['file']}-{i}.jpg" if n > 1 else f"{job['file']}.jpg")
            save_jpeg(u, dest, max_w=job.get("max_w", 1600))
            made += 1
            manifest["images"].append({"file": dest.name, "prompt": job["prompt"], "refs": job.get("refs", [])})
    outdir.mkdir(parents=True, exist_ok=True)
    manifest["estimated_cost_usd"] = round(made * PRICE_PER_IMAGE, 2)
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{made} images in {outdir}, about ${manifest['estimated_cost_usd']}")


def person_prompt(cast, model, outfit):
    """Playbook order (engine/playbook.md): who, anchors and outfit first; then references, pose, frame, relight, realism."""
    return (f"One woman alone: {model['description']}. Fixed details ({model.get('anchors', '')}). "
            f"FULLY CLOTHED, wearing {outfit}.\n"
            "Image 1 is her character sheet: keep this exact woman's face, identity, hair and fixed details unchanged; "
            "use it for identity only, never for lighting or clothing. Image 2 is the room: place her in exactly this room, same "
            "furniture, same view, same camera height. The remaining images are the garments: reproduce each one's color, fabric, "
            "cut and details exactly, including the shoes; ignore any person, mannequin or background in them.\n"
            f"{cast['pose']} Expression: {model.get('expression', 'calm')}. {cast['frame']}\n"
            f"{cast['relight']}\n{cast['realism']} {cast['modest']} {cast['no_ip']}")


def main_pairs(video, cast, outdir, only):
    """One full-length image per person per look ("<look>-<model>.jpg"); render.py places them side by side.
    People are never generated together: a tall and a petite woman in one frame gets drawn as parent and child."""
    looks = [load_json(ROOT / "data" / "looks" / f"{s}.json") for s in video["looks"]]
    people = video["cast"]
    manifest = {"video": video["id"], "endpoint": ENDPOINT, "mode": "pairs", "images": []}
    old = outdir / "manifest.json"
    if only and old.exists():
        manifest["images"] = [i for i in json.loads(old.read_text())["images"] if i.get("look") != only]
    cache = {}
    made = 0
    plate = local_ref(cast["set_plate"]) if cast.get("set_plate") and (ROOT / cast["set_plate"]).exists() else None
    for look in looks:
        if only and only != look["slug"]:
            continue
        for p in people:
            model = cast["models"][p["model"]]
            ps = pieces_for(look, p["tier"])
            prod = list(dict.fromkeys(x["ref"] for x in ps if x["ref"]))
            sheet = model.get("sheet")
            if sheet and (ROOT / sheet).exists() and plate:
                if sheet not in cache:
                    cache[sheet] = local_ref(sheet)
                refs = [cache[sheet], plate] + prod[:MAX_REFS - 2]
                prompt = person_prompt(cast, model, describe(ps))
            else:  # older path: reference photos, set described in words
                room = max(MAX_REFS - len(prod), 0)
                key = (p["model"], room)
                if key not in cache:
                    cache[key] = person_refs(model, room) if model.get("refs") and room else []
                refs = cache[key] + prod
                prompt = (f"{cast['style']} Vertical 3:4. One woman alone, full length, head to toe visible, centered, "
                          f"standing naturally: {model['description']}, wearing {describe(ps)}. Setting: {cast['set']}. {cast['reference_note']}")
            for u in call(prompt, refs, "3:4", 1):
                dest = outdir / f"{look['slug']}-{p['model']}.jpg"
                save_jpeg(u, dest)
                made += 1
                manifest["images"].append({"file": dest.name, "kind": "person", "look": look["slug"], "model": p["model"],
                                           "tier": p["tier"], "prompt": prompt, "refs": len(refs)})
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
    global ENDPOINT, PRICE_PER_IMAGE
    if video.get("endpoint"):
        ENDPOINT = video["endpoint"]
        PRICE_PER_IMAGE = PRICES.get(ENDPOINT, 0.15)
    cast = load_json(ROOT / "engine" / "models.json")
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    if video.get("mode") == "assets":
        return main_assets(video, Path(os.environ.get("CANDIDATES_DIR", ROOT / "images" / "candidates")) / video["id"], only)
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
