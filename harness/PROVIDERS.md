# PROVIDERS.md — the roster, and what we measured

**Status: MEASURED 2026-09-12 09:29–11:05 UTC and 2026-09-13 06:15 UTC.** All
five candidate providers now have keys; three are usable at $0. See §1e. Owner: **B (Praneeth)**.
See `SPRINT_PLAN.md` §0.4.

Every row here must be **measured, not assumed**, and stamped with the UTC
time it was measured — the same standard `PREREGISTRATION.md` §8 already holds
itself to ("verified live on 2026-09-09 rather than assumed").

---

## Why this document exists

`PREREGISTRATION.md` §8c says, of exactly this work:

> **Worth pursuing before Friday (would materially strengthen the study):**
> other genuinely free API tiers could restore a frontier arm at $0 — Google AI
> Studio (Gemini), GitHub Models (free with the GitHub account this repo
> already uses), Groq, Cerebras, Mistral. None are verified yet.

Nobody did it. It is the highest-leverage two hours available to this project,
for two separate reasons:

1. **Coverage.** §8c is blunt that *"none of the three models named in the
   incident can be tested for content."* A frontier arm at $0 partially
   reverses that, and moves E4 back from an open-weight-tier ranking toward the
   frontier-vs-open comparison H4 was withdrawn for lacking.
2. **Throughput.** `SPRINT_PLAN.md` §0.3 — the E1 call budget does not close on
   one provider's free tier. Four providers at a few hundred requests/day each
   is a different project from one provider at fifty.

**The constraint that does not move:** anything requiring a card is out. The
study stays at **$0.00** and that stays in the abstract.

---

## 1. Roster

| Provider | Signed up | Key env name | Models verified working | RPM | RPD | Measured (UTC) | Notes |
|---|---|---|---|---|---|---|---|
| OpenRouter (existing) | ✅ 09-09 | `OPEN_ROUTER_KEY` | 11 `:free` models, `PREREGISTRATION.md` §8a | ? | **?** | — | **No key present on this machine.** Unfunded, negative balance. Not used for E1. |
| Google AI Studio | ✅ 09-12 | `GOOGLE_AI_STUDIO_KEY` | 9 of 55 (see §1a) | see §1a | **per-model, see §1a** | 2026-09-12 09:29–09:48 | **Frontier arm restored at $0.** Quota is per-model, not per-account — see §1b. |
| GitHub Models | ✅ key, ❌ service | `GITHUB_MODELS_TOKEN` | **none — service retired** | — | — | 2026-09-13 06:15 | **HTTP 410 `github_models_retirement_brownout`.** The GPT-class arm is gone; see §1e. |
| Groq | ✅ 09-12 | `GROQ_API_KEY` | 6 of 14 (see §1c) | ~5 (TPM-bound) | **1,000/day/model** | 2026-09-12 10:55–11:05 | **Solved the volume problem, as predicted.** Open-weight only — no frontier arm here. |
| Cerebras | ✅ key, ❌ free tier | `CEREBRAS_API_KEY` | **none at $0** | — | — | 2026-09-13 06:15 | **HTTP 402 payment required** on every chat model. Recorded as `unaffordable`; see §1e. |
| Mistral | ✅ 09-13 | `MISTRAL_API_KEY` | 3 of 46 (`ministral-3b/8b/14b`) | 30 | ~937k tok/min | 2026-09-13 06:15 | Free tier covers only the `ministral-*` family — a clean 3b→8b→14b size ladder. |
| Anthropic first-party | ☐ | `ANTHROPIC_API_KEY` | | | | | **Only needed for the §0.2 attribution test.** `client.py` already routes `anthropic:<model>` here. |
| Ollama (local) | ☐ | n/a | | ∞ | ∞ | | Offline insurance. No rate limit, fully deterministic, survives any outage. |

### 1a. Google AI Studio — per-model results, measured 2026-09-12

Probed by `GET /v1beta/openai/models` (55 ids) then one live completion each.
Route them through `client.py` as `google:<id>`.

