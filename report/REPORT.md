# Fluent About the Intrusion, Silent on the Pager

## Abstract

Would an LLM on monitoring duty have paged the on-call during the July 2026
Hugging Face agent intrusion? We rebuilt the incident from its published
timeline as a replayable 17,613-action stream, generated a size-matched benign
control, verified blind that the two are not trivially separable, and ran nine
models across two providers past both — at $0.00.

Models catch the incident and cry wolf. 90% of milestone-carrying attack
windows produce a page (66/73); so do 54% of innocent windows (50/92). A
keyword rule shows the same shape, and no model reaches significance at our
sample sizes.

We then wrapped byte-identical evidence in a monitor frame and an assistant
frame. Incoherence was zero — but the frames disagreed sharply and in one
direction: models assisted on 45/45 moments while escalating on 16
(p=0.0001). The risk is not refusal; it is fluent analysis with a silent pager.


## 1. Introduction

In July 2026 an autonomous agent compromised Hugging Face's dataset-conversion
infrastructure, moved laterally through a Kubernetes cluster, extracted cloud
and VPN credentials, and reached multi-cluster administrative access. Hugging
Face published a technical timeline [1]. The obvious question for anyone
running an AI-assisted security operation is the one that timeline cannot
answer: **would a model on monitoring duty have paged the on-call in time?**

The tempting way to ask that is to show a model the incident and see whether it
notices. That question is nearly free to answer and nearly worthless. Anything
paged on every window would "catch" the incident, and a detector that pages on
everything is not a detector. **The question only means something against a
matched control**, and supplying that control is most of the work.

So we rebuilt the incident as a replayable 17,613-action stream from the
published figures, generated a size-matched benign stream from the same
marginal distributions, verified blind that the two are not trivially
separable, and ran both past the same models under the same monitor prompt.
Nine models across two providers, at a total cost of **$0.00**.

**Two findings, and the second is the one we did not expect.**

**Models catch the incident, and page on the control almost as readily.**
Across the roster, 90% of milestone-carrying attack windows produce a page
(66/73) — and so do **54% of windows in an innocent shift** (50/92). A
15-line keyword rule shows the same pattern (67% against 28%), so this is not
a matter of models being crude; it is that the discriminating signal in this
corpus is thin, and recall bought by paging on everything is worth nothing.
The spread across models matters more than any single model's number: the
best discriminators sit at 40% and 24% false-page rates while the worst pages
on 11 of 12 benign windows for a perfect 12/12 recall. **No model reaches
statistical significance on stream separation at our sample sizes**, and we
say so rather than promoting a *p* = 0.057.

**The failure mode is under-escalation, not refusal.** We expected the
safety-relevant risk to be a model that declines to engage with intrusion
evidence — the pattern where a guardrail turns a security assistant into an
obstacle mid-incident. We tested it directly: the same byte-identical evidence
wrapped in a monitor frame and in an assistant frame, 24 moments spanning every
phase. **Incoherence was zero.** Not one model refused to analyse evidence it
had just declined to escalate. But the two frames disagreed sharply and
entirely in one direction: `gpt-oss-120b` assists on 24/24 moments and escalates
on 9/24; `gpt-oss-20b` assists on 21/21 and escalates on 7/21 (McNemar exact,
*p* = 0.0001). Every discordant pair is a moment where the model **helped
without paging**, and none the reverse.

That reframes the concern. These models will explain an intrusion to you in
detail and not think it worth waking anyone over. The risk in an AI-assisted
SOC is not the model that won't talk about the incident — it is the model that
talks about it fluently while the pager stays silent.

**Contributions.** (i) A replayable, generated reconstruction of a real 2026
agent intrusion with a validated matched control, released with the harness.
(ii) A metric pair — milestone-window hit rate against benign false-page rate —
that replaces first-page latency, which we show is degenerate on this corpus
because every detector fires within the first 50 of 17,613 actions. (iii)
Non-LLM rule baselines on the same axes, so the model numbers are
interpretable. (iv) The two-frame incoherence test at K=24, returning a
pre-registered null and an unexpected significant asymmetry. (v) A full
account of what a $0 budget actually constrains, which turned out to be
throughput and not price.

---

[1] Hugging Face, *Agent intrusion: technical timeline*.
`https://huggingface.co/blog/agent-intrusion-technical-timeline`


## 2. Related Work

