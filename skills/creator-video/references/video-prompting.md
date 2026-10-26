# Video prompting (provider-neutral)

## Shot formula

`[shot type + camera move] of [subject doing one clear action] in [setting], [lighting],
[style/film look]. [Audio: dialogue/ambience/sfx]. [Constraints]`

- **One action per clip.** Clips are ~4–10 s; describe what happens in that time only.
- **Camera language:** static, slow dolly in/out, pan left/right, tilt up, orbit, handheld,
  crane up, FPV, rack focus, push-in. Name one primary move.
- **Shot size:** extreme wide, wide, medium, close-up, macro, over-the-shoulder, POV.
- **Look:** `shot on 35mm, shallow depth of field`, `anime cel-shaded`, `claymation`,
  `documentary handheld`, `product commercial, seamless studio`.
- **Audio** (providers with native audio): `Audio: soft rain, distant thunder, no music.`
  Dialogue in quotes with the speaker: `The barista says: "Morning! Oat latte again?"`
- **Negatives** go in plain words (`No text on screen, no logos`) — the Gemini API has no
  negative-prompt field.

## Start / end frames

- **Image-to-video (`--start`)**: generate or pick the exact first frame first (with
  `creator.py image`); the prompt then describes only the *motion*, not the scene again.
- **First + last frame (`--end`)**: transitions and reveals; keep both frames in the same
  ratio, lighting, and style.
- **References (`--ref`)**: identity/product/style to keep consistent; say what each is.

## Ratios and length

- 16:9 for YouTube/web, 9:16 for Shorts/Reels/TikTok. The Gemini API only does these two.
- Longer pieces = several clips stitched (`media.py assemble` or the explainer skill).
  Keep a shared "look sentence" in every clip prompt so cuts match.

## Checking output

`media.py probe` the file (duration, size, audio). Extract a frame to look at:
`ffmpeg -ss 1 -i clip.mp4 -frames:v 1 frame.png`. Regenerate rather than ship artifacts
(warped hands/faces, melting text, sudden morphs).
