# AGENTS.md — creator-skills

Provider-agnostic creator skills: one skill per creator job, any backend the user has.

## Layout

```
shared/                   # canonical source — edit here only
  scripts/creator.py      # detect / plan / image / video / speech / music / sfx / adopt
  scripts/media.py        # local ffmpeg ops: probe / still / text / cutout / reframe / captions / assemble
  references/*.md         # providers, config, prompting, audio, media ops, browser playbooks
skills/<name>/            # installable skills (discovered by `npx skills`)
  SKILL.md
  scripts/, references/   # synced copies of shared/ + skill-specific references
scripts/sync-shared.sh    # copy shared/ into every skill (--check for CI)
scripts/validate.py       # spec + convention checks (run before every commit)
skills.sh.json            # grouping on the skills.sh repo page
```

Never edit synced copies in `skills/*/scripts/` or `skills/*/references/` when the file
exists in `shared/`; edit `shared/` and run `scripts/sync-shared.sh`. Skill-specific
references (e.g. `creator-product-photo/references/modes.md`) live only in their skill.

## Principles

1. **Detect, don't assume.** No skill hard-codes a provider; all generation goes through
   `creator.py`, which honors user config, then profile defaults.
2. **Scriptable before manual.** API/CLI providers before computer-use ones.
3. **Fallback never bypasses safety.** A `policy` refusal stops the chain.
4. **Verify on disk.** A provider's success message is not proof; the file is.
5. **The host agent orchestrates.** agy/codex are invoked as providers only through
   `creator.py`; the host writes prompts and reviews output.
6. **Stdlib only.** Scripts must run on a bare Python 3.9+ with ffmpeg.

## SKILL.md frontmatter (Agent Skills spec)

```yaml
---
name: creator-<job>            # == folder name, [a-z0-9-], ≤ 64
description: >-                # ≤ 1024 chars: what it does, "Use when …", "Not for …"
  …
license: MIT
compatibility: …               # ≤ 500 chars
allowed-tools: Bash Read Write # space-separated string
metadata:
  version: "0.1.0"             # must equal VERSION
  argument-hint: "…"
---
```

No other top-level keys. Keep SKILL.md under 300 lines; move tables/examples to references.

## Adding a provider

1. `PROVIDERS` entry (per-task capabilities) and `detect_one` branch in `shared/scripts/creator.py`.
2. Adapter functions raising `ProviderError(kind, msg)`; register in `ADAPTERS`.
3. Add to `DEFAULT_ORDER` (both profiles) and `DEFAULT_MODELS`.
4. Document in `shared/references/providers.md`; browser providers get `browser-<id>.md`.
5. `scripts/sync-shared.sh && python3 scripts/validate.py`.

## Adding a skill

Create `skills/creator-<job>/SKILL.md`, run sync + validate, add it to README and
`skills.sh.json`.

## Versions

`VERSION` is the source of truth; every `metadata.version` must match. Bump all together.
