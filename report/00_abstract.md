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
