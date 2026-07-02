# Indian English + Hindi TTS Speech Dataset (Curated, 73 minutes)

A small, heavily-curated **Text-to-Speech (TTS) and speech-recognition (ASR)**
corpus: **73.2 minutes** of single-speaker, studio-grade audio split across
**Indian English (37.7 min)** and **Hindi (35.5 min)**, with human-corrected
transcripts, per-clip acoustic quality metrics, and speaking-style/emotion tags.

Every one of the 555 clips was individually listened to and its transcript
corrected against automatic speech recognition output — this is not a scraped
or auto-labeled set. Built as a reference example of **curation-first dataset
design**: source auditioning, acoustic QC gating, and documented iteration on
what didn't work, not just what did.

## Why this dataset is useful

- **TTS model fine-tuning / voice cloning research** — clean single-speaker
  audio at 24 kHz, loudness-normalized, silence-trimmed, LJSpeech-style
  sentence-level clips (4–18 s).
- **ASR benchmarking** — every clip ships both the raw Sarvam STT transcript
  and the human-corrected transcript, so you can compute word/character error
  rate directly (`wer.json` on the companion GitHub repo).
- **Indian-language speech research** — Indian English and Hindi are both
  under-represented relative to their speaker populations in most public TTS
  corpora.
- **Teaching / tutorial use** — a fully reproducible pipeline (linked below)
  makes this a good worked example for a data-curation or speech-processing
  course notebook.

## Contents

| File | Description |
|---|---|
| `clips/*.wav` | 555 mono, 24 kHz, 16-bit PCM audio clips |
| `manifest.csv` | one row per clip: text, language, emotion, duration, speaker, source URL, license, SNR/LUFS, SHA-256 |

## Schema (`manifest.csv`)

| Column | Description |
|---|---|
| `clip_id` | filename stem, joins to `clips/<clip_id>.wav` |
| `language` | `en-IN` or `hi-IN` |
| `text` | human-corrected transcript |
| `asr_transcript` | raw Sarvam ASR output (for WER benchmarking) |
| `edited` | whether the human reviewer changed the ASR transcript |
| `emotion` | speaking-style tag (LLM-derived from text; conservative, not audio-verified — see limitations) |
| `duration_s`, `sample_rate` | clip length and audio sample rate |
| `snr_db`, `lufs` | acoustic QC metrics |
| `speaker`, `source_url`, `source_title`, `license` | full provenance |

## Sources and licensing

CC-BY-4.0. Every source video carries YouTube's Creative Commons Attribution
flag, verified per clip:

- **Indian English** — NPTEL *Psychrometry* lecture series (`nptelhrd`), one
  instructor.
- **Hindi** — a single-narrator studio reading of Premchand's essay *"साहित्य
  का उद्देश्य"* (Bhoopendra Pandey Hindi Channel).

## Limitations

- Small corpus (~73 min) — a starting point for fine-tuning, not a
  from-scratch training set.
- Content skews neutral/formal in speaking style (lecture and narration
  material); affective emotion tags are rare by construction, not omitted.
- Emotion tags are transcript-derived, not independently confirmed by
  listening — documented rather than inflated.

## Full pipeline, quality report, and reproducibility

The complete curation pipeline (source auditioning, acoustic QC, ASR,
human review, normalization) is open-source, along with a full PDF report
documenting every quality-control decision and iteration:

**GitHub:** https://github.com/auraCodesKM/sarvam-tts-dataset

**Hugging Face (`datasets` library):**
```python
from datasets import load_dataset
ds = load_dataset("auraCodes/indian-english-hindi-tts-60min")
```

If you find this useful for a TTS/ASR project, a course, or a Kaggle notebook,
an upvote helps it reach more people working on Indian-language speech — and
issues/PRs on the pipeline repo are welcome.
