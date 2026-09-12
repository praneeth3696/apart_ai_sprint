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
Across the roster, 89% of milestone-carrying attack windows produce a page
(73/82) — and so do **46% of windows in an innocent shift** (56/121). A
15-line keyword rule shows the same pattern (67% against 28%), so this is not
a matter of models being crude; it is that the discriminating signal in this
corpus is thin, and recall bought by paging on everything is worth nothing.
The spread across models matters more than any single model's number: the best
discriminators reach 18% and 29% false-page rates while the worst pages on 11
of 12 benign windows for a perfect 12/12 recall. **Only 2 of 10 models separate
the streams significantly — and they are precisely the two we could afford to
sample deeply**, which makes the roster-wide gradient, not any single model's
*p*-value, the claim we stand behind.

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

**Contributions.** A replayable reconstruction of a real 2026 agent intrusion
with a validated matched control, released with the harness; a metric pair —
milestone hit rate against benign false-page rate — replacing a first-page
latency we show is degenerate here; non-LLM rule baselines on the same axes, so
the model numbers are interpretable at all; and the two-frame incoherence test
at K=24, which returns its pre-registered null and an unexpected significant
asymmetry.

---

[1] Hugging Face, *Agent intrusion: technical timeline*.
`https://huggingface.co/blog/agent-intrusion-technical-timeline`
