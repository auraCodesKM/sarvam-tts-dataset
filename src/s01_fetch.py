"""Stage 1 — Fetch source audio from YouTube with LICENSE VERIFICATION.

Downloads bestaudio (compressed) for each source in config/sources.yaml, but
ONLY after verifying the YouTube license metadata matches license_required
("Creative Commons Attribution license (reuse allowed)"). Any source failing the
license gate is skipped and logged — this is our automated licensing safeguard
for a publicly-published dataset.

Provenance (id, url, channel, license, duration, sha256) is written to
data/raw/<id>.provenance.json for full traceability.

Usage:
  python -m src.s01_fetch                 # fetch all sources
  python -m src.s01_fetch --source en_x   # fetch one
  python -m src.s01_fetch --dry-run       # verify licenses only, no download
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from .utils.io import (REPO_ROOT, ensure_dir, get_logger, load_config,
                       load_sources, sha256_file)

log = get_logger("s01_fetch")


def probe(url: str) -> dict:
    """Return yt-dlp metadata (no download)."""
    out = subprocess.run(
        ["yt-dlp", "--skip-download", "--no-warnings", "-J", url],
        capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"probe failed: {out.stderr[:200]}")
    return json.loads(out.stdout)


def fetch_one(src: dict, raw_dir: Path, license_required: str, dry_run: bool) -> dict | None:
    url = src["url"]
    if "PLACEHOLDER" in url:
        log.warning("[%s] placeholder URL — fill in a real official-channel video", src["id"])
        return None
    info = probe(url)
    lic = info.get("license") or "NA"
    rec = {"id": src["id"], "url": url, "yt_id": info.get("id"),
           "channel": info.get("channel"), "uploader": info.get("uploader"),
           "duration_s": info.get("duration"), "license": lic,
           "title": info.get("title"), "declared_language": src.get("language")}

    if lic != license_required:
        log.warning("[%s] LICENSE GATE FAIL (license=%r) — skipping", src["id"], lic)
        rec["license_gate"] = "FAIL"
        return rec
    rec["license_gate"] = "PASS"
    log.info("[%s] license OK (%s) | %ss | %s", src["id"], lic[:24],
             rec["duration_s"], rec["title"])
    if dry_run:
        return rec

    out_path = raw_dir / f"{src['id']}.%(ext)s"
    cmd = ["yt-dlp", "-f", "bestaudio", "--no-warnings",
           "-o", str(out_path), url]
    subprocess.run(cmd, check=True, timeout=600)
    audio = next((p for p in raw_dir.glob(f"{src['id']}.*")
                  if p.suffix not in (".json",)), None)
    if audio:
        rec["audio_file"] = audio.name
        rec["sha256"] = sha256_file(audio)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    sources = load_sources()
    raw_dir = ensure_dir(cfg["paths"]["raw_dir"])
    license_required = sources["license_required"]

    all_src = []
    for lang_key in ("english", "hindi"):
        all_src.extend(sources.get(lang_key, []))
    if args.source:
        all_src = [s for s in all_src if s["id"] == args.source]

    results = []
    for src in all_src:
        try:
            rec = fetch_one(src, raw_dir, license_required, args.dry_run)
            if rec:
                results.append(rec)
                (raw_dir / f"{src['id']}.provenance.json").write_text(
                    json.dumps(rec, ensure_ascii=False, indent=2))
        except Exception as e:
            log.error("[%s] fetch error: %s", src["id"], e)

    n_pass = sum(1 for r in results if r.get("license_gate") == "PASS")
    log.info("Done: %d sources processed, %d passed license gate", len(results), n_pass)


if __name__ == "__main__":
    main()
