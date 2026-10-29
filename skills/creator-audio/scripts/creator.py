#!/usr/bin/env python3
"""creator.py — provider detection, routing, and fallback for creator-skills.

Subcommands (all print JSON on stdout):
  detect                         Probe which providers this machine can use.
  plan   --task T                Ordered providers for a task after config + capability filtering.
  image  --prompt P --out F      Generate/edit one image.
  video  --prompt P --out F      Generate one video clip.
  speech --text T --out F        Text-to-speech voiceover.
  music  --prompt P --out F      Music track.
  sfx    --prompt P --out F      Sound effect.
  adopt  --src S --out F         Move a downloaded file into place, fixing format/extension.
  tashkeel-check --text T        Arabic words that must get tashkeel before TTS (speech runs it too).
  verify --audio A --text T      Transcribe a voiceover (STT) and list words read differently (speech --verify).

Keys are read from the environment, then ./.env, then ~/.config/creator-skills/.env
(see connect.py to add them safely).

Stdlib only (Python 3.9+). Exit codes: 0 ok, 1 all failed, 2 bad usage,
3 needs a manual (browser) provider, 4 blocked by content policy,
5 Arabic text needs tashkeel before TTS (nothing was sent),
6 verify: the transcript differs from the script (listen to the listed differences).
"""
from __future__ import annotations

import argparse
import base64
import glob
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HOME = Path.home()
TASKS = ("image", "video", "speech", "music", "sfx")

# --------------------------------------------------------------------------- env files

ENV_KEYS = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ELEVENLABS_API_KEY",
            "AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "HIGGSFIELD_BIN", "AGY_BIN", "CODEX_BIN",
            "GCLOUD_BIN", "CREATOR_SKILLS_CONFIG")
USER_ENV_FILE = HOME / ".config" / "creator-skills" / ".env"


def env_files() -> list[Path]:
    files = [os.environ.get("CREATOR_SKILLS_ENV"), ".env", str(USER_ENV_FILE)]
    return [Path(f).expanduser() for f in files if f and Path(f).expanduser().is_file()]


