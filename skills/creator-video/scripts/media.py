#!/usr/bin/env python3
"""media.py — local ffmpeg compositing for creator-skills (no generation, always available).

Subcommands (JSON on stdout):
  probe    FILE                                  Duration, size, audio presence.
  still    --image I --out O --duration S        Ken Burns clip from a still.
  text     --image I --out O --text T            Bold headline overlay (thumbnails, covers).
  cutout   --image I --out O                     Remove a flat background -> transparent PNG.
  reframe  --video V --out O --ratio 9:16        Crop / pad / blur-pad to a new aspect ratio.
  captions --video V --srt S --out O             Burn subtitles.
  assemble --scenes scenes.json --out O          Build a narrated video from scenes (+ music bed).

Requires ffmpeg/ffprobe on PATH. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FPS = 30
RES = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350),
       "4:3": (1440, 1080), "3:4": (1080, 1440), "21:9": (2520, 1080)}
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


class MediaError(Exception):
    pass


def ff(args: list[str], timeout: int = 900) -> None:
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise MediaError(r.stderr.strip()[-800:])


def probe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration:stream=codec_type,width,height", "-of", "json", str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise MediaError(r.stderr.strip())
    d = json.loads(r.stdout)
    streams = d.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    return {"path": str(path), "duration": float(d.get("format", {}).get("duration") or 0),
            "width": v.get("width"), "height": v.get("height"),
            "has_audio": any(s.get("codec_type") == "audio" for s in streams)}


def find_font(font: str | None) -> str:
    if font and Path(font).is_file():
        return font
    if shutil.which("fc-match"):
        r = subprocess.run(["fc-match", "-f", "%{file}", font or "sans:bold"], capture_output=True, text=True)
        if r.returncode == 0 and Path(r.stdout).is_file():
            return r.stdout
    for f in FONT_CANDIDATES:
        if Path(f).is_file():
            return f
    raise MediaError("no font found; pass --font /path/to/font.ttf")


def esc(path: str) -> str:
    """Escape a path for use inside an ffmpeg filter argument."""
    return path.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


# --------------------------------------------------------------------------- operations

def still(image: Path, out: Path, duration: float, ratio: str, motion: str) -> Path:
    W, H = RES[ratio]
    frames = max(1, int(duration * FPS))
    z = {"in": f"min(1+0.12*on/{frames},1.12)", "out": f"max(1.12-0.12*on/{frames},1)",
         "left": "1.1", "right": "1.1", "none": "1"}[motion]
    x = {"left": f"(iw-iw/zoom)*(1-on/{frames})", "right": f"(iw-iw/zoom)*on/{frames}"}.get(motion, "iw/2-(iw/zoom/2)")
    y = "ih/2-(ih/zoom/2)"
    vf = (f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},format=yuv420p")
    ff(["-loop", "1", "-i", str(image), "-vf", vf, "-frames:v", str(frames), "-c:v", "libx264",
        "-preset", "medium", "-crf", "18", str(out)])
    return out


def text(image: Path, out: Path, txt: str, pos: str, size: float, color: str, stroke: str,
         box: str | None, font: str | None, align: str = "center") -> Path:
    info = probe(image)
    h = info["height"] or 1080
    w = info["width"] or 1920
    fontsize = int(h * size)
    y = {"top": f"{int(h * 0.06)}", "center": "(h-text_h)/2", "bottom": f"h-text_h-{int(h * 0.07)}"}[pos]
    margin = int(w * 0.05)
    x = {"left": f"{margin}", "center": "(w-text_w)/2", "right": f"w-text_w-{margin}"}[align]
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tf:
        tf.write(txt)
    draw = (f"drawtext=fontfile='{esc(find_font(font))}':textfile='{esc(tf.name)}':fontsize={fontsize}:"
            f"fontcolor={color}:x={x}:y={y}:line_spacing={int(fontsize * 0.15)}:"
            f"borderw={max(2, fontsize // 14)}:bordercolor={stroke}")
    if box:
        draw += f":box=1:boxcolor={box}:boxborderw={fontsize // 3}"
    try:
        ff(["-i", str(image), "-vf", draw, "-frames:v", "1", "-update", "1", str(out)])
    finally:
        Path(tf.name).unlink(missing_ok=True)
    return out


def cutout(image: Path, out: Path, color: str, similarity: float) -> tuple[Path, str]:
    out = out.with_suffix(".png")
    if shutil.which("rembg"):
        r = subprocess.run(["rembg", "i", str(image), str(out)], capture_output=True, text=True)
        if r.returncode == 0:
            return out, "rembg"
    ff(["-i", str(image), "-vf", f"format=rgba,colorkey={color}:{similarity}:0.08",
        "-frames:v", "1", "-update", "1", str(out)])
    return out, "colorkey"


def reframe(video: Path, out: Path, ratio: str, mode: str) -> Path:
    W, H = RES[ratio]
    if mode == "crop":
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    elif mode == "pad":
        vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black"
    else:  # blur: blurred fill behind the fitted original
        vf = (f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:5[bg];"
              f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
    is_image = video.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
    args = ["-i", str(video), "-filter_complex" if mode == "blur" else "-vf", vf + ("" if is_image else ",format=yuv420p")]
    if is_image:
        args += ["-frames:v", "1", "-update", "1"]
    else:
        args += ["-c:v", "libx264", "-crf", "18", "-c:a", "copy"]
    ff(args + [str(out)])
    return out


def captions(video: Path, srt: Path, out: Path, size: int) -> Path:
    style = (f"FontName=DejaVu Sans,Bold=1,FontSize={size},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
             "BorderStyle=1,Outline=3,Shadow=0,Alignment=2,MarginV=60")
    ff(["-i", str(video), "-vf", f"subtitles='{esc(str(srt))}':force_style='{style}'",
        "-c:v", "libx264", "-crf", "18", "-c:a", "copy", str(out)])
    return out


def assemble(scenes_file: Path, out: Path, ratio: str, music: Path | None, music_volume: float,
             fade: float) -> dict:
    """scenes.json: [{"visual": "img_or_video", "audio": "vo.mp3"?, "duration": 5?, "motion": "in"?}]
    Scene length = audio length (+0.4 s tail) if audio, else `duration` (default 4 s)."""
    scenes = json.loads(scenes_file.read_text())
    base = scenes_file.parent
    W, H = RES[ratio]
    tmp = Path(tempfile.mkdtemp(prefix="assemble-"))
    parts = []
    for i, s in enumerate(scenes):
        visual = (base / s["visual"]).resolve()
        audio = (base / s["audio"]).resolve() if s.get("audio") else None
        dur = probe(audio)["duration"] + 0.4 if audio else float(s.get("duration", 4))
        seg_v = tmp / f"v{i:03d}.mp4"
        if visual.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            still(visual, seg_v, dur, ratio, s.get("motion", ["in", "out", "left", "right"][i % 4]))
        else:
            ff(["-stream_loop", "-1", "-i", str(visual), "-t", f"{dur:.3f}", "-an", "-vf",
                f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p",
                "-c:v", "libx264", "-crf", "18", str(seg_v)])
        seg = tmp / f"s{i:03d}.mp4"
        fade_out = max(0.0, dur - fade)
        vf = f"fade=t=in:st=0:d={fade},fade=t=out:st={fade_out:.3f}:d={fade}" if fade > 0 else "null"
        if audio:
            ff(["-i", str(seg_v), "-i", str(audio), "-vf", vf, "-af", "apad", "-t", f"{dur:.3f}",
                "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-ar", "48000", "-ac", "2", str(seg)])
        else:
            ff(["-i", str(seg_v), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-vf", vf,
                "-t", f"{dur:.3f}", "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-shortest", str(seg)])
        parts.append(seg)
    listing = tmp / "list.txt"
    listing.write_text("".join(f"file '{p}'\n" for p in parts))
    joined = tmp / "joined.mp4"
    ff(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(joined)])
    if music:
        ff(["-i", str(joined), "-stream_loop", "-1", "-i", str(music), "-filter_complex",
            f"[1:a]volume={music_volume}[m];[m][0:a]sidechaincompress=threshold=0.05:ratio=8:attack=20:release=400[duck];"
            f"[0:a][duck]amix=inputs=2:duration=first:dropout_transition=0,loudnorm=I=-14:TP=-1.5[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out)])
    else:
        ff(["-i", str(joined), "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5", "-c:a", "aac", "-b:a", "192k", str(out)])
    shutil.rmtree(tmp, ignore_errors=True)
    return probe(out)


# --------------------------------------------------------------------------- cli

def main() -> int:
    if not shutil.which("ffmpeg"):
        print(json.dumps({"status": "error", "detail": "ffmpeg not installed"}))
        return 2
    ap = argparse.ArgumentParser(prog="media.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("probe"); p.add_argument("file", type=Path)

    p = sub.add_parser("still")
    p.add_argument("--image", required=True, type=Path); p.add_argument("--out", required=True, type=Path)
    p.add_argument("--duration", type=float, default=5); p.add_argument("--ratio", default="16:9", choices=list(RES))
    p.add_argument("--motion", default="in", choices=["in", "out", "left", "right", "none"])

    p = sub.add_parser("text")
    p.add_argument("--image", required=True, type=Path); p.add_argument("--out", required=True, type=Path)
    p.add_argument("--text", required=True, help="use \\n in the string or real newlines for line breaks")
    p.add_argument("--pos", default="bottom", choices=["top", "center", "bottom"])
    p.add_argument("--align", default="center", choices=["left", "center", "right"])
    p.add_argument("--size", type=float, default=0.12, help="font size as fraction of image height")
    p.add_argument("--color", default="white"); p.add_argument("--stroke", default="black")
    p.add_argument("--box", help="box color, e.g. 'black@0.55' or '#FFD400'"); p.add_argument("--font")

    p = sub.add_parser("cutout")
    p.add_argument("--image", required=True, type=Path); p.add_argument("--out", required=True, type=Path)
    p.add_argument("--color", default="white"); p.add_argument("--similarity", type=float, default=0.12)

    p = sub.add_parser("reframe")
    p.add_argument("--video", required=True, type=Path); p.add_argument("--out", required=True, type=Path)
    p.add_argument("--ratio", required=True, choices=list(RES))
    p.add_argument("--mode", default="blur", choices=["crop", "pad", "blur"])

    p = sub.add_parser("captions")
    p.add_argument("--video", required=True, type=Path); p.add_argument("--srt", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path); p.add_argument("--size", type=int, default=16)

    p = sub.add_parser("assemble")
    p.add_argument("--scenes", required=True, type=Path); p.add_argument("--out", required=True, type=Path)
    p.add_argument("--ratio", default="16:9", choices=list(RES)); p.add_argument("--music", type=Path)
    p.add_argument("--music-volume", type=float, default=0.18); p.add_argument("--fade", type=float, default=0.25)

    a = ap.parse_args()
    try:
        if a.cmd == "probe":
            res = probe(a.file)
        else:
            a.out = a.out.expanduser().resolve()
            a.out.parent.mkdir(parents=True, exist_ok=True)
            if a.cmd == "still":
                res = probe(still(a.image, a.out, a.duration, a.ratio, a.motion))
            elif a.cmd == "text":
                res = {"path": str(text(a.image, a.out, a.text.replace("\\n", "\n"), a.pos, a.size, a.color,
                                        a.stroke, a.box, a.font, a.align))}
            elif a.cmd == "cutout":
                path, method = cutout(a.image, a.out, a.color, a.similarity)
                res = {"path": str(path), "method": method}
            elif a.cmd == "reframe":
                res = {"path": str(reframe(a.video, a.out, a.ratio, a.mode))}
            elif a.cmd == "captions":
                res = probe(captions(a.video, a.srt, a.out, a.size))
            else:
                res = assemble(a.scenes, a.out, a.ratio, a.music, a.music_volume, a.fade)
    except (MediaError, FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        print(json.dumps({"status": "error", "detail": str(e)}))
        return 1
    print(json.dumps({"status": "ok", **res}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
