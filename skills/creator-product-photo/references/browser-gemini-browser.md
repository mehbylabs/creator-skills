# Playbook: Gemini web app (computer use)

Use only when `creator.py` returned `needs_browser` with `gemini-browser` next, or the user
pinned it. Requires a browser tool (Playwright/Chrome DevTools MCP, Claude in Chrome,
Antigravity's browser agent, or OS-level computer use) and a signed-in Google account.

## Rules

- Navigate by what you see (accessibility snapshot / screenshot), never by fixed coordinates.
  Labels below are hints; the UI changes.
- Never type passwords or solve CAPTCHAs. If signed out, stop and ask the user to sign in.
- One image per chat turn. Start a new chat for unrelated images so earlier context does
  not leak into the result.
- Verify the downloaded file on disk before reporting success.

## Steps

1. Open `https://gemini.google.com/app`. Confirm the account avatar is visible.
2. Start a new chat. If the composer offers a tool picker, choose the image tool
   (often labelled "Create image" or shown with 🍌). Pick the best image model offered
   (Pro / "Thinking" variants give higher quality when available).
3. For reference images, use the composer's upload (+) control and attach the files first.
4. Send the prompt with the ratio stated in digits *and* words, e.g.
   `... Aspect ratio: 16:9 widescreen landscape. No text, no watermark.`
5. Wait for the image to render (typically 10–60 s). Do not send another message meanwhile.
6. Open the image, use its download control (full size if offered). Note the file name.
7. Find the newest file in `browser.downloads_dir` (default `~/Downloads`), then move it:
   ```bash
   python3 scripts/creator.py adopt --src ~/Downloads/<file> --out <requested path>
   ```
   If `adopt` is unavailable, `mv` it and check the real format with `file`.
8. Look at the image. If it misses the brief, refine in the same chat with one change at a time.

### Getting the bytes when driving via Chrome DevTools Protocol

Clicking the download control needs a real mouse event, which raw CDP makes awkward.
Two in-page recipes that work instead (the image `<img>` has `alt=", AI generated"`):

- Canvas (most reliable): draw the img to a canvas and read `toDataURL('image/png')`,
  then base64-decode client-side. The blob URL is same-origin, so the canvas isn't tainted.
- `fetch(img.src)` on the blob URL can return `Failed to fetch` (blob revoked after
  render) — don't rely on it.

The composer is `div[contenteditable="true"][role="textbox"]` ("Enter a prompt for
Gemini"); focus it and `document.execCommand('insertText', …)`; the send button is
`button[aria-label="Send message"]`. No "New chat" button is visible on the app
landing page — sending from it already starts a fresh chat.

## Known limits

- Images may carry a visible Gemini watermark depending on the user's plan; SynthID is always present.
- Aspect ratio is prompt-driven; re-ask once if it comes back square.
- "No text" in the prompt is often ignored — the model loves putting signage in scene
  illustrations. This is another reason the skills render real headlines locally.
- Video in the Gemini app is plan-limited and short; prefer `flow-browser` for video.
