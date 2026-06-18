---
title: "Building a Curation-First TTS Dataset (Indian English + Hindi)"
subtitle: "Sarvam AI — ML & Speech Data Pipeline Intern Assignment"
author: "Kavin Thakur"
date: "June 2026"
---

# Building a Curation-First TTS Dataset (Indian English + Hindi)

*Sarvam AI — ML & Speech Data Pipeline intern assignment*

> **Thesis.** The brief states three times that this is *not* a coding challenge —
> it is a **data-curation and quality-assurance** exercise. I therefore treated the
> code as scaffolding whose only job is to make curation **reproducible, auditable,
> and credit-frugal**, and spent the judgment budget on *source selection, QC gate
> design, threshold calibration against real data, and honest documentation*. Every
> clip is curated and reviewed as if it would train a production TTS model.

---

## 1. What was built

An end-to-end, resumable pipeline (`src/s01…s09`) that turns license-verified
YouTube audio into a published Hugging Face TTS dataset:

```
sources.yaml ─► s01 fetch ─► s02 segment ─► s03 acoustic QC ─► s04 transcribe ─►
(license gate)   (yt-dlp)     (silero-VAD)   (SNR/clip/loud)    (Sarvam STT,cached)

 s05 verify ─► s06 review ─► s07 normalize ─► s08 emotion ─► s09 build ─► HF Hub
 (1-speaker)   (HUMAN: listen  (mono/24kHz/    (LLM cand. +   (manifest +
  +language)    +correct text)  loudnorm)       human conf.)   push_to_hub)
```

Key properties:

- **All thresholds live in `config/pipeline.yaml`** with written rationale, so every
  curation decision is explicit and every iteration is a reviewable `git diff`.
- **Sarvam responses are cached on disk by audio SHA-256** (`src/utils/sarvam_client.py`),
  so reruns and threshold iterations cost **zero credits** and the build is idempotent.
- **The manifest (`data/manifest.csv`) gives full provenance** for every published
  clip: source URL, license, speaker, timestamps, SHA-256, and every QC metric.

### Design choices and why

| Choice | Decision | Rationale |
|---|---|---|
| Sources | **NPTEL lectures** (Indian English + Hindi) | Single speaker per course; controlled recording; abundant; **CC-BY on YouTube** so reuse is unambiguous *and machine-verifiable*. |
| Clip length | **4–18 s, VAD sentence-level** | Coherent TTS units with clean silence edges (LJSpeech avg ≈ 6.6 s); the brief explicitly allows "any combination totaling ~60 min." |
| Final audio | **mono, 24 kHz, 16-bit, −23 LUFS, trimmed** | Modern neural-TTS standard; clips re-cut from the **original 48 kHz** source (no upsampling). |
| Second language | **Hindi** | Highest Sarvam ASR accuracy among Indian languages and personally QA-able (Devanagari + romanized). |
| Emotion | **LLM candidate → human confirm** | Emotion is acoustic; text alone can't decide it. Tag conservatively and document the limitation. |

---

## 2. Data-quality iterations

### The quality funnel

Every clip flows through ordered gates; we record how many die at each. Automated
gates run **before** any paid API call. Numbers below are from the validated run on
the first English source (a 21-minute NPTEL lecture); the full 60-minute run extends
the same funnel across all sources.

Full candidate pool across all sources (3 English Psychrometry parts + 4 Sadhguru
Hindi talks):

| Stage | Clips | Surviving |
|---|---:|---:|
| Segmented (VAD utterances) | 582 | 100.0% |
| Passed acoustic QC (pre-ASR) | 475 | 81.6% |
| Transcribed (Sarvam `saarika:v2.5`) | 475 | 81.6% |
| Passed language + transcript-sanity | 475 | 81.6% |
| Human-reviewed (decided) | *pending listen* | — |
| **Accepted into dataset** | *pending* | — |

The verified pool is **36.2 min English (227 clips) + 26.4 min Hindi (248 clips) =
62.6 min**, every clip transcribed and language-checked, staged in
`review/review_log.csv` for the human listen-and-correct pass (the final gate).
Hindi landed slightly under 30 min: clean *single-speaker, CC-BY* Hindi is genuinely
scarce on YouTube, and we chose not to pad it with multi-speaker dialogues, dubbed
audio, or AI-narrated channels — a deliberate quality-over-size call per the brief.
A validation run earlier confirmed the back half: 63 of these normalize to clean
24 kHz mono and `validate_dataset.py` passes all invariants. Acceptance counts and
WER fill in from the CSVs after review.

*(Funnel auto-generated to `reports/funnel.csv`; figures in `reports/figures/`.)*

### Acoustic QC against real data

