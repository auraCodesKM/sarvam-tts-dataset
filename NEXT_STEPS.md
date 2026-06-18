# Project status & how to finish

A complete **62.6-min bilingual candidate pool is built, transcribed, and verified**.
The only remaining work is the one thing that *requires a human*: **listening** (the
graded curation core), then a one-command publish.

## ✅ Done
- Full pipeline `src/s01…s09` + `analyze.py`, run end-to-end against the **live Sarvam
  API** (475 clips transcribed; STT + LLM contracts validated).
- **CC-BY license verified per clip.** Sources (single-speaker):
  - English — NPTEL *Psychrometry* (`nptelhrd`), 36.2 min / 227 clips.
  - Hindi — Sadhguru Hindi discourses, 26.4 min / 248 clips.
- Funnel: 582 VAD segments → 475 acoustic-QC pass → 475 transcribed → 475 verified.
- All 475 staged in `review/review_log.csv` (ASR pre-filled, quality-prioritized).
- Report PDF, dataset card, README, tests (6 passing), CI, public repo.

## ▶️ To complete (needs you)

1. **The review pass — the graded core.** Listen, accept/reject, fix transcript text:
   ```
   make review        # = python -m src.s06_align_review --interactive
   ```
   Clips are ordered best-first (ideal length, high SNR, low filler) and the harness
   shows accepted-minutes per language so you can stop at ~30 min English / ~25 min
   Hindi. Resumable; saves after every decision. Keys: [p]lay [a]ccept [e]dit+accept
   [r]eject [s]kip [q]uit.

2. **Confirm emotion tags by ear:** `make emotion`, then in `data/emotion_tags.csv`
   set `confirmed=True` and fix any `final_tag` the audio disagrees with.

3. **Finalize + publish (one shot):**
   ```
   make post          # normalize(24kHz, edge-trim) → manifest → WER/funnel/figures → validate
   make push          # publish the public HF dataset: auraCodes/indian-english-hindi-tts-60min
   .venv/bin/python reports/build_pdf.py     # regenerate PDF with final numbers
   git add -A && git commit -m "Final reviewed dataset" && git push
   ```

4. **Verify:** round-trip-load the HF dataset; listen to ~10 random clips/language.

## 📤 Submit (3 links, to wherever Sarvam instructed)
1. 🤗 `https://huggingface.co/datasets/auraCodes/indian-english-hindi-tts-60min`
2. 💻 `https://github.com/auraCodesKM/sarvam-tts-dataset`
3. 📄 `reports/report.pdf`

The report's "pending" cells (acceptance counts, WER, emotion distribution) fill in
automatically from the CSVs once review is done.
