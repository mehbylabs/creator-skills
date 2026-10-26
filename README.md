# creator-skills

[![skills.sh](https://skills.sh/b/mehbylabs/creator-skills)](https://skills.sh/mehbylabs/creator-skills)
[![validate](https://github.com/mehbylabs/creator-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/mehbylabs/creator-skills/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Agent skills for creators that work with **whatever tools you already have**, and fall back
automatically when one is missing, out of quota, or signed out.

Most media skills are tied to one vendor. These detect what *you* have — a CLI, an API key,
a subscription, or just a browser — pick the best route, and keep going when a route fails.

```bash
npx skills add mehbylabs/creator-skills
```

## Providers

| Provider | Image | Video | Voice | Music | SFX | Unlocked by |
|---|---|---|---|---|---|---|
| Higgsfield CLI | ✅ | ✅ | | ✅ | ✅ | `higgsfield auth login` |
| Google Gemini API | ✅ Nano Banana | ✅ Gemini Omni | ✅ | ✅ Lyria | | `GEMINI_API_KEY` |
| OpenAI API | ✅ gpt-image (transparent) | | ✅ | | | `OPENAI_API_KEY` |
| ElevenLabs | | | ✅ | ✅ | ✅ | `ELEVENLABS_API_KEY` |
| Google Cloud TTS | | | ✅ `ar-EG` + accent prompt | | | `gcloud auth application-default login` |
| Azure Speech | | | ✅ 16 Arabic country voices | | | `AZURE_SPEECH_KEY` + `AZURE_SPEECH_REGION` |
| Google AI Studio | | | ✅ Gemini TTS, voice design | | | browser + computer use |
| Antigravity CLI (`agy`) | ✅ | | | | | Google sign-in |
| Codex CLI | ✅ | | | | | ChatGPT sign-in |
| Gemini web app | ✅ | ✅ | | | | browser + computer use |
| Google Flow | ✅ | ✅ Veo | | | | browser + computer use |
| ffmpeg (local) | text, cutouts | Ken Burns, reframe, captions, assembly | | | | always |

Your agent (Claude Code, OpenCode, Codex, Antigravity, Cursor…) plans, writes prompts, drives
the browser when needed, and checks every output.

## Skills

| Skill | What it does |
|---|---|
| `creator-setup` | Detect your tools; choose `quality` or `cost` profile, priority order, voices, brand |
| `creator-image` | Generate or edit images, references, transparent PNGs |
| `creator-video` | Text/image-to-video, first/last frame, reframe, captions; stills fallback |
| `creator-audio` | Voiceover (incl. Arabic dialects), music beds, sound effects |
| `creator-thumbnail` | YouTube thumbnails and vertical covers with crisp local headlines |
| `creator-product-photo` | Studio, lifestyle, Pinterest, hero, ad pack, try-on, marketplace sets |
| `creator-ad` | Short-form and UGC-style video ads with hook variants and multi-placement exports |
| `creator-explainer` | Topic or document → narrated video with captions and music |
| `creator-character` | Consistent faces and mascots across images and video |
| `creator-brandkit` | Palette, type, SVG logos, mockups, reusable brand kit |

Install one: `npx skills add mehbylabs/creator-skills --skill creator-thumbnail`.

## How routing works

1. `creator.py detect` finds available providers.
2. Your config (or the default profile) orders them per task.
3. Providers that can't do the job (references, transparency, end frame, size) are skipped.
4. Errors fall through: retry once on timeouts, move on for auth / quota / unsupported.
   A **content refusal stops** — it is never re-tried on another provider.
5. If only browser providers remain, the agent completes the job in Gemini or Flow.

Default orders:

| | quality (default) | cost |
|---|---|---|
| image | Higgsfield → Google → OpenAI → agy → Codex → Gemini web → Flow | agy → Codex → Higgsfield → Google → OpenAI → Gemini web → Flow |
| video | Higgsfield → Google → Flow → Gemini web | Flow → Gemini web → Higgsfield → Google |
| voice | ElevenLabs → Google → Cloud TTS → Azure → OpenAI → AI Studio | Google → AI Studio → Cloud TTS → Azure → ElevenLabs → OpenAI |
| voice, Arabic (`--lang ar*`) | Google → Cloud TTS → Azure → ElevenLabs → OpenAI → AI Studio | same |

**Arabic dialects:** `--lang ar` (Fusha), `ar-EG`, `ar-SA`, `ar-AE`, `ar-KW`, `ar-LB`, `ar-SY`,
`ar-JO`, `ar-IQ`, `ar-MA`, `ar-TN`… set dialect-aware routing, accent direction, and
per-country voices. See [`arabic-voice.md`](shared/references/arabic-voice.md).

Details: [`shared/references/providers.md`](shared/references/providers.md) ·
config: [`shared/references/config.md`](shared/references/config.md).

## Connect your tools

Keys are typed into a hidden prompt in your terminal, verified, and saved to
`~/.config/creator-skills/.env` (private, auto-loaded). Logins run each tool's own OAuth.

```bash
python3 skills/creator-setup/scripts/connect.py verify          # what's connected
python3 skills/creator-setup/scripts/connect.py google-api      # paste key (hidden) → verified → saved
python3 skills/creator-setup/scripts/connect.py higgsfield      # install + browser login
python3 skills/creator-setup/scripts/connect.py aistudio-browser
op read "op://Private/ElevenLabs/key" | python3 skills/creator-setup/scripts/connect.py elevenlabs --stdin
```

Or just ask your agent to "set up creator skills" — it will tell you which command to run.
Agents are instructed never to ask for keys in chat or read `.env` files.

## Try it without an agent

```bash
python3 skills/creator-image/scripts/creator.py detect
python3 skills/creator-image/scripts/creator.py image --prompt "flat vector lighthouse at dusk" --ratio 16:9 --out out/lighthouse.png
python3 skills/creator-image/scripts/media.py text --image out/lighthouse.png --text "NIGHT WATCH" --out out/thumb.png
```

Requirements: Python 3.9+ (stdlib only), ffmpeg recommended.

## Contributing

See [AGENTS.md](AGENTS.md). Edit `shared/`, run `scripts/sync-shared.sh`, then
`python3 scripts/validate.py`.

## Credits

Structure and conventions inspired by [higgsfield-ai/skills](https://github.com/higgsfield-ai/skills) (MIT).

## License

[MIT](LICENSE)