| Model id | Live call | Latency | Notes |
|---|---|---|---|
| `gemini-3.8-flash` | ✅ | ~2 s | **RPD = 20/day**, measured (§1b). Newest frontier flash. Spent for 09-12 by the E1 smoke. |
| `gemini-3.7-flash` | ✅ | ~2 s | |
| `gemini-3.6-flash` | ✅ | ~3 s | |
| `gemini-3.5-flash` | ✅ | ~2 s | |
| `gemini-3.5-flash-lite` | ✅ | ~1 s | |
| `gemini-3.1-flash-lite` | ✅ | ~1 s | ≥14 requests in a burst with no 429 — materially looser than `3.8-flash` |
| `gemini-3-flash-preview` | ✅ | ~2 s | |
| `gemma-4-26b-a4b-it` | ✅ | ~36 s | **Open-weight arm.** Emits a `<thought>` block before the JSON; `monitor_frame.parse_monitor` handles it. |
| `gemma-4-31b-it` | ⚠️ | ~57 s | 200 OK on a short prompt, **HTTP 500 on a full E1 prompt, 4/4 attempts**. Excluded from the roster. |
| `gemini-2.5-flash`, `gemini-2.5-pro` | ❌ 404 | — | *"no longer available to new [keys]"*. The 2.5 family is retired for keys issued now. |
| `gemini-3.1-pro-preview`, `gemini-pro-latest` | ❌ 429 | — | **`limit: 0`** on `...free_tier_requests`. The Pro tier is not merely throttled at $0 — it is unavailable. |
| `gemini-flash-latest`, `gemini-flash-lite-latest` | ✅ | — | **Deliberately excluded: aliases.** An alias is not a reproducible model id and may share quota with its target. PROVIDERS.md §4 requires reporting the id actually served. |

Not probed: embedding, TTS, image, video, audio, robotics and computer-use ids.

### 1b. The finding that changes the sizing arithmetic

`SPRINT_PLAN.md` §3 sizes the run from a single account-wide `total_rpd`:

```
windows_per_stream = (combined_RPD × (1 − reserve)) / (2 × n_models)
```

with the standing instruction *"If that returns fewer than 40 windows per
stream: cut models, not windows."* **That instruction is wrong for this
provider and must not be followed here.** It was written for OpenRouter, where
one account-wide daily cap is divided among however many models you run.

Google AI Studio's free tier is quoted per *project × model*. Read off the
`quotaId` values in a live 429 body, measured 2026-09-12 09:46 UTC:

```
GenerateRequestsPerMinutePerProjectPerModel-FreeTier
GenerateRequestsPerDayPerProjectPerModel-FreeTier
GenerateContentInputTokensPerModelPerMinute-FreeTier
GenerateContentInputTokensPerModelPerDay-FreeTier
```

Every one of them ends in `PerModel`. So models do not share a budget — each
one brings its own. **Under this provider, cutting models cuts total
throughput.** The correct move when short of quota is the opposite of §3's:
add models, and take fewer windows from each.

Two further consequences, both load-bearing for the overnight run:

- The binding limit on `gemini-3.8-flash` is **per-DAY (20), not per-minute**.
  No amount of backoff clears it. `client._quota_scope()` reads the window off
  the `quotaId` and the E1 runner abandons that model rather than sleeping.
- The 429 body says *"Please retry in 11.5s"* **for a quota with a daily
  window**. The provider's own suggested delay is wrong here; trust the
  `quotaId`, not the sentence.

Also measured: this endpoint returns **no** `x-ratelimit-*` headers and **no**
`Retry-After`. The only machine-readable statement of the wait is
`google.rpc.RetryInfo`, and when that is absent, prose at the end of
`error.message`. `client._suggested_delay()` parses both.

### 1c. Groq — per-model results, measured 2026-09-12 11:00 UTC

Route as `groq:<id>`. Probed with a full-length E1 monitor prompt, not a toy
one, and the rate figures are read off the `x-ratelimit-*` response headers
the endpoint attaches to `/chat/completions` (it attaches none to `/models`).

