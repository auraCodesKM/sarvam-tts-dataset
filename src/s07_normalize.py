"""Stage 7 - Normalize ACCEPTED clips to final TTS format.

mono | 24 kHz | 16-bit PCM | loudness-normalized (EBU R128) | peak-limited |
uniform head/tail silence padding.

Quality decision: we re-cut each clip from the ORIGINAL source audio (typically
48 kHz from YouTube) at the VAD boundaries in segments.json, rather than
upsampling the 16 kHz Sarvam segment. Upsampling 16->24 kHz adds no real fidelity
above 8 kHz; re-cutting from source preserves the full band. The 16 kHz segment
was only ever an ASR-input artifact.

Output: data/clips/<clip>.wav  (the published audio)
"""
from __future__ import annotations

import argparse
import json
from functools import lru_cache

import pandas as pd

from .utils.audio import load_mono, normalize_loudness, pad_silence, save_wav, trim_to_window
from .utils.io import REPO_ROOT, ensure_dir, get_logger, load_config

log = get_logger("s07_normalize")


def _segments_index(seg_root):
    """clip -> (source_id, start_s, end_s) from each source's segments.json."""
    idx = {}
    for sj in seg_root.glob("*/segments.json"):
        for s in json.loads(sj.read_text()):
            idx[s["clip"]] = (s["source_id"], s["start_s"], s["end_s"])
    return idx


def _orig_path(raw_dir, source_id):
    return next((p for p in raw_dir.glob(f"{source_id}.*")
                 if p.suffix not in (".json",)), None)


def main():
    cfg = load_config()
    n = cfg["normalize"]
    seg_root = REPO_ROOT / cfg["paths"]["segments_dir"]
    raw_dir = REPO_ROOT / cfg["paths"]["raw_dir"]
    out_dir = ensure_dir(cfg["paths"]["clips_dir"])

    review = pd.read_csv(REPO_ROOT / "review" / "review_log.csv")
    accepted = review[review.decision == "ACCEPT"]
    seg_idx = _segments_index(seg_root)
    pad_ms = cfg["review"]["edge_trim_pad_ms"]
    # speech span (relative to each clip) from ASR timestamps -> tighten edges
    tr_path = REPO_ROOT / "data" / "transcripts.csv"
    span = {}
    if tr_path.exists():
        tdf = pd.read_csv(tr_path)
        if "speech_start_s" in tdf:
            for _, t in tdf.iterrows():
                span[t["clip"]] = (t.get("speech_start_s"), t.get("speech_end_s"))
    log.info("Normalizing %d accepted clips -> %d kHz mono (re-cut from source)",
             len(accepted), n["sample_rate"] // 1000)

    @lru_cache(maxsize=8)
    def load_source(source_id):
        p = _orig_path(raw_dir, source_id)
        return load_mono(p, sr=n["sample_rate"]) if p else (None, None)

    count = 0
    for _, r in accepted.iterrows():
        meta = seg_idx.get(r["clip"])
        if meta is None:
            log.warning("no segment timing for %s; skipping", r["clip"]); continue
        source_id, start_s, end_s = meta
        y_full, sr = load_source(source_id)
        if y_full is None:
            log.warning("missing original for %s", source_id); continue
        # tighten to the ASR speech span (clip-relative) when available, to drop
        # leading/trailing silence/music beyond the VAD boundary.
        sp = span.get(r["clip"])
        if sp and pd.notna(sp[0]) and pd.notna(sp[1]) and sp[1] > sp[0]:
            a, b = start_s + float(sp[0]), start_s + float(sp[1])
            a, b = max(start_s, a), min(end_s, b)
        else:
            a, b = start_s, end_s
        y = trim_to_window(y_full, sr, a, b, pad_ms=pad_ms)
        y = normalize_loudness(y, sr, n["target_lufs"], n["peak_ceiling_dbfs"])
        y = pad_silence(y, sr, n["head_silence_ms"], n["tail_silence_ms"])
        save_wav(out_dir / r["clip"], y, sr,
                 subtype="PCM_16" if n["bit_depth"] == 16 else "PCM_24")
        count += 1
    log.info("Wrote %d normalized clips to %s", count, out_dir)


if __name__ == "__main__":
    main()