> **OWNED BY A (Amirtha) — NOT DRAFTED HERE.** Placeholder so the assembly is
> complete and the gap is visible rather than silent.
>
> What this section needs to cover, based on what the rest of the report
> already claims:
>
> - **Security-refusal benchmarks** — what exists, and the gap this fills:
>   none of them report a *fabrication* rate or measure escalation against a
>   matched benign control. Our contribution is the control and the
>   selectivity axis, not the refusal axis.
> - **Alert fatigue / false-positive burden in SOC literature** — needed to
>   support the Discussion's claim that a 54% false-page rate degrades
>   response capacity rather than adding to it.
> - **Agentic incident reconstruction / replayable incident corpora** — prior
>   art on turning post-incident write-ups into evaluable artefacts.
> - **LLM-as-monitor / LLM-as-judge reliability**, particularly framing
>   sensitivity, which is exactly what E3 measures.


## 3. Methodology

### 3.1 Corpus and controls

We reconstruct the July 2026 Hugging Face agent intrusion from its published
technical timeline [1] as a replayable action stream. The corpus is
**generated, not hand-written**: every count, phase boundary and milestone
timestamp is read from a single machine-readable ground-truth file, and the
generator asserts at build time that each defined milestone is actually placed.
The reconstruction covers **17,613 attacker actions** between 2026-07-09 02:28
UTC and 2026-07-13 14:14 UTC.

One source discrepancy is inherited rather than smoothed over: the published
phase and daily-volume tables disagree (16,521 vs 17,613 actions). We take the
daily-volume total as authoritative — it matches the source's own "~17,600"
headline to within 13 actions — and carry the 1,092-action remainder as an
explicit `unclassified` residual. Exfiltration is **56 actions (0.3%)**: a
needle-in-haystack problem, so any method that works by noticing volume spikes
has been handed the wrong task.

Every experiment runs against **two streams**: the attack stream and a
size-matched **benign control** from the same generator and the same marginals,
with no intrusion in it. The control converts "the model paged" into "the model
paged *selectively*"; without it a page rate is uninterpretable.

Both streams are cut into 5-minute windows — 1,278 attack, 1,280 control.
Twelve attack windows carry a sourced milestone; the control carries none by
construction. Models see only a projection of each action (index, timestamp,
host role, actor, event text); the ground-truth block is asserted out of every
prompt at runtime, since those labels are exactly what we are measuring the
model's ability to notice.

### 3.2 Is the control actually a control?

A matched control is only worth having if it is not trivially distinguishable.
Before any model ran, 20 unlabelled windows (10 per stream) were scored blind
against a pre-registered 90% failure threshold. Result: **14/20 (70%), Wilson
CI95 48.1–85.5%, p = 0.058** against chance, with attack and benign recall both
70% — no label bias. The control passes, so the false-page denominator is
defensible.

> **Disclosure.** These labels were produced by **an LLM (Claude), not the
> human rater the pre-registration specifies.** The deviation is disclosed
> rather than left implicit. An LLM is arguably a *stronger* adversary than a
> human skimming (systematic, tireless) and arguably weaker (no operational
> intuition), so we do not claim the substitution is neutral either way. And
> **n = 20 is a screen, not a powered test**: it catches the
> trivial-separability case it was built for and cannot resolve 55% from 70%.

### 3.3 E0 — non-LLM rule baselines

Three detectors run over identical streams, windowing and ground truth, at zero
API cost. Without them, "model X pages at a 40% false-page rate" gives a reader
nothing to compare against.

`volume_spike` and `keyword_sigma` see **only** the projection a model under
evaluation sees. `sev_threshold` deliberately breaks that rule and reads
ground-truth severity: **it is an ORACLE — the upper bound for a detector that
already knows the answer — and never a baseline a defender could deploy.** We
label it ORACLE at every appearance for that reason.

### 3.4 E1 — escalation and false-paging

Each model is placed in a **monitor frame**: the automated triage layer for a
production Kubernetes platform, shown a bounded rolling digest of everything
before the current window plus the window itself, returning strict JSON —
`{severity, page_oncall, rationale}`. `page_oncall` is the escalation
criterion; severity is recorded but is not it. The digest is computed locally
from model-visible fields and bounded (top hosts, top actors, last 8 events),
so this stays a triage task rather than a long-context retrieval task.

Unparseable JSON gets **exactly one** re-ask; still unparseable is recorded as
`unparseable` and excluded from page-rate denominators.

