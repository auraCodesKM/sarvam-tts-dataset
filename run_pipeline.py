"""Orchestrator — run pipeline stages in order, resumable from cache.

  python run_pipeline.py --until s05            # run s01..s05
  python run_pipeline.py --stage s03            # run one stage
  python run_pipeline.py --smoke                # one source, capped transcription

Stages are thin wrappers over `python -m src.sNN_*`. Automated stages (s01-s05,
s07-s09) run unattended; s06 (human review) and s08 confirmation are interactive
and are intentionally NOT auto-run here.
"""
from __future__ import annotations

import argparse
import subprocess
import sys

STAGES = [
    ("s01", "src.s01_fetch"),
    ("s02", "src.s02_segment"),
    ("s03", "src.s03_acoustic_qc"),
    ("s04", "src.s04_transcribe"),
    ("s05", "src.s05_speaker_check"),
    ("s06", "src.s06_align_review"),   # interactive (human)
    ("s07", "src.s07_normalize"),
    ("s08", "src.s08_emotion_tag"),
    ("s09", "src.s09_build_dataset"),
]


def run(mod: str, extra: list[str]):
    print(f"\n=== running {mod} {' '.join(extra)} ===", flush=True)
    subprocess.run([sys.executable, "-m", mod, *extra], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage")
    ap.add_argument("--until")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--source")
    args, extra = ap.parse_known_args()

    names = [s[0] for s in STAGES]
    if args.smoke:
        # one-source end-to-end up to verification, capped transcription
        src = args.source or "en_nptel_lecture_demo"
        run("src.s01_fetch", ["--source", src])
        run("src.s02_segment", ["--source", src])
        run("src.s03_acoustic_qc", ["--source", src])
        run("src.s04_transcribe", ["--source", src, "--limit", "8"])
        run("src.s05_speaker_check", [])
        print("\nSmoke test complete. Inspect data/*.csv, then run s06 review.")
        return

    selected = STAGES
    if args.stage:
        selected = [s for s in STAGES if s[0] == args.stage]
    elif args.until:
        selected = STAGES[: names.index(args.until) + 1]

    for name, mod in selected:
        if name == "s06":
            print("\n>>> s06 is the interactive human review. Run it directly:\n"
                  "    python -m src.s06_align_review --interactive\n"
                  ">>> Skipping in orchestrator.", flush=True)
            continue
        run(mod, args.source and ["--source", args.source] or [] if name in
            ("s01", "s02", "s03", "s04") else [])


if __name__ == "__main__":
    main()