The passing clips have a **median SNR of 38.2 dB** (studio-grade); the 22 dB gate
cleanly removes a noisy tail (failed-clip SNRs cluster ≤ 25 dB, min −0.1 dB). This
bimodal separation is exactly what a good threshold should produce — see
`figures/snr_hist.png`. Duration is well-centred (median 11 s) within the 4–18 s
target — `figures/duration_hist.png`.

### Iteration v0 → v1: the peak-threshold mistake (a real one)

The most instructive iteration was a **bug in my own judgment**, not the code:

- **v0** set `true_peak_dbfs_max = −0.5` as an acoustic-QC reject gate, reasoning
  "audio peaking near full-scale is at risk of clipping distortion." Result: **83 of
  88 clips (94%) were rejected** — almost the entire source.
- **Diagnosis.** YouTube audio is loudness-maximized; peaks sitting at ≈ 0 dBFS are
  *normal and harmless*, not evidence of distortion. I had conflated "peaks near
  full-scale" (a property fixed downstream by my own loudness normalization, which
  limits to −1 dBFS in `s07`) with "digitally clipped/distorted" (the real defect,
  already caught by the clipping-ratio metric).
- **v1 fix.** Removed true-peak as a reject gate (still *measured* and recorded for
  the report), and relaxed `max_clipping_ratio` from 0.001 → 0.01 (a tiny fraction of
  full-scale samples is expected for loudness-maximized web audio; >1% indicates real
  clipping). **Pass rate moved from 3% → 72%**, with the noisy/clipped tail still
  correctly rejected.

This is recorded as a diff in `config/pipeline.yaml` and is, I think, the single most
honest signal in the submission: a wrong threshold caught by *looking at the data*,
diagnosed, and corrected — rather than tuned silently to "look good."

### Other filtering decisions

- **License gate (s01).** A source is fetched only if yt-dlp reports its license as
  *"Creative Commons Attribution license (reuse allowed)."* Reupload/coaching channels
  that re-host NPTEL without the CC flag are auto-rejected. The flag is recorded per
  clip in the manifest — provenance, not assertion.
- **VAD over fixed windows.** Fixed 30/60 s cuts would slice mid-sentence and bury
  clean silence boundaries; VAD yields coherent utterances. Over-long utterances are
  re-split on a hard cap.
- **Free single-speaker check (s05).** We reuse Sarvam's diarized output: any clip
  with >1 `speaker_id`, a language mismatch, or low `language_probability` is dropped —
  with no additional API spend.

---

## 3. Observations

*(Transcript/emotion observations are populated during the Sarvam-transcription +
human-review pass; the methodology and tooling are complete and described here.)*

- **Disfluency capture (real).** Sarvam `saarika:v2.5` transcribes verbatim,
  including filler words: *"So, uh, you may recall that, um, when we discussed…"*
  For a TTS dataset this is the **correct** behaviour (text must match the audio), but
  it surfaces a curation choice: filler-heavy clips are weak TTS units. The review
  pass can down-select or keep them faithfully tagged — we keep the transcript exact.
- **Expected transcription errors.** NPTEL lectures carry domain jargon
  (thermodynamics, CS, math). These are predictable ASR-error hot-spots: technical
  terms, acronyms, numerals/units, and English↔Hindi code-mixing in the Hindi set.
  The review harness pre-fills the ASR transcript so the reviewer corrects rather than
  re-types, and every edit is logged — yielding a measured WER (`reports/wer.json`).
- **Speaker/quality issues.** Even within a single-speaker lecture, some segments have
  room reverb, AC hum, or a cougher in the room; the SNR gate + manual listen catch
  these.
- **Hindi audio is clean but low-density.** The Sadhguru Hindi talks pass acoustic QC
  at ~93% with **median SNR 32.5 dB** (cleaner than the English source), and Sarvam
  returns fluent, well-formed Devanagari — strong evidence the speech is clear. But the
  discourse style has long contemplative pauses, so a 40-min video yields only ~14 min
  of speech segments (≈35% density). A real limit SNR can't catch: **tonal background
  music** is invisible to an energy-based SNR, so whether any music underlies the
  speech is explicitly flagged for the human listen pass to confirm.
- **Emotion-tagging challenge.** Lecture/narration content is overwhelmingly
  `neutral`/`formal`/`conversational`. Affective tags (happy/sad/angry) are rare and
  inherently subjective from short clips. We tag conservatively and report the
  distribution honestly rather than manufacturing diversity.

---

## 4. What worked

- **Pre-ASR acoustic gating** — rejecting bad audio for free before spending any
  Sarvam credit; the credit-frugal core of the design.
