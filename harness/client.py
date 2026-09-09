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
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

# A model id starting with "anthropic:" is routed to Anthropic's FIRST-PARTY
# API. Bare "anthropic/..." still goes through OpenRouter. The distinction is
# load-bearing: our Wed-9 smoke test found claude-opus-5 blocked by a content
# filter via OpenRouter (all three provider routes), and whether the same
# request is blocked first-party is an open empirical question, not an
# assumption. Keep both paths so the comparison stays runnable.
ANTHROPIC_PREFIX = "anthropic:"


class RefusalOrEmpty(Exception):
    """Model returned no assistant content (hard refusal, or filtered)."""


def _find_in_env(pattern: str) -> str | None:
    here = pathlib.Path(__file__).resolve()
    for parent in [REPO_ROOT, *here.parents]:
        env = parent / ".env"
        if env.is_file():
            m = re.search(pattern, env.read_text(encoding="utf-8"))
            if m:
                return m.group(1).strip()
    return None


def load_api_key() -> str:
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"].strip()
    found = _find_in_env(r"OPEN_?ROUTER_?KEY\s*=\s*(\S+)")
    if found:
        return found
    raise RuntimeError(
        "No OpenRouter key. Set $OPENROUTER_API_KEY or put OPEN_ROUTER_KEY=... "
        "in a .env file at or above the repo root (and keep it gitignored)."
    )


def load_anthropic_key() -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"].strip()
    found = _find_in_env(r"ANTHROPIC_?(?:API_?)?KEY\s*=\s*(\S+)")
    if found:
        return found
    raise RuntimeError(
        "No Anthropic key. Set $ANTHROPIC_API_KEY or put ANTHROPIC_API_KEY=... "
        "in a .env file at or above the repo root (and keep it gitignored)."
    )


def _call_anthropic(model: str, messages: list[dict], temperature: float,
                    max_tokens: int, timeout: int) -> dict:
    """First-party Anthropic Messages API. Different shape from OpenRouter:
    x-api-key header, anthropic-version, content is a list of blocks, and a
    refusal surfaces as stop_reason='refusal' rather than a finish_reason."""
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=body,
        headers={
            "x-api-key": load_anthropic_key(),
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
    )
    t_call = datetime.now(timezone.utc).isoformat()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)

    text = "".join(
        b.get("text", "") for b in (data.get("content") or [])
        if b.get("type") == "text"
    )
    stop = data.get("stop_reason")
    usage = data.get("usage") or {}
    return {
        "model_requested": ANTHROPIC_PREFIX + model,
        "model_returned": data.get("model"),
        "provider": "Anthropic (first-party)",
        "t_utc": t_call,
        "content": text or None,
        # map Anthropic's stop_reason onto the vocabulary classify() expects
        "refusal_field": "stop_reason=refusal" if stop == "refusal" else None,
        "finish_reason": "content_filter" if stop == "refusal" else stop,
        "native_finish_reason": stop,
        "usage": {
            "prompt_tokens": usage.get("input_tokens"),
            "completion_tokens": usage.get("output_tokens"),
            "cost": None,  # first-party API does not return a per-call cost
        },
        "generation_id": data.get("id"),
        "_cache_hit": False,
    }


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

    if model.startswith(ANTHROPIC_PREFIX):
        bare = model[len(ANTHROPIC_PREFIX):]
        last_err = None
        for attempt in range(max_retries):
            try:
                rec = _call_anthropic(bare, messages, temperature, max_tokens, timeout)
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(rec, indent=2), encoding="utf-8")
                return rec
            except urllib.error.HTTPError as e:
                detail = e.read().decode()[:300]
                last_err = f"HTTP {e.code}: {detail}"
                if e.code not in (429, 500, 502, 503, 504, 529):
                    break
                time.sleep(2 ** attempt)
            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"
                time.sleep(2 ** attempt)
        raise RuntimeError(f"{model}: call failed after {max_retries} attempts - {last_err}")

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
