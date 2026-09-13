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

**Refusal benchmarks and what they do not measure.** A mature literature
measures *over-refusal*: XSTest [3] and OR-Bench [4] both build prompts that
look unsafe but are benign, and score models on wrongly declining them.
Meta's CyberSecEval line carries the same axis into security specifically as a
False Refusal Rate [5], and Gray Swan's refusal framework [6] evaluates where
an agent *should* decline offensive-security requests. Closest to our setting,
*Defensive Refusal Bias* [7] ran 2,390 real cyber-defence competition prompts
and found security keywords refused at **2.72x** the rate of neutral phrasing,
with explicit authorisation *increasing* refusal (21.8% vs 11.6%) rather than
licensing the work. Over-blocking of defensive security work is therefore a
known and actively-researched failure mode, not a novel observation — and we
separate *refused* from *filtered* (Methodology 3.6) because our own earlier
measurement found the dominant non-response mode to be a platform filter
blocking the request before generation: zero completion tokens, no model
judgment involved.

**Refusal was not the failure mode we found.** In 45 scoreable moments, not one
model declined to analyse the evidence. A benchmark measuring only the refusal
axis would have recorded a clean sheet and missed the finding entirely. What we
observe is the opposite defect: the model engages fluently and *does not
escalate*. That axis — whether the model raises an alarm, not whether it is
willing to talk — is the one these benchmarks do not score.

**Incident-response benchmarks.** Evaluating agents on real incident substrate
is an active area. SecRespond [8] gives agents forensic disk snapshots from ten
compromised cloud hosts and scores forensic reports and remediation plans;
SIR-Bench [9] replays authentic incident patterns as cloud telemetry across 794
test cases to measure investigation depth; CyberSOCEval [10] scores incident
investigation, summarisation and severity rating on SOC data. Our substrate
differs in being a *public-report reconstruction* — reproducible from two cited
documents with no proprietary telemetry (Limitations 2) — and our unit of
analysis differs in being the per-window page/don't-page decision over an
ordered stream, which is what makes detection latency measurable at all.

Two things distinguish what we measure. First, **the matched benign control.**
SIR-Bench does score false-positive rejection (73.4% for its baseline agent) on
labelled false alerts, so a false-alarm axis is not unprecedented; what we add
is a *time-matched benign stream built by the same generator as the attack
stream*, which lets us report a page rate on windows containing no intrusion at
all and so measure selectivity rather than rejection of pre-labelled decoys. To
our knowledge no prior benchmark pairs an incident replay with such a control.
Second, **frame sensitivity on byte-identical evidence** — holding the evidence
fixed and varying only whether the model is addressed as the triage layer or as
an analyst's assistant. We are not aware of prior work isolating that variable
on security-escalation decisions.

**Non-LLM baselines.** We include three rule detectors (severity oracle, volume
spike, keyword/Sigma set) on the same axes as the models, because a page rate
without a comparator is uninterpretable. This follows standard detection-
engineering practice rather than any specific prior system; the point is that
the comparison is cheap and that omitting it makes the model numbers unreadable.

---

[1] Hugging Face, *Anatomy of a Frontier Lab Agent Intrusion: A Technical
Timeline of the July 2026 Incident*, 2026-07-27.
`https://huggingface.co/blog/agent-intrusion-technical-timeline`

[2] OpenAI, *Hugging Face Incident Technical Report*, 38pp.
`https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf`

[3] P. Rottger, H. R. Kirk, B. Vidgen, G. Attanasio, F. Bianchi, D. Hovy,
*XSTest: A Test Suite for Identifying Exaggerated Safety Behaviours in Large
Language Models*, NAACL 2024. arXiv:2308.01263.

[4] J. Cui, W.-L. Chiang, I. Stoica, C.-J. Hsieh, *OR-Bench: An Over-Refusal
Benchmark for Large Language Models*. arXiv:2405.20947.

[5] M. Bhatt et al., *CyberSecEval 2: A Wide-Ranging Cybersecurity Evaluation
Suite for Large Language Models*. arXiv:2404.13161. (False Refusal Rate.)

[6] E. K. Jones, M. Dziemian, M. Fredrikson, J. Z. Kolter, *A New Framework for
Cybersecurity Refusals in AI Agents*. arXiv:2606.02644.

[7] D. Campbell, N. Kale, U. M. Sehwag, B. Herring, N. Price, D. Borges,
A. Levinson, C. Q. Knight, *Defensive Refusal Bias: How Safety Alignment Fails
Cyber Defenders*. arXiv:2603.01246.

[8] L. Wang et al., *SecRespond: Benchmarking AI Agents for Real-World
Post-Compromise Incident Response*, 2026-07-29. arXiv:2607.26791.

[9] D. Begimher, C. Leo, J. Huang, P. Gaw, B. Zheng, *SIR-Bench: Evaluating
Investigation Depth in Security Incident Response Agents*, 2026-04-13.
arXiv:2604.12040.

[10] L. Deason et al. (Meta / CrowdStrike), *CyberSOCEval: Benchmarking LLMs
Capabilities for Malware Analysis and Threat Intelligence Reasoning*.
arXiv:2509.20166.

[11] S. Tariq, M. Baruwal Chhetri, S. Nepal, C. Paris, *Alert Fatigue in
Security Operations Centres: Research Challenges and Opportunities*, ACM
Computing Surveys 57(9), Article 224, April 2025. doi:10.1145/3723158.