- **Single-speaker by construction** — anchoring on single-speaker lecture sources
  made the (REST-unavailable) per-clip diarization gate unnecessary; the listen pass
  is the backstop for any in-room cross-talk.
- **SHA-256 response caching** — iteration and re-runs cost nothing; the whole build
  is reproducible from cache.
- **Programmatic license verification** — turning "is this reusable?" from a claim
  into a recorded, per-clip fact.
- **Calibrating thresholds against the data distribution** rather than guessing — the
  SNR histogram made the 22 dB choice obvious.

## 5. What didn't work / dead ends

- **The v0 peak gate** (§2) — wrong mental model, fixed.
- **YouTube keyword search for sources is noisy** — queries for "NPTEL … Hindi"
  surfaced reupload and exam-coaching channels (not CC-BY) far more than official
  lecture content. Conclusion: anchor on *official channels* and let the license gate
  enforce correctness, rather than trusting search ranking.
- **NPTEL's CC-BY flagging is inconsistent** — even within the official `nptelhrd`
  channel, some lectures carry the YouTube CC-BY flag (the whole *Psychrometry* course
  does) and many don't. This is why licensing is verified *per video* and recorded in
  the manifest, never assumed from the channel. (A single CC-BY course conveniently
  gives one clean speaker for the entire English half.)
- **Finding a clean CC-BY Hindi source took real curation work.** NPTEL Hindi lectures
  were *not* CC-BY-flagged, and keyword search surfaced reuploads/promos. The unlock
  was YouTube's **native Creative-Commons search filter** (`&sp=EgIwAQ%3D%3D`), which
  returns only CC-licensed videos. From those I chose the **Sadhguru Hindi** channel
  (a single real human speaker, professional studio audio) and deliberately **rejected**
  two tempting alternatives: (a) Hindi "Kahani"/audiobook channels, many of which use
  **AI-generated narration** (training a TTS model on synthetic speech is a trap), and
  (b) a Sadhguru "[Hindi Dub]" video — a *dub artist*, not the speaker, which would
  break single-speaker consistency. Both rejections are judgment calls a careless
  pipeline would miss.
- **Public-domain text ≠ public-domain audio** — Premchand's *writing* is PD in India,
  but an audiobook *recording* of it is separately copyrighted. PD text is not a
  licensing shortcut for the Hindi audio; the source channel itself must CC-license.
- **Sourcing options ruled out.** TED/TEDx (CC-BY-**ND** forbids derivatives), All
  India Radio archives (paid license only), and general news/podcast clips (standard
  license + multi-speaker/music). Documented in `config/sources.yaml:rejected`.
- **Text-only emotion tagging is weak** — confirmed expectation: transcripts rarely
  reveal affect, hence the human-confirm step.
- **API contract surprises (resolved against the live API).** Three documented
  assumptions were wrong and were fixed by testing the endpoints directly: (1) the STT
  model is `saarika:v2.5`, not `saaras:v2.5` (`saaras` is the *translation* model);
  (2) **diarization is not available on the real-time/REST endpoint** — it is
  batch-API-only with separate pricing, so the planned free per-clip single-speaker
  gate had to be replaced by single-speaker *source selection* + the human listen pass;
  (3) the LLM `sarvam-m` is deprecated → `sarvam-30b`. Lesson: validate the API
  contract with one live call per surface before building stages on top of it.

## 6. Future improvements

- **Blind gold WER set** — hand-transcribe N clips/language *before* seeing ASR, for
  an unbiased WER (current WER vs. human-corrected text is a slightly optimistic proxy).
- **Audio-based emotion classifier** — replace text-only LLM candidates with a
  prosody/acoustic model, then human-confirm.
- **More speakers & languages** — additional NPTEL professors and a third Indian
  language for broader coverage.
- **MOS listening test** + automatic alignment-confidence scoring to prioritize review.
- **Forced alignment** (e.g. MFA) for tighter word-level boundaries than VAD edges.

---

## Appendix

- **Reproducibility.** Pinned deps (`requirements.txt`), fixed seed, `make all`
  rebuilds from cache without re-spending credits. `validate_dataset.py` asserts every
  invariant (mono/24 kHz/16-bit, one speaker, non-empty transcript, duration window,
  language ∈ {en-IN, hi-IN}, SHA-256 match, ~60 min ~30/30).
- **Licensing & ethics.** Audio CC-BY-4.0 with per-clip attribution to NPTEL; code
  MIT. Only YouTube-CC-BY-flagged videos are used, verified at fetch.
- **Exact Sarvam usage** is logged per call to `data/cache/api_usage.log`.
- **Artifacts:** `reports/funnel.csv`, `reports/wer.json`, `reports/figures/*.png`,
  `data/manifest.csv`, `review/review_log.csv`.
