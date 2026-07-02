"""Stage 2 - Segment each source into sentence-level utterances via silero-vad.

Why VAD over fixed 30/60s windows: TTS trains best on coherent utterances with
clean silence boundaries (LJSpeech avg ~6.6s). VAD respects natural pauses, so
clips don't cut mid-word and silence edges are clean.

Outputs:
  data/segments/<source_id>/<source_id>_0001.wav ...   (16kHz mono, Sarvam-ready)
  data/segments/<source_id>/segments.json              (timing + source ref)

Each segment is saved at 16 kHz mono (PCM) - the rate Sarvam STT accepts and
small enough to be disk-frugal. Final 24 kHz normalization happens in s07 from
the original high-rate audio, re-cut to the reviewed boundaries.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from .utils.audio import load_mono, save_wav
from .utils.io import REPO_ROOT, ensure_dir, get_logger, load_config

log = get_logger("s02_segment")
SARVAM_SR = 16000  # Sarvam STT input rate for PCM


def segment_source(audio_path: Path, out_dir: Path, cfg: dict) -> list[dict]:
    from silero_vad import get_speech_timestamps, load_silero_vad

    sc = cfg["segment"]
    model = load_silero_vad()
    y16, _ = load_mono(audio_path, sr=SARVAM_SR)
    tensor = torch.from_numpy(y16)

    ts = get_speech_timestamps(
        tensor, model, sampling_rate=SARVAM_SR,
        threshold=sc["vad_threshold"],
        min_speech_duration_ms=sc["min_speech_ms"],
        min_silence_duration_ms=sc["min_silence_ms"],
        speech_pad_ms=sc["speech_pad_ms"],
        return_seconds=True,
    )

    segments = []
    idx = 0
    for seg in ts:
        dur = seg["end"] - seg["start"]
        # Split overly long utterances on the hard cap into ~equal chunks.
        if dur > sc["hard_max_s"]:
            n = int(np.ceil(dur / sc["target_max_s"]))
            bounds = np.linspace(seg["start"], seg["end"], n + 1)
            spans = list(zip(bounds[:-1], bounds[1:]))
        else:
            spans = [(seg["start"], seg["end"])]
        for s, e in spans:
            d = e - s
            if d < sc["target_min_s"]:
                continue
            idx += 1
            clip = y16[int(s * SARVAM_SR):int(e * SARVAM_SR)]
            name = f"{audio_path.stem}_{idx:04d}.wav"
            save_wav(out_dir / name, clip, SARVAM_SR)
            segments.append({"clip": name, "source_id": audio_path.stem,
                             "start_s": round(float(s), 3),
                             "end_s": round(float(e), 3),
                             "duration_s": round(float(d), 3)})
    return segments


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source")
    args = ap.parse_args()
    cfg = load_config()
    raw_dir = REPO_ROOT / cfg["paths"]["raw_dir"]

    audio_files = [p for p in raw_dir.glob("*")
                   if p.suffix not in (".json",) and p.is_file()]
    if args.source:
        audio_files = [p for p in audio_files if p.stem == args.source]

    total = 0
    for audio in audio_files:
        out_dir = ensure_dir(Path(cfg["paths"]["segments_dir"]) / audio.stem)
        segs = segment_source(audio, out_dir, cfg)
        (out_dir / "segments.json").write_text(json.dumps(segs, indent=2))
        log.info("[%s] -> %d segments", audio.stem, len(segs))
        total += len(segs)
    log.info("Total segments: %d", total)


if __name__ == "__main__":
    main()