| Model id | Live call | Latency | RPD | Notes |
|---|---|---|---|---|
| `openai/gpt-oss-120b` | ✅ | 1.2 s | 1,000 | Open-weight, largest on offer |
| `openai/gpt-oss-20b` | ✅ | 0.7 s | 1,000 | **Same family as the 120b — a clean capability-scaling pair on one serving stack** |
| `qwen/qwen3.8-27b` | ✅ | 0.7 s | 1,000 | |
| `qwen/qwen3.6-27b` | ✅ | 4.3 s | 1,000 | Version pair with 3.8 |
| `allam-2-7b` | ✅ | 0.3 s | 7,000 | 7B; smallest capability point available |
| `groq/compound-mini` | ✅ | 1.4 s | 250 | An agentic *system*, not a bare model — different object, treat with care |
| `whisper-*`, `canopylabs/orpheus-*` | — | — | — | Audio/TTS. Not applicable. |
| `meta-llama/llama-prompt-guard-2-*` | — | — | — | Prompt-injection classifiers, not chat models. |
| `openai/gpt-oss-safeguard-20b` | — | — | — | A **safety classifier**. Not an E1 monitor, but directly relevant to `harness/safety_classifier_contrast.py` if that thread is picked back up. |

### The reasoning-token trap — size `--max-tokens` before you run

Measured 2026-09-12 on the E3 frames at `--max-tokens 2000`:

| model | calls that hit the token ceiling | reasoning tokens before any content |
|---|---|---|
| `openai/gpt-oss-20b` | 13 / 24 | **1,998 of a 2,000 budget** — zero content tokens |
| `openai/gpt-oss-120b` | 24 / 48 | partial content, still scoreable |

`gpt-oss-20b` spent its ENTIRE budget reasoning and returned empty content
with `finish_reason=length`. `RUBRIC.md` §0 classifies that as `truncated` —
**our defect, never scored** — and requires a re-run at a larger budget. It is
the same failure the rubric already records for GLM-5.2 (524 reasoning tokens
before its first content token), an order of magnitude worse.

Note the direction: the **smaller** model burned more reasoning budget than the
larger one. Do not size the budget from the model's parameter count.

`usage.completion_tokens_details.reasoning_tokens` is where Groq reports this.
Budget must exceed `reasoning_tokens + expected content`; **6,000 was enough
here**. The interaction with the TPM ceiling is the sting — a 6,000-token
completion is most of one minute's allowance, so a reasoning model costs
roughly five times the wall-clock of a non-reasoning one per call.

**The binding limit is tokens, not requests.** 8,000 TPM against an E1 prompt
of ~1,600 tokens is about **5 requests/minute** — so the 1,000/day cap is
never reached in practice and wall-clock is what rations the run. Set
`--rpm 4`.

**One trap, and it cost an hour.** Groq is behind Cloudflare, which rejects
`urllib`'s default `Python-urllib/3.x` User-Agent with **HTTP 403 and a body
of exactly `error code: 1010`** — no JSON, no message, and indistinguishable
from a rejected API key. `client.py` now sends a real User-Agent on every
request. If a provider ever 403s with an opaque body, check the User-Agent
before you check the key.

### 1d. What each provider arm is for

They are not interchangeable and the report should not present them as one
pool:

- **Google AI Studio = the frontier arm**, at thin n. 10–31 calls/model/day
  is enough for a signal, not for a tight interval.
- **Groq = the open-weight arm**, at thick n. 1,000/day/model carries the
  statistical weight, and `gpt-oss-20b` vs `gpt-oss-120b` is a
  capability-scaling comparison *within one family on one serving stack*.

- **Mistral = a second open-weight arm** at 3b/8b/14b, added 09-13. Its value
  is the within-family size ladder, not breadth.

Gemma-4 on Google, GPT-OSS/Qwen on Groq and Ministral on Mistral are all
open-weight, so the open-weight side spans three serving stacks — which is the
§4 confound, and is why provider is reported next to every model id. **No
frontier-proprietary model is reachable at $0** (§1e): the Google Pro tier
reports `limit: 0`, Cerebras 402s, and GitHub Models has been retired. Our
"frontier" arm is frontier-*flash* and the report says so.

### 1e. The three providers added on Sunday, and what each was worth

Probed 2026-09-13 06:15 UTC with a **full-length E1 monitor prompt** (~1,000
tokens), not a toy one.

