# Sarvam AI - TTS Dataset Assignment: Plan & Approach

> **Purpose of this file:** a complete, self-contained execution plan so any future session
> (or person) can pick up the work without re-deriving context. It records not just *what*
> to do but *why* - the reasoning behind every major decision, because this assignment is
> graded on judgment and curation, not code.

---

## 0. The assignment in one paragraph

Build a **60-minute high-quality TTS training dataset** - **~30 min Indian English** +
**~30 min Hindi** - sourced from **YouTube**, with clean single-speaker audio, accurate
transcripts (correct punctuation/capitalization), and an emotion/style tag per clip. Publish
it **publicly on Hugging Face** (audio + transcripts + emotion tags + dataset card), ship a
**public GitHub repo** with the full pipeline (collection, audio processing, transcription,
metadata, dataset creation, docs), and write a **PDF report**. Sarvam APIs (ASR, diarization,
LLM) are the intended tooling. Full assignment text is in `assignmenet.md`.

**The single most important sentence in the brief (lines 149/173/193):** this is *not* a
coding challenge - it is a **data curation + quality-assurance + judgment** exercise.
*"Prioritize data quality over dataset size, automation, or code complexity. Every clip
should be intentionally curated and reviewed as if it will be used to train a production-grade
TTS model."* **Everything below optimizes for that.**

---

## 1. Locked-in decisions (and why)

