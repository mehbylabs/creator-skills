# User config

`creator.py` reads the first file found:

1. `$CREATOR_SKILLS_CONFIG`
2. `./creator-skills.json` (project-local)
3. `~/.config/creator-skills/config.json` (user-global)

No config is fine: everything auto-detects and the `quality` profile applies.

```json
{
  "profile": "quality",
  "order": {
    "image": ["agy", "google-api", "codex", "gemini-browser"],
    "video": ["flow-browser", "google-api"],
    "speech": ["elevenlabs", "google-api"]
  },
  "disabled": ["openai-api"],
  "models": {
    "google-api": { "image": "gemini-3-pro-image" },
    "elevenlabs": { "speech": "eleven_v3" }
  },
  "voices": {
    "elevenlabs": "<voice_id>",
    "google-api": "Puck",
    "google-api:ar-EG": "Charon",
    "azure-tts:ar-SA": "ar-SA-HamedNeural",
    "openai-api": "cedar"
  },
  "browser": {
    "enabled": true,
    "apps": ["gemini", "flow", "aistudio"],
    "downloads_dir": "~/Downloads"
  },
  "brand": {
    "name": "Acme",
    "colors": ["#0B1F3A", "#FF6B35", "#F4F1EA"],
    "fonts": { "heading": "/path/to/Heading-Bold.ttf" },
    "logo": "/path/to/logo.png"
  }
}
```

| Key | Effect |
|---|---|
| `profile` | `quality` (default) or `cost` — picks the default order |
| `order.<task>` | Replacement order for `image` / `video` / `speech` / `music` / `sfx`. Unlisted providers are not used for that task |
| `order["speech:<lang>"]` | Order for one language or dialect, e.g. `speech:ar`, `speech:ar-MA` |
| `disabled` | Provider ids never to use |
| `models.<provider>.<task>` | Model id override |
| `voices.<provider>` / `voices["<provider>:<lang>"]` | Default voice per speech provider, optionally per language/dialect |
| `browser.enabled` | Computer-use providers are **on by default**; set `false` to never use them (e.g. an agent with no browser tool) |
| `browser.apps` | Web apps the router may drive (default all three: `gemini`, `flow`, `aistudio`); list fewer to narrow |
| `browser.downloads_dir` | Where the browser saves files, for `creator.py adopt` |
| `brand` | Optional brand defaults read by thumbnail / product / brandkit / ad skills |

Secrets never go in this file. Connect them with `scripts/connect.py <provider>` (see
`connect.md`), which stores them in `~/.config/creator-skills/.env` (chmod 600). The
scripts read real env vars first, then `./.env`, then that file. Variables: `GEMINI_API_KEY` (or
`GOOGLE_API_KEY`), `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, `AZURE_SPEECH_KEY` +
`AZURE_SPEECH_REGION`. Google Cloud TTS uses `gcloud auth application-default login`.
Binaries can be pinned with `HIGGSFIELD_BIN`, `AGY_BIN`, `CODEX_BIN`, `GCLOUD_BIN`.