def parse_env(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text(errors="replace").splitlines():
        m = re.match(r"^\s*(?:export\s+)?([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$", line)
        if not m or line.lstrip().startswith("#"):
            continue
        val = m.group(2)
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        else:
            val = val.split(" #")[0].strip()
        out[m.group(1)] = val
    return out


def load_env() -> list[str]:
    """Load known keys from .env files without overriding the real environment.
    Earlier files win (CREATOR_SKILLS_ENV, ./.env, ~/.config/creator-skills/.env)."""
    loaded = []
    for f in env_files():
        for k, v in parse_env(f).items():
            if k in ENV_KEYS and v and not os.environ.get(k):
                os.environ[k] = v
                loaded.append(str(f))
    return sorted(set(loaded))


# --------------------------------------------------------------------------- providers
# Per-task capability dicts. Absent task = provider cannot do it.

PROVIDERS = {
    "higgsfield": {"kind": "cli", "label": "Higgsfield CLI", "tasks": {
        "image": {"refs": True, "transparent": False, "max": "4k"},
        "video": {"refs": True, "end_frame": True},
        "music": {}, "sfx": {}}},
    "google-api": {"kind": "api", "label": "Google Gemini API (key)", "tasks": {
        "image": {"refs": True, "transparent": False, "max": "4k"},
        "video": {"refs": True, "end_frame": True},
        "speech": {}, "music": {}}},
    "openai-api": {"kind": "api", "label": "OpenAI API (key)", "tasks": {
        "image": {"refs": True, "transparent": True, "max": "4k"},
        "speech": {}}},
    "elevenlabs": {"kind": "api", "label": "ElevenLabs API (key)", "tasks": {
        "speech": {}, "music": {"max_s": 300}, "sfx": {}}},
    "google-cloud-tts": {"kind": "api", "label": "Google Cloud Text-to-Speech (gcloud auth)", "tasks": {
        "speech": {}}},
    "azure-tts": {"kind": "api", "label": "Azure AI Speech (key + region)", "tasks": {
        "speech": {}}},
    "aistudio-browser": {"kind": "browser", "label": "Google AI Studio speech (computer use)", "tasks": {
        "speech": {}}},
    "agy": {"kind": "agent-cli", "label": "Antigravity CLI (agy)", "tasks": {
        "image": {"refs": False, "transparent": False, "max": "1k"}}},
    "codex": {"kind": "agent-cli", "label": "Codex CLI (ChatGPT plan)", "tasks": {
        "image": {"refs": True, "transparent": True, "max": "2k"}}},
    "gemini-browser": {"kind": "browser", "label": "Gemini web app (computer use)", "tasks": {
        "image": {"refs": True, "transparent": False, "max": "2k"},
        "video": {"refs": True, "end_frame": False}}},
    "flow-browser": {"kind": "browser", "label": "Google Flow (computer use)", "tasks": {
        "image": {"refs": True, "transparent": False, "max": "2k"},
        "video": {"refs": True, "end_frame": True}}},
}

DEFAULT_ORDER = {
    "quality": {
        "image": ["higgsfield", "google-api", "openai-api", "agy", "codex", "gemini-browser", "flow-browser"],
        "video": ["higgsfield", "google-api", "flow-browser", "gemini-browser"],
        "speech": ["elevenlabs", "google-api", "google-cloud-tts", "azure-tts", "openai-api", "aistudio-browser"],
        "music": ["elevenlabs", "google-api", "higgsfield"],
        "sfx": ["elevenlabs", "higgsfield"],
    },
    "cost": {
        "image": ["agy", "codex", "higgsfield", "google-api", "openai-api", "gemini-browser", "flow-browser"],
        "video": ["flow-browser", "gemini-browser", "higgsfield", "google-api"],
        "speech": ["google-api", "aistudio-browser", "google-cloud-tts", "azure-tts", "elevenlabs", "openai-api"],
        "music": ["google-api", "elevenlabs", "higgsfield"],
        "sfx": ["elevenlabs", "higgsfield"],
    },
}

# Language-specific speech orders (used when --lang is given and config has no override).
# Arabic: Google first (strong on Egyptian + MSA, prompt-steerable), Azure next (per-country
# dialect voices), then the rest.
LANG_ORDER = {
    "speech": {
        "ar": ["google-api", "google-cloud-tts", "azure-tts", "elevenlabs", "openai-api", "aistudio-browser"],
    },
}

# Azure neural voices per Arabic locale (female, male).
AZURE_AR_VOICES = {
    "ar-EG": ("SalmaNeural", "ShakirNeural"), "ar-SA": ("ZariyahNeural", "HamedNeural"),
    "ar-AE": ("FatimaNeural", "HamdanNeural"), "ar-KW": ("NouraNeural", "FahedNeural"),
    "ar-QA": ("AmalNeural", "MoazNeural"), "ar-BH": ("LailaNeural", "AliNeural"),
    "ar-OM": ("AyshaNeural", "AbdullahNeural"), "ar-IQ": ("RanaNeural", "BasselNeural"),
    "ar-SY": ("AmanyNeural", "LaithNeural"), "ar-LB": ("LaylaNeural", "RamiNeural"),
    "ar-JO": ("SanaNeural", "TaimNeural"), "ar-MA": ("MounaNeural", "JamalNeural"),
    "ar-DZ": ("AminaNeural", "IsmaelNeural"), "ar-TN": ("ReemNeural", "HediNeural"),
    "ar-LY": ("ImanNeural", "OmarNeural"), "ar-YE": ("MaryamNeural", "SalehNeural"),
}
# Dialects without their own Azure voice -> closest locale that has one.
AZURE_AR_NEAREST = {"ar-PS": "ar-JO", "ar-SD": "ar-EG", "ar": "ar-SA", "ar-001": "ar-SA"}
ARABIC_DIALECT_NAMES = {
    "ar": "Modern Standard Arabic (Fusha)", "ar-001": "Modern Standard Arabic (Fusha)",
    "ar-EG": "Egyptian (Cairene) Arabic", "ar-SA": "Saudi (Najdi) Arabic", "ar-AE": "Emirati Gulf Arabic",
    "ar-KW": "Kuwaiti Gulf Arabic", "ar-QA": "Qatari Gulf Arabic", "ar-BH": "Bahraini Gulf Arabic",
    "ar-OM": "Omani Arabic", "ar-IQ": "Iraqi Arabic", "ar-SY": "Syrian Levantine Arabic",
    "ar-LB": "Lebanese Levantine Arabic", "ar-JO": "Jordanian Levantine Arabic",
    "ar-PS": "Palestinian Levantine Arabic", "ar-MA": "Moroccan Darija", "ar-DZ": "Algerian Arabic",
    "ar-TN": "Tunisian Arabic", "ar-LY": "Libyan Arabic", "ar-YE": "Yemeni Arabic", "ar-SD": "Sudanese Arabic",
}

DEFAULT_MODELS = {
    "higgsfield": {"image": "gpt_image_2_5", "video": "seedance_2_5", "music": "seed_audio", "sfx": "seed_audio"},
    "google-api": {"image": "gemini-nano-banana-2.1", "video": "gemini-omni-1.1-flash",
                   "speech": "gemini-3.8-flash-tts", "music": "lyria-3-clip-preview"},
    "openai-api": {"image": "gpt-image-2.5-flare", "speech": "gpt-4o-mini-tts"},
    "elevenlabs": {"speech": "eleven_multilingual_v2", "music": "music_v1", "sfx": "eleven_text_to_sound_v2"},
}

DEFAULT_MODELS["google-cloud-tts"] = {"speech": "gemini-2.5-flash-tts"}

DEFAULT_VOICES = {"google-api": "Kore", "openai-api": "marin", "elevenlabs": None,
                  "google-cloud-tts": "Kore", "azure-tts": None}

RATIO_WORDS = {
    "1:1": "1:1 square", "16:9": "16:9 widescreen landscape", "9:16": "9:16 vertical portrait",
    "4:3": "4:3 landscape", "3:4": "3:4 portrait", "3:2": "3:2 landscape", "2:3": "2:3 portrait",
    "4:5": "4:5 portrait", "5:4": "5:4 landscape", "21:9": "21:9 ultrawide",
}
SIZE_RANK = {"1k": 1, "2k": 2, "4k": 3}
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")
AUDIO_EXT = (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".opus")
VIDEO_EXT = (".mp4", ".mov", ".webm")


# --------------------------------------------------------------------------- config

def config_path() -> Path | None:
    for c in (os.environ.get("CREATOR_SKILLS_CONFIG"), "creator-skills.json",
              str(HOME / ".config" / "creator-skills" / "config.json")):
        if c and Path(c).expanduser().is_file():
            return Path(c).expanduser()
    return None


def load_config() -> dict:
    p = config_path()
    if not p:
        return {}
    try:
        return json.loads(p.read_text())
    except Exception as e:  # noqa: BLE001
        print(f"warning: could not parse {p}: {e}", file=sys.stderr)
        return {}


def model_for(cfg: dict, provider: str, task: str, override: str | None = None) -> str | None:
    return override or cfg.get("models", {}).get(provider, {}).get(task) or DEFAULT_MODELS.get(provider, {}).get(task)


def voice_for(cfg: dict, provider: str, override: str | None, lang: str | None = None) -> str | None:
    """--voice > voices["<provider>:<lang>"] > voices["<provider>:<base>"] > voices[provider] > default."""
    if override:
        return override
    voices = cfg.get("voices", {})
    if lang:
        for key in (f"{provider}:{lang}", f"{provider}:{lang.split('-')[0]}"):
            if voices.get(key):
                return voices[key]
    return voices.get(provider) or DEFAULT_VOICES.get(provider)


# --------------------------------------------------------------------------- detection

def _run(cmd: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except FileNotFoundError:
        return 127, "not installed"
    except subprocess.TimeoutExpired:
        return 124, "timed out"


def _which(name: str, env_override: str | None = None) -> str | None:
    if env_override and os.environ.get(env_override):
        p = os.environ[env_override]
        return p if Path(p).exists() else None
    found = shutil.which(name)
    if not found and (HOME / ".local/bin" / name).exists():
        found = str(HOME / ".local/bin" / name)
    return found


def google_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


BROWSER_APPS = ("gemini", "flow", "aistudio")


def browser_enabled(cfg: dict, pid: str) -> bool:
    """Computer-use providers are ON by default; the user opts out with browser.enabled: false
    or by narrowing browser.apps."""
    browser = cfg.get("browser", {})
    return browser.get("enabled", True) is not False and pid.split("-")[0] in browser.get("apps", BROWSER_APPS)


def detect_one(pid: str, cfg: dict) -> dict:
    out = {"id": pid, "label": PROVIDERS[pid]["label"], "kind": PROVIDERS[pid]["kind"],
           "tasks": list(PROVIDERS[pid]["tasks"]), "available": False, "reason": ""}
    if pid in cfg.get("disabled", []):
        out["reason"] = "disabled in config"
        return out
    if pid == "higgsfield":
        b = _which("higgsfield", "HIGGSFIELD_BIN")
        if not b:
            out["reason"] = "higgsfield CLI not installed"
        else:
            code, msg = _run([b, "account", "status"])
            out["available"] = code == 0
            out["reason"] = "ok" if code == 0 else f"not signed in (run: higgsfield auth login) — {msg[:120]}"
    elif pid == "google-api":
        out["available"] = bool(google_key())
        out["reason"] = "ok" if out["available"] else "GEMINI_API_KEY / GOOGLE_API_KEY not set"
    elif pid == "openai-api":
        out["available"] = bool(os.environ.get("OPENAI_API_KEY"))
        out["reason"] = "ok" if out["available"] else "OPENAI_API_KEY not set"
    elif pid == "elevenlabs":
        out["available"] = bool(os.environ.get("ELEVENLABS_API_KEY"))
        out["reason"] = "ok" if out["available"] else "ELEVENLABS_API_KEY not set"
    elif pid == "agy":
        if not _which("agy", "AGY_BIN"):
            out["reason"] = "agy not installed"
        else:
            signed_in = any((HOME / ".gemini" / p).exists() for p in
                            ("antigravity-oauth-token", "antigravity-cli/antigravity-oauth-token"))
            out["available"] = True
            out["reason"] = "ok" if signed_in else "installed; sign-in not confirmed (run agy once interactively)"
    elif pid == "codex":
        b = _which("codex", "CODEX_BIN")
        if not b:
            out["reason"] = "codex not installed"
        else:
            code, msg = _run([b, "login", "status"])
            if "parse error" in msg.lower():
                out["reason"] = "~/.codex/config.toml has a syntax error — fix it first"
            else:
                out["available"] = code == 0
                out["reason"] = "ok" if code == 0 else "not logged in (run: codex login)"
    elif pid == "google-cloud-tts":
        b = _which("gcloud", "GCLOUD_BIN")
        if not b:
            out["reason"] = "gcloud not installed (Cloud TTS needs OAuth, not an API key)"
        else:
            code, _ = _run([b, "auth", "application-default", "print-access-token"], timeout=30)
            out["available"] = code == 0
            out["reason"] = "ok" if code == 0 else "run: gcloud auth application-default login"
    elif pid == "azure-tts":
        ok = bool(os.environ.get("AZURE_SPEECH_KEY") and os.environ.get("AZURE_SPEECH_REGION"))
        out["available"] = ok
        out["reason"] = "ok" if ok else "AZURE_SPEECH_KEY / AZURE_SPEECH_REGION not set"
    elif pid in ("gemini-browser", "flow-browser", "aistudio-browser"):
        out["available"] = browser_enabled(cfg, pid)
        out["reason"] = ("ok (manual: agent drives the browser)" if out["available"]
                         else "browser use turned off in config (browser.enabled: false or app not in browser.apps)")
    return out


def detect(cfg: dict) -> list[dict]:
    local = {"id": "local", "label": "Local ffmpeg (media.py)", "kind": "local", "tasks": ["compose"],
             "available": bool(shutil.which("ffmpeg")),
             "reason": "ok" if shutil.which("ffmpeg") else "ffmpeg not installed"}
    return [detect_one(pid, cfg) for pid in PROVIDERS] + [local]


# --------------------------------------------------------------------------- planning

def resolve_order(cfg: dict, task: str, profile: str, lang: str | None) -> list[str]:
    """Config `order["<task>:<lang>"]` > `order["<task>:<base>"]` > `order[task]` >
    built-in language order > profile default."""
    orders = cfg.get("order", {})
    if lang:
        base = lang.split("-")[0]
        for key in (f"{task}:{lang}", f"{task}:{base}"):
            if orders.get(key):
                return orders[key]
    if orders.get(task):
        return orders[task]
    if lang and LANG_ORDER.get(task, {}).get(lang.split("-")[0]):
        return LANG_ORDER[task][lang.split("-")[0]]
    return DEFAULT_ORDER.get(profile, DEFAULT_ORDER["quality"])[task]


def plan(cfg: dict, task: str, needs: set[str], size: str = "1k",
         profile: str | None = None, only: str | None = None, lang: str | None = None) -> dict:
    profile = profile or cfg.get("profile", "quality")
    order = [only] if only else resolve_order(cfg, task, profile, lang)
    status = {d["id"]: d for d in detect(cfg)}
    chosen, skipped, smaller = [], [], []
    for pid in order:
        if pid not in PROVIDERS:
            skipped.append({"id": pid, "why": "unknown provider"}); continue
        if not status[pid]["available"]:
            skipped.append({"id": pid, "why": status[pid]["reason"]}); continue
        caps = PROVIDERS[pid]["tasks"].get(task)
        if caps is None:
            skipped.append({"id": pid, "why": f"cannot do {task}"}); continue
        missing = [n for n in needs if n in ("refs", "transparent", "end_frame") and not caps.get(n)]
        if missing:
            skipped.append({"id": pid, "why": f"no {', '.join(missing)} support"}); continue
        step = {"id": pid, "kind": PROVIDERS[pid]["kind"], "manual": PROVIDERS[pid]["kind"] == "browser"}
        if task == "image" and SIZE_RANK.get(size, 1) > SIZE_RANK.get(caps.get("max", "1k"), 1):
            # Too small natively: keep it as a late fallback, generate at its max, upscale locally.
            smaller.append({**step, "generate_at": caps["max"], "upscale_to": size}); continue
        chosen.append(step)
    # Scriptable native-size routes first, then scriptable capped routes (upscaled), then manual ones.
    order_out = [s for s in chosen if not s["manual"]] + [s for s in smaller if not s["manual"]] + \
                [s for s in chosen if s["manual"]] + [s for s in smaller if s["manual"]]
    result = {"task": task, "profile": profile, "order": order_out, "skipped": skipped}
    if lang:
        result["lang"] = lang
    return result


# --------------------------------------------------------------------------- http + files

class ProviderError(Exception):
    """kind: auth | quota | policy | transient | unsupported | failed"""

    def __init__(self, kind: str, msg: str):
        super().__init__(msg)
        self.kind = kind


def classify_text(code: int, text: str) -> str:
    t = text.lower()
    if any(w in t for w in ("safety", "policy", "moderation", "blocked", "nsfw", "prohibited")):
        return "policy"
    if code in (401, 403) or "unauthorized" in t or "invalid api key" in t or "not authenticated" in t:
        return "auth"
    if code == 429 or any(w in t for w in ("quota", "billing", "insufficient", "credit", "rate limit", "usage limit")):
        return "quota"
    if code == 404 or "not found" in t and "model" in t:
        return "unsupported"
    if code >= 500 or code in (408, 124):
        return "transient"
    return "failed"


def _send(req: urllib.request.Request, timeout: int, raw: bool = False):
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return body if raw else json.loads(body.decode())
    except urllib.error.HTTPError as e:
        text = e.read().decode(errors="replace")[:600]
        raise ProviderError(classify_text(e.code, text), f"HTTP {e.code}: {text}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise ProviderError("transient", str(e)) from None


def http_json(url: str, body: dict, headers: dict, timeout: int = 300, raw: bool = False):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    return _send(req, timeout, raw)


def http_get(url: str, headers: dict | None = None, timeout: int = 300, raw: bool = True):
    return _send(urllib.request.Request(url, headers=headers or {}), timeout, raw)


def find_media(obj, kind: str) -> tuple[str, str] | None:
    """Last media payload of `kind` (image|video|audio) in a JSON response -> ("b64"|"uri", value)."""
    found: list[tuple[str, str]] = []

    def walk(o):
        if isinstance(o, dict):
            mime = str(o.get("mime_type") or o.get("mimeType") or "")
            typ = o.get("type")
            match = typ == kind or mime.startswith(kind + "/") or (kind == "image" and "b64_json" in o)
            data = o.get("data") or o.get("b64_json")
            if match and isinstance(data, str) and len(data) > 500:
                found.append(("b64", data))
            elif match and isinstance(o.get("uri"), str):
                found.append(("uri", o["uri"]))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    return found[-1] if found else None


def sniff(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "wav"
    if data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return "mp3"
    if data[:4] == b"OggS":
        return "ogg"
    if data[:4] == b"fLaC":
        return "flac"
    if data[4:8] == b"ftyp":
        return "mp4"
    if data[:4] == b"\x1aE\xdf\xa3":
        return "webm"
    return "bin"


def save_media(data: bytes, out: Path) -> Path:
    """Write bytes to `out`; if the real format differs from the extension, convert with ffmpeg
    or fall back to the real extension."""
    out.parent.mkdir(parents=True, exist_ok=True)
    real = sniff(data)
    want = out.suffix.lower().lstrip(".").replace("jpeg", "jpg").replace("m4a", "mp4").replace("mov", "mp4")
    if real == "bin":
        raise ProviderError("failed", "response was not a recognizable media file")
    if not want or want == real:
        target = out if want else out.with_suffix("." + real)
        target.write_bytes(data)
        return target
    tmp = out.with_name(out.stem + f".tmp-{uuid.uuid4().hex[:6]}.{real}")
    tmp.write_bytes(data)
    if shutil.which("ffmpeg"):
        code, _ = _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), str(out)], timeout=300)
        if code == 0 and out.exists():
            tmp.unlink(missing_ok=True)
            return out
    fixed = out.with_suffix("." + real)
    tmp.rename(fixed)
    return fixed


def newest_file_since(patterns: list[str], since: float, exts: tuple) -> Path | None:
    files = []
    for pat in patterns:
        for f in glob.glob(os.path.expanduser(pat), recursive=True):
            p = Path(f)
            if p.is_file() and p.suffix.lower() in exts and p.stat().st_mtime >= since:
                files.append(p)
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def b64_file(path: str) -> tuple[str, str]:
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return mime, base64.b64encode(Path(path).read_bytes()).decode()


def urls_in(text: str) -> list[str]:
    return re.findall(r"https?://[^\s\"'<>\\]+", text)


def ratio_words(ratio: str) -> str:
    return RATIO_WORDS.get(ratio, ratio)


def openai_size(ratio: str, size: str) -> str:
    w, h = (int(x) for x in ratio.split(":"))
    if w == h:
        side = {"1k": 1024, "2k": 2048, "4k": 2880}.get(size, 1024)
        return f"{side}x{side}"
    long_edge = {"1k": 1536, "2k": 2560, "4k": 3840}.get(size, 1536)
    W, H = (long_edge, long_edge * h / w) if w > h else (long_edge * w / h, long_edge)
    if W * H > 8_294_400:
        k = (8_294_400 / (W * H)) ** 0.5
        W, H = W * k, H * k
    W, H = int(W // 16) * 16, int(H // 16) * 16
    while W * H < 655_360:
        W, H = W + 16 * (w >= h), H + 16 * (h > w)
    return f"{W}x{H}"


# --------------------------------------------------------------------------- higgsfield (shared)

def higgsfield_run(a, model: str, args: list[str], exts: tuple) -> Path:
    b = _which("higgsfield", "HIGGSFIELD_BIN")
    code, out = _run([b, "generate", "create", model, *args, "--wait", "--json",
                      "--wait-timeout", f"{max(60, a.timeout)}s"], timeout=a.timeout + 60)
    if code != 0:
        raise ProviderError(classify_text(124 if code == 124 else 0, out), out[-400:])
    urls = [u for u in urls_in(out) if any(e in u.lower() for e in exts)] or urls_in(out)
    if not urls:
        raise ProviderError("failed", "no result URL in higgsfield output")
    return save_media(http_get(urls[0], timeout=300), a.out)


# --------------------------------------------------------------------------- google interactions (shared)

GOOGLE_BASE = "https://generativelanguage.googleapis.com/v1beta"


def google_interact(body: dict, timeout: int) -> dict:
    return http_json(f"{GOOGLE_BASE}/interactions", body, {"x-goog-api-key": google_key()}, timeout)


def google_fetch(found: tuple[str, str], timeout: int) -> bytes:
    kind, val = found
    if kind == "b64":
        return base64.b64decode(val)
    headers = {"x-goog-api-key": google_key()}
    m = re.search(r"/files/([^:/?]+)", val)
    if m:  # wait until the file is ACTIVE
        deadline = time.time() + timeout
        while time.time() < deadline:
            meta = http_get(f"{GOOGLE_BASE}/files/{m.group(1)}", headers, 60, raw=False)
            state = meta.get("state", "ACTIVE")
            if state == "ACTIVE":
                break
            if state == "FAILED":
                raise ProviderError("failed", "Google file processing failed")
            time.sleep(5)
    return http_get(val, headers, timeout)


def google_media_or_raise(resp: dict, kind: str) -> tuple[str, str]:
    found = find_media(resp, kind)
    if not found:
        txt = json.dumps(resp)[:500]
        raise ProviderError(classify_text(0, txt) if "block" in txt.lower() or "safety" in txt.lower() else "failed",
                            f"no {kind} in response: {txt[:200]}")
    return found


# --------------------------------------------------------------------------- image adapters

def img_higgsfield(a, cfg):
    model = model_for(cfg, "higgsfield", "image", a.model)
    args = ["--prompt", a.prompt, "--aspect_ratio", a.ratio, "--resolution", a.size]
    for r in a.ref:
        args += ["--image", r]
    return higgsfield_run(a, model, args, IMAGE_EXT), model


def img_google(a, cfg):
    model = model_for(cfg, "google-api", "image", a.model)
    parts = [{"type": "text", "text": a.prompt}]
    for r in a.ref:
        mime, data = b64_file(r)
        parts.append({"type": "image", "mime_type": mime, "data": data})
    body = {"model": model, "input": parts,
            "response_format": {"type": "image", "aspect_ratio": a.ratio, "image_size": a.size.upper()}}
    try:
        resp = google_interact(body, a.timeout)
    except ProviderError as e:
        if e.kind != "unsupported":
            raise
        legacy = {"contents": [{"parts": [{"text": a.prompt}] + [
            {"inline_data": {"mime_type": p["mime_type"], "data": p["data"]}} for p in parts[1:]]}],
            "generationConfig": {"responseModalities": ["IMAGE"],
                                 "imageConfig": {"aspectRatio": a.ratio, "imageSize": a.size.upper()}}}
        resp = http_json(f"{GOOGLE_BASE}/models/{model}:generateContent", legacy,
                         {"x-goog-api-key": google_key()}, a.timeout)
    return save_media(google_fetch(google_media_or_raise(resp, "image"), a.timeout), a.out), model


def img_openai(a, cfg):
    key = os.environ["OPENAI_API_KEY"]
    model = model_for(cfg, "openai-api", "image", a.model)
    size = openai_size(a.ratio, a.size)
    headers = {"Authorization": f"Bearer {key}"}
    if a.ref:
        fields = {"model": model, "prompt": a.prompt, "size": size}
        if a.transparent:
            fields["background"] = "transparent"
        boundary = uuid.uuid4().hex
        body = b""
        for k, v in fields.items():
            body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
        for r in a.ref:
            mime = mimetypes.guess_type(r)[0] or "image/png"
            body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image[]\"; filename=\"{Path(r).name}\"\r\n"
                     f"Content-Type: {mime}\r\n\r\n").encode() + Path(r).read_bytes() + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        req = urllib.request.Request("https://api.openai.com/v1/images/edits", data=body,
                                     headers={**headers, "Content-Type": f"multipart/form-data; boundary={boundary}"})
        resp = _send(req, a.timeout)
    else:
        body = {"model": model, "prompt": a.prompt, "size": size}
        if a.transparent:
            body.update(background="transparent", output_format="png")
        resp = http_json("https://api.openai.com/v1/images/generations", body, headers, a.timeout)
    found = find_media(resp, "image")
    if not found:
        raise ProviderError("failed", "no image in response")
    return save_media(base64.b64decode(found[1]), a.out), model


def _agent_image_prompt(a, target: Path, tool: str, extra: str = "") -> str:
    return (f"Use your {tool} to create exactly one image.{extra}\n"
            f"Prompt: {a.prompt}\n\nAspect ratio: {ratio_words(a.ratio)}.\n"
            f"Save it to this absolute path: {target}\n"
            "Do not create or modify any other files. Reply with only the absolute path.")


def img_agy(a, cfg):
    b = _which("agy", "AGY_BIN")
    out_dir = a.out.parent.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / (a.out.stem + ".jpg")  # agy's generate_image always returns JPEG
    cmd = [b, "-p", _agent_image_prompt(a, target, "generate_image tool"), "--dangerously-skip-permissions",
           "--add-dir", str(out_dir), "--print-timeout", f"{max(60, a.timeout)}s"]
    model = model_for(cfg, "agy", "image", a.model)
    if model:
        cmd += ["--model", model]
    start = time.time()
    code, out = _run(cmd, timeout=a.timeout + 30)
    scratch = HOME / ".gemini" / "antigravity-cli" / "scratch"
    src = target if target.exists() and target.stat().st_mtime >= start else newest_file_since(
        [str(out_dir / "*"), str(scratch / "**" / "*")], start, IMAGE_EXT)
    if not src:
        raise ProviderError(classify_text(0, out), f"agy produced no image (exit {code}): {out[-300:]}")
    result = save_media(src.read_bytes(), a.out)
    if src.resolve() != result.resolve() and (src == target or scratch in src.resolve().parents):
        src.unlink(missing_ok=True)
    return result, model or "agy-default"


def img_codex(a, cfg):
    b = _which("codex", "CODEX_BIN")
    out_dir = a.out.parent.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    target = a.out.resolve()
    extra = (" Use the attached image(s) as references." if a.ref else "") + \
            (" Use a transparent background (PNG)." if a.transparent else "")
    cmd = [b, "exec", "--skip-git-repo-check", "--sandbox", "workspace-write", "-C", str(out_dir)]
    model = model_for(cfg, "codex", "image", a.model)
    if model:
        cmd += ["-m", model]
    for r in a.ref:
        cmd += ["-i", str(Path(r).resolve())]
    cmd.append(_agent_image_prompt(a, target, "built-in image generation tool (imagegen / image_gen)", extra))
    start = time.time()
    code, out = _run(cmd, timeout=a.timeout + 30)
    src = target if target.exists() and target.stat().st_mtime >= start else newest_file_since(
        [str(out_dir / "*"), "~/.codex/generated_images/**/*"], start, IMAGE_EXT)
    if not src:
        kind = "unsupported" if "unknown tool" in out.lower() else classify_text(0, out)
        raise ProviderError(kind, f"codex produced no image (exit {code}): {out[-300:]}")
    return (save_media(src.read_bytes(), a.out) if src != target else src), model or "codex-default"


# --------------------------------------------------------------------------- video adapters

def vid_higgsfield(a, cfg):
    model = model_for(cfg, "higgsfield", "video", a.model)
    args = ["--prompt", a.prompt, "--aspect_ratio", a.ratio, "--duration", str(a.duration),
            "--resolution", a.resolution]
    if a.start or a.end or a.ref:
        args += ["--mode", "omni_reference"]
    if a.start:
        args += ["--start-image", a.start]
    if a.end:
        args += ["--end-image", a.end]
    for r in a.ref:
        args += ["--image", r]
    return higgsfield_run(a, model, args, VIDEO_EXT), model


def vid_google(a, cfg):
    model = model_for(cfg, "google-api", "video", a.model)
    if a.ratio not in ("16:9", "9:16"):
        raise ProviderError("unsupported", "Gemini Omni video supports only 16:9 and 9:16")
    parts, task = [], "text_to_video"
    for img in [p for p in (a.start, a.end) if p]:
        mime, data = b64_file(img)
        parts.append({"type": "image", "mime_type": mime, "data": data})
    if a.start:
        task = "image_to_video"
    for r in a.ref:
        mime, data = b64_file(r)
        parts.append({"type": "image", "mime_type": mime, "data": data})
    if a.ref and not a.start:
        task = "reference_to_video"
    lead = ("Animate starting exactly from the first image" + (" and ending exactly on the second image" if a.end else "")
            + ". ") if a.start else ""
    text = f"{lead}{a.prompt}\n\nTarget length: about {a.duration} seconds."
    parts.append({"type": "text", "text": text})
    body = {"model": model, "input": parts, "store": False, "background": False,
            "generation_config": {"video_config": {"task": task}},
            "response_format": {"type": "video", "aspect_ratio": a.ratio, "resolution": a.resolution,
                                "delivery": "uri"}}
    resp = google_interact(body, a.timeout)
    return save_media(google_fetch(google_media_or_raise(resp, "video"), a.timeout), a.out), model


# --------------------------------------------------------------------------- audio adapters

def _eleven_headers():
    return {"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}


def _eleven_voice(cfg, override):
    v = voice_for(cfg, "elevenlabs", override)
    if v:
        return v
    voices = http_get("https://api.elevenlabs.io/v2/voices?page_size=10", _eleven_headers(), 60, raw=False)
    items = voices.get("voices", [])
    if not items:
        raise ProviderError("failed", "no ElevenLabs voices on this account; pass --voice")
    return items[0]["voice_id"]


def accent_style(a) -> str | None:
    """Delivery direction including the dialect implied by --lang (e.g. ar-EG -> Egyptian Arabic)."""
    parts = []
    if a.lang:
        name = ARABIC_DIALECT_NAMES.get(a.lang)
        if name:
            parts.append(f"Speak in natural, native {name}" +
                         (" with authentic colloquial pronunciation" if a.lang not in ("ar", "ar-001") else ""))
    if a.style:
        parts.append(a.style)
    return ". ".join(parts) or None


ELEVEN_LANG_MODELS = ("eleven_flash_v2_5", "eleven_turbo_v2_5", "eleven_v3", "eleven_v4")


def speech_elevenlabs(a, cfg):
    model = model_for(cfg, "elevenlabs", "speech", a.model)
    voice = _eleven_voice(cfg, voice_for(cfg, "elevenlabs", a.voice, a.lang))
    body = {"text": a.text, "model_id": model}
    if a.lang and model.startswith(ELEVEN_LANG_MODELS):
        body["language_code"] = a.lang.split("-")[0]
    if a.speed:
        body["voice_settings"] = {"speed": a.speed}
    data = http_json(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
                     body, _eleven_headers(), a.timeout, raw=True)
    return save_media(data, a.out), f"{model}/{voice}"


def speech_google(a, cfg):
    model = model_for(cfg, "google-api", "speech", a.model)
    voice = voice_for(cfg, "google-api", a.voice, a.lang)
    item = {"type": "text", "text": a.text}
    style = accent_style(a)
    if style:
        item["annotations"] = [{"type": "speech_metadata", "style": style}]
    body = {"model": model, "input": [{"type": "user_input", "content": [item]}],
            "response_format": {"type": "audio", "mime_type": "audio/wav", "sample_rate": 24000},
            "generation_config": {"speech_config": [{"voice": voice}]}}
    resp = google_interact(body, a.timeout)
    data = google_fetch(google_media_or_raise(resp, "audio"), a.timeout)
    if sniff(data) == "bin":  # older models return raw 24 kHz mono 16-bit PCM
        data = _wav_wrap(data, 24000)
    return save_media(data, a.out), f"{model}/{voice}"


def _wav_wrap(pcm: bytes, rate: int) -> bytes:
    import struct
    return (b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt " +
            struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16) + b"data" + struct.pack("<I", len(pcm)) + pcm)


def speech_openai(a, cfg):
    model = model_for(cfg, "openai-api", "speech", a.model)
    voice = voice_for(cfg, "openai-api", a.voice, a.lang)
    fmt = "wav" if a.out.suffix.lower() == ".wav" else "mp3"
    body = {"model": model, "input": a.text, "voice": voice, "response_format": fmt}
    style = accent_style(a)
    if style and "mini-tts" in model:
        body["instructions"] = style
    if a.speed:
        body["speed"] = a.speed
    data = http_json("https://api.openai.com/v1/audio/speech", body,
                     {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"}, a.timeout, raw=True)
    return save_media(data, a.out), f"{model}/{voice}"


def speech_google_cloud(a, cfg):
    """Cloud Text-to-Speech with Gemini-TTS (prompt-steerable accent). Auth via gcloud ADC."""
    model = model_for(cfg, "google-cloud-tts", "speech", a.model)
    voice = voice_for(cfg, "google-cloud-tts", a.voice, a.lang)
    gcloud = _which("gcloud", "GCLOUD_BIN")
    code, token = _run([gcloud, "auth", "application-default", "print-access-token"], timeout=30)
    if code != 0:
        raise ProviderError("auth", "gcloud auth application-default login required")
    headers = {"Authorization": f"Bearer {token.splitlines()[-1].strip()}"}
    code, project = _run([gcloud, "config", "get-value", "project"], timeout=30)
    project = project.splitlines()[-1].strip() if code == 0 and project else ""
    if project and project != "(unset)":
        headers["x-goog-user-project"] = project
    lang = a.lang or "en-US"
    if lang == "ar":
        lang = "ar-001"
    elif lang.startswith("ar-") and lang not in ("ar-EG", "ar-001", "ar-XA"):
        lang = "ar-001"  # other dialects: generic Arabic locale + accent prompt
    inp = {"text": a.text}
    style = accent_style(a)
    if style:
        inp["prompt"] = style
    body = {"input": inp, "voice": {"languageCode": lang, "name": voice, "modelName": model},
            "audioConfig": {"audioEncoding": "LINEAR16", **({"speakingRate": a.speed} if a.speed else {})}}
    resp = http_json("https://texttospeech.googleapis.com/v1/text:synthesize", body, headers, a.timeout)
    if not resp.get("audioContent"):
        raise ProviderError("failed", "no audioContent in response")
    return save_media(base64.b64decode(resp["audioContent"]), a.out), f"{model}/{voice}/{lang}"


def speech_azure(a, cfg):
    from xml.sax.saxutils import escape
    region, key = os.environ["AZURE_SPEECH_REGION"], os.environ["AZURE_SPEECH_KEY"]
    lang = a.lang or "en-US"
    voice = voice_for(cfg, "azure-tts", a.voice, a.lang)
    if not voice:
        lang = AZURE_AR_NEAREST.get(lang, lang)
        pair = AZURE_AR_VOICES.get(lang)
        if pair:
            voice = f"{lang}-{pair[0]}"
        elif lang.startswith("ar"):
            lang, voice = "ar-SA", "ar-SA-ZariyahNeural"
        else:
            voice = "en-US-AvaMultilingualNeural"
    text = escape(a.text)
    if a.speed:
        text = f"<prosody rate='{int((a.speed - 1) * 100):+d}%'>{text}</prosody>"
    ssml = (f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='{lang}'>"
            f"<voice name='{voice}'>{text}</voice></speak>")
    req = urllib.request.Request(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1", data=ssml.encode("utf-8"),
        headers={"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3", "User-Agent": "creator-skills"})
    data = _send(req, a.timeout, raw=True)
    return save_media(data, a.out), voice


def music_elevenlabs(a, cfg):
    model = model_for(cfg, "elevenlabs", "music", a.model)
    body = {"prompt": a.prompt, "model_id": model, "music_length_ms": int(a.duration * 1000),
            "force_instrumental": a.instrumental}
    data = http_json("https://api.elevenlabs.io/v1/music", body, _eleven_headers(), a.timeout, raw=True)
    return save_media(data, a.out), model


def music_google(a, cfg):
    model = model_for(cfg, "google-api", "music", a.model)
    prompt = a.prompt + (" Instrumental only, no vocals." if a.instrumental else "")
    if "clip" not in model:
        prompt += f" Length: about {int(a.duration)} seconds."
    resp = google_interact({"model": model, "input": prompt}, a.timeout)
    return save_media(google_fetch(google_media_or_raise(resp, "audio"), a.timeout), a.out), model


def music_higgsfield(a, cfg):
    model = model_for(cfg, "higgsfield", "music", a.model)
    prompt = a.prompt + (" Instrumental, no vocals." if a.instrumental else "")
    args = ["--prompt", prompt]
    if model != "seed_audio":
        args += ["--duration", str(int(a.duration))]
    return higgsfield_run(a, model, args, AUDIO_EXT), model


def sfx_elevenlabs(a, cfg):
    model = model_for(cfg, "elevenlabs", "sfx", a.model)
    body = {"text": a.prompt, "model_id": model, "loop": a.loop, "prompt_influence": 0.4}
    if a.duration:
        body["duration_seconds"] = max(0.5, min(30.0, a.duration))
    data = http_json("https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128",
                     body, _eleven_headers(), a.timeout, raw=True)
    return save_media(data, a.out), model


def sfx_higgsfield(a, cfg):
    model = model_for(cfg, "higgsfield", "sfx", a.model)
    args = ["--prompt", a.prompt]
    if model != "seed_audio" and a.duration:
        args += ["--duration", str(int(a.duration))]
    return higgsfield_run(a, model, args, AUDIO_EXT), model


ADAPTERS = {
    "image": {"higgsfield": img_higgsfield, "google-api": img_google, "openai-api": img_openai,
              "agy": img_agy, "codex": img_codex},
    "video": {"higgsfield": vid_higgsfield, "google-api": vid_google},
    "speech": {"elevenlabs": speech_elevenlabs, "google-api": speech_google, "openai-api": speech_openai,
               "google-cloud-tts": speech_google_cloud, "azure-tts": speech_azure},
    "music": {"elevenlabs": music_elevenlabs, "google-api": music_google, "higgsfield": music_higgsfield},
    "sfx": {"elevenlabs": sfx_elevenlabs, "higgsfield": sfx_higgsfield},
}


# --------------------------------------------------------------------------- Arabic tashkeel gate (before TTS)
# Undiacritized words whose reading changes the meaning. TTS engines guess, and a wrong guess
# changes a fact (real failures: «ثلثا» read as «ثلث», «عُشر» read as «عشرة»). If any of these
# appear WITHOUT a single haraka, speech generation stops until the host adds tashkeel.

TASHKEEL_RISKS = {
    "ثلث": "ثُلُث (a third)", "ثلثا": "ثُلُثا (two-thirds)", "ثلثي": "ثُلُثَي (two-thirds)",
    "ربع": "رُبْع (a quarter) · رَبْع (folk)", "خمس": "خُمْس (a fifth) · خَمْس (five)",
    "سدس": "سُدْس (a sixth)", "سبع": "سُبْع (a seventh) · سَبْع (seven)",
    "ثمن": "ثَمَن (price) · ثُمْن (an eighth)", "تسع": "تُسْع (a ninth) · تِسْع (nine)",
    "عشر": "عُشْر (a tenth) · عَشْر (ten)", "دين": "دَيْن (debt) · دِين (religion)",
    "عقد": "عَقْد (contract) · عِقْد (decade)", "ذهب": "ذَهَب (gold) · ذَهَبَ (went)",
    "ملك": "مَلِك (king) · مُلْك (ownership) · مَلَكَ (owned)", "سلم": "سَلَم (forward sale) · سِلْم (peace)",
    "صرف": "صَرْف (exchange) · صُرِف (was spent)", "حكم": "حُكْم (ruling) · حَكَم (referee)",
}
# noun/verb pairs: with the article «ال» only the noun reading is possible
_NOUN_VERB = {"ذهب", "صرف"}
_HARAKAT = re.compile("[\u064B-\u0652\u0670]")
_AR_WORD = re.compile("[\u0621-\u064A\u064B-\u0652\u0670]+")
_PREFIXES = ("وال", "فال", "بال", "كال", "لل", "ال", "و", "ف", "ب", "ل", "ك")
_SUFFIXES = ("هما", "هم", "ها", "نا", "ه", "ك")


def _stems(word: str) -> set[str]:
    out = {word}
    for p in _PREFIXES:
        if word.startswith(p) and len(word) - len(p) >= 3:
            out.add(word[len(p):])
    for w in list(out):
        for s in _SUFFIXES:
            if w.endswith(s) and len(w) - len(s) >= 3:
                out.add(w[:-len(s)])
    return out


def is_arabic(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and sum("\u0600" <= c <= "\u06FF" for c in letters) / len(letters) > 0.5


def tashkeel_check(text: str) -> dict:
    """{"ambiguous": [...] (blocking), "advice": [...] (non-blocking)} for Arabic TTS text."""
    amb, seen = [], set()
    for ln, line in enumerate(text.splitlines(), 1):
        for m in _AR_WORD.finditer(line):
            w = m.group(0)
            if _HARAKAT.search(w):
                continue
            hit = next((s for s in _stems(w) if s in TASHKEEL_RISKS), None)
            if hit in _NOUN_VERB and re.match("^[وفبك]?(ال|لل)", w):
                continue
            if hit and (w, ln) not in seen:
                seen.add((w, ln))
                amb.append({"line": ln, "word": w, "readings": TASHKEEL_RISKS[hit]})
    advice = []
    if re.search(r"[0-9\u0660-\u0669]", text):
        advice.append("digits found: write numbers as words with case endings (e.g. «ثلاثةُ ملايين»), "
                      "or verify how the TTS reads them")
    if "%" in text or "٪" in text:
        advice.append("percent sign found: write «في المئة» / «بالمئة»")
    acr = sorted(set(re.findall(r"\b[A-Z]{2,6}\b", text)))
    if acr:
        advice.append(f"acronyms {', '.join(acr[:8])}: check the reading; spell letters out if needed")
    return {"ambiguous": amb, "advice": advice}


# --------------------------------------------------------------------------- speech verify (STT round-trip)
# TTS can read a script wrong in ways that change facts (numbers, fractions, names). Transcribe the
# audio back and diff it against the script. Report-only: the host re-voices the lines that changed.

STT_ORDER = ("elevenlabs", "openai-api", "google-api")
DEFAULT_MODELS["elevenlabs"]["stt"] = "scribe_v2"
DEFAULT_MODELS["openai-api"]["stt"] = "gpt-4o-transcribe"
DEFAULT_MODELS["google-api"]["stt"] = "gemini-flash-latest"
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def _multipart(fields: dict, files: dict) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    for k, path in files.items():
        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{Path(path).name}\"\r\n"
                 f"Content-Type: {mime}\r\n\r\n").encode() + Path(path).read_bytes() + b"\r\n"
    return body + f"--{boundary}--\r\n".encode(), f"multipart/form-data; boundary={boundary}"


def transcribe(path: Path, lang: str | None, cfg: dict) -> tuple[str, str]:
    """Return (text, provider/model) from the first STT provider that works."""
    errors = []
    for pid in STT_ORDER:
        if not detect_one(pid, cfg)["available"]:
            continue
        model = model_for(cfg, pid, "stt")
        try:
            if pid == "elevenlabs":
                fields = {"model_id": model}
                if lang:
                    fields["language_code"] = lang.split("-")[0]
                body, ctype = _multipart(fields, {"file": path})
                req = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=body,
                                             headers={**_eleven_headers(), "Content-Type": ctype})
                return _send(req, 600)["text"], f"{pid}/{model}"
            if pid == "openai-api":
                fields = {"model": model, **({"language": lang.split("-")[0]} if lang else {})}
                body, ctype = _multipart(fields, {"file": path})
                req = urllib.request.Request("https://api.openai.com/v1/audio/transcriptions", data=body, headers={
                    "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": ctype})
                return _send(req, 600)["text"], f"{pid}/{model}"
            mime, data = b64_file(str(path))
            resp = http_json(f"{GOOGLE_BASE}/models/{model}:generateContent", {"contents": [{"parts": [
                {"text": "Transcribe this audio verbatim, exactly as spoken, in its original language and "
                         "script. Write numbers the way they are spoken. Output only the transcript."},
                {"inline_data": {"mime_type": mime, "data": data}}]}]}, {"x-goog-api-key": google_key()}, 600)
            text = "".join(p.get("text", "") for c in resp.get("candidates", [])
                           for p in c.get("content", {}).get("parts", []))
            if text.strip():
                return text.strip(), f"{pid}/{model}"
            raise ProviderError("failed", "empty transcript")
        except (ProviderError, KeyError) as e:
            errors.append(f"{pid}: {str(e)[:120]}")
    raise ProviderError("unsupported", "no speech-to-text provider worked" + (f" ({'; '.join(errors)})" if errors else
                        " (needs an ElevenLabs, OpenAI or Gemini key)"))


# Arabic number words (normalized spelling: no harakat, ة→ه, أ/إ/آ→ا, ى→ي, ئ→ي) -> values, so a
# script that spells numbers out compares equal to an STT transcript that writes digits.
_UNITS = {"واحد": 1, "واحده": 1, "احد": 1, "احدي": 1, "اثنان": 2, "اثنين": 2, "اثنتان": 2, "اثنتين": 2,
          "اثنا": 2, "اثني": 2, "ثلاث": 3, "ثلاثه": 3, "اربع": 4, "اربعه": 4, "خمس": 5, "خمسه": 5, "ست": 6,
          "سته": 6, "سبع": 7, "سبعه": 7, "ثمان": 8, "ثماني": 8, "ثمانيه": 8, "تسع": 9, "تسعه": 9, "عشر": 10, "عشره": 10}
_TENS = {"عشرون": 20, "عشرين": 20, "ثلاثون": 30, "ثلاثين": 30, "اربعون": 40, "اربعين": 40, "خمسون": 50,
         "خمسين": 50, "ستون": 60, "ستين": 60, "سبعون": 70, "سبعين": 70, "ثمانون": 80, "ثمانين": 80,
         "تسعون": 90, "تسعين": 90}
_HUNDREDS = {"ميه": 100, "مايه": 100, "ميتان": 200, "ميتين": 200, "مايتان": 200, "مايتين": 200}
for _w, _v in (("ثلاث", 3), ("اربع", 4), ("خمس", 5), ("ست", 6), ("سبع", 7), ("ثمان", 8), ("ثماني", 8), ("تسع", 9)):
    _HUNDREDS[_w + "ميه"] = _HUNDREDS[_w + "مايه"] = _v * 100
_THOUSANDS = {"الف": 1000, "الفا": 1000, "الفان": 2000, "الفين": 2000, "الاف": 1000}
_SCALE_CANON = {"مليون": "مليون", "مليونا": "مليون", "ملايين": "مليون", "مليونان": "مليون", "مليونين": "مليون",
                "مليار": "مليار", "مليارا": "مليار", "مليارات": "مليار", "ملياران": "مليار", "مليارين": "مليار"}


def _num_value(w: str) -> tuple[str, int] | None:
    for word in (w, w[1:] if w.startswith("و") and len(w) > 2 else None):
        if not word:
            continue
        for kind, table in (("u", _UNITS), ("t", _TENS), ("h", _HUNDREDS), ("k", _THOUSANDS)):
            if word in table:
                return kind, table[word]
    return None


def _fold_numbers(tokens: list[str]) -> list[str]:
    out, i = [], 0
    while i < len(tokens):
        if not _num_value(tokens[i]):
            out.append(_SCALE_CANON.get(tokens[i], tokens[i])); i += 1; continue
        nv0 = _num_value(tokens[i])
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        if nv0[0] == "u" and not (_num_value(nxt) or nxt in _SCALE_CANON):
            out.append(tokens[i]); i += 1; continue     # lone unit word: keep (عُشر ≠ عشرة must stay visible)
        total = cur = 0
        while i < len(tokens) and (nv := _num_value(tokens[i])):
            kind, v = nv
            if kind == "k":
                total += (cur or 1) * v if v == 1000 else v
                cur = 0
            elif kind == "u" and v == 10 and 0 < cur < 10:
                cur += 10                                   # سبعة عشر = 17
            elif kind == "h" and v == 100 and 0 < cur < 10:
                cur *= 100                                  # ثلاث مئة = 300
            else:
                cur += v
            i += 1
        out.append(str(total + cur))
    return out


def _norm_tokens(text: str) -> list[str]:
    t = _HARAKAT.sub("", text).replace("ـ", "").translate(_AR_DIGITS)
    t = re.sub("[أإآٱ]", "ا", t).replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    t = re.sub(r"(?<=\d)[,٬](?=\d{3})", "", t)
    return _fold_numbers([w for w in re.split(r"[^\w%]+", t.lower()) if w])


def verify_speech(path: Path, script: str, lang: str | None, cfg: dict) -> dict:
    import difflib
    heard, by = transcribe(path, lang, cfg)
    a, b = _norm_tokens(script), _norm_tokens(heard)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    diffs = [{"script": " ".join(a[i1:i2]), "heard": " ".join(b[j1:j2])}
             for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
    numeric = [d for d in diffs if re.search(r"\d", d["script"] + d["heard"])]
    ratio = round(sm.ratio(), 3)
    return {"status": "match" if not diffs else "check", "similarity": ratio, "by": by, "heard": heard,
            "differences": diffs[:40], "numbers_changed": numeric[:20],
            "advice": "Listen to each difference. Digits vs number-words and spelling variants are usually "
                      "fine; a changed number, fraction, name or negation is a misreading: add tashkeel or "
                      "rephrase that line and re-voice it." if diffs else "Transcript matches the script."}


# --------------------------------------------------------------------------- output checks (local ffmpeg)

LONG_EDGE = {"1k": 1024, "2k": 2048, "4k": 3840}


def _ffprobe(path: Path, entries: str) -> dict:
    code, out = _run(["ffprobe", "-v", "error", "-show_entries", entries, "-of", "json", str(path)], timeout=60)
    if code != 0:
        raise ProviderError("failed", f"ffprobe could not read {path.name}: {out[:200]}")
    return json.loads(out)


def _replace_via_ffmpeg(path: Path, args: list[str]) -> None:
    tmp = path.with_name(path.stem + f".tmp-{uuid.uuid4().hex[:6]}{path.suffix}")
    code, out = _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args, str(tmp)], timeout=600)
    if code != 0 or not tmp.exists():
        tmp.unlink(missing_ok=True)
        raise ProviderError("failed", f"ffmpeg post-process failed: {out[-300:]}")
    tmp.replace(path)


def upscale_image(path: Path, size: str) -> str:
    """Bring a capped provider's image up to the requested size class (long edge), Lanczos."""
    if not shutil.which("ffmpeg"):
        return f"generated at a smaller size; not upscaled to {size} (ffmpeg missing)"
    s = _ffprobe(path, "stream=width,height")["streams"][0]
    w, h = int(s["width"]), int(s["height"])
    target = LONG_EDGE.get(size, 1024)
    if max(w, h) >= target:
        return f"provider returned {w}x{h}, already {size}"
    k = target / max(w, h)
    W, H = int(round(w * k / 2) * 2), int(round(h * k / 2) * 2)
    _replace_via_ffmpeg(path, ["-i", str(path), "-vf", f"scale={W}:{H}:flags=lanczos", "-frames:v", "1",
                               "-update", "1", *(["-q:v", "2"] if path.suffix.lower() in (".jpg", ".jpeg") else [])])
    return f"provider max is below {size}: generated {w}x{h}, upscaled locally to {W}x{H} (Lanczos)"


def _silences(path: Path, noise_db: int = -50, min_s: float = 2.0) -> list[tuple[float, float]]:
    code, out = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
                      f"silencedetect=n={noise_db}dB:d={min_s}", "-f", "null", "-"], timeout=300)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    return [(s, ends[i] if i < len(ends) else None) for i, s in enumerate(starts)]


