## Appendix A — Limitations and Dual-Use Considerations

The first three subsections were written **before any results existed**, as
`LIMITATIONS.md` in the repository, so they are not shaped by what we found.
§A.4 records what the run itself taught us, including where the executed study
diverged from the plan these limitations were written against.

### A.1 The corpus is a reconstruction, not telemetry

Built from **published figures only**. It matches the published phase totals,
per-phase windows, daily volumes and documented milestone ordering. It does
**not** reproduce Hugging Face's logs, their internal severity logic, or their
true log verbosity. Every claim is about **model behaviour on a faithful
scaffold**, not about what HF's stack would have done.

**75% of the corpus has no sourced milestone** — recon (6,191) plus dropper
(6,972) = 13,163 actions carry published marginals and nothing else. Treat the
bulk phases as volume-realistic and content-synthetic.

**The published sources contradict each other and we did not paper over it:**
16,521 against 17,613 actions; the 1,092-action `unclassified` row this forced
is our inference and is labelled as such. **Four of twelve milestone timestamps
are interpolated** between sourced anchors, each marked `t_utc_estimated`. **The
MITRE mappings are ours** — neither source uses ATT&CK — and since the
escalation ground truth keys off tactic, our mapping partly determines the
metric that scores it (`mitre_confidence: inferred` on every row).

### A.2 Measurement caveats

**Prompt framing is not authentication.** A model reading "you are the triage
layer" cannot verify it; this is why the design calls for an attestation layer
rather than better prompting.

**Single-run, single-turn, text-only, English-only.** Temperature 0, one draw
per cell. No multi-turn drift, no tool use, no agentic scaffolds, and **no
repeated sampling** — a model that pages 40% here might page 60% on a re-run,
and we have not measured that variance.

**A model is not a model; it is a model as served by someone.** Serving stacks
differ in quantisation, sampling defaults, system-prompt injection and
moderation, so every table reports the provider beside the model ID.
`gpt-oss-20b` vs `gpt-oss-120b` is the one clean comparison, both on one stack.
Results are a snapshot of 2026-09; endpoints change without notice.

**A filter is not a refusal.** Our rubric separates `filtered` (platform
blocked the request, zero completion tokens, the model never saw it) from
`refused` (the model produced text declining to engage). Prior refusal
benchmarks collapse these; conflating them attributes to model judgment
something no model judged, and would have inflated our own headline.

**One of our own bugs is instructive and is disclosed.** At a 300-token budget
GLM-5.2 spent 524 tokens reasoning and returned empty content — scored naively,
a refusal. **This bug class recurred four times in this project**, most recently
when `gpt-oss-20b` spent 1,998 of a 2,000-token budget on reasoning and emitted
nothing. Each time the fix was budget, not interpretation. Any benchmark that
does not separate `truncated` from `refused` will systematically over-report
refusal for reasoning models, and will do so *more* for the models that reason
hardest.

### A.3 Dual-use considerations

**What the artifact contains.** An action-indexed, phase-labelled event stream,
either drawn from already-public post-mortems or synthetic filler built from
ordinary administrative commands (`kubectl get pods`, `kubectl auth can-i`). It
contains **no working exploit code, no payloads, no novel installation recipes
and no credentials.** The one credential-shaped string is the well-known
link-local IMDS address, which appears in vendor hardening documentation.

**What it is for.** SecureLayer7 publicly asked of this incident: *"which action
number does your control fire on?"* That is unanswerable without a replayable
stream. HF said much the same: *"if any of that trace ever ships in a form
defenders can replay against their own stack… some of us would build against
it."* This corpus exists to make control-firing latency measurable. Its
intended users are defenders.

**Uplift assessment.** The offensive content is a chronological ordering of
techniques already documented in the two primary sources. An attacker gains no
capability from the ordering that those do not already give them. The value-add
— marginal-matched volume, ground-truth labels, an answer key — is for
*evaluating detectors*, not for conducting intrusions.

