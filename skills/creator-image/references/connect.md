# Connecting providers (keys, OAuth, browser)

Use `scripts/connect.py`. Keys are typed by the user into a hidden prompt in their own
terminal, verified with a free API call, and stored in `~/.config/creator-skills/.env`
(mode 600). `creator.py` loads that file automatically — no shell profile edits needed.

## Agent rules (non-negotiable)

- **Never ask the user to paste a key into chat**, and never put a key in a command line,
  config JSON, commit, or log. If the user pastes one anyway: don't repeat it, don't save it
  from chat; tell them to revoke/rotate it and connect again via the terminal.
- **Never read or print `.env` files.** Use `connect.py verify` (masks keys to the last 4).
- Login commands that open a browser or prompt (OAuth device flows) must be run by the user
  in their terminal; the agent only tells them the exact command.

## What to tell the user

1. Show what's missing and what each option unlocks:
   ```bash
   python3 scripts/connect.py verify
   python3 scripts/connect.py list      # links + steps per provider
   ```
2. For each provider they choose, give the one command to run **in their own terminal**
   (with the absolute path to this skill's `scripts/connect.py`):

| Provider | Command | What happens |
|---|---|---|
| Google Gemini API | `python3 …/connect.py google-api` | Opens nothing; get the key at aistudio.google.com/apikey, paste into hidden prompt, verified, saved |
| OpenAI API | `python3 …/connect.py openai-api` | Same, key from platform.openai.com/api-keys |
| ElevenLabs | `python3 …/connect.py elevenlabs` | Same, key from elevenlabs.io → Settings → API keys |
| Azure Speech | `python3 …/connect.py azure-tts` | Prompts key (hidden) + region (e.g. `uaenorth`) |
| Higgsfield | `python3 …/connect.py higgsfield` | Offers to install the CLI, runs `higgsfield auth login` (browser device-code OAuth) |
| Codex | `python3 …/connect.py codex` | Runs `codex login` (ChatGPT OAuth in the browser) |
| Antigravity (`agy`) | `python3 …/connect.py agy` | Runs `agy` once to complete Google sign-in |
| Google Cloud TTS | `python3 …/connect.py google-cloud-tts` | `gcloud auth application-default login` (browser OAuth), sets project, enables APIs, quota project |
| Gemini web / Flow / AI Studio | `python3 …/connect.py gemini-browser` (or `flow-browser`, `aistudio-browser`) | Enables the app in config; user signs in once in the agent's browser |

3. When they say done: `python3 scripts/connect.py verify <provider>` and report the result.

## Options

- `--env-file ./.env` — save to a project `.env` instead of the user file (make sure `.env`
  is in `.gitignore`).
- `--stdin` — read from a pipe, for password managers:
  `op read "op://Private/Gemini/key" | python3 …/connect.py google-api --stdin`
- `--no-verify` — save without testing (offline setup).

## Where keys can come from (priority)

1. Real environment variables (shell profile, CI secrets, the agent's own env settings)
2. `$CREATOR_SKILLS_ENV` file
3. `./.env` in the working directory
4. `~/.config/creator-skills/.env`

Only these variables are read from `.env` files: `GEMINI_API_KEY`, `GOOGLE_API_KEY`,
`OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`,
`HIGGSFIELD_BIN`, `AGY_BIN`, `CODEX_BIN`, `GCLOUD_BIN`, `CREATOR_SKILLS_CONFIG`.

## Troubleshooting

| `verify` says | Fix |
|---|---|
| `invalid` (401/403/400 key not valid) | Wrong or revoked key, or missing permissions (ElevenLabs keys need TTS/Voices; OpenAI images may need org verification). Create a new key and reconnect |
| `unknown` network error | Offline, proxy, or region block; retry later or `--no-verify` |
| codex "config file has a syntax error" | Fix `~/.codex/config.toml` at the reported line |
| gcloud `invalid` | `gcloud auth application-default login`, then set the quota project |
| Key works in terminal but not in the agent | The agent runs in a different environment; rely on `~/.config/creator-skills/.env` (loaded by the scripts) |
