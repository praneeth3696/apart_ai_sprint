"""
client.py

Minimal OpenRouter client for the sprint: cache-on-receipt, retry with
backoff, and every call logged with its model ID and UTC timestamp
(PLAN.md 2 - "Log model ID string and UTC timestamp for every single call",
"Never re-run a completed cell. This is what makes Saturday survivable").

The API key is read from a .env file OUTSIDE the repo (searched upward from
this file) or from $OPENROUTER_API_KEY. It is never written to runs/, never
logged, and .env is gitignored - see the repo .gitignore.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNS_DIR = REPO_ROOT / "runs"
API_URL = "https://openrouter.ai/api/v1/chat/completions"


class RefusalOrEmpty(Exception):
    """Model returned no assistant content (hard refusal, or filtered)."""


def load_api_key() -> str:
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"].strip()
    here = pathlib.Path(__file__).resolve()
    for parent in [REPO_ROOT, *here.parents]:
        env = parent / ".env"
        if env.is_file():
            m = re.search(r"OPEN_?ROUTER_?KEY\s*=\s*(\S+)", env.read_text(encoding="utf-8"))
            if m:
                return m.group(1).strip()
    raise RuntimeError(
        "No OpenRouter key. Set $OPENROUTER_API_KEY or put OPEN_ROUTER_KEY=... "
        "in a .env file at or above the repo root (and keep it gitignored)."
    )


def _cache_path(exp: str, model: str, payload: dict) -> pathlib.Path:
    h = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()[:16]
    safe_model = model.replace("/", "_").replace(":", "_")
    return RUNS_DIR / exp / safe_model / f"{h}.json"


def call(
    model: str,
    messages: list[dict],
    *,
    exp: str,
    temperature: float = 0.0,
    max_tokens: int = 900,
    force_refresh: bool = False,
    max_retries: int = 4,
    timeout: int = 120,
) -> dict:
    """One chat completion. Returns the cached record if we've already made
    this exact call (same model, messages, temperature, max_tokens)."""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    cache = _cache_path(exp, model, payload)
    if cache.is_file() and not force_refresh:
        rec = json.loads(cache.read_text(encoding="utf-8"))
        rec["_cache_hit"] = True
        return rec

    key = load_api_key()
    body = json.dumps(payload).encode()
    last_err = None

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                API_URL,
                data=body,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/Amirtha-yazhini/apart_ai_sprint",
                    "X-Title": "apart-ai-incident-response-sprint",
                },
            )
            t_call = datetime.now(timezone.utc).isoformat()
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.load(r)

            choice = (data.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            content = msg.get("content")

            rec = {
                "model_requested": model,
                "model_returned": data.get("model"),
                "provider": data.get("provider"),
                "t_utc": t_call,
                "content": content,
                "refusal_field": msg.get("refusal"),
                "finish_reason": choice.get("finish_reason"),
                "native_finish_reason": choice.get("native_finish_reason"),
                "usage": data.get("usage"),
                "generation_id": data.get("id"),
                "_cache_hit": False,
            }
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(rec, indent=2), encoding="utf-8")
            return rec

        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:300]
            last_err = f"HTTP {e.code}: {detail}"
            # 429 / 5xx are worth retrying; 4xx client errors are not
            if e.code not in (429, 500, 502, 503, 504):
                break
            time.sleep(2 ** attempt)
        except Exception as e:  # network, timeout, JSON
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(2 ** attempt)

    raise RuntimeError(f"{model}: call failed after {max_retries} attempts - {last_err}")


def content_or_raise(rec: dict) -> str:
    c = rec.get("content")
    if c is None or not str(c).strip():
        raise RefusalOrEmpty(
            f"{rec['model_requested']}: empty content "
            f"(finish_reason={rec.get('finish_reason')}, refusal={rec.get('refusal_field')})"
        )
    return str(c)
