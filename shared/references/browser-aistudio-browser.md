# Playbook: Google AI Studio speech (computer use)

`https://aistudio.google.com/generate-speech` — Google's web playground for Gemini TTS.
Same voices and models as the API, usable with just a Google sign-in. Best manual route for
Arabic dialect voiceovers when the user has no `GEMINI_API_KEY`.

## Rules

- Navigate by snapshot/screenshot; control names below are hints and may change.
- Never type passwords or solve CAPTCHAs; ask the user to sign in.
- One scene/paragraph per generation so retakes are cheap.
- Verify the downloaded file (duration > 0) before reporting success.

## Steps

1. Open the URL; confirm the account is signed in and the speech page is showing.
2. Choose the model (the highest-quality Flash TTS offered) and **single-speaker** mode
   (multi-speaker only for dialogues with exactly two named speakers).
3. Pick the voice: the configured `voices["google-api:<lang>"]` if set, else audition 2–3
   voices on the first line and let the user choose. Designed voices (`voice_…`) appear in
   the user's library.
4. Style / instructions box: paste the delivery direction, e.g.
   `Speak in natural, native Egyptian (Cairene) Arabic with authentic colloquial pronunciation. Warm, upbeat, conversational.`
5. Paste the script text exactly as approved (dialect-spelled; see `arabic-voice.md`).
6. Run, listen in-page if possible, then download the audio.
7. Move it into place: `python3 scripts/creator.py adopt --src ~/Downloads/<file> --out vo/01.wav`.
8. Repeat per paragraph with the **same** voice and style text.

## Voice design (optional, once per dialect)

Open the Voice Design area, describe the speaker (age, city/region, accent, tone, pace),
generate, audition, save. Copy the `voice_…` id into config
`voices["google-api:<lang>"]` so API runs use the same voice later.
