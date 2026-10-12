# Scouting rules

## For every piece, both tiers

- **Heirloom:** the best-made option that fits the look. **Natural fibers required** (wool, cashmere, linen, cotton, silk, leather, at least 90%).
- **Everyday:** the same look at a gentler price. Prefer Amazon (earns commission through the store ID automatically). **Prefer at least 50% natural fiber**; a mostly synthetic piece is allowed only when nothing natural fits the look, and the run notes must say so.
- Both tiers should match in color and silhouette closely enough that the video makes sense for either.

## Check on the product page itself, never from search results alone

- Exact product name and the color name you are linking
- Material composition as listed, word for word, always shown on the site (sustainability is a core value: see the fiber rules above)
- Price (if it varies by size, record "from $X")
- In stock in the chosen color
- Rating and review count: avoid under 3.8 stars, and prefer 100+ reviews for Everyday
- For Amazon, the ASIN **of the exact color variant**; link as `https://www.amazon.com/dp/<ASIN>` (the build adds the store ID). Parent ASINs open on Amazon's default color, which may not be the one in the look.
- The main product photo URL as `ref_image` (from the product page's main image, highest resolution). The image model dresses the models from these, so they must show the right color.

## When the ideal piece doesn't exist

Take the closest real match and say so in the run notes, e.g. "Quince's silk skirt comes in Paprika Red, not true red."
Never invent or substitute a product that wasn't opened and checked.

## Reuse on purpose

Reusing a piece across looks is good: it shows fewer pieces making more outfits. The `three-partners` format depends on it.

## How to read Amazon

Amazon blocks automated page reads. Use the browser pane on Rogenie's computer (amazon.com is approved there) and read search results and product pages with the page's own fetch. If the computer is offline, scout non-Amazon stores only and flag the gap.

## Record

Each look is a file `data/looks/<slug>.json`. Each piece needs `types` from the taxonomy in `data/site.json`; add a new type there first if needed. Set `"draft": true` until the human review approves it.

## Re-check stock right before generating images

Colors disappear (Quince dropped "Paprika Red" between scouting and image generation on the first run). Re-open every product page in the chosen color before step 5, and replace anything gone.
