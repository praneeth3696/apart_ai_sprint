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
