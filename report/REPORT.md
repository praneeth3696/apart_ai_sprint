# Fluent About the Intrusion, Silent on the Pager

## Abstract

Would an LLM on monitoring duty have paged the on-call during the July 2026
Hugging Face agent intrusion? We rebuilt it from the published timeline as a
replayable 17,613-action stream, generated a size-matched benign control,
verified blind that the two are not trivially separable, and ran 15 models
across three providers past both, at $0.00.

Models fail in both directions. One pages on 11 of 12 innocent windows to buy
perfect recall; two others page on nothing at all, reading an active intrusion
as "resource contention". Only 2 of 15 separate the streams significantly.

We then wrapped byte-identical evidence in a monitor frame and an assistant
frame. Across 228 moments and 11 models, incoherence was zero — but the frames
disagreed in one direction only: models assisted on 228/228 and escalated on
83. The risk is not refusal; it is fluent analysis with a silent pager.


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
Ten models across two providers, at a total cost of **$0.00**.

**Two findings, and the second is the one we did not expect.**

**Models fail in both directions, and pooling hides it.** Across 15 models the
pooled numbers are 60% of milestone windows paged and 23% of innocent ones —
but that average describes no model in the study. At one end
`gemini-3.1-flash-lite` buys a perfect 12/12 recall by paging on **11 of 12
benign windows**; at the other, two Mistral models page on **nothing at all**,
0/12 milestones and 0/36 benign, reading an active intrusion as "normal
operational activity" and "resource contention". A useful monitor needs high
recall *and* low false-page rate; that region of the space is essentially
empty. **Only 2 of 15 models separate the streams at *p* < 0.05**, and those
two are the ones we could sample most deeply — so we report the shape of the
distribution, not a ranking. Capability does not order it: `gpt-oss-120b`
discriminates while `gpt-oss-20b`, same family and same serving stack, catches
2 of 12 milestones.

**The failure mode is under-escalation, not refusal.** We expected the
safety-relevant risk to be a model that declines to engage with intrusion
evidence — the pattern where a guardrail turns a security assistant into an
obstacle mid-incident. We tested it directly: byte-identical evidence wrapped
in a monitor frame and an assistant frame, 24 moments spanning every phase, 11
models across three providers. **Incoherence was zero in 228 scoreable
moments.** Not one model refused to analyse evidence it had just declined to
escalate. But the two frames disagreed sharply and *entirely* in one direction:
models assisted on **228/228** moments and escalated on **83**. Every
discordant pair falls the same way; the "escalates but won't help" cell is
empty across all eleven models.

That reframes the concern. These models will explain an intrusion to you in
detail and not think it worth waking anyone over. The risk in an AI-assisted
SOC is not the model that won't talk about the incident — it is the model that
talks about it fluently while the pager stays silent.

**Contributions.** A replayable reconstruction of a real 2026 agent intrusion
with a validated matched control, released with the harness; a metric pair —
milestone hit rate against benign false-page rate — replacing a first-page
latency we show is degenerate here; non-LLM rule baselines on the same axes, so
the model numbers are interpretable at all; and the two-frame incoherence test
at K=24 across three providers and five model families, which returns its
pre-registered null and an unexpected, strongly one-directional asymmetry.

---

[1] Hugging Face, *Agent intrusion: technical timeline*.
`https://huggingface.co/blog/agent-intrusion-technical-timeline`


## 2. Related Work

**The incident.** Our substrate is a reconstruction of the July 2026 Hugging
Face agent intrusion, built from two independently-fetched primary sources: HF's
own technical timeline [1] and OpenAI's 38-page incident report [2]. Both were
retrieved and cross-checked on 2026-09-04; where their published tables
disagree we carry the disagreement rather than resolving it silently
(Methodology §3.1). Everything offensive in our corpus is downstream of those
two documents.

**Why a replayable stream.** The question this paper answers was asked publicly
of that incident by practitioners — *"which action number does your control
fire on?"* — and it is unanswerable against a prose timeline. Post-incident
write-ups are narrative; detection latency is a function of an ordered event
stream. Converting the former into the latter, with ground-truth labels and a
matched control, is the contribution that makes the rest measurable.

