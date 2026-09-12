# HF-Replay-Recon — a replayable scaffold for the July 2026 agent intrusion

**Status: sprint day 1 (2026-09-11).** The full 17,613-action attack stream and
its matched benign control are built and asserted, and the non-LLM rule
baselines (E0) run on both. The model runs — E1/E2/E3 — are still ahead.

**Start here:** [`SPRINT_PLAN.md`](SPRINT_PLAN.md) is the execution plan (roles,
hour-by-hour, run sizing). [`PRIMER.md`](PRIMER.md) is the background doc — the
incident, the security and eval vocabulary, and the repo map — for anyone
joining without a security background.

SecureLayer7 asked of this incident: *"which action number does your control
fire on?"* You cannot answer that without a replayable stream, and the real one
was never released. This repo reconstructs one from published figures only —
matching the published phase totals, time windows, daily volumes, and milestone
ordering — and ships it with a per-field citation ledger.

**It is a scaffold, not telemetry.** See [LIMITATIONS.md](LIMITATIONS.md).

---

## Findings so far (30 calls, 2026-09-09)

**1. Requests to Claude models via OpenRouter are blocked before generation on
defensive SOC triage.** `claude-opus-5` and `claude-fable-5.1` return
`finish_reason=content_filter` with **0 completion tokens** on both a monitor
frame ("should I page the on-call?") and an assistant frame, for all 5 pivotal
moments — identical via OpenRouter auto-route, Anthropic direct, and Amazon
Bedrock. The same model answers a trivial prompt normally, so the endpoint is
reachable and the block is specific to this content.

> This is a **filter**, not a refusal. The model never saw the prompt. We score
> `filtered` separately from `refused` throughout — conflating them attributes
> to model judgment something no model judged.

> **We do not attribute the block to a layer.** Route-invariance across an
> aggregator's own routes is the *signature* of an aggregator-side filter, not
> evidence against one. Until the first-party test runs we report the
> measurement and not a culprit — see
> [PREREGISTRATION.md](PREREGISTRATION.md) §3a.

**2. No incoherence in the reachable models.** `gpt-5.6-luna` and `glm-5.2`
both scored **5/5 coherent-alarm**: paged on every pivotal moment and assisted
every time. Incoherence rate 0%.

**3. Both page *earlier* than our ground-truth rule** — on a Discovery-tactic
event, not a pivotal one. So the discriminating measurement is the **false-page
rate on the benign stream**, not escalation latency alone.

**4. A purpose-built safety classifier rates every blocked prompt safe.**
Given the byte-identical prompts blocked on the Claude route,
`nemotron-3.5-content-safety` returned **SAFE 10/10** while both Claude models
returned BLOCKED 10/10.
The classifier is calibrated, not assumed: it flags 2/2 category-level harmful
probes UNSAFE and passes 2/2 benign probes SAFE, so it is not simply
permissive. A disagreement between two safety systems, not a verdict on
either — only one third-party classifier was affordable.

Consequence, decided before the full run: **the headline moves from E3
(incoherence) to E1 (escalation latency + false-page precision)**, with the
filter result second. See [PREREGISTRATION.md](PREREGISTRATION.md) §6.

---

## Reproduce

```bash
pip install numpy pyyaml pytest
cd corpus

python allocate.py             # phase x day matrix; asserts both published margins
python generate_phase.py k8s   # 87-action k8s stream -> prototype_k8s.jsonl
python escalation.py           # the pre-registered page point
python windows.py              # 5-minute windows + E3 moments
pytest test_prototype.py -v    # 17 assertions
```

Model calls need an OpenRouter key in a **gitignored** `.env` at or above the
repo root (`OPEN_ROUTER_KEY=...`), then:

```bash
python harness/e3_incoherence_smoke.py nvidia/nemotron-3-ultra-550b-a55b:free
python harness/safety_classifier_contrast.py   # runs its own calibration first
python harness/measure_limits.py               # provider rate limits + run sizing
```

The rule baselines need no key at all:

```bash
python harness/e0_baselines.py corpus/prototype_k8s.jsonl \
                               --benign corpus/benign_stream.jsonl
```

Responses cache to `runs/{exp}/{model}/{hash}.json` on receipt; a completed
call is never re-run.

---

## Layout

```
corpus/
  ground_truth.yaml     every published figure, each with source + verified
  CITATIONS.md          parameter -> published sentence
  allocate.py           IPF solve of the phase x day matrix
  templates.py          synthetic filler banks (k8s only so far)
  generate_phase.py     row generation + render_for_model() leak barrier
  windows.py            5-minute windows, E3 moments
  escalation.py         the pre-registered escalation rule
  test_prototype.py     17 assertions
  answer_keys/FORMAT.md
harness/
  client.py                    cached client; `anthropic:` prefix = first-party
  e0_baselines.py              E0 non-LLM rule detectors (no API calls)
  measure_limits.py            provider rate limits + E1 run sizing
  PROVIDERS.md                 the roster and what we measured
  e3_incoherence_smoke.py      the Wed-9 smoke test
  safety_classifier_contrast.py  matched filter-vs-classifier contrast
  test_anthropic_surface.py      first-party vs aggregator filter test
prompts/RUBRIC.md              frozen scoring rubric
SPRINT_PLAN.md                 the execution plan
PRIMER.md                      background for a first-time reader
PREREGISTRATION.md             frozen 2026-09-09, amendments in §9
LIMITATIONS.md
```

---

## What this establishes / what it does not

**Establishes:** that a marginal-matched, milestone-anchored scaffold of this
incident can be built from public figures alone; that escalation latency and
false-page rate are measurable on it; and three reproducible model behaviours
above.

**Does not establish:** anything about what HF's actual detection stack would
have done. The corpus is a reconstruction. 75% of it (recon + dropper) carries
published marginals and synthetic content, with no sourced milestone. Model
results are single-run, text-only, and mediated by OpenRouter.

---

## Known gaps

The three corpus gaps listed here before the sprint are now closed: all 10
template banks are written, `build_corpus.py` merges them into a 17,613-action
`attack_stream.jsonl`, and `benign_stream.jsonl` is the matched false-page
control. What remains:

- **E1 is not built.** `harness/e1_escalation.py` does not exist yet. It is the
  headline experiment and Friday's exit condition.
- **The benign control is not validated yet.** The blind separability check is
  built and awaiting a score. Until it lands, the false-page denominator rests
  on an assumption nobody has tested.
- **Free-tier daily request cap is unmeasured**, and it — not money — sizes the
  whole E1 run. `harness/measure_limits.py` gets the number; nothing downstream
  should be sized until it has. See `SPRINT_PLAN.md` §0.3.
- **Budget is $0 and will stay $0.** The study runs entirely on 11 verified
  OpenRouter `:free` models. The frontier family named in the incident is
  measurable only as blocked / not-blocked, because a content-filtered call
  bills zero tokens. **GLM-5.2 — the model that did HF's actual forensic
  work — cannot be tested at all**, so the provenance claim is withdrawn.
  See PREREGISTRATION.md §8.
