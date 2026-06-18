"""Stage 9 — Assemble the manifest + HF dataset and (optionally) push to Hub.

Joins accepted clips with their QC metrics, transcripts, emotion tags, and source
provenance into data/manifest.csv (the single tracked data artifact, with SHA-256
per clip). Then builds a `datasets.Dataset` with an Audio(24kHz) column and
metadata, and pushes it PUBLICLY to the Hub.

Usage:
  python -m src.s09_build_dataset            # build manifest + local dataset
  python -m src.s09_build_dataset --push     # also push_to_hub (needs HF login)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .utils.io import REPO_ROOT, get_logger, load_config, sha256_file

log = get_logger("s09_build")


def build_manifest(cfg) -> pd.DataFrame:
    clips_dir = REPO_ROOT / cfg["paths"]["clips_dir"]
    review = pd.read_csv(REPO_ROOT / "review" / "review_log.csv")
    acc = review[review.decision == "ACCEPT"].copy()

    acoustic = pd.read_csv(REPO_ROOT / "data" / "acoustic_qc.csv")
    emo = pd.read_csv(REPO_ROOT / "data" / "emotion_tags.csv")
    transcripts = pd.read_csv(REPO_ROOT / "data" / "transcripts.csv")

    # provenance per source
    prov = {}
    for p in (REPO_ROOT / cfg["paths"]["raw_dir"]).glob("*.provenance.json"):
        d = json.loads(p.read_text()); prov[d["id"]] = d

    rows = []
    import soundfile as sf
    for _, r in acc.iterrows():
        wav = clips_dir / r["clip"]
        if not wav.exists():
            continue
        info = sf.info(str(wav))
        a = acoustic[acoustic["clip"] == r["clip"]]
        t = transcripts[transcripts["clip"] == r["clip"]]
        e = emo[emo["clip"] == r["clip"]]
        pv = prov.get(r.source_id, {})
        rows.append({
            "clip_id": Path(r["clip"]).stem,
            "audio_path": f"data/clips/{r['clip']}",
            "language": r.language_code,
            "text": r.final_transcript,
            "emotion": e.final_tag.iloc[0] if len(e) else cfg["emotion"]["default_tag"],
            "duration_s": round(info.duration, 3),
            "sample_rate": info.samplerate,
            "sha256": sha256_file(wav),
            "snr_db": a.snr_db.iloc[0] if len(a) else None,
            "lufs": a.lufs.iloc[0] if len(a) else None,
            "language_probability": t.language_probability.iloc[0] if len(t) else None,
            "speaker": pv.get("channel"),
            "source_url": pv.get("url"),
            "source_title": pv.get("title"),
            "license": pv.get("license"),
            "asr_transcript": r.asr_transcript,
            "edited": str(r.final_transcript) != str(r.asr_transcript),
        })
    df = pd.DataFrame(rows)
    out = REPO_ROOT / cfg["paths"]["manifest"]
    df.to_csv(out, index=False)
    log.info("Manifest: %d clips, %.1f min total -> %s", len(df),
             df.duration_s.sum() / 60 if len(df) else 0, out)
    if len(df):
        log.info("Per-language minutes:\n%s",
                 (df.groupby("language").duration_s.sum() / 60).round(1).to_string())
    return df


def to_hf_dataset(df: pd.DataFrame, push: bool, repo_id: str):
    from datasets import Audio, Dataset
    recs = df.to_dict("records")
    for r in recs:
        r["audio"] = str(REPO_ROOT / r["audio_path"])
    ds = Dataset.from_list(recs).cast_column("audio", Audio(sampling_rate=24000))
    save_dir = REPO_ROOT / "data" / "hf_dataset"
    ds.save_to_disk(str(save_dir))
    log.info("Built HF Dataset (%d rows) -> %s", len(ds), save_dir)
    if push:
        ds.push_to_hub(repo_id, private=False)
        log.info("Pushed PUBLICLY to https://huggingface.co/datasets/%s", repo_id)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true")
    args = ap.parse_args()
    cfg = load_config()
    df = build_manifest(cfg)
    if len(df):
        to_hf_dataset(df, args.push, cfg["dataset"]["hf_repo_id"])


if __name__ == "__main__":
    main()