**Refusal benchmarks and what they do not measure.** A mature literature
measures *over-refusal*: XSTest [3] and OR-Bench [4] both build prompts that
look unsafe but are benign, and score models on wrongly declining them.
Meta's CyberSecEval line carries the same axis into security specifically as a
False Refusal Rate [5], and Gray Swan's refusal framework [6] evaluates where
an agent *should* decline offensive-security requests. Closest to our setting,
*Defensive Refusal Bias* [7] ran 2,390 real cyber-defence competition prompts
and found security keywords refused at **2.72x** the rate of neutral phrasing,
with explicit authorisation *increasing* refusal (21.8% vs 11.6%) rather than
licensing the work. Over-blocking of defensive security work is therefore a
known and actively-researched failure mode, not a novel observation — and we
separate *refused* from *filtered* (Methodology 3.6) because our own earlier
measurement found the dominant non-response mode to be a platform filter
blocking the request before generation: zero completion tokens, no model
judgment involved.

**Refusal was not the failure mode we found.** In 45 scoreable moments, not one
model declined to analyse the evidence. A benchmark measuring only the refusal
axis would have recorded a clean sheet and missed the finding entirely. What we
observe is the opposite defect: the model engages fluently and *does not
escalate*. That axis — whether the model raises an alarm, not whether it is
willing to talk — is the one these benchmarks do not score.

**Incident-response benchmarks.** Evaluating agents on real incident substrate
is an active area. SecRespond [8] gives agents forensic disk snapshots from ten
compromised cloud hosts and scores forensic reports and remediation plans;
SIR-Bench [9] replays authentic incident patterns as cloud telemetry across 794
test cases to measure investigation depth; CyberSOCEval [10] scores incident
investigation, summarisation and severity rating on SOC data. Our substrate
differs in being a *public-report reconstruction* — reproducible from two cited
documents with no proprietary telemetry (Limitations 2) — and our unit of
analysis differs in being the per-window page/don't-page decision over an
ordered stream, which is what makes detection latency measurable at all.

Two things distinguish what we measure. First, **the matched benign control.**
SIR-Bench does score false-positive rejection (73.4% for its baseline agent) on
labelled false alerts, so a false-alarm axis is not unprecedented; what we add
is a *time-matched benign stream built by the same generator as the attack
stream*, which lets us report a page rate on windows containing no intrusion at
all and so measure selectivity rather than rejection of pre-labelled decoys. To
our knowledge no prior benchmark pairs an incident replay with such a control.
Second, **frame sensitivity on byte-identical evidence** — holding the evidence
fixed and varying only whether the model is addressed as the triage layer or as
an analyst's assistant. We are not aware of prior work isolating that variable
on security-escalation decisions.

**Non-LLM baselines.** We include three rule detectors (severity oracle, volume
spike, keyword/Sigma set) on the same axes as the models, because a page rate
without a comparator is uninterpretable. This follows standard detection-
engineering practice rather than any specific prior system; the point is that
the comparison is cheap and that omitting it makes the model numbers unreadable.

---

[1] Hugging Face, *Anatomy of a Frontier Lab Agent Intrusion: A Technical
Timeline of the July 2026 Incident*, 2026-07-27.
`https://huggingface.co/blog/agent-intrusion-technical-timeline`

[2] OpenAI, *Hugging Face Incident Technical Report*, 38pp.
`https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf`

[3] P. Rottger, H. R. Kirk, B. Vidgen, G. Attanasio, F. Bianchi, D. Hovy,
*XSTest: A Test Suite for Identifying Exaggerated Safety Behaviours in Large
Language Models*, NAACL 2024. arXiv:2308.01263.

[4] J. Cui, W.-L. Chiang, I. Stoica, C.-J. Hsieh, *OR-Bench: An Over-Refusal
Benchmark for Large Language Models*. arXiv:2405.20947.

[5] M. Bhatt et al., *CyberSecEval 2: A Wide-Ranging Cybersecurity Evaluation
Suite for Large Language Models*. arXiv:2404.13161. (False Refusal Rate.)

[6] E. K. Jones, M. Dziemian, M. Fredrikson, J. Z. Kolter, *A New Framework for
Cybersecurity Refusals in AI Agents*. arXiv:2606.02644.

[7] D. Campbell, N. Kale, U. M. Sehwag, B. Herring, N. Price, D. Borges,
A. Levinson, C. Q. Knight, *Defensive Refusal Bias: How Safety Alignment Fails
Cyber Defenders*. arXiv:2603.01246.

[8] L. Wang et al., *SecRespond: Benchmarking AI Agents for Real-World
Post-Compromise Incident Response*, 2026-07-29. arXiv:2607.26791.