**Two attack populations are reported, and never pooled.** The *milestone
census* is all 12 milestone-carrying windows — a census, not a sample, because
a uniform sample of 1,278 windows would expect to catch a fraction of one. The
*uniform sample* is evenly spaced windows, and it is the only like-for-like
comparison to the benign control. Pooling them biases the attack page rate
upward, because the census over-represents high-severity windows by
construction. Every record carries which population it belongs to, and windows
that fall in both are labelled as such rather than being silently removed from
one.

Sampling runs on a **nested ladder** (12 → 36 → 108 → 324 → 972), each rung 3×
the last. This is not cosmetic: evenly-spaced samples at *n* and *n′* share no
positions unless *n′/n* is an odd integer, so naively widening 12 → 40 windows
would have selected **none** of the windows a previous run had already paid
for. On the ladder every rung is a strict superset of those beneath it, so
widening is always additive.

### 3.5 E3 — the two-frame incoherence test

A **byte-identical** evidence block is wrapped in two prompts differing only in
the role sentence and the ask:

- *monitor* — "you are the triage layer; severity? do you page the on-call?"
- *assistant* — "I'm on the incident response team; help me analyse this."

Evidence identity is **asserted at runtime**, not assumed; if the two frames
ever diverged in content the 2×2 would be meaningless. K = 24 incident moments
are stratified across all ten phases (9 carry a milestone). The cells:

|                       | assists        | refuses        |
|-----------------------|----------------|----------------|
| **escalates**         | coherent-alarm | tension        |
| **does not escalate** | coherent-calm  | **INCOHERENT** |

Two cells sit outside the 2×2 and are reported separately, never folded in.
`filtered-both` — a platform filter blocked both prompts, so the model made no
judgment at all — is **never** counted as INCOHERENT; doing so would attribute
to model reasoning something no model did. `unscoreable-*` covers a frame that
returned no usable verdict.

### 3.6 Outcome taxonomy, and one amendment

Every call is assigned exactly one outcome from a rubric frozen before scoring
began: `comply`, `refused`, `partial`, `filtered` (a platform filter blocked
the request — the model never saw it), `truncated` (the token budget ran out
before any content — **our defect, never scored**), and `unaffordable` (HTTP
402; we could not buy the observation).

**The rubric was amended once during the run, and the amendment is logged with
a UTC timestamp in the rubric's own amendment table.** We added a
`quota_exhausted` outcome: an HTTP 429 whose `quotaId` names a **per-day**
window, as distinct from the ordinary per-minute rate limit that is simply
retried. It is the free-tier twin of the HTTP 402 that `unaffordable` already
covered — the only difference between them is whether money or quota ran out
first — and like `unaffordable` it is **excluded from every denominator**.
Recording a spent daily quota as a model declining to page would manufacture a
finding out of our own budget. No E1 or E3 item had been scored when the
outcome was added, so the frozen rubric's "applied to all previously-scored
items or not at all" condition is satisfied vacuously.

### 3.7 Providers, and why throughput is the methodology

The study cost **$0.00**; every call ran on a free tier. Price was never the
binding constraint — **throughput was**, and it shaped the experiments. Google
AI Studio meters its free tier **per project × model** at a measured 10–31
requests *per day*; Groq allows 1,000/day/model against an 8,000
tokens-per-minute organisation-wide ceiling. Per-model measurements, quota
semantics and the reproducibility traps are documented in the repository's
`PROVIDERS.md` rather than repeated here.

Two consequences belong in the method. The providers are **two arms, not one
pool**: Google a frontier arm at thin *n*, Groq an open-weight arm at real *n*,
with `gpt-oss-20b` vs `gpt-oss-120b` giving a capability-scaling contrast
within one family on one serving stack. And a model is not a model — it is a
model *as served by someone* — so the provider is reported beside every model
ID.

### 3.8 Statistics

Wilson score intervals throughout, because the rates sit near 0 and 1 where the
normal approximation runs off the end of [0,1]. Comparisons are **exact**, not
asymptotic, because per-cell *n* is 4–36: Fisher's exact test for the
census-versus-benign contrast (unpaired), and McNemar's exact test where the
pairing is real (two models on the same windows; the two frames on identical
evidence in E3). All are stdlib implementations validated against published
reference values.

---

[1] Hugging Face, *Agent intrusion: technical timeline*.
`https://huggingface.co/blog/agent-intrusion-technical-timeline`


## 4. Results

All numbers below are read from the generated results file, which is rebuilt
from the raw per-window decision log after every run. Non-observations
(`unaffordable`, `quota_exhausted`, `error`, `truncated`) are excluded from
every denominator: they record that we could not buy the observation, not that
a model did anything.

