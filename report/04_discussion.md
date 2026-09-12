## 5. Discussion

**Recall is the easy half**, and selectivity is where the roster separates —
not monotonically in capability. **Deploying on recall alone would select the
worst detector here.** Note also which models cleared significance: the two
with the deepest benign sampling, not the two most capable. Sampling depth and
selectivity are confounded, and we say so rather than reading a capability
story into it.

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