| Decision | Choice | Reason |
|---|---|---|
| Second language | **Hindi (`hi-IN`)** | Highest Sarvam ASR accuracy among Indian languages, and transcripts can be spot-checked (Devanagari + romanized). The decisive quality lever in this assignment is the ability to verify transcripts by ear/eye - pick the language you can actually QA. |
| Sarvam credits | **Low now → request more on day 1** | Assignment line 143 invites credit requests ("Sarvam is generous"). Lead time matters, so request immediately. Pipeline is also designed to be credit-frugal (see §5). |
| Curation style | **Few clean single-speaker sources** (3–6 per language) | Audiobook/lecture/podcast-style single speakers maximize acoustic consistency and cleanliness - the LJSpeech / Hi-Fi TTS norm. Consistency beats diversity for a small 60-min set and is far easier to QA to a high bar. |
| Clip length | **6–20 s, sentence-level** (not literal 30/60 s) | LJSpeech averages ~6.6 s; sentence-level utterances are better TTS units than arbitrary 30/60 s cuts. The brief explicitly allows "any combination totaling ~60 min." Deviation is intentional and **must be justified in the report** (a judgment signal). |
| Final audio format | **Mono, 24 kHz, 16-bit PCM WAV, loudness-normalized, silence-trimmed** | 24 kHz is a modern neural-TTS standard (higher fidelity than LJSpeech's 22.05 kHz, still compact). Mono + normalized + trimmed = clean, uniform training units. Configurable in `pipeline.yaml`. |

---

## 2. Strategic read of the evaluation - what actually wins

Reviewers are speech-data engineers. They will reward *evidence of human curation and sound
judgment* over pipeline cleverness. Concretely, the submission must surface these signals:

| Signal they look for | How we make it visible |
|---|---|
| Manual listening / human-in-the-loop | `review/review_log.csv`: an accept/reject decision **+ reason + edit note for every candidate clip**. The report shows real edit examples. |
| Iterative quality improvement | A documented **quality funnel** (§4) with clip counts surviving each gate, and v0→v1→v2 iteration notes. |
| Thoughtful filtering decisions | Every threshold (SNR, duration, single-speaker, language match) is explicit in `config/pipeline.yaml` **with a written rationale**. |
| Real understanding of TTS data | 24 kHz mono, loudness-normalized, silence-trimmed, sentence-level clips - each choice justified against LJSpeech / Hi-Fi TTS literature. |
| Reproducibility | One-command resumable rebuild, pinned deps, fixed seeds, cached API calls, `manifest.csv` with SHA-256 + full provenance. |
| Honest documentation | Report has a genuine **"what didn't work"** with concrete failed experiments, and a **quantified ASR error (WER)** metric - most candidates report neither. |
| Ethics / licensing judgment | Prefer Creative-Commons / public-domain / govt / educational sources; license recorded per clip. Critical because the dataset is **published publicly**. |

**Thesis to repeat across README, dataset card, and report:** *every clip was intentionally
curated and reviewed as if it would train a production TTS model.*

---

## 3. Sarvam API reference (verified June 2026)

- **STT endpoint:** `POST https://api.sarvam.ai/speech-to-text`
- **Auth header:** `api-subscription-key: <KEY>` (store in `.env`, never commit)
- **Models:** `saaras:v3` (recommended; modes: `transcribe` | `translate` | `verbatim` |
  `translit` | `codemix`) or legacy `saarika:v2.5`
- **Language codes (BCP-47):** `en-IN`, `hi-IN` (also `bn-IN`, `ta-IN`, `te-IN`, `kn-IN`, …)
- **Response (key fields):**
  ```json
  {
    "request_id": "...",
    "transcript": "...",
    "language_code": "hi-IN",
    "language_probability": 0.97,
    "timestamps": { "words": [...], "start_time_seconds": [...], "end_time_seconds": [...] },
    "diarized_transcript": { "entries": [
      { "transcript": "...", "start_time_seconds": 0.0, "end_time_seconds": 4.2, "speaker_id": "SPEAKER_00" }
    ]}
  }
  ```
- **Limits:** REST handles audio **< 30 s**; the **Batch API** handles up to **2 hours** and
  is the path for diarization on long files. Supported input formats include WAV/MP3/FLAC/
  M4A/OPUS/etc. (PCM is restricted to 16 kHz).

**Why this matters for the design:**
- `diarized_transcript.speaker_id` → **free single-speaker verification** (reject any clip
  with >1 distinct speaker_id). No separate diarization step needed for short clips.
- `timestamps.words` → **alignment-based boundary tightening** (trim partial words / silence
  at clip edges) and the basis for the WER/alignment checks.
- `language_probability` / `language_code` → **language-match filtering**.
- Because we segment to <30 s clips first, we can use the cheaper/simpler **REST** endpoint
  per clip rather than the Batch API. (Batch API remains the fallback if we ever transcribe
  a full source for reference.)

---

## 4. The quality funnel (the centerpiece - QC framework)

Every candidate clip flows through ordered gates. We **record how many clips die at each
gate** → this funnel table is a headline figure in the report. Automated gates run **before**
any Sarvam call to conserve credits.

1. **Source-selection gate (manual, highest-leverage).** Choose 3–6 sources per language.
   Acceptance criteria: a single consistent speaker; clean studio/mic audio; minimal music/
   background; no overlapping speech; correct language (Indian English / Hindi); and a
   **reusable license** (CC-BY / public-domain / govt / educational preferred). Record URL,
   speaker, and license in `config/sources.yaml`.
   *Why first & manual:* garbage-in dominates everything downstream; one careful human pass
   here saves enormous effort later and is exactly the judgment reviewers grade.

2. **Segmentation.** `silero-vad` splits each source into natural utterances; target 6–20 s.
   *Why VAD not fixed windows:* preserves sentence boundaries → coherent transcripts and
   clean silence edges.

3. **Acoustic QC gate (automated, pre-ASR).** Reject on:
   - estimated **SNR < ~25–30 dB** (noise floor vs. speech energy via VAD masks),
   - **clipping / true-peak** over threshold,
   - abnormal loudness,
   - duration outside [min, max],
   - excessive non-speech ratio.
   *Why before ASR:* costs zero credits and removes obviously-bad clips so we only spend
   Sarvam credits on plausibly-good audio.

4. **Transcription gate (Sarvam STT).** `saaras:v3`, `transcribe` mode, request word
   timestamps + diarization. Use `codemix` mode for Hindi clips with heavy English mixing.

5. **Single-speaker verification.** Reject clips with **>1 `speaker_id`** in
   `diarized_transcript`. Also enforce `language_code` match and a `language_probability`
   floor.

6. **Alignment + transcript QC (human-in-the-loop - the graded core).** Use word timestamps
   to trim partial words/silence at edges. **Listen to every surviving clip**, correct
   punctuation/capitalization and ASR errors, and log the accept/reject + reason + edit in
   `review/review_log.csv`.

7. **Normalization (final audio).** Mono; resample 24 kHz; loudness-normalize (target LUFS or
   peak ≈ −1 dBFS); consistent short head/tail silence padding.

8. **Emotion/style tagging.** Sarvam LLM proposes a candidate tag from transcript + context;
   **a human confirms by listening**. Tag conservatively (most audiobook/lecture content is
   `neutral`/`formal`/`conversational`). *Document honestly* that emotion diversity is
   limited and tagging is subjective - the brief explicitly expects this observation.

9. **Dataset assembly + publish.** Build HF `Dataset` with `Audio(sampling_rate=24000)`,
   write `metadata.jsonl`, `push_to_hub` (public), generate dataset card.

**Iteration loop:** run the funnel on one source first (v0), inspect failures, tune thresholds
in `pipeline.yaml`, rerun (v1, cached so cheap), and record what changed. These iterations are
the "data quality iterations" section of the report.

---

## 5. Pipeline architecture (GitHub repo layout)

Numbered, resumable, fully config-driven stages - mapping 1:1 to the assignment's required
scripts (collection / audio processing / transcription / metadata / dataset creation / docs).

```
sarvam-tts-dataset/
  README.md              # overview, pipeline diagram, quickstart, links to HF + report
  LICENSE
  pyproject.toml         # pinned dependencies
  .env.example           # SARVAM_API_KEY=...  HF_TOKEN=...
  Makefile               # `make all`, `make smoke`, per-stage targets
  config/
    sources.yaml         # curated URLs + speaker + license per source
    pipeline.yaml        # ALL thresholds + seed (SNR, durations, sample rate, LUFS, ...)
  src/
    s01_fetch.py         # yt-dlp bestaudio + source provenance JSON
    s02_segment.py       # silero-vad utterance segmentation
    s03_acoustic_qc.py   # SNR / clipping / loudness / duration / non-speech filters
    s04_transcribe.py    # Sarvam STT (word timestamps + diarization), disk-cached
    s05_speaker_check.py # single-speaker + language-match verification
    s06_align_review.py  # timestamp trim + manual-review harness (writes review_log.csv)
    s07_normalize.py     # mono / 24kHz / loudnorm / silence trim
    s08_emotion_tag.py   # Sarvam LLM candidate tag -> manual confirm
    s09_build_dataset.py # assemble HF Dataset + metadata.jsonl + push_to_hub
    utils/
      audio.py           # load/save/resample/SNR/loudness helpers
      sarvam_client.py   # HTTP client w/ retry, backoff, and on-disk response cache
      io.py logging.py
  review/
    review_log.csv       # per-clip accept/reject + reason + manual edit
    audit_notebook.ipynb # random-sample listen-through for final audit
  data/                  # gitignored EXCEPT manifest.csv
    manifest.csv         # final clips: checksums + provenance + every QC metric
  reports/
    report.md            # source for the PDF
    report.pdf
    figures/             # funnel table, SNR & duration histograms, per-speaker counts
  validate_dataset.py    # asserts dataset invariants (see §9)
  run_pipeline.py        # orchestrator: --stage, --source, resumable from cache
```

**Libraries to reuse (don't hand-roll):** `yt-dlp`, `ffmpeg`, `silero-vad`,
`soundfile`/`librosa`, `pyloudnorm`, `huggingface_hub` + `datasets`, `requests`, `pandas`,
`jiwer` (WER), `matplotlib`, `pandoc`/`weasyprint` (PDF).

---

## 6. Credit-frugality design (because credits are low)

- **Acoustic gate before ASR** → only plausibly-good clips ever cost a Sarvam call.
- **`sarvam_client.py` caches every response to disk keyed by clip SHA-256** → reruns and
  iteration cost **0 credits**; the whole pipeline is idempotent and resumable.
- **Retry + exponential backoff** on rate limits; **structured logging of every
  credit-spending call** (so we can report exact API usage).
- **Request additional Sarvam credits on day 1** (assignment line 143) to remove the
  bottleneck before scaling past the smoke test.

---

## 7. Reproducibility & provenance

- **`manifest.csv`** - one row per published clip: `clip_id`, `sha256`, `source_url`,
  `license`, `speaker_id`, `start/end`, `duration`, `sample_rate`, `snr_db`, `language`,
  `emotion`, `text`, plus all QC metrics → full traceability from a published clip back to
  its exact source moment.
- **`review_log.csv`** - accept/reject + reason + edit per candidate → documentary proof of
  manual curation.
- **Deterministic**: fixed seeds in `pipeline.yaml`, pinned deps, `make all` rebuilds
  end-to-end from cache without re-spending credits.

---

## 8. Risk analysis & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **Copyright / YouTube ToS** for a *public* dataset | High | Prefer CC-BY / public-domain / govt / educational sources; record license per clip; add a Licensing & Ethics section to the report + dataset card; if any source is uncertain, say so honestly or drop it. |
| Low Sarvam credits | Medium | Pre-ASR filtering + response caching + request more credits day 1. |
| Hindi ASR errors (numerals, code-mix, named entities) | Medium | Use `codemix` mode where needed; mandatory human correction pass; quantify residual error with WER on gold clips. |
| Hidden second speaker / background music | Medium | VAD + diarization single-speaker gate + manual listen. |
| Emotion tags subjective / mostly "neutral" | High (expected) | Conservative LLM-candidate → human-confirm tagging; document the limitation explicitly (the brief asks for this observation). |
| Missing the ~30/30-min balance | Low | Track running duration per language in the manifest; over-collect candidates ~1.5×. |
| Over-/under-segmentation by VAD | Low | Tune VAD aggressiveness in `pipeline.yaml`; record the tuning as an iteration. |

---

## 9. Verification - how we'll know it's done *and* good

- **`validate_dataset.py`** asserts on the final dataset/manifest: every clip is mono 24 kHz,
  exactly one `speaker_id`, non-empty transcript, duration within window, language ∈
  {`en-IN`, `hi-IN`}, and total ≈ 60 min split ≈ 30/30.
- **Round-trip load** the published HF dataset, play 10 random clips per language, confirm
  audio↔transcript alignment by ear.
- **WER check** on ~10 hand-transcribed gold clips per language; report the actual number.
- **Reproducibility check:** fresh clone + `make all` rebuilds from cache without errors or
  new credit spend.
- **Final manual audit** via `audit_notebook.ipynb` (random-sample listen-through).

---

## 10. Differentiators (how this beats other submissions)

1. **Quantified transcription quality** - WER of Sarvam ASR vs. hand-made gold transcripts.
2. **QC funnel table + distribution plots** (SNR, duration, per-speaker counts) in report & card.
3. **Honest failed-experiments log** with concrete artifacts (e.g., aggressive-VAD over-split,
   a noisy source rejected wholesale, an emotion approach that didn't pan out).
4. **Production-grade dataset card** - schema, per-speaker stats, licensing, intended use,
   limitations, ethics.
5. **One-command, cached, resumable rebuild** - reproducibility most submissions lack.

---

## 11. PDF report outline (assignment-aligned)

Write `reports/report.md`, export to PDF (pandoc/weasyprint). Sections, in the brief's order:
1. **What was built** - end-to-end pipeline diagram + stage descriptions.
2. **Data-quality iterations** - the funnel table, filters applied, issues found & fixes,
   v0→v1→v2 threshold tuning.
3. **Observations** - common transcription errors (with examples), speaker-quality issues,
   emotion-tagging challenges.
4. **What worked** - successful approaches (pre-ASR filtering, diarization single-speaker
   gate, caching, manual review).
5. **What didn't work** - concrete dead ends and failed experiments.
6. **Future improvements** - with more time/credits (e.g., more languages, audio-based
   emotion classifier, larger gold set, MOS listening test).
7. **Appendices** - dataset stats, WER results, licensing/ethics, exact Sarvam API usage.

---

## 12. Execution order (next session starts here)

1. Scaffold repo + `config/pipeline.yaml` + `utils/sarvam_client.py` (with cache).
   **Request more Sarvam credits immediately.**
2. Curate `config/sources.yaml`: 3–6 clean, reusably-licensed single-speaker sources per
   language. *(Manual, highest-leverage - spend real care here.)*
3. **Smoke test on ONE source** (minimal credits): run the full loop fetch→…→push a tiny
   preview dataset. Validate the whole chain before scaling.
4. Scale to full ~30/30 min; do the manual review pass; log every decision.
5. Build & publish the HF dataset + dataset card; finalize the GitHub repo + README.
6. Write the report (funnel table, plots, WER, failed experiments) → export PDF.

---

## Appendix - open items to confirm next session

- Hugging Face account/org + write token ready? (`HF_TOKEN`)
- GitHub account/org for the public repo?
- Sarvam API key in `.env` + outcome of the additional-credits request?
- Final dataset repo id (e.g. `<user>/indian-english-hindi-tts-60min`).
- Candidate source shortlist (URLs + licenses) for `sources.yaml`.
