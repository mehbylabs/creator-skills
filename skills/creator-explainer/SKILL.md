---
name: creator-explainer
description: >-
  Turn a topic, article, notes, or document into a narrated explainer video — script,
  voiceover, per-scene visuals, music bed, captions, final MP4 — using whatever providers
  the user has, and degrading gracefully (video clips → animated stills → captioned
  slideshow). Use when the user asks for an explainer, faceless video, narrated video,
  YouTube video from an article, educational video, listicle video, or "turn this into a
  video". Not for single clips (creator-video) or product ads (creator-ad).
license: MIT
compatibility: Python 3.9+ and ffmpeg. Best with a speech provider and an image provider.
allowed-tools: Bash Read Write
metadata:
  version: "0.2.0"
  argument-hint: "<topic or file> [--length 60s] [--vertical] [--style 'flat illustration']"
---

# Creator Explainer

Project folder: `explainer/<slug>/` with `script.md`, `vo/`, `visuals/`, `music/`,
`scenes.json`, `final.mp4`.

## Step 1 — Brief (one message, then go)

Infer and state: audience, length (default 60–90 s), format (`16:9`, or `9:16` for
Shorts/Reels), visual style (one sentence used in every scene prompt), voice. Check routes:

```bash
for t in speech image video music; do python3 scripts/creator.py plan --task $t; done
```

Pick the **visual tier** from what's available and say it in one line:

| Tier | When | Scene visuals |
|---|---|---|
| A | video provider available | 4–8 s generated clips (first frame from an image when style matters) |
| B | image provider only | generated stills animated with Ken Burns |
| C | neither | text cards (`media.py text` on a solid/gradient background) |

No speech provider → captions-only video; tell the user which key unlocks narration.

## Step 2 — Script (get approval before spending credits)

`references/explainer-structure.md`: hook (≤ 2 sentences) → 3–6 beats → payoff/CTA.
~150 spoken words per minute. One scene per beat, each with: narration, visual idea,
on-screen text (optional). Save to `script.md` and show it.

## Step 3 — Voiceover

One file per scene: `vo/01.mp3` … with `creator.py speech`; pin provider + voice after the
first success. Scene timing comes from these durations. Non-English: pass `--lang`; for
Arabic dialects write the script in the dialect and follow `references/arabic-voice.md`.
Arabic narration: add tashkeel to meaning-changing words (fractions, دَين/دِين، عَقد/عِقد,
passive verbs, numbers in words) before any TTS; `speech` stops with `needs_tashkeel` otherwise.

## Step 4 — Visuals

For each scene, prompt = style sentence + the scene's visual idea.

- Tier A: `creator.py video --prompt … --ratio <r> --duration <≈vo length> --out visuals/NN.mp4`
  (optionally `--start` from an approved still for consistency).
- Tier B: `creator.py image --prompt … --ratio <r> --out visuals/NN.png`.
- Tier C: `ffmpeg -f lavfi -i color=c=#0B1F3A:s=1920x1080 -frames:v 1 bg.png` then
  `media.py text --image bg.png --text "<key line>" --pos center`.

Look at each visual before moving on; regenerate off-style ones.

## Step 5 — Music (optional) and assembly

`creator.py music --instrumental --duration <total+5> --out music/bed.mp3` if available.

```json
[{"visual": "visuals/01.png", "audio": "vo/01.mp3"}, {"visual": "visuals/02.mp4", "audio": "vo/02.mp3"}]
```

```bash
python3 scripts/media.py assemble --scenes scenes.json --out final.mp4 --ratio 16:9 [--music music/bed.mp3]
```

Captions (recommended for vertical): build `subs.srt` from the script using scene start
times (cumulative VO durations + 0.4 s), then `media.py captions`.

## Step 6 — Deliver

`media.py probe final.mp4`; spot-check frames at 3 points. Report length, tier, providers,
and what would upgrade quality (e.g. "add GEMINI_API_KEY for real motion clips").

## References

- `references/explainer-structure.md` — script structure and pacing
- `references/audio.md`, `references/video-prompting.md`, `references/image-prompting.md`
- `references/media-ops.md` — assemble, captions, text cards
- `references/providers.md`
