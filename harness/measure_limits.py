"""
measure_limits.py

SPRINT_PLAN.md section 1.1, Friday T+0 to T+1h. The FIRST thing that runs on
sprint morning, and nothing downstream may be sized until it has.

WHY
---
PLAN.md wants ~250 windows. PREREGISTRATION.md section 8a lists 11 models. E1
runs two streams. That is:

    250 windows x 2 streams x 11 models = 5,500 calls   (E1 alone)

OpenRouter's free tier is rate-limited by requests-per-minute AND by a daily
cap that depends on lifetime credit purchased. The account behind this repo is
unfunded and running a negative balance. At the unfunded daily cap the study is
months of work; at the funded-threshold cap it is still days. Budget stopped
being the risk when the study went to $0 (PREREGISTRATION.md section 8d) -
THROUGHPUT is the risk now, and no document in this repo has a number attached
to it.

This script gets the number, from the provider rather than by guessing, and
then does the run-sizing arithmetic so the answer is not left to Friday-night
judgment.

WHAT IT DOES
------------
1. OpenRouter: GET /api/v1/key returns the account's own rate_limit, usage,
   remaining credit and is_free_tier flag. One call, exact answer - far better
   than hammering the endpoint until something 429s.
2. Any other OpenAI-compatible provider named in PROVIDERS.md: one cheap
   completion, then read the x-ratelimit-* response headers.
3. Prints the sizing formula from SPRINT_PLAN.md section 3 against whatever
   total it found.

Missing keys are reported, not fatal. Run it with whatever you have.

Usage:
    python harness/measure_limits.py
    python harness/measure_limits.py --models 6 --reserve 0.5
"""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "harness"))

from client import USER_AGENT, _find_in_env  # noqa: E402

OUT_PATH = REPO / "harness" / "measured_limits.json"

# Providers to probe. Each is (label, env/.env key pattern, base_url, a model
# id that is free on that provider). Fill the model ids in as you verify them
# on Thursday - see PROVIDERS.md. An entry with model=None is only checked for
# key presence.
PROVIDERS = [
    ("openrouter",       r"OPEN_?ROUTER_?KEY\s*=\s*(\S+)",
     "https://openrouter.ai/api/v1", None),
    ("google_ai_studio", r"GOOGLE_AI_STUDIO_KEY\s*=\s*(\S+)",
     "https://generativelanguage.googleapis.com/v1beta/openai", None),
    ("github_models",    r"GITHUB_MODELS_TOKEN\s*=\s*(\S+)",
     "https://models.inference.ai.azure.com", None),
    ("groq",             r"GROQ_API_KEY\s*=\s*(\S+)",
     "https://api.groq.com/openai/v1", None),
    ("cerebras",         r"CEREBRAS_API_KEY\s*=\s*(\S+)",
     "https://api.cerebras.ai/v1", None),
    ("mistral",          r"MISTRAL_API_KEY\s*=\s*(\S+)",
     "https://api.mistral.ai/v1", None),
    ("anthropic_first_party", r"ANTHROPIC_?(?:API_?)?KEY\s*=\s*(\S+)",
     "https://api.anthropic.com", None),
]

RATE_HEADERS = (
    "x-ratelimit-limit-requests", "x-ratelimit-remaining-requests",
    "x-ratelimit-limit-tokens", "x-ratelimit-remaining-tokens",
    "x-ratelimit-reset-requests", "retry-after",
)


def _get(url: str, headers: dict, timeout: int = 30) -> tuple[int, dict, str]:
    # User-Agent is load-bearing: Groq's Cloudflare edge 403s urllib's default.
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, **headers}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 - network shape varies
        return 0, {}, f"{type(e).__name__}: {e}"


