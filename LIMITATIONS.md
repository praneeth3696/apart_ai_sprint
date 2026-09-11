# Limitations and Dual-Use Considerations

Required appendix, and scored. Written before results so it is not shaped by
them.

---

## 1. The corpus is a reconstruction, not telemetry

`HF-Replay-Recon` is built from **published figures only**. It matches the
published phase totals, per-phase time windows, daily volumes, and documented
milestone ordering. It does **not** reproduce Hugging Face's logs, their
internal severity-scoring logic, or their true log verbosity.

Every claim is therefore about **model behaviour on a faithful scaffold**, not
about what HF's stack would have done. We label the artifact a scaffold in the
abstract itself, not only here.

**75% of the corpus has no sourced milestone.** recon (6,191) + dropper (6,972)
= 13,163 actions carry published marginals and nothing else. The kill-chain
milestones cluster in k8s, rce, tailscale, and supply_chain. A reader should
treat the bulk phases as volume-realistic and content-synthetic.

**The published sources contradict each other**, and we did not paper over it:
the HF phase table sums to 16,521 while its daily-volume table sums to 17,613.
See `corpus/CITATIONS.md` §4 for the 1,092-action `unclassified` row this
forced, which is our inference and is labelled as such.

**Timestamps are partly interpolated.** Four of twelve milestones have no exact
published time ("shortly before midnight", "early on July 12"); we interpolate
between sourced anchors, preserve ordering, respect published bounds, and mark
every such row `t_utc_estimated: true`.

**MITRE mappings are ours.** Neither source uses ATT&CK. Since the escalation
ground truth keys off tactic, our mapping partly determines the metric it
scores — flagged `mitre_confidence: inferred` on every row.

---

## 2. Measurement caveats

**Prompt framing is not authentication.** A model reading "I am HF's IR team"
cannot verify that. No prompt-only framing is authentication, which is exactly
why the Responder Mode spec calls for an attestation layer rather than better
prompting.

**Single-run, text-only, English-only.** No multi-turn drift, no tool use, no
agentic scaffolds. Temperature 0, `n=3` on P0 experiments only.

**Provider-mediated, and the attribution is open.** All calls go through
OpenRouter. The filter finding held across three of that aggregator's provider
routes (auto, Anthropic direct, Amazon Bedrock) — but **route-invariance is the
signature of an aggregator-side filter, not evidence against one.** If a
moderation layer sits in OpenRouter's own stack ahead of every route it offers,
all three block identically, which is exactly what we saw. We did not test
Anthropic's first-party API, so **we do not know which layer imposes the
block, and we do not attribute it.** We report the measurement: requests to
these models, on this route, are blocked before generation. See
`PREREGISTRATION.md` §3a and its 2026-09-10 amendment.

**A model is not a model; it is a model as served by someone.** Serving stacks
differ in quantisation, default sampling, system-prompt injection and
moderation. Every table reports the provider alongside the model ID for that
reason.

**Production endpoints change without notice.** Model IDs and UTC timestamps
are logged for every call; results are a snapshot of 2026-09.

**LLM-as-judge is not sole judge.** Both raters hand-score a 60-item subsample
and report Cohen's κ before any bulk scoring. No headline number is decided by
a model alone.

**A filter is not a refusal.** Our rubric separates `filtered` (platform blocked
the request; 0 completion tokens; the model never saw it) from `refused` (the
model produced text declining to engage). Prior refusal benchmarks collapse
these. Conflating them would attribute to model judgment something no model
judged — and would have inflated our own headline.

**The safety-classifier contrast is one instrument, not a consensus.** We
report that `nemotron-3.5-content-safety` rates 10/10 of the prompts blocked
on the Claude route as safe, and we calibrate it first so the verdict is
interpretable. But `llama-guard-4-12b` and `gpt-oss-safeguard-20b` were
unaffordable, so we could not check whether other classifiers agree. Two
safety systems disagreeing tells you they have different policies; it does not
tell you which is correctly calibrated for this content, and we do not claim it
does.

**One of our own bugs is instructive and is disclosed:** at a 300-token budget,
GLM-5.2 spent 524 tokens on reasoning and returned empty content. Scored
naively that is a refusal. Any benchmark that does not separate `truncated`
from `refused` will systematically over-report refusal for reasoning models.
This bug class recurred three times in this project — GLM-5.2 in the smoke
test, the E3 monitor frame, and the safety classifier at a 200-token budget
where it returned empty on 3/10 prompts and a naive parser read that as "no
verdict". Each time the fix was budget, not interpretation.

---

## 3. What the pre-sprint work was

Per Apart's disclosure rule, see PREREGISTRATION.md §1. In short: the corpus
machinery, the harness client, the Wed-9 smoke test and its findings, and the
frozen rubric/pre-registration pre-date the sprint. Everything reported as an
experimental result is generated during it.

---

## 4. Dual-use considerations

**What this artifact contains.** An action-indexed, phase-labelled event stream
whose content is either (a) drawn from already-public post-mortems, or
(b) synthetic filler generated from a small bank of ordinary, widely-documented
administrative commands (`kubectl get pods`, `kubectl auth can-i`). It contains
**no working exploit code**, no payloads, no novel installation recipes, and no
credentials. The one credential-shaped string in it is the well-known
link-local IMDS address, which appears in vendor hardening documentation.

**What it is for.** SecureLayer7 publicly asked of this incident: *"which action
number does your control fire on?"* That question is unanswerable without a
replayable stream. HF said much the same: *"if any of that trace ever ships in a
form defenders can replay against their own stack… some of us would build
against it."* This corpus exists to make control-firing latency measurable.
Its intended users are defenders.

**Uplift assessment.** The offensive content is a chronological ordering of
techniques already documented in two vendor post-mortems, an OpenAI technical
report, and multiple public analyses. An attacker gains no capability from the
ordering that they do not already have from the sources. The genuine value-add
here — marginal-matched volume, ground-truth labels, an answer key — is useful
for *evaluating detectors*, not for conducting intrusions.

**What we withhold.** No novel installation recipe is released without review.
The attacker-framed prompt arm (E2's twin) is P2 and derives strictly from
already-public material; it never requests working exploit code. If provider
ToS concerns arise it is dropped without touching the headline.

**A finding with disclosure weight, stated at the width we can defend.** §3a
of the pre-registration reports that requests to Claude models *via OpenRouter*
are blocked before generation on defensive SOC triage prompts over a Kubernetes
audit log — including a pure "should I page the on-call?" monitor frame. We
report this as a measured, reproducible behaviour **of that access path**. We
deliberately do not name which layer imposes it, because route-invariance does
not distinguish an aggregator filter from a vendor one and we have not run the
first-party test that would. We do not characterise it as intentional, and we
note that over-blocking of defensive security work is a known and
actively-researched failure mode (*Defensive Refusal Bias*, arXiv 2603.01246),
not a novel accusation.

Naming a company for a block we cannot localise would be the kind of error this
appendix exists to prevent. The narrower claim is also the more useful one:
aggregators are how small defenders and under-resourced CSIRTs actually reach
frontier models, and a moderation layer the defender did not choose, cannot
configure and cannot see is itself an instance of the verification gap this
project is about.

**Responsible release.** Corpus, generator, prompts, rubric, and raw cached
responses are published so the numbers can be checked. API keys are gitignored
and were never committed.