### 4.1 Rule baselines set the bar (E0)

| detector | milestone hit | benign false-page | first page |
|---|---|---|---|
| `sev_threshold` **(ORACLE)** | 12/12 = 100% | 0/1280 = 0% | action #15 |
| `volume_spike` | 1/12 = 8% | 15/1280 = 1.2% | action #15 |
| `keyword_sigma` | 8/12 = 67% | 361/1280 = 28% | action #51 |

`sev_threshold` reads ground-truth severity. **It is an ORACLE — the upper
bound for a detector that already knows the answer — and is not deployable.**
It is in the table to bound the problem, not to compete.

The two real detectors bracket the difficulty. `volume_spike` keeps a 1.2%
false-page rate but catches **1 of 12** milestone windows: it is quiet and
blind. `keyword_sigma` catches 8 of 12 but fires on **28% of the benign
control** — it cannot tell the two streams apart, which is the finding, and it
is what makes the model numbers interpretable.

### 4.2 Models catch the incident and also page on the control (E1)

| model | provider | milestone hit (census) | benign false-page (uniform) | sep. | Fisher *p* |
|---|---|---|---|---|---|
| `gemini-3-flash-preview` | Google | 10/10 (100%, 72–100%) | 6/10 (60%, 31–83%) | +40% | 0.087 |
| `gemini-3.1-flash-lite` | Google | 12/12 (100%, 76–100%) | 11/12 (92%, 65–99%) | +8% | 1.000 |
| `gemini-3.5-flash` | Google | 6/6 (100%, 61–100%) | 5/7 (71%, 36–92%) | +29% | 0.462 |
| `gemini-3.5-flash-lite` | Google | 11/12 (92%, 65–99%) | 10/12 (83%, 55–95%) | +8% | 1.000 |
| `gemini-3.6-flash` | Google | 9/10 (90%, 60–98%) | 4/10 (40%, 17–69%) | +50% | 0.057 |
| `gemini-3.7-flash` | Google | 3/5 (60%, 23–88%) | 1/4 (25%, 5–70%) | +35% | 0.524 |
| `gemini-3.8-flash` | Google | 1/1 (100%, 21–100%) | — | — | — |
| `gemma-4-26b-a4b-it` | Google | 11/12 (92%, 65–99%) | 7/12 (58%, 32–81%) | +33% | 0.155 |
| `gpt-oss-120b` | Groq | 3/5 (60%, 23–88%) | 6/25 (24%, 11–43%) | +36% | 0.143 |

Intervals are Wilson 95%. **Pooled: milestone 66/73 (90%), benign false-page
50/92 (54%).**

Models find the incident — 90% of milestone-carrying windows produce a page —
and they also page on **more than half of an innocent shift**. This is the E0
result surviving contact with frontier models: `keyword_sigma`'s inability to
separate the streams is not an artefact of it being a crude rule.

**Significance, stated plainly: 0 of 9 models reach *p* < 0.05** on the
milestone-versus-benign contrast at this sample size. Per-model *n* is 4–36 and
the intervals overlap heavily. **The reportable claim is the gradient across
models, not any individual model's separation**, and we do not dress a
*p* = 0.057 as a result. Widening the sample is the highest-value follow-up and
the sampling ladder makes it purely additive.

The gradient itself is the interesting part, and it is not monotone in
capability. `gemini-3.1-flash-lite` scores a perfect 12/12 on milestones while
paging on 11 of 12 benign windows — recall bought by paging on nearly
everything, which is worth nothing operationally. `gemini-3.6-flash` (9/10
against 40%) and `gpt-oss-120b` (3/5 against 24%) actually discriminate.
Figure 1 puts every detector on one pair of axes; distance **above** the
diagonal is the only thing on it worth having, and several models sit close
to it.

### 4.3 First-page latency is degenerate on this corpus (E1)

Every E0 detector fires at action **#15–51** of 17,613 — roughly 10,400 actions
before the escalation point at #10,498 — on filler that is byte-identical in
both streams. Any model with a non-zero false-page rate does the same.

On this corpus, therefore, **a first page measures trigger-happiness, not
detection.** We report Escalation Action Index for completeness (Figure 2) and
decline to headline it; the metric pair in §4.2 replaces it. This
reprioritisation is logged as a pre-registration amendment, and both metrics
are reported for every model, so nothing is hidden by the ordering.

### 4.4 The incoherence test returns its pre-registered null (E3)

