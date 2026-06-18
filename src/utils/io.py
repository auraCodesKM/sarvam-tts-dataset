"""Shared IO helpers: config loading, manifest, hashing, logging setup."""
from __future__ import annotations

import hashlib
import logging
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path = "config/pipeline.yaml") -> dict:
    with open(REPO_ROOT / path) as f:
        return yaml.safe_load(f)


def load_sources(path: str | Path = "config/sources.yaml") -> dict:
    with open(REPO_ROOT / path) as f:
        return yaml.safe_load(f)


def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def ensure_dir(path: str | Path) -> Path:
    p = REPO_ROOT / path if not str(path).startswith("/") else Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s",
                                         datefmt="%H:%M:%S"))
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
    return logger
