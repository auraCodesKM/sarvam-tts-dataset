"""Sarvam API client with on-disk response caching, retry, and usage logging.

Design goals (from PLAN.md §6 — credit frugality):
  * Every response is cached on disk keyed by (endpoint, sha256(audio), params).
    Reruns and threshold iterations therefore cost ZERO credits.
  * Exponential backoff on 429/5xx.
  * Every credit-spending call is logged to data/cache/api_usage.log so the
    report can state exact API usage.

Endpoints (verified against docs.sarvam.ai, June 2026):
  STT  : POST https://api.sarvam.ai/speech-to-text
  Chat : POST https://api.sarvam.ai/v1/chat/completions   (LLM, for emotion tags)
Auth   : header  api-subscription-key: <KEY>
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                      wait_exponential)

from .io import REPO_ROOT, get_logger, sha256_file

load_dotenv(REPO_ROOT / ".env")
log = get_logger("sarvam")

STT_URL = "https://api.sarvam.ai/speech-to-text"
CHAT_URL = "https://api.sarvam.ai/v1/chat/completions"


class SarvamError(RuntimeError):
    pass


class _Retryable(SarvamError):
    pass


class SarvamClient:
    def __init__(self, cache_dir: str | Path = "data/cache", api_key: str | None = None):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY")
        self.cache_dir = (REPO_ROOT / cache_dir) if not str(cache_dir).startswith("/") else Path(cache_dir)
        (self.cache_dir / "stt").mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "chat").mkdir(parents=True, exist_ok=True)
        self.usage_log = self.cache_dir / "api_usage.log"
        self.session = requests.Session()

    # -- internal ----------------------------------------------------------
    def _require_key(self):
        if not self.api_key:
            raise SarvamError(
                "SARVAM_API_KEY not set. Add it to .env (see .env.example) — "
                "get a key from https://dashboard.sarvam.ai")

    def _headers(self):
        return {"api-subscription-key": self.api_key}

    def _log_usage(self, kind: str, key: str, meta: dict):
        with open(self.usage_log, "a") as f:
            f.write(json.dumps({"ts": time.time(), "kind": kind, "cache_key": key, **meta}) + "\n")

    @staticmethod
    def _cache_key(*parts: str) -> str:
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]

    @retry(retry=retry_if_exception_type(_Retryable),
           wait=wait_exponential(multiplier=2, min=2, max=60),
           stop=stop_after_attempt(5), reraise=True)
    def _post(self, url, **kwargs):
        r = self.session.post(url, headers=self._headers(), timeout=180, **kwargs)
        if r.status_code == 429 or r.status_code >= 500:
            raise _Retryable(f"{r.status_code}: {r.text[:200]}")
        if r.status_code >= 400:
            raise SarvamError(f"{r.status_code}: {r.text[:300]}")
        return r.json()

    # -- public ------------------------------------------------------------
    def transcribe(self, audio_path: str | Path, language_code: str,
                   model: str = "saaras:v2.5", with_timestamps: bool = True,
                   with_diarization: bool = True) -> dict:
        """Transcribe one <30s clip. Cached by audio sha256 + params."""
        audio_path = Path(audio_path)
        digest = sha256_file(audio_path)
        ck = self._cache_key("stt", digest, language_code, model,
                             str(with_timestamps), str(with_diarization))
        cache_file = self.cache_dir / "stt" / f"{ck}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())

        self._require_key()
        data = {"language_code": language_code, "model": model}
        if with_timestamps:
            data["with_timestamps"] = "true"
        if with_diarization:
            data["with_diarization"] = "true"
        with open(audio_path, "rb") as fh:
            files = {"file": (audio_path.name, fh, "audio/wav")}
            resp = self._post(STT_URL, data=data, files=files)
        cache_file.write_text(json.dumps(resp, ensure_ascii=False, indent=2))
        self._log_usage("stt", ck, {"audio": audio_path.name, "lang": language_code,
                                    "sha256": digest})
        log.info("STT (billed): %s -> cached %s", audio_path.name, ck)
        return resp

    def chat(self, system: str, user: str, model: str = "sarvam-m",
             temperature: float = 0.2) -> str:
        """LLM chat completion (used for emotion-tag candidates). Cached."""
        ck = self._cache_key("chat", model, system, user, str(temperature))
        cache_file = self.cache_dir / "chat" / f"{ck}.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())["content"]

        self._require_key()
        payload = {"model": model, "temperature": temperature,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}]}
        resp = self._post(CHAT_URL, json=payload)
        content = resp["choices"][0]["message"]["content"]
        cache_file.write_text(json.dumps({"content": content, "raw": resp},
                                         ensure_ascii=False, indent=2))
        self._log_usage("chat", ck, {"model": model})
        log.info("CHAT (billed): cached %s", ck)
        return content
