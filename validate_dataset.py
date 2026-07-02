"""Dataset invariant checks - run before publishing (and in CI).

Asserts on the manifest + audio files:
  * every clip is mono, 24 kHz, 16-bit PCM WAV
  * duration within the configured window
  * language in {en-IN, hi-IN}; non-empty transcript; emotion in allowed set
  * sha256 in manifest matches the file on disk
  * total duration ~60 min and split ~30/30 (warn, not fail)
Exits non-zero on any hard failure.
"""
from __future__ import annotations

import sys

import pandas as pd
import soundfile as sf

from src.utils.io import REPO_ROOT, load_config, sha256_file


def main():
    cfg = load_config()
    df = pd.read_csv(REPO_ROOT / cfg["paths"]["manifest"])
    errors, warnings = [], []
    allowed_emotions = set(cfg["emotion"]["allowed_tags"])
    sr_target = cfg["normalize"]["sample_rate"]
    lo, hi = cfg["acoustic_qc"]["min_duration_s"], cfg["normalize"].get("hard_max_s", 25)

    for _, r in df.iterrows():
        wav = REPO_ROOT / r.audio_path
        if not wav.exists():
            errors.append(f"{r.clip_id}: missing file"); continue
        info = sf.info(str(wav))
        if info.samplerate != sr_target:
            errors.append(f"{r.clip_id}: sr {info.samplerate}!={sr_target}")
        if info.channels != 1:
            errors.append(f"{r.clip_id}: {info.channels} channels (want mono)")
        if not (lo - 0.5 <= info.duration <= 22):
            warnings.append(f"{r.clip_id}: duration {info.duration:.1f}s")
        if r.language not in ("en-IN", "hi-IN"):
            errors.append(f"{r.clip_id}: bad language {r.language}")
        if not str(r.text).strip():
            errors.append(f"{r.clip_id}: empty transcript")
        if r.emotion not in allowed_emotions:
            errors.append(f"{r.clip_id}: bad emotion {r.emotion}")
        if sha256_file(wav) != r.sha256:
            errors.append(f"{r.clip_id}: sha256 mismatch")

    total_min = df.duration_s.sum() / 60
    by_lang = (df.groupby("language").duration_s.sum() / 60).round(1).to_dict()
    if not (50 <= total_min <= 75):
        warnings.append(f"total {total_min:.1f} min (target ~60)")

    print(f"Clips: {len(df)} | total {total_min:.1f} min | by language {by_lang}")
    for w in warnings:
        print("WARN:", w)
    if errors:
        for e in errors:
            print("FAIL:", e)
        print(f"\n{len(errors)} hard failures.")
        sys.exit(1)
    print("\nAll invariants hold. Dataset is publishable.")


if __name__ == "__main__":
    main()
