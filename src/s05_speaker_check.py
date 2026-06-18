"""Stage 5 — Language-match + transcript-sanity verification.

NOTE (real API constraint): per-clip diarization is NOT available on Sarvam's REST
endpoint (batch-API only, separate pricing). So single-speaker is enforced upstream
by single-speaker SOURCE selection and downstream by the human listen pass (s06),
not by an automated per-clip diarization gate. Here we keep the checks the REST
response *does* support:
  * reject clips whose detected language_code != requested language,
  * reject clips with language_probability < floor (when present; saarika returns
    it only in auto-detect mode, so it is often absent and the check is skipped),
  * reject empty / near-empty transcripts (a strong junk-clip signal).

Output: data/verified.csv with verify_pass + verify_reasons.
"""
from __future__ import annotations

import argparse

import pandas as pd

from .utils.io import REPO_ROOT, get_logger, load_config

log = get_logger("s05_speaker_check")


def main():
    cfg = load_config()
    v = cfg["verify"]
    df = pd.read_csv(REPO_ROOT / "data" / "transcripts.csv")

    def check(r):
        reasons = []
        # diarization unavailable via REST -> n_speakers defaults to 1; flag only
        # if a value >max somehow appears (e.g. from a future batch-API pass).
        if (r.get("n_speakers") or 1) > v["max_speakers"]:
            reasons.append(f"multi_speaker({int(r['n_speakers'])})")
        if str(r.get("language_code")) != str(r.get("language_requested")):
            reasons.append(f"lang_mismatch({r.get('language_code')})")
        lp = r.get("language_probability")
        if pd.notna(lp) and float(lp) < v["min_language_probability"]:
            reasons.append(f"low_lang_prob({float(lp):.2f})")
        txt = str(r.get("transcript") or "").strip()
        if len(txt) < 3:
            reasons.append("empty_transcript")
        return pd.Series({"verify_pass": len(reasons) == 0,
                          "verify_reasons": ";".join(reasons)})

    df[["verify_pass", "verify_reasons"]] = df.apply(check, axis=1)
    out = REPO_ROOT / "data" / "verified.csv"
    df.to_csv(out, index=False)
    n = int(df["verify_pass"].sum()) if len(df) else 0
    log.info("Verification: %d/%d pass single-speaker+language gate", n, len(df))
    if len(df) and (~df.verify_pass).any():
        log.info("Fail reasons:\n%s",
                 df[~df.verify_pass].verify_reasons.str.split(";").explode()
                 .value_counts().to_string())


if __name__ == "__main__":
    main()
