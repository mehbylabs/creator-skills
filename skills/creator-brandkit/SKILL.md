---
name: creator-brandkit
description: >-
  Create or extend a visual identity with whatever providers the user has: brand brief,
  color palette, type pairing, logo concepts (vector SVG authored directly, plus generated
  explorations), and applied mockups (social posts, profile images, banners, merch,
  packaging), saved as a reusable brand kit that other creator skills read. Use when the
  user asks for a logo, brand identity, brand kit, color palette, style guide, channel
  branding, or consistent branded social templates. Not for single product photos
  (creator-product-photo) or thumbnails (creator-thumbnail).
license: MIT
compatibility: Python 3.9+ and ffmpeg. Image provider optional (logo SVGs are authored directly).
allowed-tools: Bash Read Write
metadata:
  version: "0.1.0"
  argument-hint: "<brand name + what it does> [--vibe 'calm, premium'] [--extend existing assets]"
---

# Creator Brandkit

Output folder `brand/<slug>/`:

```
brand.json          # name, positioning, colors, fonts, logo paths, voice — read by other skills
palette.svg         # swatches with hex values
logo/               # mark.svg, wordmark.svg, lockup.svg (+ PNG exports)
mockups/            # applied examples
guide.md            # one-page usage guide
```

## Step 1 — Brief

Name, what it does, audience, 3 personality words, competitors to avoid looking like,
existing assets to keep. Ask once for what's missing.

## Step 2 — Direction (approve before building)

Offer **2 directions**, each: one-line concept, 5-color palette (hex, with roles: primary,
secondary, accent, neutral dark, neutral light), type pairing (Google Fonts names), logo idea.
Use `references/brand-foundations.md` for palette contrast and type rules.

## Step 3 — Logo

1. **Author SVGs directly** (always possible, editable, scalable): geometric mark,
   wordmark (text converted only if the user supplies the font; else use a web-safe stack
   and note it), lockup. Keep marks simple: works at 16 px and in one color.
2. **Optional explorations** with an image provider for inspiration only:
   `creator.py image --prompt "flat vector logo exploration for <name>: <idea>, <palette>, white background, no mockup" --ratio 1:1`.
   Generated rasters are references, not deliverables; redraw the chosen idea as SVG.
3. Export PNGs: `ffmpeg -i logo/mark.svg -vf scale=1024:-1 logo/mark-1024.png` (if ffmpeg
   lacks SVG support, use `rsvg-convert` or a browser screenshot).

## Step 4 — Mockups

Use creator-image / `creator.py image` with the logo PNG as `--ref` and palette in words:
profile picture, social post template, YouTube banner (2560×1440, safe area 1546×423),
business card, tote/tee, packaging — only those the user needs. Add exact text with
`media.py text`, not in-image generation.

## Step 5 — Save the kit

Write `brand.json` and offer to copy colors/fonts/logo into the creator-skills config
`brand` block so thumbnails, ads, and product shots use them automatically. Write `guide.md`:
palette with roles and contrast notes, type scale, logo clear space and minimum size,
do/don't examples.

## Rules

- Run a quick originality check: avoid marks that resemble well-known logos; tell the user
  to do a trademark search before commercial use.
- Text contrast: body text ≥ 4.5:1 against its background (WCAG AA).

## References

- `references/brand-foundations.md` — palette roles, contrast, type pairing, logo rules
- `references/image-prompting.md`, `references/media-ops.md`, `references/providers.md`
