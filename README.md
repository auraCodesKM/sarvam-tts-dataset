# Indian English + Hindi TTS Dataset

A reproducible, quality-first pipeline that builds a ~60-minute Text-to-Speech
training corpus (Indian English + Hindi) from licence-verified YouTube sources,
with clean single-speaker audio, human-reviewed transcripts, and emotion/style
tags. Built for the Sarvam AI ML & Speech Data Pipeline assignment.

This project is treated as a **data-curation and quality-assurance** problem, not a
scripting exercise. The code exists to make curation reproducible, auditable, and
credit-frugal; the judgment lives in source selection, QC-gate design, threshold
calibration against real data, and honest documentation of what worked and what did
not.

- **Hugging Face dataset:** [`auraCodes/indian-english-hindi-tts-60min`](https://huggingface.co/datasets/auraCodes/indian-english-hindi-tts-60min)
- **Report:** [`reports/report.pdf`](reports/report.pdf)
- **Design rationale:** [`PLAN.md`](PLAN.md) · **Finish/submit checklist:** [`NEXT_STEPS.md`](NEXT_STEPS.md)

## Dataset at a glance

| Property | Value |
|---|---|
| Languages | Indian English (`en-IN`), Hindi (`hi-IN`) |
| Final size | 555 clips, 73.2 min (37.7 min English, 35.5 min Hindi) |
| Audio format | mono, 24 kHz, 16-bit PCM WAV, loudness-normalized (−23 LUFS), silence-trimmed |
| Clip length | sentence-level utterances, ~4–18 s (VAD-segmented) |
| English source | NPTEL *Psychrometry* lectures (`nptelhrd`), single instructor, CC-BY |
| Hindi source | Bhoopendra Pandey - single-narrator reading of Premchand's essay *"साहित्य का उद्देश्य"*, CC-BY |
| Per-clip fields | `audio`, `text`, `language`, `emotion`, `duration_s`, `speaker`, `source_url`, `license`, `snr_db`, `lufs` |
| ASR quality | WER 0.05% (en-IN), 0.0% (hi-IN) vs. human-corrected transcripts |
| Licence | CC-BY-4.0, with per-clip attribution recorded in the manifest |

## What this submission does differently

| Signal | Where to see it |
|---|---|
| Programmatic licence verification - every source must carry YouTube's *Creative Commons Attribution (reuse allowed)* flag, checked at fetch and recorded per clip | `src/s01_fetch.py`, `data/manifest.csv` |
| Source auditioning for TTS suitability - SNR, non-speech gap-floor (continuous-music detector), and speech density profiled before committing a source | `src/audition.py` |
| Pre-ASR acoustic gate - SNR / clipping / loudness / duration filters run before any paid API call (zero-credit rejection of bad audio) | `src/s03_acoustic_qc.py` |
| Human-in-the-loop review - accept/reject + reason + transcript edit logged for every clip | `review/review_log.csv` |
| Quantified ASR quality - word/character error rate of Sarvam ASR vs. human-corrected text | `reports/wer.json` |
| Documented quality iterations - e.g. a peak-threshold that wrongly rejected 94% of clips, and a Hindi source rejected at manual review and replaced | `reports/report.pdf` |
| Reproducible, cached, resumable rebuild - reruns cost zero credits | `Makefile`, `data/cache/` |

## Pipeline

```
sources.yaml → s01 fetch → s02 segment → s03 acoustic QC → s04 transcribe →
(licence gate)  (yt-dlp)    (silero-VAD)   (SNR/clip/loud)   (Sarvam STT, cached)

 s05 verify → s06 review → s07 normalize → s08 emotion → s09 build → HF Hub
 (lang +      (human:        (24 kHz mono,   (LLM tag +    (manifest +
  transcript)  listen + fix)  loudnorm,       human         push_to_hub)
                              edge-trim)       confirm)
```

Each stage is an independent, resumable module under `src/`. All thresholds live in
[`config/pipeline.yaml`](config/pipeline.yaml) with written rationale, so every
curation decision is explicit and each iteration is a reviewable `git diff`.

## Quickstart

```bash
make setup                       # virtualenv + dependencies + .env from template
# edit .env: SARVAM_API_KEY (https://dashboard.sarvam.ai), HF_TOKEN (for publishing)

make all                         # s01..s05: fetch → segment → QC → transcribe → verify
make review                      # s06: interactive listen / accept / reject / correct
make post                        # s07..s09 + analysis + validation
make push                        # publish the public Hugging Face dataset
```

Sources are curated in [`config/sources.yaml`](config/sources.yaml); the fetch-time
licence gate is the source of truth - any non-CC-BY URL is dropped and logged.

## Repository layout

```
config/      sources.yaml (curated URLs + licence), pipeline.yaml (all thresholds)
src/         s01..s09 stages, audition.py, analyze.py, utils/ (audio, sarvam_client, io)
review/      review_log.csv  - per-clip human decisions (the curation record)
data/        manifest.csv (tracked: checksums + provenance + QC). raw/segments/clips gitignored
reports/     report.md / report.pdf, funnel.csv, wer.json, figures/
run_pipeline.py   orchestrator     validate_dataset.py   dataset invariant checks
tests/       unit tests for the audio/QC core
```

## Design choices

- **Single-speaker, studio-grade sources.** Acoustic consistency matters more than
  speaker diversity for a small corpus. English uses one NPTEL lecturer; Hindi uses
  one audiobook-style narrator. A first Hindi source (public discourse) was rejected
  at manual review for audience interaction and PA-processed audio, and replaced with
  clean studio narration - see the report.
- **Sentence-level clips (~4–18 s), not fixed 30/60 s cuts.** Voice-activity
  segmentation yields coherent utterances with clean silence boundaries, matching
  LJSpeech / Hi-Fi TTS conventions.
- **24 kHz mono, loudness-normalized, edge-trimmed**, re-cut from the original
  high-rate source (no upsampling) - a modern neural-TTS standard.
- **Conservative emotion tagging** (LLM candidate, human-confirmed). Lecture and
  narration content skews neutral/formal; this limitation is documented rather than
  inflated.

## Licence and ethics

Pipeline code is MIT (`LICENSE`). Audio data is CC-BY-4.0, sourced only from videos
carrying YouTube's Creative Commons Attribution flag, verified per clip and recorded
in the manifest with attribution to each source. TED (CC-BY-ND), All India Radio
(paid licence), and standard-licence news/podcast content were deliberately excluded;
see `config/sources.yaml` and the report's licensing section.
