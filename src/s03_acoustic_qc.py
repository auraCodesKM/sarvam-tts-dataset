"""Stage 3 — Acoustic QC gate (runs BEFORE any Sarvam call => costs 0 credits).

For each segment we measure SNR, clipping, true-peak, loudness, and non-speech
ratio, then PASS/FAIL against config thresholds. Only PASS clips proceed to
(billed) transcription. Every measurement is written to data/acoustic_qc.csv so
the report can show the distribution of each metric and the funnel attrition.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from .utils.audio import (clipping_ratio, estimate_snr_db, load_mono,
                          measure_lufs, true_peak_dbfs)
from .utils.io import REPO_ROOT, get_logger, load_config

log = get_logger("s03_acoustic_qc")
SR = 16000


def speech_mask_for(y: np.ndarray, model, cfg) -> np.ndarray:
    """Boolean per-sample speech mask from silero-vad (for SNR estimation)."""
    from silero_vad import get_speech_timestamps
    ts = get_speech_timestamps(torch.from_numpy(y), model, sampling_rate=SR,
                               threshold=cfg["segment"]["vad_threshold"],
                               return_seconds=False)
    mask = np.zeros(len(y), dtype=bool)
    for seg in ts:
        mask[seg["start"]:seg["end"]] = True
    return mask


def qc_clip(path: Path, model, cfg) -> dict:
    a = cfg["acoustic_qc"]
    y, _ = load_mono(path, sr=SR)
    dur = len(y) / SR
    mask = speech_mask_for(y, model, cfg)
    nonspeech_ratio = 1.0 - (mask.mean() if len(mask) else 0.0)
    snr = estimate_snr_db(y, SR, speech_mask=mask)
    clip_ratio = clipping_ratio(y)
    peak = true_peak_dbfs(y)
    lufs = measure_lufs(y, SR)

    reasons = []
    if dur < a["min_duration_s"]:           reasons.append(f"too_short({dur:.1f}s)")
    if dur > a["max_duration_s"]:            reasons.append(f"too_long({dur:.1f}s)")
    if snr < a["min_snr_db"]:                reasons.append(f"low_snr({snr:.1f}dB)")
    if clip_ratio > a["max_clipping_ratio"]: reasons.append(f"clipping({clip_ratio:.4f})")
    if peak > a["true_peak_dbfs_max"]:       reasons.append(f"hot_peak({peak:.1f}dB)")
    if lufs < a["min_lufs"]:                 reasons.append(f"too_quiet({lufs:.1f}LUFS)")
    if lufs > a["max_lufs"]:                 reasons.append(f"too_loud({lufs:.1f}LUFS)")
    if nonspeech_ratio > a["max_nonspeech_ratio"]:
        reasons.append(f"nonspeech({nonspeech_ratio:.2f})")

    return {"clip": path.name, "source_id": path.parent.name,
            "duration_s": round(dur, 2), "snr_db": round(snr, 1),
            "clipping_ratio": round(clip_ratio, 5), "peak_dbfs": round(peak, 2),
            "lufs": round(lufs, 1), "nonspeech_ratio": round(nonspeech_ratio, 3),
            "qc_pass": len(reasons) == 0, "qc_reasons": ";".join(reasons)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source")
    args = ap.parse_args()
    cfg = load_config()
    from silero_vad import load_silero_vad
    model = load_silero_vad()

    seg_root = REPO_ROOT / cfg["paths"]["segments_dir"]
    dirs = [seg_root / args.source] if args.source else sorted(
        p for p in seg_root.iterdir() if p.is_dir())

    rows = []
    for d in dirs:
        for clip in sorted(d.glob("*.wav")):
            rows.append(qc_clip(clip, model, cfg))
    df = pd.DataFrame(rows)
    out = REPO_ROOT / "data" / "acoustic_qc.csv"
    df.to_csv(out, index=False)
    n_pass = int(df["qc_pass"].sum()) if len(df) else 0
    log.info("Acoustic QC: %d clips, %d pass (%.0f%%) -> %s",
             len(df), n_pass, 100 * n_pass / max(1, len(df)), out)
    if len(df):
        log.info("Top fail reasons:\n%s",
                 df[~df.qc_pass].qc_reasons.str.split(";").explode()
                 .value_counts().head(8).to_string())


if __name__ == "__main__":
    main()
