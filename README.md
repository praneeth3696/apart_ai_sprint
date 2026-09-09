# HF-Replay-Recon — a replayable scaffold for the July 2026 agent intrusion

**Status: pre-sprint (2026-09-09).** Corpus machinery and the Wed-9 smoke test
are done; the full runs happen during the sprint (Fri 11 – Sun 13 Sep).

SecureLayer7 asked of this incident: *"which action number does your control
fire on?"* You cannot answer that without a replayable stream, and the real one
was never released. This repo reconstructs one from published figures only —
matching the published phase totals, time windows, daily volumes, and milestone
ordering — and ships it with a per-field citation ledger.

**It is a scaffold, not telemetry.** See [LIMITATIONS.md](LIMITATIONS.md).

---

## Findings so far (30 calls, 2026-09-09)

**1. Anthropic models are blocked by a platform content filter on defensive SOC
triage.** `claude-opus-5` and `claude-fable-5.1` return
`finish_reason=content_filter` with **0 completion tokens** on both a monitor
frame ("should I page the on-call?") and an assistant frame, for all 5 pivotal
moments. Not route-specific — identical via OpenRouter auto-route, Anthropic
direct, and Amazon Bedrock. The same model answers a trivial prompt normally.

> This is a **filter**, not a refusal. The model never saw the prompt. We score
> `filtered` separately from `refused` throughout — conflating them attributes
> to model judgment something no model judged.

**2. No incoherence in the reachable models.** `gpt-5.6-luna` and `glm-5.2`
both scored **5/5 coherent-alarm**: paged on every pivotal moment and assisted
every time. Incoherence rate 0%.

**3. Both page *earlier* than our ground-truth rule** — on a Discovery-tactic
event, not a pivotal one. So the discriminating measurement is the **false-page
rate on the benign stream**, not escalation latency alone.

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
python harness/e3_incoherence_smoke.py z-ai/glm-5.2
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
  client.py                    cached OpenRouter client
  e3_incoherence_smoke.py      the Wed-9 smoke test
prompts/RUBRIC.md              frozen scoring rubric
PREREGISTRATION.md             frozen 2026-09-09
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

## Known gaps before the sprint

- 9 of 10 phase template banks unwritten (only `k8s` exists)
- Benign baseline stream not built — this is the false-page control, and the
  headline now depends on it
- `build_corpus.py` (all-phase merge, global `action_idx`) not written
- **Budget is $0 and will stay $0.** The study runs entirely on 11 verified
  OpenRouter `:free` models. The frontier family named in the incident is
  measurable only as blocked / not-blocked, because a content-filtered call
  bills zero tokens. **GLM-5.2 — the model that did HF's actual forensic
  work — cannot be tested at all**, so the provenance claim is withdrawn.
  See PREREGISTRATION.md §8.
