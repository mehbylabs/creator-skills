#!/usr/bin/env python3
"""connect.py — connect creator-skills providers: API keys, OAuth/CLI logins, browser apps.

  connect.py list                      What each provider needs and whether it's connected (JSON).
  connect.py verify [provider ...]     Test configured keys/logins with a free call (JSON, keys masked).
  connect.py <provider> [--env-file F] [--stdin] [--no-verify]
                                       Interactive: prompt for the key (hidden), verify, save to
                                       ~/.config/creator-skills/.env (chmod 600); or run the
                                       provider's OAuth/CLI login; or enable a browser app.

Run `connect.py <provider>` in YOUR terminal, not through an agent: keys are typed into a
hidden prompt and never shown. `--stdin` reads the key from a pipe (password managers).
Stdlib only.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import creator  # noqa: E402

PROVIDERS = {
    "google-api": {
        "type": "key", "vars": ["GEMINI_API_KEY"],
        "get": "https://aistudio.google.com/apikey",
        "steps": ["Sign in to Google AI Studio", "Create API key (pick or create a Google Cloud project)",
                  "Free tier works for testing; enable billing on the project for higher limits"],
        "unlocks": "images (Nano Banana), video (Gemini Omni), speech (Gemini TTS incl. Arabic), music (Lyria)"},
    "openai-api": {
        "type": "key", "vars": ["OPENAI_API_KEY"],
        "get": "https://platform.openai.com/api-keys",
        "steps": ["Create a secret key (project key is fine)", "Add billing credit",
                  "Image models may require Organization Verification in platform settings"],
        "unlocks": "images (gpt-image, transparent PNG), speech (until Jan 2027)"},
    "elevenlabs": {
        "type": "key", "vars": ["ELEVENLABS_API_KEY"],
        "get": "https://elevenlabs.io/app/settings/api-keys",
        "steps": ["Create API key", "Permissions: Text to Speech, Sound Effects, Music, Voices (read)"],
        "unlocks": "speech (best voices), music, sound effects"},
    "azure-tts": {
        "type": "key", "vars": ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"],
        "get": "https://portal.azure.com/#create/Microsoft.CognitiveServicesSpeechServices",
        "steps": ["Create a Speech resource (free F0 tier available)",
                  "Open the resource → Keys and Endpoint", "Copy KEY 1 and the Location/Region (e.g. uaenorth, westeurope)"],
        "unlocks": "speech with per-country Arabic dialect voices"},
    "higgsfield": {
        "type": "cli", "bin": "higgsfield",
        "install": "curl -fsSL https://raw.githubusercontent.com/higgsfield-ai/cli/main/install.sh | sh",
        "login": ["higgsfield", "auth", "login"],
        "check": ["higgsfield", "account", "status"],
        "steps": ["Install the CLI", "Run the device-code login and approve it in the browser"],
        "unlocks": "images, video (Seedance/Kling/Veo), music, sfx — uses Higgsfield credits"},
    "codex": {
        "type": "cli", "bin": "codex",
        "install": "npm install -g @openai/codex",
        "login": ["codex", "login"],
        "check": ["codex", "login", "status"],
        "steps": ["Install Codex CLI", "Sign in with ChatGPT (OAuth in the browser)"],
        "unlocks": "images via your ChatGPT plan"},
    "agy": {
        "type": "cli", "bin": "agy",
        "install": "Download Antigravity CLI from https://antigravity.google/product/antigravity-cli/",
        "login": ["agy"],
        "check": None,
        "steps": ["Install the Antigravity CLI", "Run `agy` once and complete Google sign-in, then exit"],
        "unlocks": "images via your Google plan"},
    "google-cloud-tts": {
        "type": "gcloud", "bin": "gcloud",
        "install": "https://cloud.google.com/sdk/docs/install",
        "steps": ["Install the Google Cloud CLI",
                  "gcloud auth application-default login   (browser OAuth)",
                  "gcloud config set project <PROJECT_ID>",
                  "gcloud services enable texttospeech.googleapis.com aiplatform.googleapis.com",
                  "gcloud auth application-default set-quota-project <PROJECT_ID>",
                  "Billing must be enabled on the project"],
        "unlocks": "speech via Cloud TTS (Gemini-TTS, ar-EG with accent prompt)"},
    "gemini-browser": {"type": "browser", "app": "gemini", "url": "https://gemini.google.com/app",
                       "unlocks": "images and short video through the agent's browser"},
    "flow-browser": {"type": "browser", "app": "flow", "url": "https://labs.google/fx/tools/flow",
                     "unlocks": "Veo video and images through the agent's browser (Flow credits)"},
    "aistudio-browser": {"type": "browser", "app": "aistudio", "url": "https://aistudio.google.com/generate-speech",
                         "unlocks": "Gemini TTS and voice design through the agent's browser"},
}


def mask(v: str | None) -> str:
    return f"…{v[-4:]}" if v and len(v) > 8 else ("set" if v else "missing")


def _get(url: str, headers: dict, method: str = "GET", data: bytes | None = None) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=headers, method=method, data=data)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:200]
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, str(e)


def verify_key(pid: str, env: dict) -> tuple[str, str]:
    """-> (status, detail) with status in ok | invalid | missing | unknown."""
    if pid == "google-api":
        key = env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY")
        if not key:
            return "missing", "GEMINI_API_KEY not set"
        code, msg = _get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=1", {"x-goog-api-key": key})
    elif pid == "openai-api":
        key = env.get("OPENAI_API_KEY")
        if not key:
            return "missing", "OPENAI_API_KEY not set"
        code, msg = _get("https://api.openai.com/v1/models", {"Authorization": f"Bearer {key}"})
    elif pid == "elevenlabs":
        key = env.get("ELEVENLABS_API_KEY")
        if not key:
            return "missing", "ELEVENLABS_API_KEY not set"
        code, msg = _get("https://api.elevenlabs.io/v2/voices?page_size=1", {"xi-api-key": key})
    elif pid == "azure-tts":
        key, region = env.get("AZURE_SPEECH_KEY"), env.get("AZURE_SPEECH_REGION")
        if not key or not region:
            return "missing", "AZURE_SPEECH_KEY and AZURE_SPEECH_REGION required"
        code, msg = _get(f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken",
                         {"Ocp-Apim-Subscription-Key": key, "Content-Length": "0"}, "POST", b"")
    else:
        return "unknown", "not a key provider"
    if code == 200:
        return "ok", "key works"
    low = msg.lower()
    if code in (401, 403) or (code == 400 and ("api key not valid" in low or "invalid api key" in low
                                                 or "api_key_invalid" in low)):
        return "invalid", f"rejected ({code}) — wrong key, revoked, or missing permissions: {msg[:120]}"
    if code == 0:
        return "unknown", f"network error: {msg[:120]}"
    return "unknown", f"HTTP {code}: {msg[:120]}"


def verify_cli(pid: str) -> tuple[str, str]:
    spec = PROVIDERS[pid]
    b = creator._which(spec["bin"], f"{spec['bin'].upper()}_BIN")
    if not b:
        return "missing", f"{spec['bin']} not installed — {spec['install']}"
    if pid == "google-cloud-tts":
        code, _ = creator._run([b, "auth", "application-default", "print-access-token"], timeout=30)
        return ("ok", "application-default credentials present") if code == 0 else \
            ("invalid", "run: gcloud auth application-default login")
    if not spec.get("check"):
        d = creator.detect_one(pid, creator.load_config())
        return ("ok" if d["available"] and d["reason"] == "ok" else "unknown"), d["reason"]
    code, msg = creator._run([b, *spec["check"][1:]], timeout=30)
    if "parse error" in msg.lower():
        return "invalid", f"{spec['bin']} config file has a syntax error: {msg[:160]}"
    return ("ok", "signed in") if code == 0 else ("invalid", f"not signed in — run: {' '.join(spec['login'])}")


def verify(pid: str) -> dict:
    spec = PROVIDERS[pid]
    if spec["type"] == "key":
        status, detail = verify_key(pid, dict(os.environ))
        return {"provider": pid, "status": status, "detail": detail,
                "keys": {v: (os.environ.get(v) or "missing") if v.endswith("REGION") else mask(os.environ.get(v))
                         for v in spec["vars"]}}
    if spec["type"] in ("cli", "gcloud"):
        status, detail = verify_cli(pid)
        return {"provider": pid, "status": status, "detail": detail}
    on = creator.browser_enabled(creator.load_config(), pid)
    return {"provider": pid, "status": "ok" if on else "missing",
            "detail": "enabled (default; sign-in happens in the browser)" if on else
            f"turned off in config — run: connect.py {pid}  (then sign in at {spec['url']} in the agent's browser)"}


# --------------------------------------------------------------------------- writers

def write_env(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    lines = path.read_text().splitlines() if path.exists() else ["# creator-skills secrets — never commit this file"]
    for k, v in values.items():
        new = f'{k}="{v}"'
        for i, line in enumerate(lines):
            if line.split("=", 1)[0].replace("export ", "").strip() == k:
                lines[i] = new
                break
        else:
            lines.append(new)
    path.write_text("\n".join(lines) + "\n")
    os.chmod(path, 0o600)


def enable_browser_app(app: str) -> Path:
    cfg_path = creator.config_path() or (creator.HOME / ".config" / "creator-skills" / "config.json")
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    browser = cfg.setdefault("browser", {})
    browser["enabled"] = True
    apps = browser.setdefault("apps", list(creator.BROWSER_APPS))
    if app not in apps:
        apps.append(app)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
    return cfg_path


# --------------------------------------------------------------------------- interactive connect

def say(msg: str = "") -> None:
    print(msg, file=sys.stderr)


def connect(pid: str, env_file: Path, use_stdin: bool, no_verify: bool) -> int:
    spec = PROVIDERS[pid]
    interactive = sys.stdin.isatty()

    if spec["type"] == "browser":
        path = enable_browser_app(spec["app"])
        print(json.dumps({"status": "ok", "provider": pid, "config": str(path),
                          "next": f"Sign in at {spec['url']} in the browser your agent controls."}))
        return 0

    if spec["type"] == "key":
        if not interactive and not use_stdin:
            print(json.dumps({"status": "needs_terminal", "provider": pid,
                              "detail": "Run this command yourself in a terminal so the key is typed into a hidden prompt.",
                              "get_key": spec["get"], "steps": spec["steps"]}))
            return 2
        say(f"\nConnect {pid} — unlocks: {spec['unlocks']}")
        say(f"Get a key: {spec['get']}")
        for s in spec["steps"]:
            say(f"  • {s}")
        values = {}
        piped = sys.stdin.read().split() if use_stdin else []
        for i, var in enumerate(spec["vars"]):
            if use_stdin:
                val = piped[i] if i < len(piped) else ""
            elif var.endswith("REGION"):
                val = input(f"{var} (e.g. uaenorth, westeurope, eastus): ").strip()
            else:
                val = getpass.getpass(f"{var} (hidden): ").strip()
            if not val:
                say(f"No value for {var}; nothing saved.")
                return 2
            values[var] = val
        if not no_verify:
            status, detail = verify_key(pid, values)
            say(f"Verify: {status} — {detail}")
            if status == "invalid":
                say("Not saved. Check the key and try again (or pass --no-verify).")
                print(json.dumps({"status": "invalid", "provider": pid, "detail": detail}))
                return 1
        write_env(env_file, values)
        print(json.dumps({"status": "ok", "provider": pid, "saved_to": str(env_file),
                          "keys": {k: (v if k.endswith("REGION") else mask(v)) for k, v in values.items()}}))
        return 0

    # CLI / OAuth providers
    b = creator._which(spec["bin"], f"{spec['bin'].upper()}_BIN")
    if not b:
        if not interactive or spec["type"] == "gcloud" or not spec["install"].startswith(("curl", "npm")):
            print(json.dumps({"status": "not_installed", "provider": pid, "install": spec["install"],
                              "steps": spec["steps"]}))
            return 2
        if input(f"{spec['bin']} is not installed. Run `{spec['install']}` now? [y/N] ").strip().lower() != "y":
            return 2
        subprocess.run(spec["install"], shell=True, check=False)
        b = creator._which(spec["bin"], f"{spec['bin'].upper()}_BIN")
        if not b:
            say("Install did not put the binary on PATH; open a new shell and retry.")
            return 1
    if spec["type"] == "gcloud":
        cmds = [[b, "auth", "application-default", "login"]]
        if not interactive:
            print(json.dumps({"status": "needs_terminal", "provider": pid, "steps": spec["steps"]}))
            return 2
        for c in cmds:
            subprocess.run(c, check=False)
        project = input("Google Cloud project ID to bill Text-to-Speech to: ").strip()
        if project:
            for c in ([b, "config", "set", "project", project],
                      [b, "services", "enable", "texttospeech.googleapis.com", "aiplatform.googleapis.com"],
                      [b, "auth", "application-default", "set-quota-project", project]):
                subprocess.run(c, check=False)
    else:
        if not interactive:
            print(json.dumps({"status": "needs_terminal", "provider": pid, "login": " ".join(spec["login"]),
                              "steps": spec["steps"]}))
            return 2
        say(f"Starting `{' '.join(spec['login'])}` — complete the sign-in, then exit if it opens a session.")
        subprocess.run([b, *spec["login"][1:]], check=False)
    result = verify(pid)
    print(json.dumps(result))
    return 0 if result["status"] == "ok" else 1


def main() -> int:
    ap = argparse.ArgumentParser(prog="connect.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="list | verify | <provider id>")
    ap.add_argument("providers", nargs="*", help="for verify: limit to these providers")
    ap.add_argument("--env-file", type=Path, default=creator.USER_ENV_FILE,
                    help=f"where to save keys (default {creator.USER_ENV_FILE}; use ./.env for one project)")
    ap.add_argument("--stdin", action="store_true", help="read key(s) from stdin, whitespace-separated")
    ap.add_argument("--no-verify", action="store_true")
    a = ap.parse_args()
    creator.load_env()

    if a.target == "list":
        out = []
        for pid, spec in PROVIDERS.items():
            item = {"provider": pid, "type": spec["type"], "unlocks": spec["unlocks"]}
            item.update({k: spec[k] for k in ("vars", "get", "install", "url", "steps") if k in spec})
            out.append(item)
        print(json.dumps({"env_files": [str(p) for p in creator.env_files()], "providers": out}, indent=2))
        return 0
    if a.target == "verify":
        ids = a.providers or list(PROVIDERS)
        bad = [i for i in ids if i not in PROVIDERS]
        if bad:
            print(json.dumps({"status": "error", "detail": f"unknown provider(s): {bad}"}))
            return 2
        print(json.dumps({"env_files": [str(p) for p in creator.env_files()],
                          "results": [verify(i) for i in ids]}, indent=2))
        return 0
    if a.target not in PROVIDERS:
        print(json.dumps({"status": "error", "detail": f"unknown provider {a.target}",
                          "providers": list(PROVIDERS)}))
        return 2
    return connect(a.target, a.env_file.expanduser(), a.stdin, a.no_verify)


if __name__ == "__main__":
    sys.exit(main())
