---
name: creator-ad
description: >-
  Make short-form video ads and UGC-style ads for a product or app with whatever providers
  the user has: hook-first script, presenter or product shots, voiceover, captions, music,
  and placement-ready exports (9:16, 1:1, 16:9). Uses Higgsfield Marketing Studio when
  available, otherwise builds the ad from generated clips or animated stills plus voiceover.
  Use when the user asks for a video ad, UGC ad, TikTok/Reels/Shorts ad, product promo,
  unboxing, testimonial-style, before/after, or ad variations/hooks to test. Not for
  static product photos (creator-product-photo) or long explainers (creator-explainer).
license: MIT
compatibility: Python 3.9+ and ffmpeg. Better with video and speech providers; works with images only.
allowed-tools: Bash Read Write
metadata:
  version: "0.2.0"
  argument-hint: "<product + angle> [--hooks 3] [--length 15s] [--placements 9:16,1:1]"
---

# Creator Ad

Project folder: `ads/<product-slug>/`.

## Step 1 — Brief

Collect (ask once, together, only what's missing): product (photos or URL content the
user pastes), audience, single key benefit, offer/CTA, length (default 15 s), placements
(default 9:16). Read config `brand`.

## Step 2 — Script variants

Write 3 hooks × 1 body using `references/ad-formats.md` (formats: problem→solution,
UGC testimonial, unboxing, before/after, 3 reasons, demo). Each script: hook (0–3 s), body,
proof, CTA, ≤ 40 words for 15 s. Show them; user picks or approves all.

## Step 3 — Route

```bash
python3 scripts/creator.py detect
```

| Available | Build |
|---|---|
| Higgsfield signed in | Marketing Studio: `higgsfield generate create marketing_studio_video --prompt … --mode ugc --aspect_ratio 9:16 --duration 15 --wait` (product import / avatars via `higgsfield marketing-studio --help`). Captions/CTA end card added locally |
| Video provider | Per beat: product-locked still (`creator.py image --ref product.jpg`) → `creator.py video --start` |
| Image provider only | Per beat: product-locked stills → Ken Burns via `media.py assemble` |

Voiceover per beat with `creator.py speech` (pinned voice, energetic but natural style;
`--lang` for the market's language — Arabic dialect ads: `references/arabic-voice.md`;
add tashkeel to meaning-changing words before any TTS, or `speech` stops with `needs_tashkeel`).
Presenter faces: use creator-character packs only for the user or consenting people.

## Step 4 — Assemble each variant

1. `scenes.json` per variant (hook scene differs, body shared), then
   `media.py assemble --ratio 9:16 --music music/bed.mp3`.
2. Captions: big, centered-lower, ≤ 5 words per line → `media.py captions`.
3. End card: product hero still + CTA via `media.py text`, 1.5–2 s scene.
4. Other placements: `media.py reframe --ratio 1:1|16:9 --mode blur` and re-check that
   product and captions stay in frame.

## Step 5 — QA and deliver

- Hook visible and audible in the first 1–2 s; product appears by 3 s; CTA on screen ≥ 1.5 s.
- Captions inside safe zones (avoid top 12% and bottom 20% on 9:16 for platform UI).
- Product matches the reference in every shot.
- Deliver files per variant/placement with one line on what each tests.

## Rules

- No fake testimonials presented as real customers, no invented stats, prices, or claims;
  label AI presenters if the platform or law requires it.
- No real people's likeness without consent; no competitor trademarks in visuals.

## References

- `references/ad-formats.md` — formats, hook bank, timing
- `references/audio.md`, `references/video-prompting.md`, `references/media-ops.md`,
  `references/providers.md`
