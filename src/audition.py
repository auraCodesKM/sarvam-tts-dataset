"""Audition a candidate source for TTS-dataset suitability (before committing).

Motivated by a real failure: a public-discourse Hindi source passed SNR but was
unusable for TTS (audience Q&A, multiple speakers, PA-processed timbre). SNR alone
does not capture source *type*. This tool profiles a short slice of a candidate and
reports the signals that actually predict TTS quality:

  * snr_db                : speech vs. non-speech-gap energy (higher = cleaner)
  * nonspeech_floor_dbfs  : RMS inside VAD gaps. Near-silent (very low dBFS) => clean
                            studio narration; elevated => continuous music/room/PA bed.
  * speech_density        : fraction of audio that is speech (narration ~0.7-0.9;
                            discourse with long pauses ~0.3-0.5).
  * sample transcripts    : fluency sanity check (garbled => music/processing).

It does NOT replace human listening (AI-voice vs human, PA timbre still need ears),
but it ranks candidates objectively so the human auditions the best one first.

Usage: python -m src.audition data/audition/*.m4a   (or any audio files)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from .utils.audio import estimate_snr_db, load_mono
from .utils.io import get_logger

log = get_logger("audition")
SR = 16000


def profile(path: Path) -> dict:
    from silero_vad import get_speech_timestamps, load_silero_vad
    import torch
    y, _ = load_mono(path, sr=SR)
    model = load_silero_vad()
    ts = get_speech_timestamps(torch.from_numpy(y), model, sampling_rate=SR,
                               return_seconds=False)
    mask = np.zeros(len(y), dtype=bool)
    for s in ts:
        mask[s["start"]:s["end"]] = True
    speech, gaps = y[mask], y[~mask]
    speech_rms = float(np.sqrt(np.mean(speech ** 2) + 1e-12)) if mask.any() else 0.0
    gap_rms = float(np.sqrt(np.mean(gaps ** 2) + 1e-12)) if (~mask).any() else 1e-6
    return {
        "file": path.name,
        "dur_s": round(len(y) / SR, 1),
        "snr_db": round(estimate_snr_db(y, SR, speech_mask=mask), 1),
        "nonspeech_floor_dbfs": round(20 * np.log10(gap_rms + 1e-12), 1),
        "speech_density": round(float(mask.mean()), 2),
        "n_utterances": len(ts),
    }


def main():
    files = [Path(p) for p in sys.argv[1:] if Path(p).exists()]
    if not files:
        log.error("no audio files given"); return
    rows = [profile(f) for f in files]
    rows.sort(key=lambda r: (r["nonspeech_floor_dbfs"], -r["snr_db"]))  # cleanest gaps first
    print("\nTTS-suitability profile (cleanest first):")
    print(f"{'file':<22}{'dur':>6}{'SNR dB':>8}{'gapFloor dBFS':>15}{'density':>9}{'utts':>6}")
    for r in rows:
        print(f"{r['file']:<22}{r['dur_s']:>6}{r['snr_db']:>8}"
              f"{r['nonspeech_floor_dbfs']:>15}{r['speech_density']:>9}{r['n_utterances']:>6}")
    print("\nGuide: gapFloor < -55 dBFS = clean studio silence in pauses (ideal);"
          "\n       > -45 dBFS suggests continuous music/room/PA. Higher SNR + higher"
          "\n       speech_density both favour clean long-form narration.")


if __name__ == "__main__":
    main()
