# Brand foundations

## Palette (5 roles)

| Role | Use | Guidance |
|---|---|---|
| Primary | logo, key surfaces | the most ownable hue; test in one-color logo |
| Secondary | supporting surfaces | analogous or muted complement of primary |
| Accent | CTAs, highlights | highest saturation; ≤ 10% of any layout |
| Neutral dark | text, dark mode bg | near-black tinted toward primary (not #000) |
| Neutral light | backgrounds | off-white tinted toward primary (not #FFF) |

Contrast check (WCAG): body text ≥ 4.5:1, large text/icons ≥ 3:1. Compute relative luminance
`L = 0.2126R + 0.7152G + 0.0722B` (linearized sRGB); ratio `(L1+0.05)/(L2+0.05)`.

## Type pairing

- One display/heading face + one text face, or a single superfamily.
- Contrast in structure (geometric sans + humanist serif), not two similar sans.
- Safe Google Fonts pairs: Inter + Source Serif 4 · Space Grotesk + Inter · Playfair Display
  + Lato · DM Serif Display + DM Sans · Archivo Black + Archivo · Fraunces + Work Sans.
- Scale: 1.25 ratio (e.g. 16 / 20 / 25 / 31 / 39 / 49 px).

## Logo rules

- Mark legible at 16 px; works in one color, reversed, and on photos.
- Clear space ≥ the height of the mark's main stroke/letter x-height on all sides.
- SVG: `viewBox` set, no embedded raster, shapes not strokes where possible, colors as hex.
- Provide: mark, wordmark, horizontal lockup, stacked lockup (if needed), favicon 32/180/512.

## brand.json shape

```json
{
  "name": "Acme",
  "tagline": "…",
  "personality": ["calm", "precise", "warm"],
  "colors": {"primary": "#0B1F3A", "secondary": "#3E5C76", "accent": "#FF6B35",
             "dark": "#0E1116", "light": "#F4F1EA"},
  "fonts": {"heading": "Space Grotesk", "body": "Inter"},
  "logo": {"mark": "logo/mark.svg", "lockup": "logo/lockup.svg"},
  "voice": "Short sentences. Confident, never hype."
}
```