def probe_openrouter(key: str) -> dict:
    """GET /api/v1/key - the authoritative statement of this account's own
    limits, straight from the provider. Returns rate_limit {requests,
    interval}, usage, limit (credit remaining) and is_free_tier."""
    status, headers, body = _get(
        "https://openrouter.ai/api/v1/key",
        {"Authorization": f"Bearer {key}"},
    )
    out = {"status": status}
    try:
        data = json.loads(body).get("data", {})
        out.update({
            "rate_limit": data.get("rate_limit"),
            "usage": data.get("usage"),
            "credit_limit": data.get("limit"),
            "limit_remaining": data.get("limit_remaining"),
            "is_free_tier": data.get("is_free_tier"),
        })
    except Exception:  # noqa: BLE001
        out["raw"] = body[:400]
    out["rate_headers"] = {k: v for k, v in headers.items()
                           if k.lower() in RATE_HEADERS}
    return out


def probe_generic(label: str, key: str, base_url: str) -> dict:
    """One GET /models. Cheap, usually free, and most OpenAI-compatible
    providers attach their x-ratelimit-* headers to it."""
    status, headers, body = _get(f"{base_url}/models",
                                 {"Authorization": f"Bearer {key}"})
    return {
        "status": status,
        "rate_headers": {k: v for k, v in headers.items()
                         if k.lower() in RATE_HEADERS},
        "note": "" if status == 200 else body[:200],
    }


def sizing(total_rpd: int, n_models: int, reserve: float) -> dict:
    """SPRINT_PLAN.md section 3:

        windows_per_stream = (total_daily_calls x (1 - reserve)) / (2 x N)

    The reserve holds back budget for E3, E2 and re-runs. If this returns
    fewer than 40 windows per stream, CUT MODELS, NOT WINDOWS - a latency
    curve needs resolution more than it needs a wide roster."""
    usable = total_rpd * (1 - reserve)
    per_stream = int(usable // (2 * max(n_models, 1)))
    return {
        "total_rpd_measured": total_rpd,
        "n_models": n_models,
        "reserved_for_e2_e3_reruns": reserve,
        "windows_per_stream": per_stream,
        "e1_calls": per_stream * 2 * n_models,
        "verdict": (
            "OK" if per_stream >= 40 else
            "TOO FEW WINDOWS - cut models, not windows, or add a provider"
        ),
    }


def main(argv: list[str]) -> int:
    n_models = int(argv[argv.index("--models") + 1]) if "--models" in argv else 6
    reserve = float(argv[argv.index("--reserve") + 1]) if "--reserve" in argv else 0.5

    results: dict[str, dict] = {}
    print(f"measuring provider limits  {datetime.now(timezone.utc).isoformat()}\n")

    for label, pattern, base_url, _model in PROVIDERS:
        key = _find_in_env(pattern)
        if not key:
            results[label] = {"status": "NO KEY"}
            print(f"  {label:<24} no key found")
            continue
        res = probe_openrouter(key) if label == "openrouter" else probe_generic(label, key, base_url)
        results[label] = res
        if label == "openrouter":
            rl = res.get("rate_limit")
            print(f"  {label:<24} HTTP {res['status']}  rate_limit={rl}  "
                  f"free_tier={res.get('is_free_tier')}  "
                  f"credit_remaining={res.get('limit_remaining')}")
        else:
            print(f"  {label:<24} HTTP {res['status']}  {res['rate_headers'] or '(no rate headers)'}")

    print()
    print("  NOTE: a provider's advertised RPM is not its daily cap. Where the")
    print("  headers do not state a daily figure, run the smoke loop and record")
    print("  where it 429s - then write BOTH numbers into PROVIDERS.md with the")
    print("  UTC timestamp you measured them.\n")

    total = 0
    if "--total-rpd" in argv:
        total = int(argv[argv.index("--total-rpd") + 1])
        s = sizing(total, n_models, reserve)
        print("run sizing (SPRINT_PLAN.md section 3):")
        for k, v in s.items():
            print(f"  {k:<28} {v}")
        results["_sizing"] = s
    else:
        print("run sizing: pass --total-rpd <n> once you know the combined daily")
        print("            cap across every provider you got working.")

    OUT_PATH.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {OUT_PATH.relative_to(REPO)}")
    print("Record the outcome in harness/PROVIDERS.md and, if it changes the")
    print("roster, amend PREREGISTRATION.md section 9 with a UTC timestamp.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
