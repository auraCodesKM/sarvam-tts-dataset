"""Analysis & report artifacts: the QC funnel table, WER, and figures.

Produces (from the pipeline CSVs):
  * reports/funnel.csv + a markdown funnel table   (headline figure)
  * reports/wer.json  - Sarvam ASR WER/CER vs. human-corrected transcripts
  * reports/figures/*.png - SNR & duration histograms, per-speaker & emotion counts

WER here = error of raw Sarvam ASR measured against the human-corrected final
transcript on every clip a reviewer edited (a real, if optimistic, proxy for ASR
quality; the report states this caveat). A stricter blind-gold WER is future work.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .utils.io import REPO_ROOT, ensure_dir, get_logger

log = get_logger("analyze")
D = REPO_ROOT / "data"
FIG = ensure_dir("reports/figures")


def _safe_read(p):
    return pd.read_csv(D / p) if (D / p).exists() else pd.DataFrame()


def funnel() -> pd.DataFrame:
    seg = _safe_read("acoustic_qc.csv")
    tr = _safe_read("transcripts.csv")
    ver = _safe_read("verified.csv")
    review_p = REPO_ROOT / "review" / "review_log.csv"
    rev = pd.read_csv(review_p) if review_p.exists() else pd.DataFrame()

    stages = []
    stages.append(("Segmented (VAD utterances)", len(seg)))
    if len(seg):
        stages.append(("Passed acoustic QC", int(seg.qc_pass.sum())))
    stages.append(("Transcribed (Sarvam STT)", len(tr)))
    if len(ver):
        stages.append(("Passed single-speaker + language", int(ver.verify_pass.sum())))
    if len(rev):
        stages.append(("Human-reviewed (decided)",
                        int(rev.decision.isin(["ACCEPT", "REJECT"]).sum())))
        stages.append(("ACCEPTED into dataset", int((rev.decision == "ACCEPT").sum())))
    df = pd.DataFrame(stages, columns=["stage", "clips"])
    df["surviving_pct"] = (100 * df.clips / df.clips.iloc[0]).round(1) if len(df) and df.clips.iloc[0] else 0
    df.to_csv(REPO_ROOT / "reports" / "funnel.csv", index=False)
    log.info("Funnel:\n%s", df.to_string(index=False))
    return df


def wer():
    review_p = REPO_ROOT / "review" / "review_log.csv"
    if not review_p.exists():
        log.info("no review log; skip WER"); return
    rev = pd.read_csv(review_p)
    acc = rev[rev.decision == "ACCEPT"].dropna(subset=["asr_transcript", "final_transcript"])
    if not len(acc):
        log.info("no accepted clips; skip WER"); return
    import jiwer
    out = {}
    for lang, g in acc.groupby("language_code"):
        ref = g.final_transcript.astype(str).tolist()
        hyp = g.asr_transcript.astype(str).tolist()
        out[lang] = {"n": len(g),
                     "wer": round(jiwer.wer(ref, hyp), 4),
                     "cer": round(jiwer.cer(ref, hyp), 4),
                     "pct_clips_edited": round(100 * (g.asr_transcript != g.final_transcript).mean(), 1)}
    (REPO_ROOT / "reports" / "wer.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    log.info("WER (ASR vs human-corrected):\n%s", json.dumps(out, indent=2, ensure_ascii=False))


def figures():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    seg = _safe_read("acoustic_qc.csv")
    if len(seg):
        for col, title, fname in [("snr_db", "SNR (dB) distribution", "snr_hist.png"),
                                  ("duration_s", "Clip duration (s)", "duration_hist.png")]:
            plt.figure(figsize=(6, 3.2))
            plt.hist(seg[col].dropna(), bins=30, color="#3b6", edgecolor="k", alpha=.8)
            plt.title(title); plt.tight_layout()
            plt.savefig(FIG / fname, dpi=130); plt.close()
    man = REPO_ROOT / "data" / "manifest.csv"
    if man.exists():
        df = pd.read_csv(man)
        for col, fname in [("speaker", "per_speaker.png"), ("emotion", "emotion_dist.png"),
                           ("language", "language_dist.png")]:
            if col in df:
                plt.figure(figsize=(6, 3.2))
                df[col].value_counts().plot(kind="bar", color="#36b", edgecolor="k")
                plt.title(f"clips by {col}"); plt.tight_layout()
                plt.savefig(FIG / fname, dpi=130); plt.close()
    log.info("Figures written to %s", FIG)


def main():
    funnel(); wer(); figures()


if __name__ == "__main__":
    main()
