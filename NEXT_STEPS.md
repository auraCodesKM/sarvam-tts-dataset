# Project status and how to finish

A complete ~69-minute bilingual candidate pool is built, transcribed, and verified.
The only remaining work is the part that requires a human — listening — followed by a
one-command publish.

## Current state

- Full pipeline (`src/s01`–`s09`, `audition.py`, `analyze.py`) run end-to-end against
  the live Sarvam API. STT and LLM contracts validated.
- Licence verified per clip (YouTube CC-BY). Sources, single-speaker:
  - English — NPTEL *Psychrometry* (`nptelhrd`): 36.2 min, 227 clips.
  - Hindi — Bhoopendra Pandey, Premchand essay narration: 33.1 min, 331 clips.
- Funnel: 640 VAD segments → 558 acoustic-QC pass → 558 transcribed → 558 verified.
- All 558 clips staged in `review/review_log.csv` (ASR pre-filled, quality-ordered).
- Report PDF, dataset card, README, unit tests, CI, and public repo are in place.

## Steps to complete (require you)

1. Review pass — the graded core. Listen, accept/reject, and correct transcript text:
   ```
   make review
   ```
   Clips are presented best-first (ideal length, high SNR, low filler), and the harness
   tracks accepted minutes per language so you can stop at ~30 minutes each. The pass is
   resumable and saves after every decision. Keys: play / accept / edit+accept / reject
   / skip / quit.

2. Confirm emotion tags by ear:
   ```
   make emotion
   ```
   Then in `data/emotion_tags.csv`, set `confirmed=True` and correct any `final_tag`
   the audio disagrees with.

3. Finalize and publish:
   ```
   make post          # normalize (24 kHz, edge-trim) -> manifest -> WER/funnel/figures -> validate
   make push          # publish the public dataset: auraCodes/indian-english-hindi-tts-60min
   .venv/bin/python reports/build_pdf.py        # regenerate the PDF with final numbers
   git add -A && git commit -m "Final reviewed dataset" && git push
   ```

4. Verify: round-trip-load the published dataset and listen to ~10 random clips per
   language.

## Submission deliverables (all must be public)

1. Hugging Face dataset: `https://huggingface.co/datasets/auraCodes/indian-english-hindi-tts-60min`
2. GitHub repository: `https://github.com/auraCodesKM/sarvam-tts-dataset`
3. PDF report: `reports/report.pdf`

The report's pending values (acceptance counts, WER, emotion distribution) populate
automatically from the CSVs once the review pass is complete.