| model | incoherence | escalated | refused to assist | McNemar *p* |
|---|---|---|---|---|
| `gpt-oss-120b` | **0/24** (0%, 0–14%) | 9/24 = 38% | 0/24 = 0% | 0.0001 |
| `gpt-oss-20b` | **0/21** (0%, 0–15%) | 7/21 = 33% | 0/21 = 0% | 0.0001 |

**Pooled: 0 of 45 scoreable cells are INCOHERENT.** No model in this roster
refused to analyse evidence it had just declined to escalate. This is the
pre-registered null and it is a result: the design commits in advance to E0+E1
carrying the paper in this branch, and refusal-driven incoherence is simply not
what these models do.

**But the two frames do not agree, and the asymmetry runs opposite to the
concern that motivated the test.** On byte-identical evidence, `gpt-oss-120b`
assists on **24/24** moments and escalates on **9/24**; `gpt-oss-20b` assists on
21/21 and escalates on 7/21. Every discordant pair falls the same way — 15 and
14 moments respectively where the model helped without paging, **zero** in the
reverse direction (McNemar exact, *p* = 0.0001 both).

The failure mode this study set out to find was a model that clams up in both
frames. What it measured instead is a model that will **explain an intrusion to
you in detail and not think it worth waking anyone over**. Under-escalation, not
refusal, is the safety-relevant behaviour here.

**What was excluded, and whether it was random.** Three moments on
`gpt-oss-20b` remain unscoreable as `truncated` even after re-running at a 3×
token budget — the model spent its entire budget on reasoning tokens and
emitted no content, which the rubric classes as our defect and never scores.
**These exclusions are not evenly spread across phases: two are `supply_chain`
and one is `k8s`.** Evidence length is identical across all 24 moments (10 rows
each), so prompt size does not explain it; the model simply reasoned longest on
the late-stage material. The residue therefore falls on the
higher-consequence phases — the direction that **flatters** the model, since
those are the moments where failing to escalate would matter most. We state it
rather than averaging over it.

### 4.5 Cost

**$0.00.** Every call ran on a free tier. The binding constraint was
throughput, not price: 10–31 requests per model per day on Google AI Studio,
1,000 on Groq, measured rather than assumed.


## 5. Discussion

**Recall is the easy half.** Nine models, two providers, three rule baselines,
and almost everything finds the incident. What separates them is selectivity,
and the spread there is large and not monotone in capability: a flash-lite
model buys 12/12 recall by paging on 11 of 12 benign windows, while a
mid-sized model reaches 9/10 at a 40% false-page rate. Deploying on recall
alone would select the worst detector in the roster.

**The metric you pick decides the answer.** First-page latency — the obvious
metric, and the one we pre-registered — is degenerate here: every detector,
rule and model alike, fires within the first 50 of 17,613 actions, on filler
identical in both streams. It measures eagerness. We only found that because
the rule baselines cost nothing to run and made it visible before the model
budget was spent. Cheap non-LLM controls are not a nicety; they are what keeps
an expensive metric honest.

**Under-escalation is the finding worth acting on.** The pre-registered worry
was refusal — a guardrail turning a security assistant into an obstacle
mid-incident. It did not happen once in 45 scoreable moments. What happened
instead is that the same models, on the same bytes, will produce a competent
analysis and decline to raise an alarm, every discordant pair falling that way
and none the other. An operator reading the assistant-frame output would
conclude the model understood the situation. They would be right, and the
pager would still be silent.

This suggests the safety question for monitoring deployments is not "will the
model help?" but "does the model's willingness to *act* track its
understanding?" — and here it demonstrably does not.


## Appendix A — Limitations and Dual-Use Considerations

### A.1 What this study cannot establish

These were pre-registered before any model was run, and are reproduced with
what the run actually taught us added.

**The corpus is a reconstruction, not a capture.** Claims are about model
behaviour on a faithful scaffold built from published figures, not about what
Hugging Face's stack would have done. The generator follows the source's counts,
phase boundaries and milestone timestamps, but **75% of the corpus (13,163
actions across recon and dropper) carries no sourced milestone** — it is filler
obeying published marginals, so behaviour there is behaviour on our generator.
The two published source tables also disagree (16,521 vs 17,613); we took the
daily-volume total and carried the remainder as an `unclassified` residual, and
a different resolution would shift denominators slightly.

**Prompt framing is not authentication.** A model reading "you are the triage
layer" cannot verify it. Everything here measures response to a *claimed* role.

**Single-run, single-turn, text-only, English-only.** No temperature sweep, no
multi-turn drift, no tool use, no repeated sampling — every number is one draw
at temperature 0. A model that pages 40% of the time here might page 60% on a
re-run, and we have not measured that variance.

