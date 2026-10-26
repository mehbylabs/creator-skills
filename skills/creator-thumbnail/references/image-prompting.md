# Image prompting (provider-neutral)

Write one prompt that works on every provider, so fallback does not change the result much.

## Structure

`[medium] of [subject + action], [setting], [composition], [lighting], [palette], [mood]. [constraints]`

1. **Medium first** — the highest-leverage word: `cinematic photograph, 35mm`, `flat vector
   illustration`, `isometric 3D render`, `watercolor`, `product studio photo`.
2. **Subject + action** — concrete nouns and verbs, not adjectives.
3. **Composition** — framing and empty space: `centered`, `rule of thirds, subject left`,
   `generous negative space at top for a headline`.
4. **Light** — `soft window light`, `golden hour`, `hard rim light`, `overcast`.
5. **Palette** — name colors (`teal and burnt orange`), never "nice colors".
6. **Constraints** — `no text, no watermark, no logos` unless text is the point.

Ratio is passed with `--ratio`; the router also restates it in words for agent/browser routes.

## Text in images

- `openai-api`, `google-api` (Nano Banana 2.1 / Pro) and Higgsfield `gpt_image_2_5` render
  short text well. Quote exact text: `the headline "SHIP IT" in bold condensed sans`.
- `agy` and browser routes are less reliable for text. For thumbnails, banners, and ads,
  prefer generating art with empty space and compositing type locally (HTML/SVG/ffmpeg).

## References

- Say what each reference is for: `Use image 1 for the face, image 2 for the jacket style`.
- Character consistency: same references + same descriptive anchor sentence every call.

## Iteration

Change one axis per round (composition, or light, or palette) so you know what moved.
Look at every output before reporting it; a prompt that reads well can still render wrong.
