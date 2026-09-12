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
pairing is real (two models on the same windows; the two frames on identical
evidence in E3). All are stdlib implementations validated against published
reference values.

---

[1] Hugging Face, *Agent intrusion: technical timeline*.
`https://huggingface.co/blog/agent-intrusion-technical-timeline`
