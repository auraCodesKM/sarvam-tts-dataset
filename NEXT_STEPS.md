# Project status

Complete. The dataset is built, reviewed, normalized, and ready to publish.

## Final numbers

- 555 clips, 73.2 minutes total (37.7 min Indian English, 35.5 min Hindi).
- Sources, single-speaker, CC-BY licensed:
  - English - NPTEL *Psychrometry* (`nptelhrd`).
  - Hindi - Bhoopendra Pandey, Premchand essay narration.
- Funnel: 640 VAD segments → 558 acoustic-QC pass (87.2%) → 558 transcribed →
  558 human-reviewed → 555 accepted (86.7%).
- Every accepted clip's audio was listened to and its transcript corrected against
  Sarvam ASR output. Resulting WER vs. the corrected text: 0.05% (en-IN), 0.0%
  (hi-IN) - evidence of clean source audio and accurate ASR, not evidence that no
  correction was needed.
- Emotion/style tags are LLM-derived from transcript text (conservative default to
  neutral/formal); they were not individually re-confirmed by listening. This is
  recorded as a limitation in the dataset card and report rather than presented as
  fully human-verified.

## Submission deliverables (all public)

1. Hugging Face dataset: `https://huggingface.co/datasets/auraCodes/indian-english-hindi-tts-60min`
2. GitHub repository: `https://github.com/auraCodesKM/sarvam-tts-dataset`
3. PDF report: `reports/report.pdf`

## Reproducing the build

```bash
make setup      # virtualenv + deps + .env from template
make all         # s01..s05: fetch -> segment -> QC -> transcribe -> verify
make review      # s06: interactive listen / accept / reject / correct
make post        # s07..s09: normalize -> emotion -> build -> analyze -> validate
make push        # publish the public Hugging Face dataset
```
