# Local media ops (`scripts/media.py`)

Deterministic ffmpeg operations. Always available when ffmpeg is installed; use them to
finish, fix, or replace generated media. All commands print JSON.

| Command | Use for |
|---|---|
| `probe FILE` | Duration, size, whether audio exists — verify every output |
| `still --image I --out O.mp4 --duration 5 --ratio 16:9 --motion in\|out\|left\|right\|none` | Ken Burns clip from a still; the video fallback when no video provider exists |
| `text --image I --out O.png --text "LINE ONE\nLINE TWO" --pos top\|center\|bottom --align left\|center\|right --size 0.12 [--box "black@0.55"] [--font F.ttf] [--color white --stroke black]` | Crisp headline overlay; place it in the empty area the art reserved |
| `cutout --image I --out O.png [--color white --similarity 0.12]` | Transparent PNG from a flat background (uses `rembg` if installed) |
| `reframe --video V --out O --ratio 9:16 --mode blur\|crop\|pad` | Change aspect ratio of a video or image |
| `captions --video V --srt S.srt --out O.mp4 [--size 16]` | Burn subtitles |
| `assemble --scenes scenes.json --out O.mp4 [--ratio 16:9] [--music bed.mp3 --music-volume 0.18]` | Narrated slideshow/explainer: scenes timed to their voiceover, music ducked under speech, loudness normalized to −14 LUFS |

`scenes.json` (paths relative to the file):

```json
[
  {"visual": "s1.png", "audio": "vo1.mp3", "motion": "in"},
  {"visual": "s2.mp4", "audio": "vo2.mp3"},
  {"visual": "end.png", "duration": 2.5, "motion": "none"}
]
```

A scene lasts its audio length + 0.4 s, or `duration` (default 4 s) without audio. Video
visuals loop or trim to fit. Sizes: 16:9 1920×1080, 9:16 1080×1920, 1:1 1080×1080,
4:5 1080×1350.

For richer motion graphics (kinetic type, animated charts, branded lower-thirds), use a
dedicated composition tool if the user has one (HyperFrames, Remotion); `media.py` is the
dependable baseline, not the ceiling.
