---
name: creator-product-photo
description: >-
  Brand-quality product imagery from a product photo or description, using whatever image
  provider the user has: studio packshots, lifestyle scenes, hands-in-frame close-ups,
  Pinterest pins, hero banners, social carousels, ad packs, virtual try-on, conceptual/CGI
  shots, restyles, and marketplace listing sets (Amazon/Etsy/Shopify main image, secondary
  images, A+ style modules). Use when the user wants product photos, packshots, e-commerce
  or marketplace images, listing images, product ads, or "put my product in a scene".
  Not for logos or brand systems (creator-brandkit) or video ads (creator-ad).
license: MIT
compatibility: Python 3.9+ and ffmpeg. Best with a provider that accepts reference images.
allowed-tools: Bash Read Write
metadata:
  version: "0.3.0"
  argument-hint: "<mode> <product photo or description> [--count n] [--ratio r]"
---

# Creator Product Photo

## Step 1 — Inputs

- **Product reference** — strongly preferred: 1–3 clean photos (front, angle, detail).
  Without one, the product will be *invented*; say so and get approval for that.
- **Mode** — infer from the request using `references/modes.md`; ask only if two modes fit
  equally.
- **Brand** — read config `brand` (colors, logo) if present.
- **Count & ratio** — mode defaults in `references/modes.md`.

Check the route supports references: `python3 scripts/creator.py plan --task image --needs refs`.
If nothing supports references, say the product's exact look can't be preserved and offer
(a) description-only concept shots, or (b) adding a key / enabling Flow or the Gemini app.

## Step 2 — Prompt

Build from the mode template in `references/modes.md`:

`Use image 1 as the exact product — keep its shape, colors, label, and proportions
unchanged.` + scene + lighting + camera + composition + constraints.

Never let the model rewrite label text or logos; if the label must be legible, say
`keep the label exactly as in image 1`.

## Step 3 — Generate

```bash
python3 scripts/creator.py image --prompt "<prompt>" --ref product.jpg --ratio <r> --size 2k --out ./out/<mode>-01.png
```

For sets (carousel, ad pack, marketplace set) generate the hero first, get approval, then
the rest with the *same* style sentence and pinned `--provider`.

Marketplace main image needs a pure white background: generate on white, then if the
background isn't clean, `media.py cutout` and composite onto white
(`ffmpeg -i cut.png -filter_complex "color=white:s=2000x2000[bg];[bg][0]overlay=(W-w)/2:(H-h)/2" -frames:v 1 main.jpg`).

## Step 4 — QA every image

Compare with the reference: shape, color, label, logo, proportions, and count of parts.
Reject and regenerate on any product drift; that's the #1 failure. Then report the set.

## Rules

- Don't fabricate certifications, awards, claims, or reviews in images or copy.
- Marketplace rules (white background, no added text/badges on main image) are in
  `references/modes.md`; follow them for listing images.

## References

- `references/modes.md` — every mode: ratio, count, prompt template, rules
- `references/image-prompting.md`, `references/media-ops.md`, `references/providers.md`