def extend_audio(path: Path, want: float, xfade: float = 4.0) -> float:
    """Lengthen a music track to `want` seconds without a hard loop: keep the intro, repeat the
    body with crossfades, and end on the track's own ending."""
    dur = float(_ffprobe(path, "format=duration")["format"]["duration"])
    tail = min(10.0, 0.1 * dur)
    off = 0.25 * dur
    pieces = [(0.0, dur - tail)]
    length = dur - tail
    while length + (dur - off) - xfade < want:
        pieces.append((off, dur - tail))
        length += (dur - tail - off) - xfade
    start = max(off, dur - (want - length + xfade))
    pieces.append((start, dur))
    n = len(pieces)
    # one input per piece: asplit with many branches starves some of them (data silently lost)
    fc = "".join(f"[{i}:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS[p{i}];" for i, (a, b) in enumerate(pieces))
    prev = "p0"
    for i in range(1, n):
        fc += f"[{prev}][p{i}]acrossfade=d={xfade}:c1=tri:c2=tri[x{i}];"
        prev = f"x{i}"
    inputs = [x for _ in range(n) for x in ("-i", str(path))]
    _replace_via_ffmpeg(path, [*inputs, "-filter_complex", fc.rstrip(";"), "-map", f"[{prev}]"])
    return float(_ffprobe(path, "format=duration")["format"]["duration"])


