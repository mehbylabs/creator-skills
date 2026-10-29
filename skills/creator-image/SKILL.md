---
name: creator-image
description: >-
  Generate or edit images with whatever the user has — Higgsfield CLI, Google Gemini API
  (Nano Banana), OpenAI API (gpt-image), Antigravity CLI (agy), Codex CLI, or the Gemini web
  app / Google Flow via computer use — with automatic fallback. Use when the user asks to
  generate, create, draw, or edit an image, illustration, hero image, banner art, poster,
  wallpaper, icon art, sticker, transparent PNG, or to restyle or edit a photo with a
  reference. Not for thumbnails with headline text (creator-thumbnail), product shots
  (creator-product-photo), consistent characters (creator-character), video, or setup.
license: MIT
compatibility: Python 3.9+; ffmpeg recommended. Needs at least one image provider (see creator-setup).
allowed-tools: Bash Read
metadata:
  version: "0.2.0"
  argument-hint: "<prompt> [--ratio 16:9] [--size 1k|2k|4k] [--ref img] [--transparent] [--provider id]"
---

# Creator Image

## Step 1 — Shape the request

Decide from the message; ask at most one question if something essential is missing.

- **Prompt** — rewrite with `references/image-prompting.md` (medium, subject, composition,
  light, palette, constraints). Keep the user's intent.
- **Ratio** — banner/hero/YouTube `16:9`; Story/Reel/Short/phone `9:16`; Instagram feed
  `4:5`; Pinterest `2:3`; otherwise `1:1`.
- **Size** — `1k` default; `2k`/`4k` only when asked or for print/hero.
- **References** — attached or named images → `--ref` (repeatable).
- **Transparency** — logos, stickers, cutouts → `--transparent`.
- **Output** — the user's path, else `./out/<slug>.png`.
- **Provider** — `--provider` only when the user names one ("use agy", "with codex").

## Step 2 — Generate

```bash
python3 scripts/creator.py image --prompt "<prompt>" --out <path> --ratio <r> [--size 2k] [--ref a.png] [--transparent] [--provider <id>]
```

Agent-CLI routes take 30–120 s; run in the background if your harness supports it.

## Step 3 — Act on the JSON result

| `status` | Do |
|---|---|
| `ok` | View the image and check it against the brief. Report path + provider in one line |
| `ok` + `"post": "remove_background"` | No provider could do alpha; run `python3 scripts/media.py cutout --image <path> --out <path>` and say so |
| `needs_browser` | Follow `references/browser-<next[0]>.md` using `request`; finish with `creator.py adopt` |
| `blocked` | Content refused. Don't retry elsewhere; explain and offer a revised prompt |
| `failed` | One line per attempt (provider → reason) and the single most useful fix from `connect` — a command the user runs in their own terminal (`references/connect.md`) |

If the extension changed (e.g. `.png` → `.jpg` without ffmpeg), mention it.

## Step 4 — Iterate

Change one thing per round. Pin the provider that made the accepted image
(`--provider <id>`) so the look stays stable. To edit the last output, pass it as `--ref`
and describe only the change.

## Rules

- Be brief: no JSON, no command narration, no model ids unless asked.
- Never ask for API keys in chat.
- Text inside images: only short, quoted text, and only on providers good at it; otherwise
  generate clean art and add type with `media.py text`.

## References

- `references/image-prompting.md` — prompt structure, text, references
- `references/providers.md` — matrix, order, fallback, exit codes
- `references/media-ops.md` — cutout, text overlay, reframe
- `references/browser-gemini-browser.md`, `references/browser-flow-browser.md` — manual routes
