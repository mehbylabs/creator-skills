# Product photo modes

All templates start with the product lock sentence:
`Use image 1 as the exact product — keep its shape, colors, materials, label, and
proportions unchanged.`

| Mode | Ratio · count | Template (after lock sentence) |
|---|---|---|
| `studio` | 1:1 · 1–3 | `Professional studio packshot on a seamless [color] backdrop, soft key light from upper left, subtle reflection, product centered and filling 70% of frame, tack sharp, catalog quality, no props, no text.` |
| `lifestyle` | 4:5 · 1–3 | `The product in use in a [real setting] — [who/what action], natural [time of day] light, shallow depth of field with the product in sharp focus, authentic editorial photo, no text.` |
| `closeup-hands` | 4:5 · 1–2 | `Tight close-up of hands [action] the product, [skin tone/manicure if relevant], soft diffused light, macro detail on texture, background softly blurred, no text.` |
| `pinterest` | 2:3 · 1–3 | `Vertical moodboard-style pin: product styled with [3 complementary props] on [surface], top-down or 45° angle, airy natural light, cohesive [palette], room at top for a title, no text.` |
| `hero-banner` | 21:9 or 16:9 · 1 | `Wide campaign hero: product on the [right] third, dramatic [lighting], [environment], empty negative space on the [left] for headline and button, no text.` |
| `carousel` | 4:5 or 1:1 · 3–10 | Same scene family, one idea per slide: hero → detail → in use → scale/size → variants → CTA background. Shared style sentence on every slide. |
| `ad-pack` | 1:1, 4:5, 9:16 · 3–6 | One concept rendered in each placement ratio; keep subject position safe for each crop; leave space for overlay copy. |
| `try-on` | 3:4 or 4:5 · 1–4 | `A [model description] wearing/using the product from image 1 in [setting], natural pose, fabric/fit accurate, editorial fashion photo, no text.` Use a person reference (image 2) only with consent. |
| `conceptual` | 1:1 or 4:5 · 1–2 | `Surreal/CGI concept: the product [levitating / splashing / sculpted from its ingredients / in a miniature world], studio-quality 3D render lighting, bold [palette], no text.` |
| `restyle` | input ratio · 1 | `Keep the scene composition of image 1; change [season / mood / palette / time of day] to [target]. Product unchanged.` |
| `marketplace-main` | 1:1 · 1 | `Pure white (#FFFFFF) background, product only, centered, fills ~85% of frame, even shadowless lighting, front 3/4 angle, no props, no text, no badges, no watermark.` |
| `marketplace-secondary` | 1:1 · 4–6 | One per angle/use: back, side, detail macro, in use, scale with a common object, what's in the box. Text callouts, if any, added locally with `media.py text`. |
| `a-plus` | 970×600 or 16:9 · 3–5 | Module images: brand story banner, feature trio (three panels), comparison background, lifestyle wide. Copy is overlaid locally, never generated in-image. |

## Marketplace rules (main image)

- Pure white background (RGB 255,255,255), product fills ≥ 85%, no text, logos added by you,
  badges, borders, or props that aren't included. ≥ 1600 px on the long side for zoom.
- Secondary images may show context and callouts but must not claim things the product
  doesn't do.
- Check the specific marketplace's current image policy if the user names one.

## QA checklist

- [ ] Shape and proportions match the reference
- [ ] Colors and materials match
- [ ] Label/logo text unchanged and not garbled
- [ ] Correct number of parts (caps, buttons, straps)
- [ ] No extra products, hands with wrong finger count, or melted edges