def check_music(path: Path, want: float, asked: float) -> list[str]:
    """Reject silent / truncated music (raises transient -> one retry, then next provider);
    extend a track that is shorter than wanted (provider cap or slightly short)."""
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        return ["music not checked (ffmpeg missing): listen before use"]
    dur = float(_ffprobe(path, "format=duration")["format"].get("duration") or 0)
    if dur < 1:
        path.unlink(missing_ok=True)
        raise ProviderError("transient", "music file is empty")
    tail_from = dur - max(10.0, 0.1 * dur)
    bad = [(s, (e if e is not None else dur)) for s, e in _silences(path) if s < tail_from and (e or dur) > 1.5]
    gap = sum(e - s for s, e in bad)
    if gap > max(8.0, 0.1 * dur) or any(e - s >= 6 for s, e in bad):
        where = ", ".join(f"{s:.0f}–{e:.0f}s" for s, e in bad[:4])
        path.unlink(missing_ok=True)
        raise ProviderError("transient", f"music output check failed: {gap:.0f}s of silence mid-track ({where})")
    if dur < 0.5 * asked:
        path.unlink(missing_ok=True)
        raise ProviderError("transient", f"music output check failed: {dur:.0f}s returned for {asked:.0f}s asked")
    notes = []
    if dur < want - 1:
        new = extend_audio(path, want)
        notes.append(f"music was {dur:.0f}s; extended to {new:.0f}s with crossfaded repeats (no hard loop)")
    return notes


