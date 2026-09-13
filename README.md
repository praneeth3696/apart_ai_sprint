# HF-Replay-Recon

**A replayable reconstruction of the July 2026 Hugging Face agent intrusion,
with a matched benign control, for measuring whether LLM monitors page the
on-call in time — and how often they page on nothing.**

Apart Research **AI Incident Response Sprint**, 11–13 September 2026.
Amirtha Yazhini M · Praneeth Reddy Y. Total API spend: **$0.00**.

---

## The findings

**Models fail in both directions.** Across 15 models and three providers, the
pooled numbers are 60% of milestone-carrying attack windows paged and 23% of
innocent ones — but that average describes no model in the study. One model
buys a perfect 12/12 recall by paging on **11 of 12 benign windows**; two others
page on **nothing at all**, reading an active intrusion as *"normal operational
activity"* and *"resource contention"*. The useful region — high recall **and**
low false-page rate — is essentially empty. Only 2 of 15 models separate the
streams at *p* < 0.05.

**Under-escalation, not refusal, is the failure mode.** Wrapping
byte-identical evidence in a monitor frame and an assistant frame across 11
models, five families and three providers: incoherence was **0 of 228**. Not
one model refused to analyse evidence it had just declined to escalate. But the
frames disagreed in one direction only — models assisted on **228/228** moments
and escalated on **83**. The "escalates but won't help" cell is empty in every
arm.

## Repository map

| path | what it is |
|---|---|
| `corpus/` | The generated attack stream (17,613 actions), its matched benign control, windowing, and the ground truth everything is scored against |
| `harness/` | Multi-provider client, the E1 escalation runner, the E3 two-frame runner, E0 rule baselines, and measured provider limits |
| `analysis/` | Statistics (Wilson, exact Fisher, exact McNemar), figures, and the generated results |
| `report/` | The submitted report, section by section, plus the number-checking gate |
| `prompts/RUBRIC.md` | The scoring rubric, frozen before scoring, with its amendment log |
| `PREREGISTRATION.md` | Hypotheses, metrics, and a timestamped amendment log recording every mid-sprint change and whether it was made before or after seeing data |
| `LIMITATIONS.md` | Limitations written **before** results, plus a dated post-run reconciliation of where the executed study diverged from the plan |
| `docs/` | Sprint materials and the coordination notes between the two authors |

## Reproducing

```bash
python3 -m venv .venv && .venv/bin/python3 -m pip install numpy pyyaml pytest matplotlib

# no API key, no network — exercises every parse and failure branch
.venv/bin/python3 harness/e1_escalation.py --dry-run
.venv/bin/python3 harness/e3_incoherence.py --dry-run

# E0 rule baselines: zero API calls
.venv/bin/python3 harness/e0_baselines.py corpus/attack_stream.jsonl \
    --benign corpus/benign_stream.jsonl

# analysis and figures
.venv/bin/python3 analysis/stats.py --eai
.venv/bin/python3 analysis/figures.py
.venv/bin/python3 report/check_numbers.py      # verifies the report against the data
```

Live runs need a key in a gitignored `.env` at the repository root — see
[`harness/PROVIDERS.md`](harness/PROVIDERS.md) for which providers work at $0
and what each one's measured limits actually are.

**Tests:** 218 total — `corpus` 48, `harness` 146, `analysis` 24.

## A note on the corpus

It is a **reconstruction from published figures**, not captured telemetry. It
matches the published phase totals, per-phase windows, daily volumes and
milestone ordering from Hugging Face's technical timeline and OpenAI's incident
report — but 75% of the actions carry published marginals and nothing else, six
of twelve milestone timestamps are interpolated within published bounds, and
one milestone is unreconciled between the two sources. Every one of those
caveats is documented in [`corpus/CITATIONS.md`](corpus/CITATIONS.md) and
[`LIMITATIONS.md`](LIMITATIONS.md).

It contains no working exploit code, no payloads, no credentials, and no
technique that is not already in the two cited public sources. It is a
detection substrate: it describes what an intrusion looked like in a log, not
how to perform one.
