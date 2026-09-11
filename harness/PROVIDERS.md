# PROVIDERS.md — the roster, and what we measured

**Status: TEMPLATE, unfilled. Fill it Thursday night 2026-09-10.**
Owner: **B (Praneeth)**. See `SPRINT_PLAN.md` §0.4.

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

## 1. Roster — fill this in

| Provider | Signed up | Key env name | Models verified working | RPM | RPD | Measured (UTC) | Notes |
|---|---|---|---|---|---|---|---|
| OpenRouter (existing) | ✅ 09-09 | `OPEN_ROUTER_KEY` | 11 `:free` models, `PREREGISTRATION.md` §8a | ? | **?** | — | Unfunded, negative balance. **The RPD is the unknown that sizes the whole sprint.** |
| Google AI Studio | ☐ | `GOOGLE_AI_STUDIO_KEY` | | | | | **Highest value — a genuine frontier arm at $0** |
| GitHub Models | ☐ | `GITHUB_MODELS_TOKEN` | | | | | Free with the GitHub account this repo already uses; GPT-class arm |
| Groq | ☐ | `GROQ_API_KEY` | | | | | Open-weight, high throughput — solves the E1 volume problem |
| Cerebras | ☐ | `CEREBRAS_API_KEY` | | | | | Redundancy against a Saturday 429 wall |
| Mistral | ☐ | `MISTRAL_API_KEY` | | | | | Cheap diversity |
| Anthropic first-party | ☐ | `ANTHROPIC_API_KEY` | | | | | **Only needed for the §0.2 attribution test.** `client.py` already routes `anthropic:<model>` here. |
| Ollama (local) | ☐ | n/a | | ∞ | ∞ | | Offline insurance. No rate limit, fully deterministic, survives any outage. |

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
