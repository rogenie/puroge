# Image and video playbook

Lessons from Mark Tilbury's "AI Influencer Cheat Sheet" (made with Higgsfield's in-house creatives), adapted to Purogé. Every generation prompt in the engine follows these rules.

## 1. Lock each person with a character sheet

- Each person (T, P, and later Rogenie's twin) gets **one character sheet**: three panels on a plain grey backdrop.
  - Full body
  - 90° side profile, medium bust
  - Front medium bust
- Generate a few, pick one, **never regenerate it**. The sheet is `engine/people-ai/<X>-sheet.jpg`.
- Attach the sheet as **image 1** in every generation, before anything else.
- Each person has **2–3 signature anchors**: small fixed details such as a mole, freckles or one specific earring. Write them **word for word, identically**, in every prompt. Anchor wording lives in `engine/models.json`.

## 2. Build the world once

- Make one **empty location still** per set, with no people: `engine/sets/del-mar-living.jpg`.
- Attach it as the **scene reference** in every image, so the room is the same in every video.
- No readable text, no brands, and lived-in rather than staged.

## 3. How to write a prompt

1. **Important things first.** Long prompts get their ends cut off silently, so keep them under about 3,500 characters. The first paragraph says:
   - age
   - "fully clothed"
   - the anchors
   - the outfit
2. **Force the age** in plain words: "clearly an adult woman in her thirties, NOT a teenager, NOT a child". This also fixes the problem of a petite woman being drawn as a child.
3. **Describe states positively.** "Bare face with eyes fully visible" works; "sunglasses off" gets ignored.
4. **Count jewellery.** For example, "exactly one pair of small gold stud earrings, no other jewellery".
5. **Describe texture, not quality adjectives.** Use phrases like "visible pores, fine peach fuzz, matte unretouched skin, no airbrushing". Never write "porcelain skin" or "8K perfection".
6. **Say strong features three times:** in the opener, in each panel, and in the character section.
7. **Include a modest block:** opaque fabric, torso covered, no revealing styling.
8. **Include a no-IP block:** no logos, no readable text, no real-person likeness.

## 4. Relight: no pasted-in stickers

A sheet shot on a grey backdrop gets pasted into a room like a sticker unless the prompt says otherwise. Every scene prompt carries a relight line:
- Discard the sheet's lighting.
- Name the key light and its direction.
- Name the fill.
- Name one colour bounce off a real surface in the room.
- Ask for real contact shadows.
- End with: never brighter than the room.

For Del Mar, that means:
- Key: late sun through the ocean glass, from camera left.
- Fill: warm bounce off the cream marble floor.
- A soft shadow from her feet on the jute rug.

## 5. Alive, not catalogue

- **Lookbook poses, never passport poses:**
  - weight on one leg
  - a hand in a pocket or resting on a cuff
  - a calm gaze with the faintest warmth at the corners of the lips
- A stiff "face camera, arms down" pose reads as AI.
- **Camera:** handheld or propped phone, slightly imperfect framing. Never "tripod".
- **Text-safe frame:** keep the upper third calm, because our captions go there.

## 6. Video (Higgsfield / image-to-video)

Silent text-over b-roll is our format, since text and voice get added in post. Each clip:
- One small action with a start and an end, for example adjusting a cuff then looking up.
- 8–12 seconds, looping, where the last pose roughly matches the first.
- Every prop is in frame from the first frame.
- Other people stay at the edges, blurred.
- No dialogue, only ambient sound.
- If the light must not change, say "the lighting state is constant, not a time-lapse".

Prompt order:
1. TOP PRIORITY
2. REFERENCE KEY (@image1 sheet, @image2 room)
3. RELIGHT
4. IMAGE QUALITY
5. Camera
6. Performance
7. Physics
8. Composition
9. Consistency
10. Audio
11. Timed SHOT BREAKDOWN

## 7. Scripts and hooks

- **Hooks:** write three and keep the best. Put the surprising or specific word first. The hook must read in one second as on-screen text, because most people watch muted.
- **Hold:** every video needs a reason to watch to the end, such as a countdown or a payoff in the last line.
- **Length:** 15–30 seconds, 40–90 words.
- **Sound spoken, not written:**
  - Avoid tidy rule-of-three lists.
  - Don't sum things up with thesis sentences.
  - Include one uselessly specific detail.
  - Keep the rhythm uneven.
- **Series formats grow accounts.** Ours are the three formats in `formats.json`.

## 8. Launch rules

- **Say it's AI:** in the bio, with the platform's AI-creator toggle, and in every caption ("Models are AI. Every piece is real and linked.").
- Post about 10 videos on day one, so a new viewer has more to watch. Then post on schedule.
- Judge results by saves, shares and comments, not followers. Give it about 5 days before deciding.

## 9. Higgsfield specifics (for when the account is ready)

- **Soul 2.0:** character sheets and photos.
- **Soul Cinema:** a tight face portrait as the identity anchor.
- **Cinema Studio:** video at 9:16, 1080p, max 30 seconds per generation.
- **Voice:** one locked voice per character. Give it four things: accent, age, register and energy, plus anti-drift words such as "not posh" or "never frail". Generate it once and reuse the file.
- The connector `https://mcp.higgsfield.ai/mcp` lets Claude send prompts directly, and it uses credits.
