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
pretty_name: Indian English + Hindi TTS Dataset (60 min, curation-first)
size_categories:
  - n<1K
---

# Indian English + Hindi TTS Dataset (60 min)

A small, **heavily-curated** Text-to-Speech dataset: ~30 min Indian English +
~30 min Hindi, single-speaker clean clips with human-reviewed transcripts and
emotion/style tags. Built for the Sarvam AI ML & Speech Data Pipeline assignment
with a curation-first methodology — every clip reviewed by ear as if it would
train a production TTS model.

- **Pipeline & report:** https://github.com/auraCodesKM/sarvam-tts-dataset
- **License:** CC-BY-4.0. Sources are YouTube **CC-BY**-flagged, single-speaker:
  Indian English from **NPTEL** *Psychrometry* lectures (`nptelhrd`), Hindi from
  **Sadhguru Hindi** discourses (Isha Foundation). Per-clip attribution + the
  recorded license flag are in the manifest.

## Schema

| field | type | description |
|---|---|---|
| `audio` | Audio(24 kHz) | mono, 16-bit PCM, loudness-normalized (−23 LUFS), silence-trimmed |
| `text` | string | human-corrected transcript (punctuation + capitalization) |
| `language` | string | `en-IN` or `hi-IN` |
| `emotion` | string | style/emotion tag (LLM candidate → human-confirmed) |
| `duration_s` | float | clip duration |
| `speaker` | string | source speaker/channel |
| `source_url` | string | originating YouTube video (CC-BY) |
| `license` | string | recorded YouTube license flag |
| `snr_db`, `lufs` | float | acoustic QC metrics |

## How it was built (quality summary)

Clips pass an ordered quality funnel: VAD segmentation → **pre-ASR acoustic QC**
(SNR ≥ 22 dB, clipping, loudness, duration) → Sarvam STT → **single-speaker +
language verification** (from diarization) → **human listen-and-correct review** →
24 kHz normalization → emotion tagging. Acoustic gates run before any API call;
all decisions are logged in `review/review_log.csv`. ASR quality is quantified by
WER vs. human-corrected transcripts (`reports/wer.json`).

## Intended use & limitations

- **Intended:** research/educational TTS and ASR fine-tuning for Indian English &
  Hindi; small-scale voice modeling; a worked example of curation methodology.
- **Limitations:** lecture-domain content skews **neutral/formal** — affective
  emotion diversity is limited (documented honestly, not inflated). Small size
  (60 min). Hindi includes English code-mixing (technical terms).
- **Ethics:** only YouTube CC-BY-flagged sources; attribution preserved per clip.
  Not for speaker impersonation or voice cloning of identifiable individuals
  without consent.

## Citation

```
@misc{indian_en_hi_tts_60min_2026,
  title  = {Indian English + Hindi TTS Dataset (60 min, curation-first)},
  author = {Thakur, Kavin},
  year   = {2026},
  note   = {Sources: NPTEL + Sadhguru Hindi (CC-BY). Pipeline: github.com/auraCodesKM/sarvam-tts-dataset}
}
```
