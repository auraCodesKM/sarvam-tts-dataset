# Project status & how to finish

The pipeline, curation framework, docs, report, and public repo are **done and
validated**. The remaining work is exactly the two things that *require a human*:
a **Sarvam API key** (for transcription) and **listening** (the graded curation core).

## ✅ Done (autonomous)
- Full pipeline `src/s01…s09` + `analyze.py`, validated end-to-end through the
  credit-free stages on a real source (88 VAD segments → 63 passed acoustic QC,
  median SNR 38 dB).
- Programmatic **CC-BY license verification** (`s01`); curated, verified English
  source: the nptelhrd **Psychrometry** course (Parts 1–5, ~127 min, one speaker).
- Report (`reports/report.pdf`), dataset card (`dataset_card.md`), README, tests
  (6 passing), CI, public repo: https://github.com/auraCodesKM/sarvam-tts-dataset

## ▶️ To complete (needs you)

1. **Get a Sarvam key** at https://dashboard.sarvam.ai → API Keys. Request extra
   credits the same day (only transcription spends credits). Put it in `.env`:
   ```
   cp .env.example .env      # then set SARVAM_API_KEY=...
   ```
2. **Pick a CC-BY Hindi source** (the one open curation item). Browse nptelhrd /
   NPTEL-NOC IITM for a Hindi "(in Hindi)/हिंदी" lecture and verify it:
   ```
   # paste the URL into config/sources.yaml under `hindi:`, then:
   .venv/bin/python -m src.s01_fetch --dry-run     # confirms the CC-BY flag
   ```
3. **Run the automated chain**, then **review by ear** (the graded core):
   ```
   make all                                  # fetch → segment → QC → transcribe → verify
   .venv/bin/python -m src.s06_align_review --interactive   # listen, accept/reject, fix text
   ```
   Aim for ~30 min accepted per language. The harness is resumable.
4. **Confirm emotion tags by ear**: run `make emotion`, then open
   `data/emotion_tags.csv` and set `confirmed=True` / correct `final_tag` where the
   audio disagrees with the LLM candidate.
5. **Finalize + publish**:
   ```
   make post           # normalize → build manifest → analyze (funnel/WER/figures) → validate
   make push           # publish the public HF dataset (auraCodes/...)
   .venv/bin/python reports/build_pdf.py    # regenerate the PDF with final numbers
   ```
6. **Verify**: round-trip-load the HF dataset and listen to ~10 random clips/language.

That's it — the report's "pending" cells fill in automatically from the CSVs once
the review pass is done.
