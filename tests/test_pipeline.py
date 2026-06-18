"""Unit tests for the audio/QC core — synthetic signals, no network or credits.

Run: .venv/bin/python -m pytest tests/ -q   (or: python -m unittest)
"""
import unittest

import numpy as np

from src.utils import audio
from src.utils.io import load_config


class TestAudioMetrics(unittest.TestCase):
    def setUp(self):
        self.sr = 16000
        t = np.linspace(0, 2.0, 2 * self.sr, endpoint=False)
        self.tone = 0.3 * np.sin(2 * np.pi * 220 * t).astype(np.float32)

    def test_snr_high_for_clean_tone_with_quiet_noise(self):
        rng = np.random.default_rng(0)
        noise = 0.001 * rng.standard_normal(len(self.tone)).astype(np.float32)
        mask = np.ones(len(self.tone), dtype=bool)
        mask[: self.sr // 2] = False  # first 0.5s = "noise" region
        sig = self.tone.copy()
        sig[: self.sr // 2] = noise[: self.sr // 2]
        snr = audio.estimate_snr_db(sig, self.sr, speech_mask=mask)
        self.assertGreater(snr, 20.0)

    def test_snr_low_for_noisy_signal(self):
        rng = np.random.default_rng(1)
        noisy = self.tone + 0.3 * rng.standard_normal(len(self.tone)).astype(np.float32)
        snr = audio.estimate_snr_db(noisy, self.sr)
        self.assertLess(snr, 15.0)

    def test_loudness_normalization_moves_toward_target(self):
        quiet = 0.02 * self.tone
        out = audio.normalize_loudness(quiet, self.sr, target_lufs=-23.0,
                                       peak_ceiling_dbfs=-1.0)
        self.assertLessEqual(audio.true_peak_dbfs(out), -1.0 + 0.2)
        # normalized signal should be louder than the very quiet input
        self.assertGreater(np.sqrt(np.mean(out ** 2)),
                           np.sqrt(np.mean(quiet ** 2)))

    def test_clipping_ratio_detects_full_scale(self):
        clipped = np.ones(1000, dtype=np.float32)
        self.assertAlmostEqual(audio.clipping_ratio(clipped), 1.0, places=3)
        self.assertEqual(audio.clipping_ratio(0.5 * np.ones(1000, np.float32)), 0.0)

    def test_pad_silence_lengthens(self):
        out = audio.pad_silence(self.tone, self.sr, head_ms=100, tail_ms=200)
        self.assertEqual(len(out), len(self.tone) + int(self.sr * 0.3))


class TestConfig(unittest.TestCase):
    def test_thresholds_are_sane(self):
        cfg = load_config()
        self.assertEqual(cfg["normalize"]["sample_rate"], 24000)
        self.assertEqual(cfg["normalize"]["channels"], 1)
        self.assertGreater(cfg["acoustic_qc"]["min_snr_db"], 0)
        self.assertLess(cfg["segment"]["target_min_s"], cfg["segment"]["target_max_s"])
        self.assertIn(cfg["emotion"]["default_tag"], cfg["emotion"]["allowed_tags"])


if __name__ == "__main__":
    unittest.main()