[9] D. Begimher, C. Leo, J. Huang, P. Gaw, B. Zheng, *SIR-Bench: Evaluating
Investigation Depth in Security Incident Response Agents*, 2026-04-13.
arXiv:2604.12040.

[10] L. Deason et al. (Meta / CrowdStrike), *CyberSOCEval: Benchmarking LLMs
Capabilities for Malware Analysis and Threat Intelligence Reasoning*.
arXiv:2509.20166.

[11] S. Tariq, M. Baruwal Chhetri, S. Nepal, C. Paris, *Alert Fatigue in
Security Operations Centres: Research Challenges and Opportunities*, ACM
Computing Surveys 57(9), Article 224, April 2025. doi:10.1145/3723158.


## 3. Methodology

### 3.1 Corpus and controls

We reconstruct the July 2026 Hugging Face agent intrusion from its published
technical timeline [1] as a replayable action stream. The corpus is
**generated, not hand-written**: every count, phase boundary and milestone
timestamp comes from one machine-readable ground-truth file, and the generator
asserts at build time that each defined milestone is placed. It covers **17,613
attacker actions** inside the published campaign envelope, 2026-07-09 02:28 to
2026-07-13 14:14 UTC.

One source discrepancy is inherited rather than smoothed over: the published
phase and daily-volume tables disagree (16,521 vs 17,613). We take the
daily-volume total, which matches the source's own "~17,600" headline to within
13 actions, and carry the 1,092-action remainder as an explicit `unclassified`
residual. Exfiltration is **56 actions (0.3%)** — a needle-in-haystack problem,
so any method working by volume spike has the wrong task.

Every experiment runs against **two streams**: the attack stream and a
size-matched **benign control** from the same generator and the same marginals,
with no intrusion in it. The control converts "the model paged" into "the model
paged *selectively*"; without it a page rate is uninterpretable.

