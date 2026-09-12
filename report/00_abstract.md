# Fluent About the Intrusion, Silent on the Pager

## Abstract

Would an LLM on monitoring duty have paged the on-call during the July 2026
Hugging Face agent intrusion? We rebuilt it from the published timeline as a
replayable 17,613-action stream, generated a size-matched benign control,
verified blind that the two are not trivially separable, and ran ten models
across two providers past both, at $0.00.

Models catch the incident and cry wolf: 89% of milestone-carrying attack
windows produce a page (73/82), and so do 46% of innocent windows (56/121). A
keyword rule shows the same shape. Only 2 of 10 models separate the streams
significantly — the two we sampled deepest.

We then wrapped byte-identical evidence in a monitor frame and an assistant
frame. Incoherence was zero, but the frames disagreed in one direction: models
assisted on 45/45 moments while escalating on 16 (p=0.0001). The risk is not
refusal; it is fluent analysis with a silent pager.
