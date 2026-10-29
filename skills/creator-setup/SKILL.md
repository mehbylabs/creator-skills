---
name: creator-setup
description: >-
  Detect which media tools this user can use (Higgsfield CLI, Gemini/Google API key, OpenAI
  API key, ElevenLabs API key, Antigravity CLI agy, Codex CLI, Gemini web app, Google Flow)
  and save their creator-skills preferences: quality vs cost profile, provider priority per
  task, disabled providers, default voices, brand defaults. Guides connecting API keys
  (hidden prompt, verified, stored in a private .env) and OAuth logins. Use when the user
  says "set up creator skills", "connect my API key", "add my Gemini/OpenAI/ElevenLabs/Azure
  key", "log in to Higgsfield/Codex", "what tools do I have", "change provider order", "use
  my subscription first", "enable browser use", or a generation skill reported missing or
  invalid providers. Not for generating media.
license: MIT
compatibility: Python 3.9+. Works with any subset of the supported providers.
allowed-tools: Bash Read Write
metadata:
  version: "0.3.0"
  argument-hint: "[profile|order|disable|voices|brand|enable-browser]"
---

# Creator Setup

Generation skills work with no config (auto-detect + `quality` profile). This skill makes
the user's choices explicit and fixes what's missing.

## Step 1 — Detect and verify

```bash
python3 scripts/creator.py detect
python3 scripts/connect.py verify
```

Show a short table: provider · status (connected / missing / invalid) · what it unlocks.
Don't print JSON or key fragments beyond the masked last 4.

## Step 2 — Connect what the user wants

Ask which missing providers they want (suggest the cheapest path to cover image, video,
and voice). For each, follow `references/connect.md`:

- Give the **exact command with this skill's absolute script path** for the user to run
  in **their own terminal** (`python3 <abs>/scripts/connect.py google-api`). It prompts for
  the key hidden, verifies it, saves to `~/.config/creator-skills/.env` (chmod 600).
- OAuth/CLI providers (`higgsfield`, `codex`, `agy`, `google-cloud-tts`) — same command; it
  runs their browser login.
- Browser apps (`gemini-browser`, `flow-browser`, `aistudio-browser`) are **on by default**
  as the last fallback; the user only signs in once in the agent's browser. If this agent has
  no browser / computer-use tool, or the user doesn't want computer use, set
  `"browser": {"enabled": false}` (or narrow `browser.apps`) in the config.
- When they're done, run `python3 scripts/connect.py verify <provider>` and report.

**Never** ask for keys in chat, read `.env` files, or put keys on a command line. If a key
is pasted into chat, tell the user to rotate it and use the terminal flow.

## Step 3 — Choose (one question at a time, only what's unclear)

1. **Profile** — `quality` (APIs/CLIs first) or `cost` (subscription tools — agy, codex,
   Flow — before pay-per-call APIs). Explain with `references/providers.md`.
2. **Order** — only if the user states a preference ("always agy first for images").
3. **Disable** — providers they never want used or billed.
4. **Voice** — optional default voice for voiceovers (`references/audio.md`).
5. **Brand** — optional colors, heading font file, logo path for thumbnails/ads.

## Step 4 — Write and confirm

Write `~/.config/creator-skills/config.json` (or `./creator-skills.json` for one project)
following `references/config.md`. Never write secrets into it. Then:

```bash
for t in image video speech music sfx; do python3 scripts/creator.py plan --task $t; done
```

Report one line per task: the order that will be used, or "no provider — <cheapest fix>".

## Rules

- Secrets only flow through `connect.py` in the user's terminal, a password-manager pipe
  (`--stdin`), or env vars the user sets themselves.
- If `detect` reports a broken tool config (e.g. Codex `config.toml` parse error), tell the
  user the file; don't edit other tools' configs without permission.

## References

- `references/connect.md` — connecting keys, OAuth logins, browser apps; security rules
- `references/providers.md` — matrix, default orders, fallback rules
- `references/config.md` — config schema
- `references/audio.md` — voices
