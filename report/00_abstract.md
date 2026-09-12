# Fluent About the Intrusion, Silent on the Pager

## Abstract

Would an LLM on monitoring duty have paged the on-call during the July 2026
Hugging Face agent intrusion? We rebuilt the incident from its published
timeline as a replayable 17,613-action stream, generated a size-matched benign
control, verified blind that the two are not trivially separable, and ran nine
models across two providers past both — at $0.00.

Models catch the incident and cry wolf. 90% of milestone-carrying attack
windows produce a page (66/73); so do 54% of innocent windows (50/92). A
keyword rule shows the same shape, and no model reaches significance at our
sample sizes.

We then wrapped byte-identical evidence in a monitor frame and an assistant
frame. Incoherence was zero — but the frames disagreed sharply and in one
direction: models assisted on 45/45 moments while escalating on 16
(p=0.0001). The risk is not refusal; it is fluent analysis with a silent pager.
