#!/usr/bin/env python3
"""Turn one approved group image into a vertical video with slow camera moves and on-screen text.

Usage:  python3 engine/render.py engine/runs/<date>/<video>.json [group.jpg] [out.mp4]
Defaults: group image images/videos/<video id>.jpg, output videos/<video id>.mp4

Reads the video file's "script" (shot timing: "wide" uses the group image; a shot naming Model A/B/C uses
that model's full-length look image from images/looks/, falling back to the generation candidates)
and its "on_screen" text. Shots crossfade; each shot holds a slow push-in.
The video is silent on purpose: add a trending sound and the voiceover (TikTok or CapCut text-to-speech,
using the script) inside the app when posting. Needs ffmpeg and Pillow. Costs nothing to run.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS = 1080, 1920, 30
FONT = str(ROOT / "engine" / "fonts" / "Inter-SemiBold.otf")


def seconds(span):
    a, b = re.findall(r"[\d.]+", span)[:2]
    return float(a), float(b)


def nine16(img_w, img_h, focus_y=0.45):
    """Largest 9:16 window inside the image, centered horizontally."""
    w = min(img_w, img_h * 9 / 16)
    h = w * 16 / 9
    return ((img_w - w) / 2, (img_h - h) * focus_y, w, h)


def shot_source(shot, video, group, order, cand_dir):
    m = re.search(r"Model ([ABC])", shot)
    if not m or m.group(1) not in order:
        return group
    slug = video["looks"][order.index(m.group(1))]
    for p in (ROOT / "images" / "looks" / f"{slug}.jpg", cand_dir / f"{slug}.jpg"):
        if p.exists():
            return Image.open(p).convert("RGB")
    return group


def ease(t):
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def text_layer(text):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if not text:
        return layer
    d = ImageDraw.Draw(layer)
    font = ImageFont.truetype(FONT, 54)
    lines = []
    for para in text.split("\n"):
        words, cur = para.split(), ""
        for w_ in words:
            trial = (cur + " " + w_).strip()
            if d.textlength(trial, font=font) > W - 160 and cur:
                lines.append(cur)
                cur = w_
            else:
                cur = trial
        lines.append(cur)
    line_h = 70
    y = int(H * 0.12)
    for line in lines:
        tw = d.textlength(line, font=font)
        x = (W - tw) / 2
        d.rounded_rectangle((x - 24, y - 10, x + tw + 24, y + line_h - 6), radius=14, fill=(32, 26, 22, 200))
        d.text((x, y), line, font=font, fill=(246, 241, 232, 255))
        y += line_h + 8
    return layer


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    video = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    img_path = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "images" / "videos" / f"{video['id']}.jpg"
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "videos" / f"{video['id']}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    group = Image.open(img_path).convert("RGB")
    cast = json.loads((ROOT / "engine" / "models.json").read_text())
    order = cast["positions"][str(len(video["looks"]))]
    cand_dir = ROOT / "images" / "candidates" / video["id"]
    shots = []
    for s_ in video["script"]:
        src = shot_source(s_["shot"], video, group, order, cand_dir)
        shots.append((seconds(s_["t"]), src, nine16(src.width, src.height)))
    texts = [(seconds(t["t"]), text_layer(t["text"])) for t in video["on_screen"]]
    total = max(b_ for (_, b_), _, _ in shots)
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                             "-preset", "medium", "-crf", "20", "-movflags", "+faststart", str(out)],
                            stdin=subprocess.PIPE)

    def render(idx, t):
        (a_, b_), src, (x, y, w, h) = shots[idx]
        z = 1 - 0.06 * ease(min(max((t - a_) / max(b_ - a_, 0.01), 0), 1))   # slow push-in
        cw, ch = w * z, h * z
        cx, cy = x + (w - cw) / 2, y + (h - ch) * 0.35
        return src.crop((round(cx), round(cy), round(cx + cw), round(cy + ch))).resize((W, H), Image.LANCZOS)

    FADE = 0.35
    for f in range(int(total * FPS)):
        t = f / FPS
        idx = next((i for i, ((a_, b_), _, _) in enumerate(shots) if a_ <= t < b_), len(shots) - 1)
        frame = render(idx, t)
        a_ = shots[idx][0][0]
        if idx and t - a_ < FADE:
            frame = Image.blend(render(idx - 1, t), frame, ease((t - a_) / FADE))
        frame = frame.convert("RGBA")
        layer = next((lay for (ta, tb), lay in texts if ta <= t < tb), None)
        if layer is not None:
            frame.alpha_composite(layer)
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"Rendered {out} ({total:.0f}s)")


if __name__ == "__main__":
    main()
