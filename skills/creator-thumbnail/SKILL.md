---
name: creator-thumbnail
description: >-
  Design high-click YouTube thumbnails and vertical covers (Shorts, Reels, TikTok) with
  whatever image provider the user has, compositing headline text locally so it is always
  crisp. Plans the concept, generates 2–3 variants, keeps faces and logos faithful via
  reference images, and checks readability at small size. Use when the user asks for a
  YouTube thumbnail, video thumbnail, Shorts/Reels cover, podcast episode cover, or
  "make my thumbnail pop". Not for general images (creator-image) or channel branding
  (creator-brandkit).
license: MIT
compatibility: Python 3.9+ and ffmpeg. Needs at least one image provider.
allowed-tools: Bash Read Write
metadata:
  version: "0.1.0"
  argument-hint: "<video title/topic> [--face photo] [--text 'HEADLINE'] [--vertical]"
---

# Creator Thumbnail

## Step 1 — Concept (before generating anything)

From the title/topic, write **one** concept in three lines and confirm only if the user
seems to care about direction; otherwise proceed:

- **Promise** — the single idea the viewer must get in 1 second (truthful to the video).
- **Focal subject** — one face/object, big, high contrast. Faces: strong, honest emotion.
- **Headline** — 0–4 words that *add* to the title, never repeat it. Optional.

Rules in `references/thumbnail-rules.md` (composition, contrast, text, honesty).

## Step 2 — Generate the art (no text)

- Ratio `16:9` (YouTube) or `9:16` (vertical cover). Size `2k` if a provider allows it.
- Reserve space for the headline: `generous empty space on the left third for a headline`.
- User's face/logo/product → pass photos with `--ref` and say what each is for.
- Ask for **no text** in the image; the headline goes on in Step 3.

```bash
python3 scripts/creator.py image --prompt "<art prompt>" --ratio 16:9 --size 2k --out ./out/thumb-a.png [--ref face.jpg]
```

Make 2–3 variants that differ in **one** big way (emotion, color, or composition), not tiny
tweaks. Pin the provider after the first success.

## Step 3 — Headline

```bash
python3 scripts/media.py text --image ./out/thumb-a.png --out ./out/thumb-a-final.png --text "TWO\nLINES" --pos center --align left --size 0.16 [--box "black@0.55"] [--font <brand heading font>]
```

Put the text in the space reserved in Step 2 (`--align left` for left-third space) and
never over the face/subject. Use the brand font/colors from config `brand` if present.
Max ~4 words; break into two short lines with `\n` when it's wide.

## Step 4 — Check

1. Downscale preview: `ffmpeg -y -i final.png -vf scale=320:-1 small.png`, then look at it —
   subject and words must read at that size.
2. Check the bottom-right corner (YouTube's timestamp covers it) is free of key content.
3. Present variants side by side with one line each on what differs; recommend one.

## Rules

- Truthful: no fake quotes, fake screenshots, or implied events that aren't in the video.
- Don't put real people who aren't the user into the thumbnail without their consent.
- 1280×720 minimum for YouTube; under 2 MB (`ffmpeg -i in.png -q:v 3 out.jpg` if needed).

## References

- `references/thumbnail-rules.md` — composition, text, color, examples
- `references/image-prompting.md`, `references/media-ops.md`, `references/providers.md`
