---
license: cc-by-4.0
task_categories:
  - text-to-speech
  - automatic-speech-recognition
language:
  - en
  - hi
tags:
  - tts
  - speech
  - indian-english
  - hindi
  - curated
pretty_name: Indian English + Hindi TTS Dataset (curation-first)
size_categories:
  - n<1K
---

# Indian English + Hindi TTS Dataset

A small, heavily-curated Text-to-Speech corpus: approximately 30 minutes of Indian
English and 30 minutes of Hindi, comprising single-speaker, studio-grade clips with
human-reviewed transcripts and emotion/style tags. Built for the Sarvam AI ML &
Speech Data Pipeline assignment using a quality-first methodology — every clip was
reviewed by ear as if it would train a production TTS model.

- **Pipeline and report:** https://github.com/auraCodesKM/sarvam-tts-dataset
- **Licence:** CC-BY-4.0. Sources carry YouTube's Creative Commons Attribution flag,
  verified per clip, and are single-speaker:
  - Indian English — NPTEL *Psychrometry* lectures (`nptelhrd`), one instructor.
  - Hindi — a single-narrator reading of Premchand's essay *"साहित्य का उद्देश्य"*
    (Bhoopendra Pandey Hindi Channel); the text is public domain, the recording is
    CC-BY. Per-clip attribution and the recorded licence flag are in the manifest.

## Schema

| Field | Type | Description |
|---|---|---|
| `audio` | Audio(24 kHz) | mono, 16-bit PCM, loudness-normalized (−23 LUFS), silence-trimmed |
| `text` | string | human-corrected transcript with punctuation and capitalization |
| `language` | string | `en-IN` or `hi-IN` |
| `emotion` | string | style/emotion tag (LLM candidate, human-confirmed) |
| `duration_s` | float | clip duration in seconds |
| `speaker` | string | source speaker / channel |
| `source_url` | string | originating YouTube video (CC-BY) |
| `license` | string | recorded YouTube licence flag |
| `snr_db`, `lufs` | float | acoustic QC metrics |

## How it was built

Clips pass an ordered quality funnel: voice-activity segmentation, a pre-ASR
acoustic gate (SNR, clipping, loudness, duration), Sarvam speech-to-text,
language/transcript verification, a human listen-and-correct review, 24 kHz
normalization with edge-trimming, and conservative emotion tagging. Automated gates
run before any API call; every decision is logged in `review/review_log.csv`. ASR
quality is quantified by word/character error rate against the human-corrected
transcripts (`reports/wer.json`). Candidate sources were auditioned for TTS
suitability before selection (`src/audition.py`).

## Intended use and limitations

- **Intended use:** research and educational TTS / ASR fine-tuning for Indian English
  and Hindi; small-scale voice modeling; a worked reference for curation methodology.
- **Limitations:** lecture and narration content skews neutral/formal, so affective
  emotion diversity is limited (documented rather than inflated). The corpus is small
  (~60 minutes). The English source contains domain-specific terminology
  (thermodynamics); the Hindi source is literary prose.
- **Ethics:** only YouTube CC-BY-flagged sources are used, with attribution preserved
  per clip. Not intended for impersonation or voice cloning of identifiable
  individuals without consent.

## Citation

```bibtex
@misc{indian_en_hi_tts_2026,
  title  = {Indian English + Hindi TTS Dataset (curation-first)},
  author = {Thakur, Kavin},
  year   = {2026},
  note   = {Sources: NPTEL + Bhoopendra Pandey (CC-BY).
            Pipeline: github.com/auraCodesKM/sarvam-tts-dataset}
}
```
