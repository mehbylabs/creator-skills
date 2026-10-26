# Audio: voiceover, music, sound effects

## Voiceover (`creator.py speech`)

```bash
python3 scripts/creator.py speech --text-file script.txt --out vo.mp3 [--lang ar-EG] [--voice ID] [--style "warm, upbeat"] [--speed 1.05]
```

**Arabic or any Arabic dialect → read `arabic-voice.md` first** (script must be written in
the dialect; `--lang` picks dialect-aware routing and voices).

- Write for the ear: short sentences, numbers as words when ambiguous ("twenty twenty-six"),
  spell out acronyms you want letter-by-letter ("A-P-I").
- Long scripts: split into one file per scene/paragraph so retakes are cheap and the
  explainer can time scenes to audio.
- `--style` is delivery direction. Google TTS and OpenAI `gpt-4o-mini-tts` honour it;
  ElevenLabs ignores it (choose the voice instead; `eleven_v3` reads inline tags like
  `[whispers]`, `[laughs]`). Google also reads inline tags: `<short pause>`, `<laugh>`, `<sigh>`.

Voices:

| Provider | Default | Good alternatives |
|---|---|---|
| ElevenLabs | first voice in the account (set `voices.elevenlabs` in config) | list with `GET /v2/voices`; the legacy default voices retire Dec 31 2026 |
| Google | `Kore` | `Puck` (upbeat), `Charon` (deep, informative), `Zephyr` (bright), `Aoede`, `Fenrir`, `Leda`, `Orus`, `Enceladus`, `Sulafat` |
| OpenAI | `marin` | `cedar`, `coral`, `sage`, `ash`, `nova`, `onyx` |
| Google Cloud TTS | `Kore` | same names as Gemini; locale from `--lang` |
| Azure | per `--lang` country voice (e.g. `ar-EG-SalmaNeural`) | any `<locale>-<Name>Neural` |

Use the same provider + voice for every line of one project. If fallback switched provider
mid-project, regenerate the earlier lines on the new provider rather than mixing voices.

## Music (`creator.py music`)

```bash
python3 scripts/creator.py music --prompt "lo-fi hip hop, warm Rhodes, vinyl crackle, 80 bpm" --duration 60 --instrumental --out bed.mp3
```

Prompt with genre, instrumentation, tempo (bpm), mood, energy arc ("builds at 0:20").
Background beds under narration: always `--instrumental`, mixed by `media.py assemble`
(ducked automatically). Google's default `lyria-3-clip-preview` returns 30 s; loop or pick
`lyria-3.5` in config for full-length tracks.

## Sound effects (`creator.py sfx`)

```bash
python3 scripts/creator.py sfx --prompt "whoosh transition, airy, fast" --duration 1.2 --out whoosh.mp3
```

Describe source, action, space, and length: "heavy wooden door creaks open in a stone hall".
`--loop` for ambiences.

## Licensing

Generated audio is subject to the provider's terms and the user's plan; mention this when
the user says the piece is for paid ads or broadcast.