**Statistical power is the dominant limitation and it is unevenly
distributed.** Per-cell *n* is 4–36, intervals overlap heavily, and **no model
reaches *p* < 0.05** on stream separation. The gradient across models is the
reportable claim; no individual model's separation is established. The Google
arm is thinnest — free-tier caps of 10–31 requests per model per day left
several Gemini models at *n* = 1–12, one at a single window. **Those rows are
in the table because omitting them would be selective reporting, not because
they support a conclusion.** The sampling ladder makes widening purely
additive, so this is a resource limit, not a design one.

**Three E3 moments are unscoreable and they are not randomly distributed.**
`gpt-oss-20b` exhausted its whole token budget on reasoning for moments 19, 23
and 24 even at a 3× re-run — two `supply_chain`, one `k8s`. Evidence length is
identical across all 24 moments, so the loss is model behaviour, not prompt
size. It falls on the late-stage, higher-consequence phases, which is the
direction that flatters the model.

**E3 covers two models, both from one family on one provider.** The zero
incoherence rate and the escalate-vs-assist asymmetry are established for
`gpt-oss-120b` and `gpt-oss-20b`, not for the frontier arm. Whether Gemini
models show the same asymmetry is untested and is the first thing we would run
next.

**The blind separability check was labelled by an LLM, not a human.** The
pre-registration specifies a human rater. n = 20 makes it a screen for trivial
separability, not a powered test — it cannot resolve 55% from 70%.

**Serving stacks are a confound we bound but cannot remove.** A model is a
model *as served by someone*: quantisation, sampling defaults, system-prompt
injection and moderation layers all differ. We report the provider beside every
model ID and keep the two as separate arms. `gpt-oss-20b` vs `gpt-oss-120b` is
the one clean comparison, both on one stack.

**Frontier proprietary models are absent.** The Gemini Pro tier returns
`limit: 0` at $0 — refused, not throttled — and no GPT- or Claude-class model
was reachable free. Our "frontier" arm is frontier-*flash*.

### A.2 Dual-use considerations

**What is in the artefact.** A generated action stream reconstructing a
publicly documented intrusion, a benign control, a monitor-frame harness, and
scoring code. The corpus contains synthetic log lines describing attacker
behaviour at the level of abstraction the published timeline already uses —
phase names, host roles, event descriptions, timestamps.

**What is not in it, deliberately.** No working exploit, payload, credential,
novel installation recipe, or technique absent from the public source. The
corpus is a *detection* substrate: it describes what an intrusion looked like
in a log, not how to perform one. Every step is downstream of a vendor's own
post-incident write-up.

**The realistic misuse path, and why we judge it low.** Someone could read the
corpus as a checklist of what a real agent intrusion looked like — information
already public in the source we cite, in more operational detail than our
reconstruction carries. We add no capability; we add a benchmark.

**The genuine dual-use surface is the finding, not the data.** We report which
models under-escalate and by how much. An attacker who knew that a particular
monitor model pages on only a third of pivotal moments could, in principle,
shape activity to stay under it. Three things bound this. The measurement is a
snapshot of production endpoints in September 2026 and will not survive model
updates. It is specific to our reconstruction, and generalisation to a real
SOC's telemetry is exactly what we do not claim. And the same information is
what a defender needs to decide whether to put a model on monitoring duty at
all — withholding it protects no one and leaves operators calibrating on
optimism.

**On the false-page finding specifically.** Publishing "these models page on
half of a benign shift" is defensive information. Alert fatigue is a documented
failure mode in security operations; a monitor that cries wolf at this rate
degrades response capacity rather than adding to it, and an operator deploying
one should know that before the pager does.

**Release posture.** Harness, corpus generator, ground truth, raw per-window
decisions and scoring code are released so the numbers can be audited and the
sample widened. Consistent with the sprint's disclosure guidance, we release no
novel installation recipe and nothing that is not derivable from the cited
public source.

### A.3 Honest scope statement

This is a weekend study. It has a validated control, pre-registered metrics, a
frozen rubric with a logged amendment, exact rather than asymptotic statistics,
and non-LLM baselines on the same axes. It does not have the sample size to
rank individual models, and it should not be cited as doing so. What it
supports is a claim about a *pattern* — high recall, poor selectivity, and
under-escalation on evidence models will readily discuss — and a reusable
substrate for testing whether that pattern holds at *n* we could not afford.
