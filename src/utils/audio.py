"""Audio analysis & processing helpers (load, SNR, loudness, normalize, trim)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf


def _ffmpeg_decode(path: str | Path, sr: int) -> np.ndarray:
    """Decode any container (webm/opus/m4a/...) to float32 mono via ffmpeg pipe.

    Avoids writing large intermediate WAVs (disk-frugal): ffmpeg streams 16-bit
    PCM to stdout which we read into numpy.
    """
    import subprocess
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le",
           "-acodec", "pcm_s16le", "-ac", "1", "-ar", str(sr), "-"]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype="<i2").astype(np.float32) / 32768.0


def load_mono(path: str | Path, sr: int | None = None) -> tuple[np.ndarray, int]:
    """Load audio as float32 mono. Optionally resample. Falls back to ffmpeg for
    containers libsndfile can't read (webm/opus/m4a from yt-dlp bestaudio)."""
    try:
        y, file_sr = sf.read(str(path), dtype="float32", always_2d=False)
        if y.ndim > 1:
            y = y.mean(axis=1)
        if sr is not None and sr != file_sr:
            import librosa
            y = librosa.resample(y, orig_sr=file_sr, target_sr=sr)
            file_sr = sr
        return y, file_sr
    except sf.LibsndfileError:
        target = sr or 16000
        return _ffmpeg_decode(path, target), target


def save_wav(path: str | Path, y: np.ndarray, sr: int, subtype: str = "PCM_16"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), y, sr, subtype=subtype)


def measure_lufs(y: np.ndarray, sr: int) -> float:
    """Integrated loudness (EBU R128). Returns -inf-safe float."""
    if len(y) < sr // 2:  # <0.5s: meter is unreliable
        return -70.0
    meter = pyln.Meter(sr)
    try:
        return float(meter.integrated_loudness(y))
    except Exception:
        return -70.0


def true_peak_dbfs(y: np.ndarray) -> float:
    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    return 20.0 * np.log10(peak + 1e-12)


def clipping_ratio(y: np.ndarray, thresh: float = 0.999) -> float:
    if not len(y):
        return 0.0
    return float(np.mean(np.abs(y) >= thresh))


def estimate_snr_db(y: np.ndarray, sr: int, speech_mask: np.ndarray | None = None) -> float:
    """Estimate SNR using a VAD speech mask if given, else an energy-percentile
    heuristic (top frames = speech, bottom = noise floor).

    speech_mask: boolean array over *samples* (True = speech). When provided we
    compute speech RMS over masked samples and noise RMS over the rest.
    """
    if speech_mask is not None and speech_mask.any() and (~speech_mask).any():
        speech = y[speech_mask]
        noise = y[~speech_mask]
        sp = np.sqrt(np.mean(speech ** 2) + 1e-12)
        no = np.sqrt(np.mean(noise ** 2) + 1e-12)
        return float(20.0 * np.log10(sp / no))

    # Fallback: frame energies, top 15% = speech, bottom 15% = noise.
    frame = max(1, int(0.025 * sr))
    n = len(y) // frame
    if n < 4:
        return 0.0
    frames = y[: n * frame].reshape(n, frame)
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
    rms_sorted = np.sort(rms)
    k = max(1, int(0.15 * n))
    noise = np.mean(rms_sorted[:k])
    speech = np.mean(rms_sorted[-k:])
    return float(20.0 * np.log10((speech + 1e-12) / (noise + 1e-12)))


def normalize_loudness(y: np.ndarray, sr: int, target_lufs: float,
                       peak_ceiling_dbfs: float) -> np.ndarray:
    """Loudness-normalize to target LUFS, then hard-limit to a peak ceiling."""
    loudness = measure_lufs(y, sr)
    if loudness > -70.0:
        y = pyln.normalize.loudness(y, loudness, target_lufs)
    ceiling = 10.0 ** (peak_ceiling_dbfs / 20.0)
    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    if peak > ceiling:
        y = y * (ceiling / peak)
    return y.astype(np.float32)


def pad_silence(y: np.ndarray, sr: int, head_ms: int, tail_ms: int) -> np.ndarray:
    head = np.zeros(int(sr * head_ms / 1000), dtype=y.dtype)
    tail = np.zeros(int(sr * tail_ms / 1000), dtype=y.dtype)
    return np.concatenate([head, y, tail])


def trim_to_window(y: np.ndarray, sr: int, start_s: float, end_s: float,
                   pad_ms: int = 80) -> np.ndarray:
    """Crop y to [start_s, end_s] with a small symmetric pad (for edge trim)."""
    pad = sr * pad_ms / 1000
    a = max(0, int(start_s * sr - pad))
    b = min(len(y), int(end_s * sr + pad))
    return y[a:b]
