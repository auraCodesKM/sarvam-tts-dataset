# Indian English + Hindi TTS Dataset — a curation-first pipeline

A reproducible pipeline that builds a **60-minute, production-grade Text-to-Speech
training dataset** (~30 min Indian English + ~30 min Hindi) from **license-verified
YouTube sources**, with clean single-speaker audio, human-reviewed transcripts, and
emotion/style tags. Built for the **Sarvam AI ML & Speech Data Pipeline** intern
assignment.

> **This is a data-curation & QA project, not a scripting exercise.** Every clip is
> intentionally curated and reviewed as if it would train a production TTS model.
> The code exists to make that curation *reproducible, auditable, and credit-frugal*.

- 🤗 **Dataset:** `auraCodes/indian-english-hindi-tts-60min` *(published after review)*
- 📄 **Report:** [`reports/report.pdf`](reports/report.pdf)
- 🎯 **Plan & reasoning:** [`PLAN.md`](PLAN.md)

---

## What makes this submission different

| Signal | Where to see it |
|---|---|
| **Programmatic license verification** — every source must carry YouTube's *Creative Commons Attribution (reuse allowed)* flag, checked at fetch and recorded per clip | `src/s01_fetch.py`, `manifest.csv:license` |
| **A documented quality funnel** — clip counts dying at each gate | `reports/funnel.csv`, report §2 |
| **Pre-ASR acoustic gate** — SNR/clipping/loudness filters run *before* any paid API call (0-credit rejection of bad audio) | `src/s03_acoustic_qc.py` |
| **Single-speaker by construction** — single-speaker lecture sources + a language/transcript-sanity gate (REST diarization is batch-only; documented) | `src/s05_speaker_check.py` |
| **Human-in-the-loop review log** — accept/reject + reason + transcript edit for every clip | `review/review_log.csv` |
| **Quantified ASR quality (WER/CER)** — Sarvam ASR vs. human-corrected text | `reports/wer.json` |
| **Real QC iterations** — e.g. a v0 peak-threshold that wrongly rejected 94% of clips, diagnosed and fixed | report §3 |
| **One-command, cached, resumable rebuild** — reruns cost 0 credits | `Makefile`, `data/cache/` |

---

## Pipeline

```
sources.yaml ─► s01 fetch ─► s02 segment ─► s03 acoustic QC ─► s04 transcribe ─►
(license gate)   (yt-dlp)     (silero-VAD)   (SNR/clip/loud)    (Sarvam STT,cached)

 s05 verify ─► s06 review ─► s07 normalize ─► s08 emotion ─► s09 build ─► HF Hub
 (1-speaker)   (HUMAN: listen  (mono/24kHz/    (LLM cand. +   (manifest +
  +language)    +correct text)  loudnorm)       human conf.)   push_to_hub)
```

Each stage is an independent, resumable module under `src/`. All thresholds live in
[`config/pipeline.yaml`](config/pipeline.yaml) with written rationale, so iterations
are auditable by `git diff`.

## Quickstart

```bash
make setup                       # venv + deps + .env from template
# edit .env: add SARVAM_API_KEY (https://dashboard.sarvam.ai) and HF_TOKEN

# 1) curate sources in config/sources.yaml (license auto-verified at fetch)
make smoke                       # one source end-to-end (minimal credits)

# 2) scale + automated gates
make all                         # s01..s05 (fetch -> verified candidates)

# 3) the graded core: listen & decide
make review                      # interactive: play, accept/reject, correct text

# 4) finalize + publish
make post                        # normalize -> emotion -> build -> analyze -> validate
make push                        # push public HF dataset
```

## Repository layout

```
config/      sources.yaml (curated URLs+license), pipeline.yaml (all thresholds)
src/         s01..s09 stages, analyze.py, utils/ (audio, sarvam_client w/ cache, io)
review/      review_log.csv (per-clip human decisions) — the curation evidence
data/        manifest.csv (tracked: checksums+provenance+QC). raw/segments/clips gitignored
reports/     report.md/.pdf, funnel.csv, wer.json, figures/
run_pipeline.py   orchestrator   |   validate_dataset.py   invariant checks
```

## Design choices (full rationale in `PLAN.md` / report)

- **Sources (single-speaker, CC-BY-on-YouTube, verified per clip):**
  - *Indian English* — **NPTEL** *Psychrometry* lectures (`nptelhrd`), one instructor.
  - *Hindi* — **Sadhguru Hindi** discourses (Isha Foundation), one speaker.
  Both carry YouTube's CC-BY flag, so reuse is unambiguous and machine-verifiable.
  CC-BY Hindi *lectures* proved scarce; the Hindi source was found via YouTube's
  native CC search filter, choosing a real human voice over AI-narrated channels and
  rejecting multi-speaker/dubbed audio. Dataset released **CC-BY-4.0** with per-clip
  attribution.
- **Sentence-level 4–18 s clips** (VAD), not arbitrary 30/60 s cuts — coherent TTS
  units with clean silence edges (LJSpeech/Hi-Fi TTS norm).
- **24 kHz mono, 16-bit, loudness-normalized (−23 LUFS), silence-trimmed** — a modern
  neural-TTS standard; final clips re-cut from the original 48 kHz source (no upsampling).
- **Conservative emotion tagging** (LLM candidate → human confirm); lecture content
  skews neutral/formal and we document that honestly.

## License & ethics

Pipeline code: MIT (`LICENSE`). Audio data: **CC-BY-4.0**, sourced only from videos
carrying YouTube's *Creative Commons Attribution* flag (verified per clip; recorded in
the manifest). TED/AIR/standard-license sources were deliberately excluded — see
`config/sources.yaml:rejected` and the report's Licensing & Ethics section.
