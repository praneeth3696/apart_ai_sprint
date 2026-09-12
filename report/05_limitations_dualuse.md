## Appendix A — Limitations and Dual-Use Considerations

### A.1 What this study cannot establish

These were pre-registered before any model was run, and are reproduced with
what the run actually taught us added.

**The corpus is a reconstruction, not a capture.** Claims are about model
behaviour on a faithful scaffold built from published figures, not about what
Hugging Face's stack would have done. The generator is driven by the source's
own counts, phase boundaries and milestone timestamps, but **75% of the corpus
(13,163 actions across recon and dropper) carries no sourced milestone** — it
is filler obeying published marginals. A model's behaviour on that filler is
behaviour on our generator, not on the incident.

**The two published source tables disagree** (16,521 vs 17,613 actions). We
took the daily-volume total as authoritative and carried the 1,092-action
remainder as an explicit `unclassified` residual. A different resolution would
shift the denominators slightly.

**Prompt framing is not authentication.** A model reading "you are the triage
layer" cannot verify that. Everything here measures response to a *claimed*
role.

**Single-run, single-turn, text-only, English-only.** No temperature sweep, no
multi-turn drift, no tool use, no repeated sampling. Every number is one draw
at temperature 0. A model that pages 40% of the time might page 60% on a
re-run, and we have not measured that variance.

**Statistical power is the dominant limitation, and it is not evenly
distributed.** Per-cell *n* is 4–36, intervals overlap heavily, and **no model
reaches *p* < 0.05** on stream separation. The gradient across models is the
reportable claim; no individual model's separation is established. The Google
arm is the thinnest: free-tier caps of 10–31 requests per model per day meant
several Gemini models contribute *n* = 1–12 and one contributes a single
window. **Those rows are in the table because omitting them would be
selective reporting, not because they support a conclusion.** The sampling
ladder makes widening purely additive, so this is a resource limitation rather
than a design one.

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

**Provider serving stacks are a confound we can bound but not remove.** A model
is a model *as served by someone*: quantisation, default sampling, system-prompt
injection and moderation layers all differ. We report the provider beside every
model ID and keep the two providers as separate arms. The `gpt-oss-20b` vs
`gpt-oss-120b` contrast is the one comparison here that is clean, because both
run on one stack.

**Frontier proprietary models are absent.** The Gemini Pro tier returns
`limit: 0` on the free tier — refused, not throttled — and no GPT- or
Claude-class model was reachable at $0. The frontier arm is therefore
"frontier-flash", not frontier.

### A.2 Dual-use considerations

**What is in the artefact.** A generated action stream reconstructing a
publicly documented intrusion, a benign control, a monitor-frame harness, and
scoring code. The corpus contains synthetic log lines describing attacker
behaviour at the level of abstraction the published timeline already uses —
phase names, host roles, event descriptions, timestamps.

**What is not in it, deliberately.** No working exploit, no payload, no
credential, no novel installation recipe, and no technique not already in the
public source. The corpus is a *detection* substrate: it describes what an
intrusion looked like in a log, not how to perform one. Every attack step is
downstream of a vendor's own published post-incident write-up.

**The realistic misuse path, and why we judge it low.** Someone could read the
corpus as a checklist of what a real agent intrusion looked like. That
information is already public in the source we cite, in more operational
detail than our reconstruction carries. We add no capability; we add a
benchmark.

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
