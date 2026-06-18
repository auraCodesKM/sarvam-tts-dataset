"""Stage 4 — Transcribe acoustic-QC-passing clips with Sarvam STT (cached).

Only clips with qc_pass==True are sent (credit frugality). Responses are cached
on disk by audio sha256 (see sarvam_client), so reruns/iterations cost 0 credits.
Word timestamps + diarization are requested (used by s05/s06).

Output: data/transcripts.csv (clip, language, transcript, language_probability,
n_speakers, raw_json_path).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .utils.io import REPO_ROOT, get_logger, load_config, load_sources
from .utils.sarvam_client import SarvamClient

log = get_logger("s04_transcribe")


def lang_of(source_id: str, sources: dict) -> str:
    for key in ("english", "hindi"):
        for s in sources.get(key, []):
            if s["id"] == source_id or source_id.startswith(s["id"]):
                return s["language"]
    # fallback: infer from id prefix
    return "hi-IN" if source_id.startswith("hi") else "en-IN"


def n_speakers(resp: dict) -> int:
    dia = resp.get("diarized_transcript") or {}
    entries = dia.get("entries") or []
    return len({e.get("speaker_id") for e in entries}) if entries else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source")
    ap.add_argument("--limit", type=int, default=0, help="cap clips (smoke test)")
    args = ap.parse_args()

    cfg = load_config()
    sources = load_sources()
    tc = cfg["transcribe"]
    client = SarvamClient(cache_dir=cfg["paths"]["cache_dir"])

    qc = pd.read_csv(REPO_ROOT / "data" / "acoustic_qc.csv")
    qc = qc[qc.qc_pass]
    if args.source:
        qc = qc[qc.source_id == args.source]
    if args.limit:
        qc = qc.head(args.limit)

    seg_root = REPO_ROOT / cfg["paths"]["segments_dir"]
    rows = []
    for _, r in qc.iterrows():
        clip_path = seg_root / r.source_id / r["clip"]
        lang = lang_of(r.source_id, sources)
        try:
            resp = client.transcribe(clip_path, language_code=lang,
                                     model=tc["model"],
                                     with_timestamps=tc["with_timestamps"],
                                     with_diarization=tc["with_diarization"])
        except Exception as e:
            log.error("[%s] transcribe failed: %s", r["clip"], e)
            continue
        rows.append({
            "clip": r["clip"], "source_id": r.source_id,
            "language_requested": lang,
            "language_code": resp.get("language_code", lang),
            "language_probability": resp.get("language_probability"),
            "n_speakers": n_speakers(resp),
            "transcript": (resp.get("transcript") or "").strip(),
        })
    df = pd.DataFrame(rows)
    out = REPO_ROOT / "data" / "transcripts.csv"
    df.to_csv(out, index=False)
    log.info("Transcribed %d clips -> %s (cache: %s)", len(df), out,
             client.cache_dir / "stt")


if __name__ == "__main__":
    main()