# --------------------------------------------------------------------------- runner

def run_task(task: str, a, cfg) -> int:
    needs: set[str] = set()
    if getattr(a, "ref", None) or getattr(a, "start", None):
        needs.add("refs")
    if getattr(a, "end", None):
        needs.add("end_frame")
    if getattr(a, "transparent", False):
        needs.add("transparent")
    size = getattr(a, "size", "1k")
    lang = getattr(a, "lang", None)
    p = plan(cfg, task, needs, size, a.profile, a.provider, lang)
    post = None
    if task == "image" and a.transparent and not p["order"]:
        # No provider can do alpha: render on flat white, cut out locally afterwards.
        needs.discard("transparent")
        a.transparent = False
        a.prompt += "\n\nIsolated subject on a flat, pure white (#FFFFFF) background, no shadow, no floor."
        p = plan(cfg, task, needs, size, a.profile, a.provider, lang)
        post = "remove_background"

    attempts, manual = [], []
    for step in p["order"]:
        pid = step["id"]
        if step["manual"]:
            manual.append(pid)
            continue
        adapter = ADAPTERS[task].get(pid)
        if not adapter:
            continue
        for attempt in range(2):
            t0 = time.time()
            notes = []
            try:
                if step.get("generate_at"):
                    want, a.size = a.size, step["generate_at"]
                    try:
                        path, model = adapter(a, cfg)
                    finally:
                        a.size = want
                    notes.append(upscale_image(path, want))
                elif task == "music":
                    cap = PROVIDERS[pid]["tasks"]["music"].get("max_s")
                    want = a.duration
                    asked = min(want, cap) if cap else want
                    a.duration = asked
                    try:
                        path, model = adapter(a, cfg)
                    finally:
                        a.duration = want
                    notes += check_music(path, want, asked)
                else:
                    path, model = adapter(a, cfg)
                attempts.append({"provider": pid, "ok": True, "seconds": round(time.time() - t0, 1)})
                result = {"status": "ok", "task": task, "provider": pid, "model": model, "path": str(path),
                          "attempts": attempts, "skipped": p["skipped"]}
                if notes:
                    result["notes"] = notes
                if getattr(a, "tashkeel_advice", None):
                    result["tashkeel_advice"] = a.tashkeel_advice
                if task == "speech" and getattr(a, "verify", False):
                    try:
                        result["verify"] = verify_speech(Path(path), a.text, a.lang, cfg)
                    except ProviderError as e:
                        result["verify"] = {"status": "not_checked", "detail": str(e)[:300]}
                if post:
                    result["post"] = post
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
            except ProviderError as e:
                attempts.append({"provider": pid, "ok": False, "error": e.kind, "detail": str(e)[:300]})
                if e.kind == "policy":
                    print(json.dumps({"status": "blocked", "task": task, "provider": pid, "detail": str(e)[:300],
                                      "advice": "Content was refused. Do not route to another provider to get "
                                                "around it; revise the request with the user.",
                                      "attempts": attempts}, indent=2))
                    return 4
                if e.kind != "transient" or attempt == 1:
                    break
                time.sleep(3)
            except Exception as e:  # noqa: BLE001
                attempts.append({"provider": pid, "ok": False, "error": "crash", "detail": repr(e)[:300]})
                break
    fixable = [s["id"] for s in p["skipped"] if "not set" in s["why"] or "not signed" in s["why"]
               or "not installed" in s["why"] or "not logged" in s["why"] or "browser use turned off" in s["why"]]
    fixable += [t["provider"] for t in attempts if t.get("error") == "auth"]
    connect_hint = [f"python3 scripts/connect.py {pid}" for pid in dict.fromkeys(fixable)]
    if manual:
        req = {k: str(v) if isinstance(v, Path) else v for k, v in vars(a).items()
               if k not in ("cmd", "profile", "provider", "timeout", "model") and v not in (None, [], False)}
        print(json.dumps({"status": "needs_browser", "task": task, "next": manual, "request": req, "post": post,
                          "attempts": attempts, "skipped": p["skipped"],
                          "advice": "Drive the first provider in `next` with browser/computer use; "
                                    "see references/browser-<id>.md, then `creator.py adopt`."}, indent=2))
        return 3
    print(json.dumps({"status": "failed", "task": task, "attempts": attempts, "skipped": p["skipped"],
                      "connect": connect_hint,
                      "advice": "Have the user run one `connect` command in their own terminal "
                                "(see references/connect.md), then retry."}, indent=2))
    return 1


