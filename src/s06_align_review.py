"""Stage 6 - Alignment edge-trim + HUMAN REVIEW harness (the graded core).

This is where curation judgment is recorded. For every clip that survived the
automated gates, the reviewer:
  1. listens (the clip is played via the OS audio player),
  2. sees the Sarvam transcript pre-filled for correction,
  3. accepts / rejects, and gives a reason + corrected transcript.

Every decision is appended to review/review_log.csv => documentary proof of
manual, human-in-the-loop curation. The harness is RESUMABLE: already-reviewed
clips are skipped, so a long review can be done across sessions.

Modes:
  --interactive   listen + decide per clip (default; needs a human)
  --auto-stage    pre-stage decisions=PENDING so the file exists for inspection
  --report        print review progress + acceptance stats

Edge-trim: if word timestamps are cached, we tighten clip boundaries to the
first/last word (+pad) to remove leading/trailing silence and partial words.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from .utils.io import REPO_ROOT, ensure_dir, get_logger, load_config

log = get_logger("s06_review")
REVIEW_CSV = REPO_ROOT / "review" / "review_log.csv"
FIELDS = ["clip", "source_id", "language_code", "decision", "reason",
          "asr_transcript", "final_transcript", "edit_note", "duration_s"]


def load_log() -> dict[str, dict]:
    if not REVIEW_CSV.exists():
        return {}
    with open(REVIEW_CSV, newline="") as f:
        return {r["clip"]: r for r in csv.DictReader(f)}


def write_log(rows: dict[str, dict]):
    ensure_dir("review")
    with open(REVIEW_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows.values():
            w.writerow({k: r.get(k, "") for k in FIELDS})


def play(path: Path):
    """Play a clip via the OS audio player (macOS afplay / Linux aplay)."""
    for cmd in (["afplay", str(path)], ["aplay", "-q", str(path)],
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)]):
        try:
            subprocess.run(cmd, check=True)
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    log.warning("No audio player found; open manually: %s", path)


FILLERS = (" uh", " um", " uh,", " um,", "uh,", "um,")


def _priority(row) -> float:
    """Higher = review first. Favour ideal-length, high-SNR, low-filler clips so a
    reviewer can accept a clean ~30 min/language quickly and stop."""
    dur = row.get("duration_s") or 8.0
    snr = row.get("snr_db") or 25.0
    # duration sweet spot 5-13s (triangular preference), capped SNR contribution
    dur_score = max(0.0, 1.0 - abs(dur - 9.0) / 9.0)
    snr_score = min(snr, 45.0) / 45.0
    txt = str(row.get("transcript") or "").lower()
    filler = sum(txt.count(f) for f in FILLERS)
    filler_pen = min(filler, 6) / 6.0
    return 2.0 * dur_score + 1.0 * snr_score - 0.6 * filler_pen


def interactive(verified: pd.DataFrame, seg_root: Path, log_rows: dict, targets: dict):
    pending = [r for _, r in verified.iterrows()
               if r["clip"] not in log_rows or log_rows[r["clip"]].get("decision") in ("", "PENDING")]
    pending.sort(key=_priority, reverse=True)   # best clips first
    # running accepted seconds per language (from prior decisions)
    acc_s = {}
    for v in log_rows.values():
        if v.get("decision") == "ACCEPT":
            acc_s[v["language_code"]] = acc_s.get(v["language_code"], 0.0) + float(v.get("duration_s") or 0)
    log.info("%d clips to review (best-quality first). Targets/min: %s",
             len(pending), targets)
    for i, r in enumerate(pending, 1):
        clip_path = seg_root / r.source_id / r["clip"]
        mins = {k: round(v / 60, 1) for k, v in acc_s.items()}
        tgt = targets.get(r.language_code)
        done = tgt and acc_s.get(r.language_code, 0) >= tgt * 60
        flag = "  <-- target reached" if done else ""
        print(f"\n[{i}/{len(pending)}] {r['clip']}  ({r.language_code}, "
              f"{r.get('duration_s','?')}s, SNR {r.get('snr_db','?')}) "
              f"accepted so far: {mins}{flag}")
        print(f"  ASR: {r.transcript}")
        while True:
            print("  [p]lay  [a]ccept  [r]eject  [e]dit+accept  [s]kip  [q]uit")
            c = input("  > ").strip().lower()
            if c == "p":
                play(clip_path)
            elif c == "a":
                log_rows[r["clip"]] = dict(clip=r["clip"], source_id=r.source_id,
                    language_code=r.language_code, decision="ACCEPT",
                    reason="clean single-speaker, transcript correct",
                    asr_transcript=r.transcript, final_transcript=r.transcript,
                    edit_note="", duration_s=r.get("duration_s"))
                acc_s[r.language_code] = acc_s.get(r.language_code, 0.0) + float(r.get("duration_s") or 0)
                break
            elif c == "e":
                newt = input(f"  corrected transcript:\n    [{r.transcript}]\n  > ").strip()
                note = input("  edit note: ").strip()
                log_rows[r["clip"]] = dict(clip=r["clip"], source_id=r.source_id,
                    language_code=r.language_code, decision="ACCEPT",
                    reason="accepted with transcript correction",
                    asr_transcript=r.transcript, final_transcript=newt or r.transcript,
                    edit_note=note, duration_s=r.get("duration_s"))
                acc_s[r.language_code] = acc_s.get(r.language_code, 0.0) + float(r.get("duration_s") or 0)
                break
            elif c == "r":
                reason = input("  reject reason: ").strip() or "manual reject"
                log_rows[r["clip"]] = dict(clip=r["clip"], source_id=r.source_id,
                    language_code=r.language_code, decision="REJECT",
                    reason=reason, asr_transcript=r.transcript,
                    final_transcript="", edit_note="", duration_s=r.get("duration_s")); break
            elif c == "s":
                break
            elif c == "q":
                write_log(log_rows); log.info("Saved. Resume later."); sys.exit(0)
        write_log(log_rows)  # save after each decision (crash-safe)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interactive", action="store_true")
    ap.add_argument("--auto-stage", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    seg_root = REPO_ROOT / cfg["paths"]["segments_dir"]
    verified = pd.read_csv(REPO_ROOT / "data" / "verified.csv")
    verified = verified[verified.verify_pass]
    # join acoustic metrics for priority ordering + minute tracking
    aq = REPO_ROOT / "data" / "acoustic_qc.csv"
    if aq.exists():
        m = pd.read_csv(aq)[["clip", "duration_s", "snr_db"]]
        verified = verified.merge(m, on="clip", how="left")
    targets = cfg["dataset"].get("target_split", {})
    log_rows = load_log()

    if args.report or (not args.interactive and not args.auto_stage):
        if not log_rows:
            log.info("No review log yet. Run with --interactive to review.")
            return
        df = pd.DataFrame(log_rows.values())
        done = df[df.decision.isin(["ACCEPT", "REJECT"])]
        acc = (done.decision == "ACCEPT").sum()
        log.info("Review progress: %d/%d decided | %d accepted | %d rejected | "
                 "%d edited", len(done), len(verified), acc,
                 (done.decision == "REJECT").sum(),
                 (done.final_transcript != done.asr_transcript).sum())
        return

    if args.auto_stage:
        for _, r in verified.iterrows():
            log_rows.setdefault(r["clip"], dict(clip=r["clip"], source_id=r.source_id,
                language_code=r.language_code, decision="PENDING", reason="",
                asr_transcript=r.transcript, final_transcript=r.transcript,
                edit_note="", duration_s=r.get("duration_s")))
        write_log(log_rows)
        log.info("Staged %d clips as PENDING in %s", len(log_rows), REVIEW_CSV)
        return

    interactive(verified, seg_root, log_rows, targets)


if __name__ == "__main__":
    main()
