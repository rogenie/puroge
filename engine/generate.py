#!/usr/bin/env python3
"""Generate images for one video file with fal.ai (Nano Banana edit, product photos as references).

Usage:  FAL_KEY=... python3 engine/generate.py engine/runs/<date>/<video>.json [--group-only]

Writes candidates to images/candidates/<video id>/:
  group-<n>.jpg        all models together, 9:16, for the video (2 candidates)
  <look slug>.jpg      one model per look, 3:4, for the look page and the video close-ups
  manifest.json        prompts, references and costs, for the quality check
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
    return ", ".join(f'{p["name"].split(",")[-1].strip().lower()} {p["item"].lower()} ({p["material"]})' for p in pieces)


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


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if not os.environ.get("FAL_KEY"):
        sys.exit("FAL_KEY is not set. Add it as a repository secret named FAL_KEY.")
    video = load_json(sys.argv[1])
    cast = load_json(ROOT / "engine" / "models.json")
    tier = video.get("tier_shown", "everyday")
    looks = [load_json(ROOT / "data" / "looks" / f"{s}.json") for s in video["looks"]]
    order = cast["positions"][str(len(looks))]
    outdir = ROOT / "images" / "candidates" / video["id"]
    manifest = {"video": video["id"], "endpoint": ENDPOINT, "tier": tier, "images": []}

    # Group image for the video: every model, every reference.
    lines, refs = [], []
    for pos, (model_key, look) in enumerate(zip(order, looks)):
        side = ["On the left", "In the center", "On the right"][pos if len(looks) == 3 else (0 if pos == 0 else 2)]
        ps = pieces_for(look, tier)
        lines.append(f"{side}: {cast['models'][model_key]}, wearing {describe(ps)}.")
        refs += [p["ref"] for p in ps if p["ref"]]
    refs = list(dict.fromkeys(refs))
    group_prompt = (f"{cast['style']} Vertical 9:16. {len(looks)} women standing side by side, full length, head to toe visible. "
                    + " ".join(lines) + f" Setting: {cast['set']}. {cast['reference_note']}")
    urls = call(group_prompt, refs, "9:16", 2)
    for i, u in enumerate(urls, 1):
        dest = outdir / f"group-{i}.jpg"
        save_jpeg(u, dest)
        manifest["images"].append({"file": str(dest.relative_to(ROOT)), "kind": "group", "prompt": group_prompt, "refs": refs})

    # One image per look for the site.
    if "--group-only" not in sys.argv:
        for model_key, look in zip(order, looks):
            ps = pieces_for(look, tier)
            look_refs = [p["ref"] for p in ps if p["ref"]]
            prompt = (f"{cast['style']} Vertical 3:4. One woman, full length, head to toe visible: {cast['models'][model_key]}, "
                      f"wearing {describe(ps)}. Setting: {cast['set']}. {cast['reference_note']}")
            for u in call(prompt, look_refs, "3:4", 1):
                dest = outdir / f"{look['slug']}.jpg"
                save_jpeg(u, dest)
                manifest["images"].append({"file": str(dest.relative_to(ROOT)), "kind": "look", "look": look["slug"],
                                           "prompt": prompt, "refs": look_refs})

    outdir.mkdir(parents=True, exist_ok=True)
    manifest["estimated_cost_usd"] = round(len(manifest["images"]) * PRICE_PER_IMAGE, 2)
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
