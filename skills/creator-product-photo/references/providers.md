# Providers, priority, and fallback

Every creator skill generates through `scripts/creator.py`. It detects what the user has,
orders providers by config/profile, filters by capability, and falls back on failure.
Local compositing (text, Ken Burns, reframe, captions, assembly) is `scripts/media.py`.

## Provider matrix

| id | Runs via | image | video | speech | music | sfx | Pays with |
|---|---|---|---|---|---|---|---|
| `higgsfield` | `higgsfield` CLI | ✅ refs, 4K | ✅ Seedance 2.5, start/end frame | – | ✅ | ✅ | credits |
| `google-api` | REST, `GEMINI_API_KEY` | ✅ Nano Banana 2.1, refs, 4K | ✅ Gemini Omni Flash | ✅ Gemini TTS | ✅ Lyria | – | per call |
| `openai-api` | REST, `OPENAI_API_KEY` | ✅ gpt-image-2.5, refs, **transparent** | – | ✅ (until Jan 2027) | – | – | per call |
| `elevenlabs` | REST, `ELEVENLABS_API_KEY` | – | – | ✅ best voices | ✅ | ✅ | per call / plan |
| `google-cloud-tts` | REST, `gcloud` OAuth (no API key) | – | – | ✅ Gemini-TTS, `ar-EG` + accent prompt | – | – | per call |
| `azure-tts` | REST, `AZURE_SPEECH_KEY` + `AZURE_SPEECH_REGION` | – | – | ✅ voices per Arabic country | – | – | per call / free tier |
| `aistudio-browser` | computer use, aistudio.google.com | – | – | ✅ Gemini TTS + voice design | – | – | Google sign-in |
| `agy` | `agy -p` headless | ✅ text-only, ~1K, JPEG | – | – | – | – | Google plan |
| `codex` | `codex exec` headless | ✅ refs, transparent | – | – | – | – | ChatGPT plan |
| `gemini-browser` | computer use, gemini.google.com | ✅ | ✅ short | – | – | – | Google plan |
| `flow-browser` | computer use, Google Flow | ✅ | ✅ Veo, best manual video | – | – | – | Flow credits |

The **host agent** (Claude Code, OpenCode, Codex, Antigravity…) is the orchestrator: it
writes prompts, chooses routes, drives the browser, and reviews output. It never claims to
generate media itself.

Notes that matter for routing:

- Veo is no longer served by the Gemini API (shut down Oct 2026); API video goes through
  `gemini-omni-1.1-flash`. Veo is still reachable through Flow and Higgsfield.
- OpenAI's video API (Sora) is gone; `openai-api` does images and speech only.
- `agy` replaces the old Gemini CLI. It cannot take reference images and returns JPEG.
  It has **no speech/audio tool** (verified) — it is an image-only provider.
- `codex` costs ~30k agent tokens of the user's Codex allowance per image.

## Default order

| task | `quality` (default) | `cost` |
|---|---|---|
| image | higgsfield → google-api → openai-api → agy → codex → gemini-browser → flow-browser | agy → codex → higgsfield → google-api → openai-api → gemini-browser → flow-browser |
| video | higgsfield → google-api → flow-browser → gemini-browser | flow-browser → gemini-browser → higgsfield → google-api |
| speech | elevenlabs → google-api → google-cloud-tts → azure-tts → openai-api → aistudio-browser | google-api → aistudio-browser → google-cloud-tts → azure-tts → elevenlabs → openai-api |
| speech `--lang ar*` | google-api → google-cloud-tts → azure-tts → elevenlabs → openai-api → aistudio-browser | (same) |
| music | elevenlabs → google-api → higgsfield | google-api → elevenlabs → higgsfield |
| sfx | elevenlabs → higgsfield | elevenlabs → higgsfield |

Why: scriptable APIs/CLIs first (reliable, verifiable, parameterized); subscription agent
CLIs next (cheap, fewer controls); computer use last (slow; UI changes break it).
User config always wins: `order.<task>` replaces the list, `order["<task>:<lang>"]`
(e.g. `speech:ar-MA`) overrides it for one language/dialect, `disabled` removes ids.
Manual (browser) providers are always tried after every scriptable one fails, wherever
they sit in the list.

## Capability filtering

- `--ref` / `--start` → needs reference support (drops `agy`).
- `--end` (video) → needs end-frame support (drops `gemini-browser`).
- `--transparent` → only `openai-api`, `codex`. If neither is available the router renders on
  white and returns `"post": "remove_background"` → run `media.py cutout`.
- `--size 2k|4k` (image) → providers whose max is lower move to the end of the scriptable
  routes (`generate_at` / `upscale_to` in the plan): they generate at their max and the
  router upscales locally (Lanczos) and says so in `notes`. Native-size routes go first.

## When nothing can generate

| task | Local fallback |
|---|---|
| video | Generate stills with `image`, then `media.py still` (Ken Burns) or `assemble` |
| image with text | Generate art without text, then `media.py text` |
| speech/music/sfx | No local generator. Say which key would unlock it; offer a silent/captioned cut |

## Fallback rules

| Error | Router action |
|---|---|
| `transient` (timeout, 5xx, network) | retry once, then next provider |
| `auth` (signed out, bad key) | next provider; report the fix at the end (`connect` list in the JSON) |
| `quota` (429, credits, usage limit) | next provider |
| `unsupported` (model/endpoint/tool/ratio missing) | next provider |
| `failed` (anything else) | next provider |
| `policy` (content refused) | **stop**. Never shop a refused request to other providers |

**Output checks (verify on disk).** Music is checked after every call: a track with silence
mid-way (≥ 6 s, or > 10% of its length outside the final fade) or under half the asked
length is deleted and counts as `transient` (one retry, then the next provider). A track
shorter than wanted, or a request above the provider's cap (ElevenLabs Music: 300 s), is
extended locally with crossfaded repeats of its body and its own ending (`notes` says so).

**Arabic speech gate.** With `--lang ar*` (or Arabic text), `speech` first checks for words
whose meaning depends on vowels (ثلث/ثلثا، عُشر/عَشر، دَين/دِين، عَقد/عِقد، ذَهَب/ذَهَبَ…). If any
appear with no haraka, nothing is sent: exit `5`, `status: needs_tashkeel` with the words
and their readings. Add tashkeel and rerun (`arabic-voice.md`).

Only manual providers left → exit `3`, `status: needs_browser`, with `next` and the full
`request` to reproduce in the browser. Follow `browser-<id>.md`, then `creator.py adopt`.

**Speech verify.** `speech --verify` / `verify --audio A --text-file T` transcribe with the first
available STT (ElevenLabs `scribe_v2` → OpenAI `gpt-4o-transcribe` → Gemini) and diff against
the script after normalizing tashkeel, spelling variants and number words vs digits. Report
only: `match`, or `check` with `differences` and `numbers_changed`.

Exit codes: `0` ok · `1` all failed · `2` bad usage · `3` needs browser · `4` policy block · `5` Arabic text needs tashkeel · `6` verify found differences.

## Models

Defaults are in `creator.py` (`DEFAULT_MODELS`); override per provider in config
(`models.<provider>.<task>`) or per call (`--model`). When a call returns `unsupported`,
check the live list before changing defaults: `higgsfield model list`, Google model docs,
OpenAI image docs, `agy models` (agy's model only drives the tool; a cheap Flash is right).
