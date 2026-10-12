# Purogé site

1. Each look is one file in `data/looks/`, named after its address (`navy-and-brown.json` lives at puroge.com/navy-and-brown). Copy an existing look to start a new one.
   Tags (occasion, colors, season) must come from the lists in `data/site.json`; the build stops and says why if one does not.
2. Looks marked `"draft": true` stay hidden. Remove that line to publish a look.
3. Push to `main`. GitHub Actions builds the site and publishes it to puroge.com in about a minute.

Preview locally with `python3 build.py --drafts`, then open `site/index.html`.

Links to use in posts and DMs:
- Whole outfit: `puroge.com/look/001`
- One piece: `puroge.com/go/001-3-h` (piece 3, Heirloom) or `puroge.com/go/001-3-e` (piece 3, Everyday)

When a piece sells out, set `"sold_out": true` or paste a replacement `url`, update `last_checked`, rebuild. Every video and DM link keeps working.

Put affiliate links (Amazon, Walmart, Target, ShopMy) in the `url` fields. Add the AI image path in `image`.