| Provider | Result | What it cost us to find out |
|---|---|---|
| **GitHub Models** | **HTTP 410, `github_models_retirement_brownout`** on both the current (`models.github.ai`) and legacy (`models.inference.ai.azure.com`) endpoints. The legacy host no longer resolves at all. | The GPT-class arm this roster most needed. **There is no frontier-proprietary model reachable at $0 anywhere in this study.** |
| **Cerebras** | **HTTP 402 `payment_required_error`** on all three chat models it lists (`gpt-oss-120b`, `qwen-3.8-27b`); `gemma-4-31b` additionally 404s. | Nothing usable. Note this is exactly the outcome `RUBRIC.md` §0 calls `unaffordable` — a budget fact, never a model behaviour, excluded from every denominator. |
| **Mistral** | **3 of 46 models usable.** `ministral-3b-latest`, `ministral-8b-latest`, `ministral-14b-latest` all answer in ~1–2 s. Everything larger (`mistral-medium*`, `mistral-small-latest`, `magistral-*`) returns a persistent HTTP 429 `rate_limited` on the first call, i.e. it is gated to a paid tier rather than throttled. | A genuine third arm, and a **within-family size ladder (3b → 8b → 14b)** that mirrors the `gpt-oss-20b`/`120b` pair. |

Measured Mistral limits, read from the response headers on a successful call:
`x-ratelimit-limit-req-minute: 30`, `x-ratelimit-limit-tokens-minute: 937500`.
Far looser than Groq's 8,000 TPM, so Mistral runs fast; `--rpm 20` is safe.

**Two lessons worth carrying beyond this sprint.** A free tier can be
*withdrawn between the plan and the run* — GitHub Models was named in
`PREREGISTRATION.md` §8c as the GPT-class hope and was retired before we
reached it. And a provider listing a model in `GET /models` says nothing about
whether your tier can call it: Cerebras and Mistral both advertise models that
answer 402/429 on first contact. **Probe with a real prompt, not a catalogue
read.**

## 2. How to measure

```bash
# 1. Put every key you obtain in the gitignored .env at or above the repo root.
# 2. One call per provider; reads the provider's own stated limits.
python harness/measure_limits.py

# 3. Once you know the combined daily cap, size the E1 run:
python harness/measure_limits.py --models 6 --total-rpd <combined RPD>
```

The sizing formula (also in `SPRINT_PLAN.md` §3):

```
windows_per_stream = (combined_RPD × (1 − reserve)) / (2 × n_models)
```

with `reserve = 0.5` held back for E3, E2 and re-runs.

> **If that returns fewer than 40 windows per stream: cut models, not windows.**
> A latency curve needs resolution more than it needs a wide roster. An EAI
> plotted over 20 windows is not a measurement.
>
> ⚠️ **This rule assumes an account-wide daily cap, and does not hold for
> Google AI Studio, the only provider we actually have** — its quota is
> per-model, so cutting models cuts throughput. See §1b. It still holds for
> OpenRouter if that key ever comes back.

A provider's advertised RPM is **not** its daily cap. Where the response
headers do not state a daily figure, run a smoke loop and record where it
starts returning 429 — then write **both** numbers into the table above.

## 3. Rules that apply to everything in this file

- **HTTP 429 is retryable and is never a model behaviour.** `RUBRIC.md` §0
  has no `rate_limited` outcome because a 429 is not an outcome — it is a
  reason to wait. Back off and retry; never score it.
- **HTTP 402 is `unaffordable`** — a distinct outcome from `filtered` and
  `refused`, excluded from every denominator. Recording a 402 as a refusal
  would manufacture a finding out of our own budget.
- **Anything that works re-enters the study through an amendment.**
  `PREREGISTRATION.md` §8c commits to this in as many words: *"If any works, it
  re-enters as a frontier arm and this section is amended with a timestamp."*
  Add the row to §9 with the UTC time and whether it was added before or after
  seeing data.
- **Model IDs and UTC timestamps are logged for every call** (`client.py`
  already does this). Production endpoints change without notice; the results
  are a snapshot of 2026-09.

## 4. Cross-provider comparability — state this in the report

Running the same prompt through different providers is not the same experiment
as running it through one. Serving stacks differ in quantisation, default
sampling, system-prompt injection, and — the finding this project already
owns — **moderation layers**. Two consequences, both of which belong in
Methodology rather than being discovered by a judge:

- Report the **provider alongside the model ID** in every table. A model is
  not a model; it is a model *as served by someone*.
- Where the same model is reachable on two providers, run it on both if the
  budget allows. That comparison is nearly free and it is a direct measurement
  of the serving-layer effect that §0.2 is about.