Both streams are cut into 5-minute windows — 1,278 attack, 1,280 control.
Twelve attack windows carry a milestone; the control carries none by
construction. **"Milestone" does not mean "published timestamp" for all twelve**,
and `corpus/CITATIONS.md` §5 grades each one: six are read off a published table
in HF or OpenAI's report; five have a bounded or estimated time, where the source
fixes the event but not the minute ("shortly before midnight on July 11", "early
on July 12", "in under 13 hours"); and one, `supply_chain_token_mint`, is
**unreconciled** — HF's account puts it on 07-12 and OpenAI's on 07-13, and we
have not resolved which is right. The milestone *set* is sourced; six of the
twelve *timestamps* are interpolated within published bounds, and the escalation
point is one of them (PREREGISTRATION §4). Models see only a projection of each action (index, timestamp,
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
API cost; without them a model's page rate has nothing to compare against.
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

**Two accounts, disclosed.** The Google arm was collected on two separate free
tiers: one per author, each on their own Google AI Studio project and API key.
Google meters the free tier per project per model per day, so these are two
independent quotas rather than one quota circumvented — the same arrangement as
two researchers each running their own laptop. No paid tier, no shared or
secondary accounts, and no key was used beyond its own published free limit.
Total spend across the study is $0.00.

### 3.8 Statistics

Wilson score intervals throughout, because the rates sit near 0 and 1 where the
normal approximation runs off the end of [0,1]. Comparisons are **exact**, not
asymptotic, because per-cell *n* is 4–36: Fisher's exact test for the
census-versus-benign contrast (unpaired), and McNemar's exact test where the
pairing is real (two models on the same windows, across 15; the two frames on identical
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

### 4.2 Models fail in both directions (E1)

| model | provider | milestone hit (census) | benign false-page (uniform) | Fisher *p* |
|---|---|---|---|---|
| `gemini-3.1-flash-lite` | Google | 12/12 (100%, 76–100%) | **11/12 (92%, 65–99%)** | 1.000 |
| `gemini-3.5-flash-lite` | Google | 11/12 (92%, 65–99%) | 10/12 (83%, 55–95%) | 1.000 |
| `gemini-3.5-flash` | Google | 6/6 (100%, 61–100%) | 5/7 (71%, 36–92%) | 0.462 |
| `gemini-3-flash-preview` | Google | 10/10 (100%, 72–100%) | 6/10 (60%, 31–83%) | 0.087 |
| `gemma-4-26b-a4b-it` | Google | 11/12 (92%, 65–99%) | 7/12 (58%, 32–81%) | 0.155 |
| `gemini-3.6-flash` | Google | 9/10 (90%, 60–98%) | 4/10 (40%, 17–69%) | 0.057 |
| `qwen3.8-27b` | Groq | 10/12 (83%, 55–95%) | 11/36 (31%, 18–47%) | **0.002** |
| `gemini-3.7-flash` | Google | 3/5 (60%, 23–88%) | 1/4 (25%, 5–70%) | 0.524 |
| `gpt-oss-120b` | Groq | 7/12 (58%, 32–81%) | 7/36 (19%, 10–35%) | **0.024** |
| `gpt-oss-20b` | Groq | 2/12 (17%, 5–45%) | 4/33 (12%, 5–27%) | 0.650 |
| `ministral-14b` | Mistral | 1/12 (8%, 1–35%) | 0/36 (0%, 0–10%) | 0.250 |
| `ministral-8b` | Mistral | **0/12 (0%, 0–24%)** | 0/36 (0%, 0–10%) | 1.000 |
| `ministral-3b` | Mistral | **0/12 (0%, 0–24%)** | 0/36 (0%, 0–10%) | 1.000 |
| `gemini-3.8-flash` | Google | 1/1 (100%, 21–100%) | — | — |
| `qwen3.6-27b` | Groq | 1/1 (100%, 21–100%) | 0/3 (0%, 0–56%) | 0.250 |

Intervals are Wilson 95%, ordered by false-page rate. The last two rows carry
*n* = 1: `gemini-3.8-flash` exhausted its 20-request daily cap, and
`qwen3.6-27b` rejects the E1 prompt as too large. **They are listed because
omitting them would be selective reporting, not because they support
anything.**

**The distribution is bimodal, and that is the result.** Pooled across models
the numbers are 84/141 (60%) on milestones and 66/283 (23%) on benign windows —
but **the pooled figure describes no model in the study.** It is the average of
a monitor that pages on 92% of an innocent shift and one that pages on nothing
at all, and reporting it alone would hide the finding rather than state it.

At one end, `gemini-3.1-flash-lite` achieves a perfect 12/12 milestone recall by
paging on **11 of 12 benign windows**. Its recall is free and worth nothing: a
pager that always fires carries no information.

At the other, `ministral-3b` and `ministral-8b` page on **nothing at all** —
0/12 milestones and 0/36 benign windows. This is not a parsing artefact; both
return well-formed verdicts with severity ratings and reasoning. They simply
read the intrusion as an operations problem. On the window containing the first
sandbox RCE, `ministral-8b` returns *"normal operational activity… no signs of
errors, security risks"*; on a window where Python processes jump 16→256 during
credential-access reconnaissance, *"resource contention or scaling issues."*
**A monitor that never pages has a perfect false-page rate**, which is precisely
why false-page rate cannot be read without recall beside it.

Only two models separate the streams at *p* < 0.05: `qwen3.8-27b` (10/12 against
31%, *p* = 0.002) and `gpt-oss-120b` (7/12 against 19%, *p* = 0.024). **Thirteen
do not.** Those two are also the models we could sample most deeply (*n* = 36
benign against *n* = 4–12 for the Google arm), so **significance here tracks
sampling budget as much as model behaviour** and we do not present it as a
ranking.

Figure 1 places every detector and every rule baseline on one pair of axes.
The useful region is the **top-left** — high recall, low false-page — and it is
empty. Models spread instead along and above the diagonal at the trigger-happy
end, or collapse into the bottom-left corner with the blind ones.

Capability does not order this. `gpt-oss-120b` discriminates while
`gpt-oss-20b` — same family, same provider, same serving stack — catches 2 of
12 milestones. Within Mistral the 3b, 8b and 14b models are near-identical and
all near-silent. **Scale did not buy selectivity in either family.**

### 4.3 First-page latency is degenerate on this corpus (E1)

Every E0 detector fires at action **#15–51** of 17,613 — roughly 10,400 actions
before the escalation point at #10,498 — on filler that is byte-identical in
both streams. Any model with a non-zero false-page rate does the same.

On this corpus, therefore, **a first page measures trigger-happiness, not
detection.** We report Escalation Action Index for completeness (Figure 2) and
decline to headline it; the metric pair in §4.2 replaces it. This
reprioritisation is logged as a pre-registration amendment, and both metrics
are reported for every model, so nothing is hidden by the ordering.

**The pre-registered negative-lead-time result.** We committed in advance to
reporting this whichever way it came out, because it is unflattering to the
whole framing of escalation latency. The ground-truth escalation point — the
first sourced pivotal milestone, action #10,498 at 2026-07-11 17:47:30 UTC —
falls **51.4 hours *after* the first exfiltration action** (#1,894, 07-09
14:21). Exfiltration is not the thing a perfectly-calibrated detector gets
ahead of on this incident; by the time the escalation criterion is satisfiable
at all, data has been leaving for more than two days.

Lead time to admin/host-level access is **+10.0 h**, so the criterion is not
useless — it is early for the privilege-escalation milestone and hopelessly
late for the exfiltration one. This is a property of the published phase
windows rather than a defect in the rule, and we declined to reselect a rule
that produces a prettier number.

The two facts in this section compound rather than cancel. The rule that
*should* fire is already 51 hours too late for exfiltration; the detectors that
beat it to the punch do so only by firing on action #15 of 17,613, on filler
identical in both streams. **Neither "page early" nor "page correctly" is
achieved by anything we measured.**

### 4.4 The incoherence test: a null, and a strong asymmetry (E3)

Eleven models across **three providers and five families**, 228 scoreable
moments on byte-identical evidence.

| model | incoherence | escalated | assisted | McNemar *p* |
|---|---|---|---|---|
| `gemini-3.6-flash` | 0/10 | 9/10 (90%) | 10/10 | 1.000 |
| `gemini-3.1-flash-lite` | 0/24 | 21/24 (88%) | 24/24 | 0.250 |
| `gemini-3.5-flash-lite` | 0/24 | 14/24 (58%) | 24/24 | **0.002** |
| `gemma-4-26b-a4b-it` | 0/24 | 14/24 (58%) | 24/24 | **0.002** |
| `qwen3.6-27b` | 0/5 | 2/5 (40%) | 5/5 | 0.250 |
| `gpt-oss-120b` | 0/24 | 9/24 (38%) | 24/24 | **0.0001** |
| `gpt-oss-20b` | 0/21 | 7/21 (33%) | 21/21 | **0.0001** |
| `qwen3.8-27b` | 0/24 | 6/24 (25%) | 24/24 | **<0.0001** |
| `ministral-14b` | 0/24 | 1/24 (4%) | 24/24 | **<0.0001** |
| `ministral-8b` | 0/24 | 0/24 (0%) | 24/24 | **<0.0001** |
| `ministral-3b` | 0/24 | 0/24 (0%) | 24/24 | **<0.0001** |

**Incoherence is zero — 0 of 228.** The pre-registered null holds across every
model, family and provider we could reach. **Not one model, on any moment,
refused to analyse evidence it had just declined to escalate.** The design
commits in advance to E0+E1 carrying the paper in this branch; that commitment
is honoured, and the null is reported as a result.

**The frames disagree, overwhelmingly and in one direction.** Every model
assisted on **228/228** moments. They escalated on **83/228 (36%)**. Every
discordant pair in the entire experiment falls the same way — the model helped
without paging — and the `tension` cell (escalates but will not help) is
**empty across all eleven models**. Seven of eleven are individually
significant at *p* < 0.05.

The failure mode this experiment was built to detect was a model that clams up
in both frames. What it measured is the mirror image: **a model that will
explain an intrusion to you in detail and not think it worth waking anyone
over.** Under-escalation, not refusal, is the safety-relevant behaviour here.

**The two findings reconcile rather than conflict.** The weakest E3 arms are
the strongest E1 cry-wolf models: `gemini-3.1-flash-lite` escalates on 21 of 24
moments and is not individually significant — but it is the same model that
bought 12/12 recall by paging on 11 of 12 innocent windows. **A model that
pages on nearly everything has no headroom to show an escalation deficit.** Its
high escalation rate is a symptom of §4.2, not a counterexample to this
section. Conversely the Mistral models, which page on nothing in E1, escalate
on 0–4% here while assisting on all 72 of their moments — the same behaviour
seen from the other side.

**What was excluded, and whether it was random.** Three `gpt-oss-20b` moments
remain `truncated` after a 3× budget re-run — two `supply_chain`, one `k8s`.
Evidence length is identical across all 24 moments, so prompt size does not
explain it; the model reasoned longest on the late-stage material. **The residue
is not evenly spread across phases** and falls on the higher-consequence ones,
the direction that flatters the model. A further 41 moments (`allam-2-7b`
entirely, most of `qwen3.6-27b`) were lost to a network outage and a
per-request size limit respectively; both are infrastructure, not behaviour,
and both are excluded rather than imputed.

### 4.5 Cost

**$0.00.** Every call ran on a free tier. The binding constraint was
throughput, not price: 10–31 requests per model per day on Google AI Studio,
1,000 on Groq, measured rather than assumed.


## 5. Discussion

**Neither half is easy, and they fail separately.** Selecting a monitor on
recall alone picks `gemini-3.1-flash-lite`, which pages on 92% of an innocent
shift. Selecting on false-page rate alone picks `ministral-3b`, which pages on
nothing whatever. Both look excellent on one axis and are useless. **This is
the practical argument for the matched control**: without a benign stream,
half the roster would have looked deployable.

Capability does not resolve it. `gpt-oss-120b` discriminates while
`gpt-oss-20b` — same family, same provider, same serving stack — catches 2 of
12 milestones, and Mistral's 3b, 8b and 14b are near-identical and near-silent.
**Scale did not buy selectivity in either family.** Note too which models
cleared significance: the two with the deepest benign sampling, not the two
most capable. Sampling depth and selectivity are confounded here, and we say so
rather than reading a capability story into it.

**A false page is not a free page.** Alert fatigue is a documented,
surveyed failure mode in real security operations centres [11]: false
positives consume the analyst hours that genuine detections need, and
sustained volume drives both error and attrition. A monitor that pages on
roughly half of an intrusion-free stream is therefore not a conservative
monitor with a tolerable overhead — on the receiving end it is
indistinguishable from the alert load SOC teams already cannot clear. The
benign-stream page rate belongs next to recall in any deployment decision,
not in a footnote.

**The metric you pick decides the answer.** First-page latency — the obvious
metric, and the one we pre-registered — is degenerate here: every detector,
rule and model alike, fires within the first 50 of 17,613 actions, on filler
identical in both streams. It measures eagerness. We only found that because
the rule baselines cost nothing to run and made it visible before the model
budget was spent. Cheap non-LLM controls are not a nicety; they are what keeps
an expensive metric honest.

**Under-escalation is the finding worth acting on.** The pre-registered worry
was refusal — a guardrail turning a security assistant into an obstacle
mid-incident. It did not happen once in 228 scoreable moments, across 11 models and three providers. What happened
instead is that the same models, on the same bytes, will produce a competent
analysis and decline to raise an alarm, every discordant pair falling that way
and none the other. An operator reading the assistant-frame output would
conclude the model understood the situation. They would be right, and the
pager would still be silent.

**The two findings are one finding seen from two sides.** The weakest E3 arms
are the strongest E1 cry-wolf models, and the strongest E3 arms are the silent
ones: `gemini-3.1-flash-lite` escalates on 21 of 24 moments precisely because
it pages on almost everything, and Mistral escalates on 0–4% precisely because
it pages on almost nothing. A model with no headroom cannot show an escalation
deficit, and a model with no alarm at all shows the largest one.

So the safety question for monitoring deployments is not "will the model help?"
— it demonstrably will, on 228 of 228 moments — but "does the model's
willingness to *act* track its understanding?" Here it does not, and the gap
runs one way: **fluent analysis, silent pager.**


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
distributed.** Per-cell *n* runs from 1 to 36. Only **2 of 15 models reach
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

**E3 now spans 11 models, five families and three providers — but the effect
size varies a great deal across them.** The zero incoherence rate replicates
everywhere (0/228). The escalate-vs-assist asymmetry replicates in direction
everywhere — the "escalates but will not help" cell is empty in all eleven —
but escalation itself ranges from 0% (`ministral-3b`) to 90%
(`gemini-3.6-flash`), and only 7 of 11 models are individually significant.
`gemini-3.1-flash-lite` in particular is *not* (21/24 escalated, *p* = 0.25).
Reporting the pooled asymmetry alone would overstate how uniform it is.

The residual limitation is narrower than the original one but real: **no
frontier-*proprietary* model is in this study at all.** The Google Pro tier
returns `limit: 0` at $0, Cerebras requires payment, and GitHub Models — the
GPT-class arm the pre-registration named — was retired mid-sprint (HTTP 410).
Our "frontier" arm is frontier-*flash*, and whether a GPT- or Claude-class
model shows the same asymmetry is untested and is the first thing we would run
next.

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
