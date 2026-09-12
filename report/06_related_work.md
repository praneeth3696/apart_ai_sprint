## 2. Related Work

**The incident.** Our substrate is a reconstruction of the July 2026 Hugging
Face agent intrusion, built from two independently-fetched primary sources: HF's
own technical timeline [1] and OpenAI's 38-page incident report [2]. Both were
retrieved and cross-checked on 2026-09-04; where their published tables
disagree we carry the disagreement rather than resolving it silently
(Methodology §3.1). Everything offensive in our corpus is downstream of those
two documents.

**Why a replayable stream.** The question this paper answers was asked publicly
of that incident by practitioners — *"which action number does your control
fire on?"* — and it is unanswerable against a prose timeline. Post-incident
write-ups are narrative; detection latency is a function of an ordered event
stream. Converting the former into the latter, with ground-truth labels and a
matched control, is the contribution that makes the rest measurable.

**Refusal benchmarks and what they do not measure.** Existing security-refusal
evaluations score a model's willingness to engage with security content, and
typically collapse *refused* and *filtered* into one category. We separate them
(Methodology §3.6), because our own earlier measurement found the dominant
non-response mode on defensive SOC prompts to be a platform filter blocking the
request before generation — zero completion tokens, no model judgment involved.
Over-blocking of defensive security work is a known and actively-researched
failure mode rather than a novel observation [3].

Two things distinguish what we measure from that literature. First, refusal
benchmarks have no **matched benign control**, so they cannot report
selectivity — and selectivity, not willingness, turns out to be where these
models fail. Second, and more directly: **refusal was not the failure mode we
found at all.** In 45 scoreable moments, not one model declined to analyse
evidence. A benchmark measuring only the refusal axis would have recorded a
clean sheet and missed the finding entirely.

**Non-LLM baselines.** We include three rule detectors (severity oracle, volume
spike, keyword/Sigma set) on the same axes as the models, because a page rate
without a comparator is uninterpretable. This follows standard detection-
engineering practice rather than any specific prior system; the point is that
the comparison is cheap and that omitting it makes the model numbers unreadable.

> **Note for revision.** The claims in the third and fourth paragraphs about
> what existing security-refusal benchmarks do and do not report are stated
> from our own reading and are **not yet backed by specific citations**. Before
> submission, either attach named benchmarks or soften to "to our knowledge".
> Named prior work is the one thing in this report not sourced to a document in
> the repository. See `report/README.md`.

---

[1] Hugging Face, *Anatomy of a Frontier Lab Agent Intrusion: A Technical
Timeline of the July 2026 Incident*, 2026-07-27.
`https://huggingface.co/blog/agent-intrusion-technical-timeline`

[2] OpenAI, *Hugging Face Incident Technical Report*, 38pp.
`https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf`

[3] *Defensive Refusal Bias*, arXiv:2603.01246.
