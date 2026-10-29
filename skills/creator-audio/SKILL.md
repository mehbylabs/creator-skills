---
name: creator-audio
description: >-
  Make voiceovers, background music, and sound effects with whatever the user has —
  ElevenLabs, Google Gemini API (Gemini TTS, Lyria), Google Cloud TTS, Azure Speech, OpenAI,
  Higgsfield CLI, or Google AI Studio via computer use — with automatic fallback and
  dialect-aware routing for Arabic (Fusha, Egyptian, Gulf, Saudi, Levantine, Iraqi,
  Maghrebi). Use when the user asks for a voiceover, narration, text-to-speech, Arabic or
  dialect voiceover (تعليق صوتي، صوت بالعامية), reading a script aloud, a podcast intro,
  background music, a jingle, a sound effect, ambience, or foley. Not for dubbing or voice
  cloning.
license: MIT
compatibility: Python 3.9+; ffmpeg for format conversion. Needs one of ElevenLabs, Gemini, Azure, OpenAI keys, gcloud auth, Higgsfield CLI, or a browser tool for AI Studio.
allowed-tools: Bash Read Write
metadata:
  version: "0.2.0"
  argument-hint: "voiceover|music|sfx <text-or-prompt> [--voice id] [--duration s]"
---

# Creator Audio

Pick the mode from the request, then follow `references/audio.md` for prompt and voice
guidance.

## Voiceover

1. **Language** — detect it from the request/script. For Arabic, ask which dialect if not
   clear (Fusha, Egyptian, Saudi, Emirati/Gulf, Levantine, Iraqi, Moroccan…) and map it to
   `--lang` with `references/arabic-voice.md`.
2. **Script** — if the user gave a topic, draft it (≈150 words/min; Arabic ≈ 120–130).
   For a dialect, write it *in that dialect's spelling*. Show it; wait for approval.
3. Split into paragraphs/scenes; save as `vo/01.txt`, `vo/02.txt`, …
   **Arabic: add tashkeel to every word whose meaning depends on its vowels** (fractions,
   دَين/دِين، عَقد/عِقد، ذَهَب…, passive verbs, numbers in words) before any TTS, then run
   `python3 scripts/creator.py tashkeel-check --text-file vo/01.txt` until it says `ok`
   (`references/arabic-voice.md`).
4. Generate the **first** file and have the user listen before doing the rest:
   ```bash
   python3 scripts/creator.py speech --text-file vo/01.txt --out vo/01.mp3 [--lang ar-EG] [--voice <id>] [--style "warm, confident"]
   ```
5. Pin the provider and voice from the result (`--provider <id> --voice <voice>`, keep
   `--lang`) for every remaining file so the narrator never changes.
6. `python3 scripts/media.py probe vo/01.mp3` to confirm duration; report total length.

`needs_browser` with `aistudio-browser` → follow `references/browser-aistudio-browser.md`.

## Music

```bash
python3 scripts/creator.py music --prompt "<genre, instruments, bpm, mood, arc>" --duration 60 [--instrumental] --out music/bed.mp3
```

Beds under speech → always `--instrumental`. The router rejects silent or truncated takes
and extends short ones to the exact `--duration` (see `notes`); still listen once.

## Sound effects

```bash
python3 scripts/creator.py sfx --prompt "<source, action, space>" [--duration 2] [--loop] --out sfx/<name>.mp3
```

## Results

| `status` | Do |
|---|---|
| `ok` | Report file, length, provider/voice |
| `blocked` | Explain; offer a revised script/prompt |
| `needs_tashkeel` (exit 5) | Nothing was sent. Add tashkeel to each listed word for the intended reading, rerun |
| `needs_browser` | Drive the provider in `next` (computer use is on by default) |
| `failed` | Name the cheapest provider to add and its `connect` command from the JSON (user runs it in their terminal; `references/connect.md`) |

## Rules

- Never generate a voice that imitates a real, identifiable person without their consent.
- Don't mix voices from different providers in one piece; regenerate instead.
- Output format follows the extension (`.mp3` default, `.wav` for editing).

## References

- `references/audio.md` — voices, scripting for the ear, music and sfx prompts
- `references/arabic-voice.md` — Arabic dialects: script rules, `--lang`, routes, voices
- `references/browser-aistudio-browser.md` — AI Studio speech playground (manual route)
- `references/providers.md` — speech/music/sfx order and fallback
- `references/media-ops.md` — combining audio with visuals
