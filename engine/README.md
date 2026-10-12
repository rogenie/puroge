# The Purogé content engine

One run per week (Wednesday) produces 14 posts: two a day, Thursday through Wednesday.
Each step below is done by an LLM, following the files in this folder. A human approves the batch once, before anything is posted.

| Step | Reads | Writes |
|---|---|---|
| 1. Plan | `formats.json`, `data/site.json` (taxonomy), last week's results | 14 briefs in `runs/<date>/plan.json` |
| 2. Scout | `scouting.md` | one look file per look in `data/looks/` with `"draft": true` |
| 3. Stylist check | `brand.md` | rejects or swaps pieces that clash or read as boring |
| 4. Write | `brand.md`, `formats.json` | `runs/<date>/<video>.json`: hook, script, on-screen text, caption |
| 5. Dress the models | `brand.md` (set, models, prompt template) | images and clips per video |
| 6. Quality check | product photos vs generated images | pass/fail notes in the video file |
| 7. Human review | everything above | approve or reject each video |
| 8. Publish | approved videos | removes `"draft"` from looks, pushes the site, queues posts |
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
