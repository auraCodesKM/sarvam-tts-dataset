# Sarvam AI – TTS Dataset Creation Assignment For Intern - ML & Speech Data Pipeline position at Sarvam

## Objective

Create a **high-quality Text-to-Speech (TTS) training dataset** with a total duration of **60 minutes**, consisting of:

* ~30 minutes of Indian English
* ~30 minutes of any Indian language (Hindi, Tamil, Telugu, Kannada, Bengali, etc.)

The dataset can be structured as:

* 60 samples × ~1 minute each
* 120 samples × ~30 seconds each
* Any combination totaling ~60 minutes

---

## Dataset Requirements

Each dataset sample must contain:

### Audio

* Clean audio segment
* Single speaker only
* Sourced from YouTube
* Minimal background noise
* No overlapping speakers

### Transcription

* Accurate text transcription
* Closely aligned with spoken content
* Correct punctuation and capitalization where appropriate

### Metadata

Each sample should include:

* Audio path
* Language
* Transcript
* Emotion/style tag

Example emotion/style tags:

* neutral
* happy
* sad
* excited
* angry
* formal
* whisper
* conversational
* energetic
* serious

---

## Required Output

### 1. Hugging Face Dataset

Publish the dataset publicly on Hugging Face.

Dataset should contain:

* Audio files
* Transcriptions
* Emotion/style annotations
* Dataset card/documentation

### 2. GitHub Repository

Public repository containing:

* Data collection scripts
* Audio processing pipeline
* Transcription pipeline
* Metadata generation code
* Dataset creation scripts
* Documentation

### 3. PDF Report

The report should document:

#### What was built

* End-to-end pipeline overview

#### Data quality iterations

* How data quality was improved
* Filtering steps applied
* Issues found and fixes implemented

#### Observations

* Common transcription errors
* Speaker quality issues
* Emotion tagging challenges

#### What worked

* Successful approaches

#### What didn't work

* Failed experiments
* Dead ends

#### Future improvements

* What would be done with additional time

---

## Available Tools

AI coding tools are allowed:

* ChatGPT
* Claude
* Cursor
* GitHub Copilot
* Any other AI coding assistant

### Sarvam AI APIs

Use Sarvam APIs for:

* ASR (Automatic Speech Recognition)
* Speaker diarization
* LLM-based processing

Documentation:
https://docs.sarvam.ai

Dashboard:
https://dashboard.sarvam.ai

If credits run out, request additional credits from Sarvam AI.

---

## Evaluation Criteria

This assignment is **not primarily a coding challenge**.

The focus is on:

### Data Quality

* Selecting clean speech samples
* Ensuring accurate transcriptions
* Removing noisy or low-quality clips
* Verifying speaker consistency

### Judgment & Curation

* Listening to audio manually
* Inspecting generated transcripts
* Iteratively improving dataset quality
* Making thoughtful filtering decisions

### Documentation

* Explaining quality decisions
* Demonstrating iteration and evaluation
* Showing understanding of TTS dataset requirements

The strongest submissions treat this as a **data curation and quality assurance problem**, not merely a scripting task.

---

## Deliverables Checklist

* [ ] 30 minutes Indian English audio
* [ ] 30 minutes Indian language audio
* [ ] Single-speaker clean clips
* [ ] Accurate transcripts
* [ ] Emotion/style tags
* [ ] Public Hugging Face dataset
* [ ] Public GitHub repository
* [ ] PDF report
* [ ] Dataset documentation

---

## Key Principle

> Prioritize data quality over dataset size, automation, or code complexity. Every clip should be intentionally curated and reviewed as if it will be used to train a production-grade TTS model.
