# Brand rules for every video

## Voice

Warm, exacting, a little dry. Someone raised around a sewing machine who can't help checking the hem.

- Teach a reason, not a vibe. Not "burgundy and red is striking" alone, but why: two reds of different depth create tension the eye enjoys.
- One idea per line, readable in two seconds on screen.
- Name the material of every piece in captions and on the site.
- Never shame what people already own. Never say "look rich" or "classy vs. trashy."
- "Lola" may appear naturally. Nothing should need a translation to follow.

## The set: Rogenie's future home in Del Mar

Every image uses the same room so the feed is recognizable before anyone reads a word. The exact wording lives in `models.json` ("set"):

> A sunlit beachfront living room in Del Mar: floor-to-ceiling glass onto the Pacific and palms, cream marble floors with soft gold veining, a deep cream sectional with linen pillows, a marble block coffee table with white hydrangeas and coral, an olive tree in a stone planter, slatted oak columns, a jute rug. Natural materials only, no television.

## The models

Two people in every image, side by side, each wearing one tier of the same look:

| Side | Who | Height label | Default tier |
|---|---|---|---|
| Left | A recurring AI model (T) | 5'9" | Heirloom |
| Right | Rogenie (R), from her reference photos | 4'6" | Everyday |

Heights are shown on screen as labels only, never written into image prompts: the image model turns "4'6\"" into a child. Prompts describe both as grown adult women and give relative height in words. Any image where Rogenie reads as a child fails quality check.
Rogenie's reference photos stay private (never in the public repository). The tall model gets a reference sheet so her face stays the same every week.

## Image prompt template

```
Full-length fashion photo, vertical 9:16. {models_and_positions}.
{for each model: "<position> model wears <piece 1>, <piece 2>, <piece 3>" with exact colors and fabrics}.
Setting: {the atelier}. Natural standing poses, hands relaxed, faces toward camera.
Photorealistic, true-to-life fabric texture, no text, no logos, no extra accessories beyond those listed.
```

Generate with the product photos as garment references (virtual try-on), one model at a time, then composite.

## Labels

- TikTok and Instagram: turn on the AI-generated content label for every post.
- Caption line, always: "Models are AI. Every piece is real and linked."