# --------------------------------------------------------------------------- cli

def _common(p, out=True):
    if out:
        p.add_argument("--out", required=True, type=Path)
    p.add_argument("--provider", help="force one provider (no fallback)")
    p.add_argument("--profile", choices=["quality", "cost"])
    p.add_argument("--model", help="override the provider's model id")
    p.add_argument("--timeout", type=int, default=600)


def main() -> int:
    ap = argparse.ArgumentParser(prog="creator.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("detect")

    pp = sub.add_parser("plan")
    pp.add_argument("--task", default="image", choices=TASKS)
    pp.add_argument("--needs", default="", help="comma list: refs,transparent,end_frame")
    pp.add_argument("--size", default="1k", choices=list(SIZE_RANK))
    pp.add_argument("--profile", choices=["quality", "cost"])
    pp.add_argument("--provider")
    pp.add_argument("--lang", help="speech language/dialect, e.g. ar, ar-EG, ar-SA")

    ip = sub.add_parser("image")
    ip.add_argument("--prompt", required=True)
    ip.add_argument("--ratio", default="1:1", choices=list(RATIO_WORDS))
    ip.add_argument("--size", default="1k", choices=list(SIZE_RANK))
    ip.add_argument("--ref", action="append", default=[], help="reference image (repeatable)")
    ip.add_argument("--transparent", action="store_true")
    _common(ip)

    vp = sub.add_parser("video")
    vp.add_argument("--prompt", required=True)
    vp.add_argument("--ratio", default="16:9", choices=["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"])
    vp.add_argument("--duration", type=int, default=8, help="seconds (provider limits apply)")
    vp.add_argument("--resolution", default="720p", choices=["480p", "720p", "1080p", "4k"])
    vp.add_argument("--start", help="first-frame image")
    vp.add_argument("--end", help="last-frame image")
    vp.add_argument("--ref", action="append", default=[], help="subject/style reference image (repeatable)")
    _common(vp)
    vp.set_defaults(timeout=1200)

    sp = sub.add_parser("speech")
    sp.add_argument("--text", help="text to speak (or --text-file)")
    sp.add_argument("--text-file", type=Path)
    sp.add_argument("--voice", help="provider voice id/name")
    sp.add_argument("--lang", help="BCP-47 language/dialect: ar (MSA), ar-EG, ar-SA, ar-AE, ar-LB, ar-MA, en-US …")
    sp.add_argument("--style", help="delivery direction, e.g. 'warm, upbeat, conversational'")
    sp.add_argument("--speed", type=float)
    sp.add_argument("--allow-ambiguous", action="store_true",
                    help="skip the Arabic tashkeel gate (not recommended)")
    sp.add_argument("--verify", action="store_true",
                    help="transcribe the result back (STT) and report words read differently from the script")
    _common(sp)

    vp2 = sub.add_parser("verify", help="transcribe a voiceover and diff it against its script")
    vp2.add_argument("--audio", required=True, type=Path)
    vp2.add_argument("--text")
    vp2.add_argument("--text-file", type=Path)
    vp2.add_argument("--lang")

    tp = sub.add_parser("tashkeel-check", help="list Arabic words that need tashkeel before TTS")
    tp.add_argument("--text")
    tp.add_argument("--text-file", type=Path)

    mp = sub.add_parser("music")
    mp.add_argument("--prompt", required=True)
    mp.add_argument("--duration", type=float, default=30)
    mp.add_argument("--instrumental", action="store_true")
    _common(mp)

    xp = sub.add_parser("sfx")
    xp.add_argument("--prompt", required=True)
    xp.add_argument("--duration", type=float)
    xp.add_argument("--loop", action="store_true")
    _common(xp)

    dp = sub.add_parser("adopt", help="move a downloaded file to --out, fixing format/extension")
    dp.add_argument("--src", required=True, type=Path)
    dp.add_argument("--out", required=True, type=Path)

    a = ap.parse_args()
    env_loaded = load_env()
    cfg = load_config()

    if a.cmd == "detect":
        print(json.dumps({"config": str(config_path() or ""), "env_files": env_loaded,
                          "providers": detect(cfg)}, indent=2))
        return 0
    if a.cmd == "plan":
        needs = {n for n in a.needs.split(",") if n}
        print(json.dumps(plan(cfg, a.task, needs, a.size, a.profile, a.provider, a.lang), indent=2))
        return 0
    if a.cmd == "tashkeel-check":
        txt = a.text_file.read_text() if a.text_file else (a.text or "")
        if not txt:
            print(json.dumps({"status": "error", "detail": "--text or --text-file required"}))
            return 2
        chk = tashkeel_check(txt)
        print(json.dumps({"status": "needs_tashkeel" if chk["ambiguous"] else "ok", **chk},
                         ensure_ascii=False, indent=2))
        return 5 if chk["ambiguous"] else 0
    if a.cmd == "verify":
        txt = a.text_file.read_text() if a.text_file else (a.text or "")
        if not txt or not a.audio.is_file():
            print(json.dumps({"status": "error", "detail": "--audio file and --text/--text-file required"}))
            return 2
        try:
            res = verify_speech(a.audio, txt, a.lang, cfg)
        except ProviderError as e:
            print(json.dumps({"status": "not_checked", "detail": str(e)[:300]}, ensure_ascii=False))
            return 1
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["status"] == "match" else 6
    if a.cmd == "adopt":
        src = a.src.expanduser()
        if not src.is_file():
            print(json.dumps({"status": "error", "detail": f"not found: {src}"}))
            return 2
        path = save_media(src.read_bytes(), a.out.expanduser().resolve())
        if src.resolve() != path.resolve():
            src.unlink(missing_ok=True)
        print(json.dumps({"status": "ok", "path": str(path)}))
        return 0

    if a.provider and a.provider not in PROVIDERS:
        print(json.dumps({"status": "error", "detail": f"unknown provider {a.provider}"}))
        return 2
    a.out = a.out.expanduser().resolve()
    for f in [*getattr(a, "ref", []), getattr(a, "start", None), getattr(a, "end", None)]:
        if f and not Path(f).is_file():
            print(json.dumps({"status": "error", "detail": f"input not found: {f}"}))
            return 2
    if a.cmd == "speech":
        if a.text_file:
            a.text = a.text_file.read_text()
        if not a.text:
            print(json.dumps({"status": "error", "detail": "--text or --text-file required"}))
            return 2
        if (a.lang or "").startswith("ar") or (not a.lang and is_arabic(a.text)):
            chk = tashkeel_check(a.text)
            if chk["ambiguous"] and not a.allow_ambiguous:
                print(json.dumps({"status": "needs_tashkeel", "task": "speech", **chk,
                                  "advice_fix": "Add tashkeel to each listed word for the meaning you intend "
                                                "(one haraka is enough to pass), then run again. Nothing was sent "
                                                "to any TTS provider. --allow-ambiguous skips this check."},
                                 ensure_ascii=False, indent=2))
                return 5
            a.tashkeel_advice = chk["advice"]
    return run_task(a.cmd, a, cfg)


if __name__ == "__main__":
    sys.exit(main())
