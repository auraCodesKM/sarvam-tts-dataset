"""Stage 8 — Emotion/style tagging: Sarvam LLM candidate -> human confirm.

The LLM proposes ONE tag from the allowed set using the transcript (+ content
type) as context. This is a *candidate only*: emotion is an acoustic property the
text often can't reveal, so a human confirms by listening (review/emotion_log.csv).
We tag conservatively — lecture/audiobook content skews neutral/formal — and the
report documents this limitation honestly (the brief explicitly expects it).

Output: data/emotion_tags.csv (clip, llm_tag, final_tag, confirmed)
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from .utils.io import REPO_ROOT, get_logger, load_config, load_sources
from .utils.sarvam_client import SarvamClient

log = get_logger("s08_emotion")

SYSTEM = (
    "You label the speaking STYLE/EMOTION of a short speech clip given only its "
    "transcript. Reply with EXACTLY ONE word from this set and nothing else: "
    "{tags}. Most lecture/narration content is 'neutral', 'formal', or "
    "'conversational' — only choose an affective tag (happy/sad/excited/angry) "
    "when the wording clearly signals it.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-llm", action="store_true",
                    help="skip LLM, default everything to default_tag")
    args = ap.parse_args()
    cfg = load_config()
    tags = cfg["emotion"]["allowed_tags"]
    default = cfg["emotion"]["default_tag"]

    review = pd.read_csv(REPO_ROOT / "review" / "review_log.csv")
    accepted = review[review.decision == "ACCEPT"].copy()
    client = SarvamClient(cache_dir=cfg["paths"]["cache_dir"])
    system = SYSTEM.format(tags=", ".join(tags))

    rows = []
    for _, r in accepted.iterrows():
        text = str(r.final_transcript)
        if args.no_llm:
            cand = default
        else:
            try:
                out = client.chat(system, text).strip().lower()
                cand = next((t for t in tags if t in out), default)
            except Exception as e:
                log.warning("[%s] LLM tag failed (%s) -> default", r.clip, e)
                cand = default
        rows.append({"clip": r.clip, "llm_tag": cand, "final_tag": cand,
                     "confirmed": False})
    df = pd.DataFrame(rows)
    out = REPO_ROOT / "data" / "emotion_tags.csv"
    df.to_csv(out, index=False)
    log.info("Proposed emotion tags for %d clips -> %s", len(df), out)
    if len(df):
        log.info("Tag distribution (LLM candidate):\n%s",
                 df.final_tag.value_counts().to_string())
    log.info("NEXT: a human confirms each tag by listening, sets confirmed=True "
             "and corrects final_tag where the audio disagrees.")


if __name__ == "__main__":
    main()
