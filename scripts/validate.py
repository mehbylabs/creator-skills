#!/usr/bin/env python3
"""Validate every skill against the Agent Skills spec and repo conventions.

Checks: frontmatter fields/limits, name == folder, metadata.version == VERSION,
referenced files exist, SKILL.md length, shared copies in sync, scripts compile.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_LINES = 300


def frontmatter(text: str) -> tuple[dict, dict]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise ValueError("missing frontmatter")
    fields: dict[str, str] = {}
    meta: dict[str, str] = {}
    key, block = None, []
    for line in m.group(1).splitlines():
        top = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if top:
            if key:
                fields[key] = " ".join(block).strip()
            key, rest = top.group(1), top.group(2)
            block = [] if rest in (">-", ">", "|", "|-", "") else [rest.strip('"')]
        elif key == "metadata":
            sub = re.match(r"^\s+([\w-]+):\s*(.*)$", line)
            if sub:
                meta[sub.group(1)] = sub.group(2).strip().strip('"')
        elif key:
            block.append(line.strip())
    if key:
        fields[key] = " ".join(block).strip()
    return fields, meta


def main() -> int:
    errors: list[str] = []
    version = (ROOT / "VERSION").read_text().strip()
    skills = sorted(p for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file())
    for skill in skills:
        rel = skill.relative_to(ROOT)
        text = (skill / "SKILL.md").read_text()
        try:
            fields, meta = frontmatter(text)
        except ValueError as e:
            errors.append(f"{rel}: {e}")
            continue
        for k in fields:
            if k not in ALLOWED:
                errors.append(f"{rel}: field '{k}' not allowed by spec (move under metadata)")
        name = fields.get("name", "")
        if not NAME_RE.match(name) or len(name) > 64:
            errors.append(f"{rel}: invalid name '{name}'")
        if name != skill.name:
            errors.append(f"{rel}: name '{name}' != folder '{skill.name}'")
        desc = fields.get("description", "")
        if not desc or len(desc) > 1024:
            errors.append(f"{rel}: description length {len(desc)} (1–1024)")
        if len(fields.get("compatibility", "")) > 500:
            errors.append(f"{rel}: compatibility > 500 chars")
        if meta.get("version") != version:
            errors.append(f"{rel}: metadata.version {meta.get('version')} != VERSION {version}")
        lines = text.count("\n")
        if lines > MAX_LINES:
            errors.append(f"{rel}: SKILL.md has {lines} lines (> {MAX_LINES})")
        for ref in set(re.findall(r"`((?:references|scripts)/[\w./-]+\.(?:md|py))`", text)):
            if "<" in ref:
                continue
            if not (skill / ref).is_file():
                errors.append(f"{rel}: references missing file {ref}")
        for py in (skill / "scripts").glob("*.py"):
            try:
                compile(py.read_text(), str(py), "exec")
            except SyntaxError as e:
                errors.append(f"{rel}: {py.name} does not compile: {e}")

    sync = subprocess.run([str(ROOT / "scripts" / "sync-shared.sh"), "--check"], capture_output=True, text=True)
    if sync.returncode != 0:
        errors.append("shared copies drifted:\n" + sync.stdout.strip())

    for e in errors:
        print(f"✗ {e}")
    print(f"{len(skills)} skills checked, {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
