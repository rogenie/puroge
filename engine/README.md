# The Purogé content engine

One run per week (Wednesday) produces 14 posts: two a day, Thursday through Wednesday.
Each step below is done by an LLM, following the files in this folder. A human approves the batch once, before anything is posted.

| Step | Reads | Writes |
|---|---|---|
| 1. Plan | `formats.json`, `data/site.json` (taxonomy), last week's results | 14 briefs in `runs/<date>/plan.json` |
| 2. Scout | `scouting.md` | one look file per look in `data/looks/` with `"draft": true` |
| 3. Stylist check | `brand.md` | rejects or swaps pieces that clash or read as boring |
| 4. Write | `brand.md`, `formats.json` | `runs/<date>/<video>.json`: hook, script, on-screen text, caption |
| 5. Dress the models | `models.json`, product photos (`ref_image` on each piece) | `engine/generate.py` via the "Content engine" workflow: image candidates in `images/candidates/` |
| 6. Quality check | product photos vs generated images | pass/fail notes in the video file |
| 7. Human review | everything above | approve or reject each video |
| 8. Publish | approved videos | `engine/approve.py` sets the chosen images, `engine/render.py` makes the vertical video, looks go live, posts are queued |
| 9. Learn | views, saves, clicks | notes feeding next week's plan |

## Weekly mix (14 posts)

- 5 × **one color, three partners** (`three-partners`)
- 5 × **color swap** (`color-swap`)
- 4 × **Heirloom vs Everyday** (`two-tiers`)

The planner keeps the site balanced: across a month, every occasion, piece type and season should get looks.

## Rules that never change

- Every piece in a video is real, in stock when checked, and linked on puroge.com.
- Every video carries the platform's AI-generated label and says the clothes are real.
- Every video ends with the numbered pieces and the short link, shown and spoken.
- The short link must open the exact look or series shown in the video.

## Lean production (about $3 to $10 a week)

- One image call per video with all product photos as references (fal.ai, Nano Banana edit, about $0.04 per image), plus one full-length image per look for the site and the video close-ups. About $0.20 per three-look video.
- `engine/render.py` turns the images into a silent 1080x1920 video for free: slow push-ins, crossfades, on-screen text from the video file.
- Voiceover (TikTok or CapCut text-to-speech, reading the script) and a trending sound are added in the app when posting.
- Only proven winners get paid AI video later.

## Running a video by hand

1. Actions → "Content engine" → Run workflow → step `generate`, video file path. Needs the `FAL_KEY` repository secret.
2. Quality check the candidates in `images/candidates/<video id>/` against the product photos.
3. `python3 engine/approve.py <video id> --group group-1.jpg --looks`, then push (the site updates).
4. Actions → "Content engine" → step `render`; download the video from the run's artifacts.
