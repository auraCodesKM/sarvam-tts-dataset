PY := .venv/bin/python

.PHONY: help setup fetch segment qc transcribe verify review normalize emotion \
        build analyze validate smoke all push clean

help:
	@echo "Targets: setup smoke fetch segment qc transcribe verify review \\"
	@echo "         normalize emotion build analyze validate all push clean"

setup:
	python3 -m venv .venv && $(PY) -m pip install -U pip && $(PY) -m pip install -r requirements.txt
	cp -n .env.example .env || true

# --- one-source end-to-end dry run (minimal credits) ---
smoke:
	$(PY) run_pipeline.py --smoke

# --- individual stages ---
fetch:       ; $(PY) -m src.s01_fetch
segment:     ; $(PY) -m src.s02_segment
qc:          ; $(PY) -m src.s03_acoustic_qc
transcribe:  ; $(PY) -m src.s04_transcribe
verify:      ; $(PY) -m src.s05_speaker_check
review:      ; $(PY) -m src.s06_align_review --interactive   # HUMAN-IN-THE-LOOP
normalize:   ; $(PY) -m src.s07_normalize
emotion:     ; $(PY) -m src.s08_emotion_tag
build:       ; $(PY) -m src.s09_build_dataset
analyze:     ; $(PY) -m src.analyze
validate:    ; $(PY) validate_dataset.py

# automated chain up to review, then post-review chain
all: fetch segment qc transcribe verify
	@echo "Now run: make review   (human listening pass), then: make post"
post: normalize emotion build analyze validate

push:
	$(PY) -m src.s09_build_dataset --push

clean:
	rm -rf data/segments data/clips data/hf_dataset
