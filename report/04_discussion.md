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
