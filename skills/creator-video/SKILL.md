---
name: creator-video
description: >-
  Generate short video clips with whatever the user has — Higgsfield CLI (Seedance, Kling,
  Veo), Google Gemini API (Gemini Omni Flash), Google Flow or the Gemini web app via computer
  use — and fall back to animated stills (Ken Burns) when no video provider exists. Covers
  text-to-video, image-to-video, first/last-frame transitions, reference-guided clips,
  reframing to 9:16/16:9, and burned captions. Use when the user asks to make a video or
  clip, animate an image, image-to-video, B-roll, a Reel/Short/TikTok clip, a transition,
  or to reframe or caption a clip. Not for narrated multi-scene explainers
  (creator-explainer) or ads (creator-ad).
license: MIT
compatibility: Python 3.9+ and ffmpeg. Video providers optional; stills fallback needs an image provider.
allowed-tools: Bash Read
metadata:
  version: "0.3.0"
  argument-hint: "<prompt> [--start img] [--end img] [--ratio 16:9|9:16] [--duration 8]"
---

# Creator Video

## Step 1 — Plan the clip

- **What moves** — one subject, one action, one camera move per clip
  (`references/video-prompting.md`).
- **Ratio** — Shorts/Reels/TikTok `9:16`, everything else `16:9`.
- **Duration** — default 8 s; longer stories become several clips joined later.
- **Start frame?** — if the look matters (brand, character, product), make the first frame
  as an image first (creator-image or `creator.py image`), approve it, then animate it with
  `--start`. This is the most reliable way to control the result on every provider.
- **End frame / references** — `--end` for transitions and reveals, `--ref` for identity.
- **Resolution** — `720p` default; `1080p` when asked.

## Step 2 — Generate

```bash
python3 scripts/creator.py video --prompt "<motion prompt>" --out ./out/<slug>.mp4 --ratio 16:9 --duration 8 [--start first.png] [--end last.png] [--ref ref.png] [--resolution 1080p]
```

Video takes 1–10 minutes. Run it in the background when possible and don't start a second
generation meanwhile.

## Step 3 — Handle the result

| `status` | Do |
|---|---|
| `ok` | `python3 scripts/media.py probe <path>`; extract a frame and look at it; report path, length, provider |
| `needs_browser` | Follow `references/browser-flow-browser.md` (or gemini) with the `request` fields; then `creator.py adopt --src <download> --out <path>` |
| `blocked` | Content refused; revise with the user, don't route around it |
| `failed` and no video provider at all | Use the stills fallback below and tell the user which provider would unlock real motion |

### Stills fallback (always available)

1. Make 1–3 stills with `creator.py image` in the target ratio.
2. `python3 scripts/media.py still --image s1.png --out clip.mp4 --duration 6 --ratio 16:9 --motion in`
   (vary `--motion` per still; join several with `media.py assemble`).

## Step 4 — Finish (optional)

- Reframe: `media.py reframe --video clip.mp4 --out clip-9x16.mp4 --ratio 9:16 --mode blur`
  (`crop` when the subject is centered).
- Captions: write an `.srt`, then `media.py captions --video clip.mp4 --srt subs.srt --out final.mp4`.
- Sound: `creator.py sfx` / `music` and mix with `media.py assemble` (single scene).

## Rules

- Verify on disk (duration > 0, expected ratio) before reporting success.
- Mention when a route spends credits per clip (Flow, Higgsfield) if the user asks for many.
- Keep one "look sentence" across clips of the same project.

## References

- `references/video-prompting.md` — shot formula, frames, references
- `references/providers.md` — video order and fallback
- `references/media-ops.md` — still, reframe, captions, assemble
- `references/browser-flow-browser.md`, `references/browser-gemini-browser.md`
