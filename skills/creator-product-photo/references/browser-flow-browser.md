# Playbook: Google Flow (computer use)

Flow (`https://labs.google/fx/tools/flow`) is Google's filmmaking app on top of Veo and
Google's image models. It is the best manual route for video and works for stills too.
Requires a browser tool and a signed-in Google account with Flow access (credits apply).

## Rules

- Navigate by snapshot/screenshot, never fixed coordinates. Labels below are hints.
- Never type passwords or solve CAPTCHAs; ask the user to sign in.
- Check the credit cost shown before generating video; if the user set a budget, respect it.
- Generate one output per prompt unless the user asked for variants (saves credits).
- Verify the downloaded file on disk before reporting success.

## Steps — image

1. Open Flow, create a new project (or reuse the one named for this task).
2. Switch the generation mode to image. In settings choose aspect ratio and outputs = 1.
3. Paste the prompt (ratio also stated in words). Attach references as "ingredients" if needed.
4. Generate, wait, open the result, download at the highest resolution offered.
5. Move from `browser.downloads_dir` to the requested path:
   `python3 scripts/creator.py adopt --src <file> --out <path>`.

## Steps — video

1. New project → choose the mode that fits:
   - text only → text-to-video
   - start (and optional end) still → frames-to-video
   - characters/products/scenes to keep consistent → ingredients-to-video
2. Settings: model (highest Veo tier the user has unless they asked to save credits),
   aspect ratio (16:9 or 9:16), outputs = 1.
3. Prompt with shot language: subject, action, camera move, lighting, audio cues, duration.
4. Generate (often 1–5 min). Do not navigate away from the project meanwhile.
5. Download the MP4 (upscaled version if offered and the user wants 1080p+), then move it
   to the requested path and confirm with `ffprobe`.

## Known limits

- Clip length is capped per model (around 8 s per shot); longer pieces need several shots
  stitched with Flow's scene builder or locally with ffmpeg.
- UI and mode names change frequently; re-read the screen each step.
