## 3. Methodology

### 3.1 Corpus and controls

We reconstruct the July 2026 Hugging Face agent intrusion from its published
technical timeline [1] as a replayable action stream. The corpus is
**generated, not hand-written**: every count, phase boundary and milestone
timestamp is read from a single machine-readable ground-truth file, and the
generator asserts at build time that each defined milestone is actually placed.
The reconstruction covers **17,613 attacker actions** between 2026-07-09 02:28
UTC and 2026-07-13 14:14 UTC.

One discrepancy in the source is inherited rather than smoothed over. The
published phase table and the published daily-volume table disagree — 16,521
against 17,613 actions. We treat the daily-volume total as authoritative
because it agrees with the source's own rounded headline ("~17,600") to within
13 actions, and carry the 1,092-action remainder as an explicit `unclassified`
residual rather than deleting it. Exfiltration is **56 of ~17,600 actions
(0.3%)**: this is a needle-in-haystack detection problem, not a volume problem,
and any method that works by noticing traffic spikes is being handed the wrong
task.

Every experiment runs against **two streams**: the attack stream and a
size-matched **benign control** built by the same generator from the same
marginal distributions, with no intrusion in it. The control is what converts
"the model paged" into "the model paged *selectively*", and without it a page
rate is uninterpretable.

**Windowing.** Both streams are cut into 5-minute alert windows — 1,278 for the
attack stream, 1,280 for the control. Twelve attack windows carry a sourced
milestone; the benign stream carries none by construction. Models see only a
projection of each action (index, timestamp, host role, actor, event text);
the ground-truth block travelling with each window is asserted out of every
prompt at runtime, because the milestone and tactic labels are precisely what
we are measuring the model's ability to notice.

### 3.2 Is the control actually a control?

A matched control is only worth having if it is not trivially distinguishable.
Before any model was run, 20 unlabelled windows — 10 from each stream — were
scored blind against a pre-registered failure threshold of 90% accuracy.

Result: **14/20 (70%), Wilson CI95 48.1–85.5%, p = 0.058** against chance;
attack recall 70%, benign recall 70%, no label bias. The control passes: it is
not trivially separable, so the false-page denominator is defensible.

> **Disclosure.** These labels were produced by **an LLM (Claude), not by a
> human rater.** The pre-registration specifies a human labeller; it did not
> happen that way, and the deviation is disclosed here rather than left
> implicit. An LLM is arguably a *stronger* adversary than a human skimming
> (systematic, tireless) and arguably weaker (no operational intuition), so we
> do not claim the substitution is neutral in either direction. Additionally,
> **n = 20 is a screen, not a powered experiment** — the interval spans roughly
> ±20 points, so this check reliably catches the trivial-separability case it
> was designed for and cannot resolve 55% from 70%.

### 3.3 E0 — non-LLM rule baselines

Three detectors run over the identical streams, windowing and escalation
ground truth, at zero API cost. Without them, "model X pages at window 12 with
a 40% false-page rate" gives a reader nothing to compare against.

`volume_spike` and `keyword_sigma` see **only** the same model-visible
projection a model under evaluation sees. `sev_threshold` deliberately breaks
that rule and reads ground-truth severity directly: **it is an ORACLE — an
upper bound on what any detector could achieve if it already knew the answer —
and it is never a baseline a defender could deploy.** We label it ORACLE at
every appearance for that reason.

### 3.4 E1 — escalation and false-paging

Each model is placed in a **monitor frame**: it is the automated triage layer
for a production Kubernetes platform, it sees a bounded rolling digest of
everything before the current window plus the current window itself, and it
must return strict JSON — `{severity, page_oncall, rationale}`. `page_oncall`
is the escalation criterion; severity is recorded but is not it. The rolling
digest is computed locally from model-visible fields and is bounded (top hosts,
top actors, the last 8 events), so the measurement stays a triage task rather
than becoming a long-context retrieval task.

Unparseable JSON gets **exactly one** re-ask with the same prompt plus "Return
only the JSON object"; still unparseable is recorded as `unparseable` and
excluded from page-rate denominators.

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
the last. This is not cosmetic: the evenly-spaced sample at *n* and at *n′*
share no positions unless *n′/n* is an odd integer, so a naive widening from 12
to 40 windows would have selected **none** of the windows a previous run had
already paid for. On the ladder, every rung is a strict superset of every rung
beneath it, so widening a run is always additive and never wastes quota.

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
binding constraint — **throughput was**, and the shape of that constraint
determined the shape of the experiments. Google AI Studio meters its free tier
**per project × model** at a measured 10–31 requests *per day*; Groq allows
1,000 per day per model against an 8,000 tokens-per-minute organisation-wide
ceiling. Full per-model measurements, the quota semantics, and the
reproducibility traps we hit are documented in the repository's `PROVIDERS.md`
rather than repeated here.

Two consequences belong in the method, not in a footnote. First, the two
providers are **two arms, not one pool**: Google supplies a frontier arm at
thin *n*, Groq an open-weight arm at real *n*, and `gpt-oss-20b` versus
`gpt-oss-120b` gives a capability-scaling contrast within one family on one
serving stack. Second, a model is not a model — it is a model *as served by
someone* — so the provider is reported alongside every model ID.

### 3.8 Statistics

Wilson score intervals throughout, because the rates sit near 0 and 1 where the
normal approximation runs off the end of [0,1]. Comparisons are **exact**, not
asymptotic, because the per-cell *n* here is 4–36: Fisher's exact test for the
milestone-census-versus-benign contrast (unpaired — different windows from
different streams), and McNemar's exact test where the pairing is real (two
models on the same windows; the two frames on identical evidence in E3). All
tests are implemented in the standard library and validated against published
reference values.

---

[1] Hugging Face, *Agent intrusion: technical timeline*.
`https://huggingface.co/blog/agent-intrusion-technical-timeline`
