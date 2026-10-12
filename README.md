# Purogé site

1. Each look is one file in `data/looks/`, named after its address (`navy-and-brown.json` lives at puroge.com/navy-and-brown). Copy an existing look to start a new one.
   Every look is tagged three ways, matching the three ways into the site:
   - `tags.occasion` → /occasion/<x> ("Where are you going?")
   - each piece's `types` → /style/<piece> ("Style a piece you own")
   - `tags.pairing` → /colors/<pair> ("Colors that work")
   plus `tags.mood` and `tags.season` as filters. All values must come from the lists in `data/site.json`;
   the build stops and says which one is wrong if not. Add new occasions, pieces or pairings there first.
   A piece can carry an optional `"fit"` note (e.g. "runs small, size up") on either tier.
2. Looks marked `"draft": true` stay hidden. Remove that line to publish a look.
3. Push to `main`. GitHub Actions builds the site and publishes it to puroge.com in about a minute.

Preview locally with `python3 build.py --drafts`, then open `site/index.html`.

Links to use in posts and DMs:
- Whole outfit: `puroge.com/navy-and-brown` (short link, say it or show it in the video)
- Bio link: `puroge.com/latest` (newest looks first)
- One piece: `puroge.com/go/navy-and-brown-3-h` (piece 3, Heirloom) or `...-3-e` (Everyday)

When a piece sells out, set `"sold_out": true` or paste a replacement `url`, update `last_checked`, rebuild. Every video and DM link keeps working.

Put affiliate links (Amazon, Walmart, Target, ShopMy) in the `url` fields. Add the AI image path in `image`.
