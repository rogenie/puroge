#!/usr/bin/env python3
"""Approve images from a generation run after the quality check.

Usage:  python3 engine/approve.py <video id> --group group-2.jpg [--looks]
        python3 engine/approve.py <video id> --pairs [look slug ...]
  --pairs          two-person runs: publish each look's <look>-<model>.jpg as images/looks/<look>-<tier>.jpg,
                   set the look's "images" (one per tier; the look page swaps them with the tabs) and "image" (Heirloom)
  --group <file>   the group image to use for the video (copied to images/videos/<video id>.jpg)
  --looks          also publish each look's image (images/looks/<slug>.jpg) and set it on the look
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def approve_pairs(vid, only):
    cand = ROOT / "images" / "candidates" / vid
    manifest = json.loads((cand / "manifest.json").read_text())
    for img in manifest["images"]:
        slug, tier = img["look"], img["tier"]
        if only and slug not in only:
            continue
        out = ROOT / "images" / "looks" / f"{slug}-{tier}.jpg"
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cand / img["file"], out)
        lf = ROOT / "data" / "looks" / f"{slug}.json"
        look = json.loads(lf.read_text())
        look.setdefault("images", {})[tier] = f"/images/looks/{slug}-{tier}.jpg"
        look["image"] = look["images"].get("heirloom", look["images"][tier])
        lf.write_text(json.dumps(look, indent=2, ensure_ascii=False) + "\n")
        print("look image:", out.relative_to(ROOT))


def main():
    args = sys.argv[1:]
    if args and "--pairs" in args:
        return approve_pairs(args[0], [a for a in args[1:] if a != "--pairs"])
    if not args or "--group" not in args:
        sys.exit(__doc__)
    vid = args[0]
    cand = ROOT / "images" / "candidates" / vid
    group = cand / args[args.index("--group") + 1]
    dest = ROOT / "images" / "videos" / f"{vid}.jpg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(group, dest)
    print("video image:", dest.relative_to(ROOT))
    if "--looks" in args:
        manifest = json.loads((cand / "manifest.json").read_text())
        for img in manifest["images"]:
            if img["kind"] != "look":
                continue
            slug = img["look"]
            out = ROOT / "images" / "looks" / f"{slug}.jpg"
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / img["file"], out)
            lf = ROOT / "data" / "looks" / f"{slug}.json"
            look = json.loads(lf.read_text())
            look["image"] = f"/images/looks/{slug}.jpg"
            lf.write_text(json.dumps(look, indent=2, ensure_ascii=False) + "\n")
            print("look image:", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
