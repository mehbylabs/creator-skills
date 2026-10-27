# Playbook: Google Flow (computer use)

Flow (`https://flow.google.com`, formerly `labs.google/fx/tools/flow`) is Google's
filmmaking app on top of Veo and Google's image models. It is the best manual route for
video and works for stills too.
Requires a browser tool and a signed-in Google account with Flow access (credits apply,
e.g. AI Pro subscribers get a daily credit allowance).

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

1. From the Flow home/library view (`flow.google.com`), use the bottom composer —
   the project is created implicitly. The composer is a `div[contenteditable="true"]`
   ("What do you want to create?"), NOT a textarea; the only real textarea on the page
   is an invisible reCAPTCHA field.
2. Click the model chip at the composer's right (e.g. "🍌 Nano Banana 2.1 · x2") to open
   the settings popover. It has an **Image | Video** toggle — switching to **Video**
   reveals the Veo tiers (Veo 3.1 - Lite / Fast / Quality, Omni 1.1 Flash). The
   "Select model family" dropdown alone only lists image models.
3. Set outputs to x1 unless variants were requested (saves credits). The popover shows
   the exact credit cost before generating ("Generating will use N credits") — read it
   out to the user before starting if there's no set budget.
4. Paste the prompt (ratio also stated in words). Attach references as "ingredients"
   with the + control if needed.
5. Generate (often 1–5 min). Do not navigate away meanwhile. Progress shows as a % on
   the media tile; the finished clip appears in the media grid.
6. Click the tile to open the viewer, then the download control (top bar "Download
   media"). It offers 270p GIF / **720p original (free)** / 1080p + 4K (paid upgrade).
   720p original is the default choice.
7. Move from `browser.downloads_dir` to the requested path:
   `python3 scripts/creator.py adopt --src <file> --out <path>`, confirm with `ffprobe`.

## Rules — driving Flow programmatically

- **Synthetic DOM events are ignored by Flow** (dispatching `MouseEvent`/`click` or
  setting `textarea.value` does nothing: send clicks land, nothing generates, the
  prompt is silently cleared). Use the browser tool's *trusted input* — CDP
  `Input.dispatchMouseEvent` + `Input.insertText`, Playwright's real click/fill, or
  OS-level input. Verify the generation actually started (% progress on a tile) before
  declaring the step done.
- Navigate by snapshot/screenshot, never fixed coordinates. Labels are hints; the UI
  changes (this playbook was verified against Flow's late-2026 rebuild).

## Notes from production use (late 2026)

- **Agent mode** may be on by default in new projects (an "Agent" chip with
  `aria-pressed="true"`). Toggle it off to get the direct settings popover with model,
  resolution, duration and output count.
- Credit costs seen per 8 s clip at 720p, x1: Omni 1.1 Flash 6, Veo 3.1 Lite 10,
  Fast 20, **Quality 100**. Quality is visibly better; on a paid plan
  (e.g. 1,000+ credits) prefer it for hero shots.
- Several prompts can be queued back to back; they render in parallel.
- Failed generations are refunded automatically. A frequent cause is a minor in close-up
  ("a child's hand"): rephrase ("a hand") and resubmit.
- Each finished row has its own download button: a direct MP4 named after the prompt
  (e.g. `Girl_solves_chess_puzzle_<timestamp>.mp4`), with no menu.
- Switching Google accounts: avatar → "Switch account" → account chooser; Flow keeps its
  own session separate from other Google tabs.

## Known limits

- Clip length is capped per model (around 8 s per shot); longer pieces need several shots
  stitched with Flow's scene builder or locally with ffmpeg.
- UI and mode names change frequently; re-read the screen each step.
