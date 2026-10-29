---
name: creator-character
description: >-
  Keep a person, mascot, or character consistent across many images and videos with
  whatever providers the user has. Builds a reusable character pack (reference sheet,
  anchor description, approved reference images) and reuses it in every generation; uses a
  Higgsfield Soul ID when available. Use when the user wants the same face or character in
  multiple images, a recurring mascot, a consistent AI influencer or presenter, "use my
  face", a character sheet, or a story with recurring characters. Not for one-off images
  (creator-image).
license: MIT
compatibility: Python 3.9+. Needs a provider that accepts reference images (Higgsfield, Google, OpenAI, Codex, or browser).
allowed-tools: Bash Read Write
metadata:
  version: "0.2.0"
  argument-hint: "create|use <name> [photos...]"
---

# Creator Character

A **character pack** lives in `characters/<name>/`:

```
characters/<name>/
  character.json     # anchor sentence, provider used, soul_id (optional), consent note
  refs/              # 3–6 approved reference images (the source of truth)
  sheet.png          # turnaround / expression sheet
```

## Create

1. **Source**
   - Real person: 5–15 clear photos (front, 3/4, profile; varied light; no sunglasses or
     heavy filters). **Only the user themself, or someone who has consented.** Record this
     in `character.json` → `"consent": "self" | "<who confirmed>"`.
   - Invented character: a short description; first generate 3–4 candidates with
     `creator.py image` and let the user choose one.
2. **Anchor sentence** — 25–40 words fixing what must not drift: age range, face shape,
   eye color, hair style/color, skin tone, distinguishing marks, signature outfit/colors.
3. **Higgsfield available?** (`creator.py detect`) → offer to train a Soul ID
   (`higgsfield soul-id create …`, see their CLI help) and store the returned id as
   `soul_id`. Otherwise the reference-image method below works everywhere refs are supported.
4. **Reference sheet** — generate with the best ref-capable provider:
   ```bash
   python3 scripts/creator.py image --prompt "Character reference sheet of <anchor>: front, 3/4, profile, back views and 4 expressions, neutral grey background, consistent lighting, no text" --ref refs/01.jpg --ratio 16:9 --size 2k --out characters/<name>/sheet.png
   ```
5. Approve 3–6 best images into `refs/`. Save the pinned provider in `character.json`.

## Use

For every image/video with the character:

- Prompt = `Same person as the reference images: <anchor sentence>.` + the scene.
- Pass 2–3 refs (`--ref` repeatable; most-similar angle first) and pin the pack's provider.
- Video: make the first frame as an image with the character, then `creator.py video --start`.
- After each output, compare face/outfit against `refs/`; regenerate on drift. Add new
  approved outputs to `refs/` only if they're clearly on-model.

## Rules

- Never create packs of real people without consent, and never for impersonation,
  deception, or sexual content.
- `agy` can't take references; it's unsuitable for consistency work (the router skips it
  when `--ref` is passed).

## References

- `references/image-prompting.md` — reference usage
- `references/video-prompting.md` — start frames
- `references/providers.md` — which providers accept references
