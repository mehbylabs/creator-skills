# Arabic voiceover and dialects

## The most important rule

**Write the script in the dialect itself.** Every TTS model reads text verbatim, so spelling
drives the accent more than any setting. `إزيك؟ عامل إيه النهارده؟` will sound Egyptian;
`كيف حالك؟ ماذا تفعل اليوم؟` will sound like Fusha whatever accent you request.
Ask the user for the target dialect, then draft (or convert) the script into it and get the
user's approval of the wording before generating.

- MSA/Fusha: add tashkeel (diacritics) to names, rare words, and anything ambiguous (next
  section: this is required, not optional).
- Dialects: use the spelling native speakers use online; avoid mixing Fusha grammar in.
- Numbers, dates, brand names: write them as they should be spoken (in words, in Arabic
  script) — e.g. `ألفين وستة وعشرين`, not `2026`.
- Mixed Arabic/English (common in Gulf/Levantine/Egyptian content): keep English words in
  Latin script; Gemini TTS handles code-switching.

## Tashkeel before any TTS (required)

Every TTS engine guesses the vowels of bare Arabic text, and some guesses change the facts.
Real failures in a finance documentary: «ثلثا» (two-thirds) read as «ثلث» (a third), «عُشر»
(a tenth) read as «عشرة» (ten), «98» heard as «89». So before any Arabic text goes to any
provider (API, CLI or browser):

1. **Selective tashkeel, not full.** Mark only what decides the meaning or the case:
   - fractions vs numbers: ثُلُث / ثُلُثا، رُبْع، خُمْس / خَمْس، سُبْع / سَبْع، ثُمْن / ثَمَن (price)، تُسْع / تِسْع، عُشْر / عَشْر
   - same letters, different words: دَيْن (debt) / دِين، عَقْد (contract) / عِقْد (decade)، ذَهَب / ذَهَبَ، مُلْك / مَلِك، سَلَم / سِلْم، صَرْف / صُرِف، حُكْم / حَكَم
   - passive vs active where it changes who did what: أُعلِن، قُدِّر، بِيع، سُمِح
   - names and rare words (تُوَيتشِل، السُّلَيْمان), and the case ending on numbers in words
     (ثلاثةُ ملايينَ، بأكثرَ من عشرين).
2. **Numbers as words** with case endings; percentages as «في المئة»; acronyms spelled the way
   they should be heard («إيه جي بي آي» or the full name).
3. **Check, then generate.** `python3 scripts/creator.py tashkeel-check --text-file vo/01.txt`
   lists bare risky words and their readings. `speech` runs the same check and stops with
   exit `5` (`needs_tashkeel`, nothing sent) until each listed word has at least one haraka.
   `--allow-ambiguous` exists for text you have checked by ear; don't use it to save time.
4. **After generating, verify by ear and by STT.** `speech --verify` (or
   `creator.py verify --audio vo/01.mp3 --text-file vo/01.txt --lang ar`) transcribes the audio
   (ElevenLabs Scribe → OpenAI → Gemini, whichever you have) and lists the words read
   differently. Tashkeel, hamza/ta-marbuta spellings and spelled-out vs digit numbers are
   normalized away («ثلاثمئة وخمسين» = 350), so what remains is worth a listen; `numbers_changed`
   comes first. A changed number, fraction, name or negation = re-voice that line.

The checker knows the common traps, not every word: you (the host) still read the script as
a listener would and add tashkeel wherever two readings are possible.

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

## Tunisian (Tounsi) spelling: do and don't

A script with mixed-dialect words produces a mixed accent, whatever the style prompt says.
A real failure: a "Tunisian" script containing «الحوت» (fish), «حانة», «يقيسوا», «دوك» came out
sounding Algerian/Egyptian.

- Use: توّا (now), برشا (a lot), فمّا (there is), موش (not), علاش (why), كيفاش (how),
  نجّم (can), متاعك (yours), برك (only), باهي (ok), ديما (always), السوم (price),
  كارطة (card), وقتلّي (when), كان (if), باش (will / in order to), شويّة شويّة,
  التلامذة, الإنقليزية, البي سي.
- Avoid Egyptian (دلوقتي، عايز، كده، إزاي، بتاع، ببلاش) and Algerian (بزاف، واش، راني، درك، نتاع).
- Stick to the brand's real facts: don't invent features to fill the runtime.

## Quality check

You can't verify Arabic dialect quality by reading the file. Ask the user (or a native
speaker) to listen to the first line before generating the rest. If it drifts toward Fusha,
fix the spelling first, then try the next provider in the Arabic order.

When nobody can listen, generate the same line with 3 voices and ask Gemini (web or API,
audio input) to act as a native-dialect judge: score each 1–10 and name the drifting
words. Keep the top voice for every line.