**The dual-use surface is the finding, not the data.** We report which models
under-escalate and by how much. An attacker knowing a monitor pages on only a
third of pivotal moments could in principle shape activity beneath it. Three
things bound this: it is a September-2026 snapshot of production endpoints that
model updates will invalidate; it is specific to our reconstruction, and
generalisation to real SOC telemetry is exactly what we do not claim; and it is
the same fact a defender needs before putting a model on monitoring duty.
Withholding it protects no one and leaves operators calibrating on optimism.
The same applies to the false-page rate: alert fatigue is a documented failure
mode, and a monitor that fires on 46% of a benign shift degrades response
capacity rather than adding to it.

**What we withhold.** No novel installation recipe is released without review.

**A finding stated at the width we can defend.** Requests to Claude models *via
OpenRouter* were blocked before generation on defensive SOC triage prompts,
including a pure "should I page the on-call?" frame. We report this as a
measured behaviour **of that access path** and deliberately do not name which
layer imposes it: route-invariance across three of that aggregator's routes
does not distinguish an aggregator filter from a vendor one, and we did not run
the first-party test that would. Over-blocking of defensive security work is a
known failure mode [3], not a novel accusation. Naming a company for a block we
cannot localise would be the error this appendix exists to prevent.

### A.4 What the run changed, and what it added

**Where the executed study diverged from the plan.** The pre-results version of
this appendix assumed all calls would run through OpenRouter at `n = 3`, and
that a 60-item E2 subsample would be double-scored for Cohen's κ. None of that
happened: no OpenRouter key was available, so the study ran on Google AI Studio
and Groq at `n = 1`; **E2 and E4 were cut** to protect E0, E1 and E3; and with
E2 cut there is **no inter-rater κ**. No headline number here is decided by a
model acting as judge — the E1 and E3 verdicts are the models' own structured
outputs, scored mechanically — but the calibration step the plan promised did
not occur, and we do not claim it did.

**Statistical power is the dominant limitation and it is unevenly
distributed.** Per-cell *n* runs from 1 to 33. Only **2 of 10 models reach
*p* < 0.05** on stream separation, and the confound is ours: they are the two
we could sample deepest (*n* = 33 and *n* = 21 benign windows, against
*n* = 4–12 for the Google arm). **Significance here tracks sampling budget at
least as much as model behaviour.** Free-tier caps of 10–31 requests per model
per day left several Gemini models at *n* = 1–12, one at a single window.
Those rows are in the table because omitting them would be selective
reporting, not because they support a conclusion.

**Frontier proprietary models are absent.** The Gemini Pro tier returns
`limit: 0` at $0 — refused, not throttled — and no GPT- or Claude-class model
was reachable free. Our "frontier" arm is frontier-*flash*.

**E3 covers two models from one family on one provider.** The zero incoherence
rate and the escalate-vs-assist asymmetry are established for `gpt-oss-120b`
and `gpt-oss-20b`, not for the frontier arm. Whether Gemini models show the
same asymmetry is untested and is the first thing we would run next.

**Three E3 moments are unscoreable and not randomly distributed.** Moments 19,
23 and 24 on `gpt-oss-20b` remain `truncated` after a 3× budget re-run — two
`supply_chain`, one `k8s`. Evidence length is identical across all 24 moments,
so prompt size does not explain it. The residue falls on the higher-consequence
phases, the direction that **flatters** the model.

**Scope statement.** This is a weekend study with a validated control,
pre-registered metrics, a frozen rubric with a logged amendment, exact rather
than asymptotic statistics, and non-LLM baselines on the same axes. It does not
have the sample size to rank individual models and should not be cited as doing
so. What it supports is a claim about a *pattern* — high recall, poor
selectivity, and under-escalation on evidence models will readily discuss — and
a reusable substrate for testing whether that pattern holds at *n* we could not
afford.
