# Arabic voiceover and dialects

## The most important rule

**Write the script in the dialect itself.** Every TTS model reads text verbatim, so spelling
drives the accent more than any setting. `إزيك؟ عامل إيه النهارده؟` will sound Egyptian;
`كيف حالك؟ ماذا تفعل اليوم؟` will sound like Fusha whatever accent you request.
Ask the user for the target dialect, then draft (or convert) the script into it and get the
user's approval of the wording before generating.

- MSA/Fusha: add tashkeel (diacritics) to names, rare words, and anything ambiguous.
- Dialects: use the spelling native speakers use online; avoid mixing Fusha grammar in.
- Numbers, dates, brand names: write them as they should be spoken (in words, in Arabic
  script) — e.g. `ألفين وستة وعشرين`, not `2026`.
- Mixed Arabic/English (common in Gulf/Levantine/Egyptian content): keep English words in
  Latin script; Gemini TTS handles code-switching.

## `--lang` values

| `--lang` | Dialect | Best routes (in order) |
|---|---|---|
| `ar` / `ar-001` | Modern Standard Arabic (Fusha) | google-api · google-cloud-tts · azure-tts (`ar-SA`) · elevenlabs |
| `ar-EG` | Egyptian (Cairene) | google-api (officially supported) · google-cloud-tts `ar-EG` · azure-tts |
| `ar-SA` | Saudi (Najdi/Hijazi) | google-api (prompted) · azure-tts · elevenlabs library voice |
| `ar-AE` `ar-KW` `ar-QA` `ar-BH` `ar-OM` | Gulf / Khaleeji | google-api (prompted) · azure-tts (per-country voice) |
| `ar-LB` `ar-SY` `ar-JO` `ar-PS` | Levantine / Shami | google-api (prompted) · azure-tts |
| `ar-IQ` | Iraqi | google-api (prompted) · azure-tts |
| `ar-MA` `ar-DZ` `ar-TN` `ar-LY` | Maghrebi / Darija | azure-tts · google-api (prompted, test first) |
| `ar-YE` `ar-SD` | Yemeni, Sudanese | google-api (prompted) · azure-tts (`ar-YE`) |

With `--lang ar*`, the router uses the Arabic order (Google first). Override per dialect in
config: `"order": {"speech:ar-MA": ["azure-tts", "google-api"]}`.

What `--lang` does per provider:

- **google-api (Gemini TTS)** — adds a style line "Speak in natural, native <dialect>…";
  the model auto-detects Arabic. Officially lists Egyptian Arabic and Standard Arabic;
  other dialects work through dialect-spelled text + the style line — listen before
  shipping. For a permanent dialect, create a designed voice (below) and set it per dialect.
- **google-cloud-tts (Gemini-TTS on Cloud)** — `ar-EG` natively; other dialects use the
  generic Arabic locale plus the accent `prompt`. Needs `gcloud auth application-default login`.
- **azure-tts** — picks the country's neural voice (`ar-EG-SalmaNeural`, `ar-SA-ZariyahNeural`,
  `ar-AE-FatimaNeural`, `ar-LB-LaylaNeural`, `ar-MA-MounaNeural`, …). Most consistent per-country
  accent; still needs dialect-spelled text to sound colloquial. Male voices: pass `--voice`
  (e.g. `ar-EG-ShakirNeural`, `ar-SA-HamedNeural`).
- **elevenlabs** — sends `language_code: ar` on models that accept it; the *voice* carries the
  dialect, so pick a native-dialect voice from the library and save it per dialect.
- **openai-api** — accent instruction only; weakest on dialects; retires Jan 2027.

## Saving dialect voices

```json
"voices": {
  "google-api:ar-EG": "Charon",
  "google-api:ar-SA": "voice_abc123",
  "azure-tts:ar-SA": "ar-SA-HamedNeural",
  "elevenlabs:ar": "<voice_id of a native speaker voice>"
}
```

## Designing a dialect voice (Gemini, optional)

Gemini voice design creates a reusable `voice_…` id from a description. Do it once in the
AI Studio speech page (`browser-aistudio-browser.md`, Voice Design tab) or via the API
(`POST https://generativelanguage.googleapis.com/v1beta/voices`, `type: "prompted"`, with a
`language_code` such as `ar-SA` and a description like *"A Riyadh man in his 30s, warm
and confident, natural Najdi Saudi accent, conversational pace"*). Save the returned id
under `voices["google-api:ar-SA"]`. Voice replication from a real person's recording
requires that person's consent.

## Quality check

Arabic dialect quality can't be verified by reading the file. Ask the user (or a native
speaker) to listen to the first line before generating the rest. If it drifts toward Fusha,
fix the spelling first, then try the next provider in the Arabic order.
