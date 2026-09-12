"""
client.py

Multi-provider client for the sprint: cache-on-receipt, retry with backoff,
and every call logged with its model ID and UTC timestamp (PLAN.md 2 - "Log
model ID string and UTC timestamp for every single call", "Never re-run a
completed cell. This is what makes Saturday survivable").

ROUTING
-------
The model id decides the route. There are exactly three shapes:

    "qwen/qwen3-coder:free"        -> OpenRouter          (the default)
    "anthropic:claude-opus-5"      -> Anthropic first-party Messages API
    "google:gemini-2.5-flash"      -> that provider's OpenAI-compatible API

A **slash** is part of an OpenRouter model id ("anthropic/claude-opus-5" is
OpenRouter's Anthropic route). A leading **`<provider>:`** whose provider is in
PROVIDERS below is a direct route. Anything else - including OpenRouter's own
":free" suffix, which is a suffix and not a prefix - falls through to
OpenRouter unchanged.

That distinction is load-bearing and predates this file's multi-provider
support: our Wed-9 smoke test found claude-opus-5 blocked by a content filter
via OpenRouter (all three provider routes), and whether the same request is
blocked first-party is an open empirical question, not an assumption. The same
logic now applies to every model reachable on two providers - see
PROVIDERS.md 4, "a model is not a model; it is a model *as served by
someone*".

KEYS
----
Read from a gitignored .env at or above the repo root, or from the environment.
Never written to runs/, never logged.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
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
# API. Bare "anthropic/..." still goes through OpenRouter. See the module
# docstring - keep both paths so the comparison stays runnable.
ANTHROPIC_PREFIX = "anthropic:"

# ---------------------------------------------------------------------------
# Direct providers. All OpenAI-compatible: the only thing that changes is the
# base URL and where the key comes from, which is why this is a table and not
# seven client classes.
#
# base_url is the OpenAI-compatible root; we POST {base_url}/chat/completions.
# The base URLs are the same ones harness/measure_limits.py probes, so the
# roster in PROVIDERS.md, the limit measurement and the runner cannot drift
# apart. env_pattern is matched against .env; env_var against os.environ.
# ---------------------------------------------------------------------------
PROVIDERS: dict[str, dict] = {
    "google": {
        "label": "Google AI Studio",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "env_var": "GOOGLE_AI_STUDIO_KEY",
        "env_pattern": r"GOOGLE_AI_STUDIO_KEY\s*=\s*(\S+)",
    },
    "github": {
        "label": "GitHub Models",
        "base_url": "https://models.inference.ai.azure.com",
        "env_var": "GITHUB_MODELS_TOKEN",
        "env_pattern": r"GITHUB_MODELS_TOKEN\s*=\s*(\S+)",
    },
    "groq": {
        "label": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "env_var": "GROQ_API_KEY",
        "env_pattern": r"GROQ_API_KEY\s*=\s*(\S+)",
    },
    "cerebras": {
        "label": "Cerebras",
        "base_url": "https://api.cerebras.ai/v1",
        "env_var": "CEREBRAS_API_KEY",
        "env_pattern": r"CEREBRAS_API_KEY\s*=\s*(\S+)",
    },
    "mistral": {
        "label": "Mistral",
        "base_url": "https://api.mistral.ai/v1",
        "env_var": "MISTRAL_API_KEY",
        "env_pattern": r"MISTRAL_API_KEY\s*=\s*(\S+)",
    },
    # Offline insurance (PROVIDERS.md 1). No key, no rate limit, no network.
    "ollama": {
        "label": "Ollama (local)",
        "base_url": "http://localhost:11434/v1",
        "env_var": None,
        "env_pattern": None,
    },
}

# 429 is retryable and is never a model behaviour (PROVIDERS.md 3). 5xx and
# Anthropic's 529 "overloaded" likewise. Everything else is a client error and
# retrying it just burns quota.
RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}


class RefusalOrEmpty(Exception):
    """Model returned no assistant content (hard refusal, or filtered)."""


class ApiError(RuntimeError):
    """A call that failed after retries. Carries the HTTP status where there
    was one, so callers can tell a 402 (RUBRIC.md 0 `unaffordable` - excluded
    from every denominator, never scored as a refusal) apart from a 400.

    `quota_scope` is "minute" or "day" for a 429 whose body named the quota it
    broke. A per-DAY exhaustion is not a thing to back off from - it is this
    model finished until the quota resets - and the runner uses it to move on
    to the next model instead of sleeping through the rest of the night.
    """

    def __init__(self, message: str, status: int | None = None,
                 quota_scope: str | None = None):
        super().__init__(message)
        self.status = status
        self.quota_scope = quota_scope


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


def load_provider_key(prefix: str) -> str | None:
    """Key for one direct provider, or None for a provider that needs none
    (Ollama). Raises if a key IS needed and none is set."""
    spec = PROVIDERS[prefix]
    if spec["env_var"] is None:
        return None
    if os.environ.get(spec["env_var"]):
        return os.environ[spec["env_var"]].strip()
    found = _find_in_env(spec["env_pattern"])
    if found:
        return found
    raise RuntimeError(
        f"No {spec['label']} key. Set ${spec['env_var']} or put "
        f"{spec['env_var']}=... in a .env file at or above the repo root "
        f"(and keep it gitignored). See harness/PROVIDERS.md."
    )


def split_model(model: str) -> tuple[str | None, str]:
    """('google', 'gemini-2.5-flash') for a direct route, (None, model) for
    OpenRouter. OpenRouter's ':free' SUFFIX must not be mistaken for a prefix,
    so only a leading segment that names a known provider counts."""
    prefix, sep, rest = model.partition(":")
    if sep and prefix in PROVIDERS and rest:
        return prefix, rest
    return None, model


def available_providers() -> dict[str, bool]:
    """Which routes have a usable key right now. Used by measure_limits.py and
    by the runners to fail early instead of 400 calls in."""
    out: dict[str, bool] = {}
    for prefix in PROVIDERS:
        try:
            load_provider_key(prefix)
            out[prefix] = True
        except RuntimeError:
            out[prefix] = False
    for label, loader in (("openrouter", load_api_key),
                          ("anthropic", load_anthropic_key)):
        try:
            loader()
            out[label] = True
        except RuntimeError:
            out[label] = False
    return out


def _post_json(url: str, body: bytes, headers: dict, timeout: int) -> dict:
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _from_openai_shape(data: dict, model_requested: str, provider: str,
                       t_call: str) -> dict:
    """Normalise an OpenAI-compatible response into our record. Identical for
    OpenRouter and every direct provider - that is the whole point of the
    base-URL swap."""
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    return {
        "model_requested": model_requested,
        "model_returned": data.get("model"),
        "provider": provider,
        "t_utc": t_call,
        "content": msg.get("content"),
        "refusal_field": msg.get("refusal"),
        "finish_reason": choice.get("finish_reason"),
        "native_finish_reason": choice.get("native_finish_reason"),
        "usage": data.get("usage"),
        "generation_id": data.get("id"),
        "_cache_hit": False,
    }


def _call_openrouter(model: str, payload: dict, timeout: int) -> dict:
    key = load_api_key()
    t_call = datetime.now(timezone.utc).isoformat()
    data = _post_json(
        API_URL,
        json.dumps(payload).encode(),
        {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Amirtha-yazhini/apart_ai_sprint",
            "X-Title": "apart-ai-incident-response-sprint",
        },
        timeout,
    )
    rec = _from_openai_shape(data, model, data.get("provider"), t_call)
    # OpenRouter reports the serving provider itself; keep whatever it said.
    rec["provider"] = data.get("provider")
    return rec


def _call_direct(prefix: str, bare: str, model_requested: str, payload: dict,
                 timeout: int) -> dict:
    """Any OpenAI-compatible provider from the PROVIDERS table."""
    spec = PROVIDERS[prefix]
    key = load_provider_key(prefix)
    body = dict(payload)
    body["model"] = bare  # the provider has never heard of our prefix
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    t_call = datetime.now(timezone.utc).isoformat()
    data = _post_json(f"{spec['base_url']}/chat/completions",
                      json.dumps(body).encode(), headers, timeout)
    return _from_openai_shape(data, model_requested, spec["label"], t_call)


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
    t_call = datetime.now(timezone.utc).isoformat()
    data = _post_json(
        ANTHROPIC_URL,
        body,
        {
            "x-api-key": load_anthropic_key(),
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        timeout,
    )

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


def _suggested_delay(headers, body: str) -> float | None:
    """The provider's own answer to "how long should I wait", if it gave one.

    Two places to look. Most OpenAI-compatible providers use the `Retry-After`
    header. Google AI Studio does not: it returns HTTP 429 with a
    google.rpc.RetryInfo block in the JSON body, `"retryDelay": "41s"`, and
    hammering it again at 2s just extends the lockout.
    """
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if raw:
        try:
            return float(raw)
        except (TypeError, ValueError):
            pass
    for pat in (
        # google.rpc.RetryInfo, when the compat layer includes it
        r'"retryDelay"\s*:\s*"?(\d+(?:\.\d+)?)s',
        # ...and when it does not, Google AI Studio states the delay only as
        # prose at the end of the error message: "Please retry in 51.98s."
        r"[Pp]lease retry in (\d+(?:\.\d+)?)\s*s",
    ):
        m = re.search(pat, body or "")
        if m:
            return float(m.group(1))
    return None


def _quota_scope(body: str) -> str | None:
    """"minute" or "day" for a 429 that named its own quota, else None.

    Measured on Google AI Studio 2026-09-12: a free-tier 429 carries
    google.rpc.QuotaFailure violations whose quotaId spells the window out -
    `GenerateRequestsPerMinutePerProjectPerModel-FreeTier` versus
    `GenerateRequestsPerDayPerProjectPerModel-FreeTier`. The distinction is
    the difference between waiting 12 seconds and waiting until tomorrow, and
    the `Please retry in 11.5s` in the same body is wrong about which one it
    is - it said that for a quota with a DAILY window.
    """
    ids = re.findall(r'"quotaId"\s*:\s*"([^"]+)"', body or "")
    joined = " ".join(ids)
    if not joined:
        return None
    if "PerMinute" in joined:
        return "minute"          # a real backoff will clear it
    if "PerDay" in joined:
        return "day"
    return None


def _backoff(status: int | None, headers, body: str, attempt: int) -> float:
    """Seconds to wait before the next attempt.

    A 429 gets its own floor. Every other retryable status is a transient
    server-side blip that usually clears in a second or two, but a 429 is a
    QUOTA - a per-minute allowance does not refill in 2s, and retrying inside
    the window burns an attempt for nothing. Capped at 90s so one absurd
    Retry-After cannot stall an unattended run.
    """
    suggested = _suggested_delay(headers, body)
    if suggested is not None:
        return min(max(suggested + 1.0, 1.0), 90.0)
    if status == 429:
        return min(15.0 * (2 ** attempt), 90.0)
    return float(2 ** attempt)


def call(
    model: str,
    messages: list[dict],
    *,
    exp: str,
    temperature: float = 0.0,
    max_tokens: int = 900,
    force_refresh: bool = False,
    max_retries: int = 4,
    max_rate_limit_retries: int = 8,
    timeout: int = 120,
) -> dict:
    """One chat completion. Returns the cached record if we've already made
    this exact call (same model, messages, temperature, max_tokens).

    Raises ApiError on a call that fails after retries; ApiError.status is the
    HTTP status where there was one (402 -> RUBRIC.md 0 `unaffordable`).

    A 429 draws on `max_rate_limit_retries`, NOT on `max_retries`. PROVIDERS.md
    3: "HTTP 429 is retryable and is never a model behaviour... Back off and
    retry; never score it." Letting a rate limit exhaust the same budget as a
    genuine failure is how an overnight run turns a free-tier quota window into
    a column of `error` rows.
    """
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    # Cache key uses the PREFIXED id, so the same model served by two
    # providers occupies two cache slots. That comparison is the point.
    cache = _cache_path(exp, model, payload)
    if cache.is_file() and not force_refresh:
        rec = json.loads(cache.read_text(encoding="utf-8"))
        rec["_cache_hit"] = True
        return rec

    prefix, bare = split_model(model)
    if model.startswith(ANTHROPIC_PREFIX):
        def do_call() -> dict:
            return _call_anthropic(model[len(ANTHROPIC_PREFIX):], messages,
                                   temperature, max_tokens, timeout)
    elif prefix is not None:
        def do_call() -> dict:
            return _call_direct(prefix, bare, model, payload, timeout)
    else:
        def do_call() -> dict:
            return _call_openrouter(model, payload, timeout)

    last_err = None
    last_status = None
    attempts = 0
    fails = 0        # non-429 failures, against max_retries
    throttles = 0    # 429s, against max_rate_limit_retries
    while fails < max_retries and throttles < max_rate_limit_retries:
        attempts += 1
        try:
            rec = do_call()
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(rec, indent=2), encoding="utf-8")
            return rec
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            last_err = f"HTTP {e.code}: {body[:300]}"
            last_status = e.code
            if e.code not in RETRYABLE_STATUS:
                break
            if e.code == 429:
                scope = _quota_scope(body)
                if scope == "day":
                    # Not a throttle. This model is done until the quota
                    # resets; sleeping 90s eight times would only turn one
                    # exhausted model into a stalled run.
                    raise ApiError(
                        f"{model}: free-tier DAILY quota exhausted - {last_err}",
                        status=429, quota_scope="day",
                    ) from None
                wait = _backoff(429, e.headers, body, throttles)
                throttles += 1
                # An unattended run that sleeps silently looks hung. stderr, so
                # it never contaminates a piped result file.
                print(f"  [rate limit] {model}: waiting {wait:.0f}s "
                      f"({throttles}/{max_rate_limit_retries})",
                      file=sys.stderr, flush=True)
            else:
                wait = _backoff(e.code, e.headers, body, fails)
                fails += 1
            time.sleep(wait)
        except Exception as e:  # network, timeout, JSON
            last_err = f"{type(e).__name__}: {e}"
            last_status = None
            time.sleep(2 ** fails)
            fails += 1

    # Report the attempts actually made, not the ceiling: a 404 breaks out of
    # the loop on the first try, and "failed after 4 attempts" on a
    # non-retryable status sends you hunting for a flaky network instead of a
    # retired model id.
    raise ApiError(
        f"{model}: call failed after {attempts} "
        f"attempt{'s' if attempts != 1 else ''} - {last_err}",
        status=last_status,
        quota_scope="minute" if last_status == 429 else None,
    )


def content_or_raise(rec: dict) -> str:
    c = rec.get("content")
    if c is None or not str(c).strip():
        raise RefusalOrEmpty(
            f"{rec['model_requested']}: empty content "
            f"(finish_reason={rec.get('finish_reason')}, refusal={rec.get('refusal_field')})"
        )
    return str(c)
