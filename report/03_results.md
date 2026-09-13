## 4. Results

All numbers below are read from the generated results file, which is rebuilt
from the raw per-window decision log after every run. Non-observations
(`unaffordable`, `quota_exhausted`, `error`, `truncated`) are excluded from
every denominator: they record that we could not buy the observation, not that
a model did anything.

### 4.1 Rule baselines set the bar (E0)

| detector | milestone hit | benign false-page | first page |
|---|---|---|---|
| `sev_threshold` **(ORACLE)** | 12/12 = 100% | 0/1280 = 0% | action #15 |
| `volume_spike` | 1/12 = 8% | 15/1280 = 1.2% | action #15 |
| `keyword_sigma` | 8/12 = 67% | 361/1280 = 28% | action #51 |

`sev_threshold` reads ground-truth severity. **It is an ORACLE — the upper
bound for a detector that already knows the answer — and is not deployable.**
It is in the table to bound the problem, not to compete.

The two real detectors bracket the difficulty. `volume_spike` keeps a 1.2%
false-page rate but catches **1 of 12** milestone windows: it is quiet and
blind. `keyword_sigma` catches 8 of 12 but fires on **28% of the benign
control** — it cannot tell the two streams apart, which is the finding, and it
is what makes the model numbers interpretable.

### 4.2 Models fail in both directions (E1)

| model | provider | milestone hit (census) | benign false-page (uniform) | Fisher *p* |
|---|---|---|---|---|
| `gemini-3.1-flash-lite` | Google | 12/12 (100%, 76–100%) | **11/12 (92%, 65–99%)** | 1.000 |
| `gemini-3.5-flash-lite` | Google | 11/12 (92%, 65–99%) | 10/12 (83%, 55–95%) | 1.000 |
| `gemini-3.5-flash` | Google | 6/6 (100%, 61–100%) | 5/7 (71%, 36–92%) | 0.462 |
| `gemini-3-flash-preview` | Google | 10/10 (100%, 72–100%) | 6/10 (60%, 31–83%) | 0.087 |
| `gemma-4-26b-a4b-it` | Google | 11/12 (92%, 65–99%) | 7/12 (58%, 32–81%) | 0.155 |
| `gemini-3.6-flash` | Google | 9/10 (90%, 60–98%) | 4/10 (40%, 17–69%) | 0.057 |
| `qwen3.8-27b` | Groq | 10/12 (83%, 55–95%) | 11/36 (31%, 18–47%) | **0.002** |
| `gemini-3.7-flash` | Google | 3/5 (60%, 23–88%) | 1/4 (25%, 5–70%) | 0.524 |
| `gpt-oss-120b` | Groq | 7/12 (58%, 32–81%) | 7/36 (19%, 10–35%) | **0.024** |
| `gpt-oss-20b` | Groq | 2/12 (17%, 5–45%) | 4/33 (12%, 5–27%) | 0.650 |
| `ministral-14b` | Mistral | 1/12 (8%, 1–35%) | 0/36 (0%, 0–10%) | 0.250 |
| `ministral-8b` | Mistral | **0/12 (0%, 0–24%)** | 0/36 (0%, 0–10%) | 1.000 |
| `ministral-3b` | Mistral | **0/12 (0%, 0–24%)** | 0/36 (0%, 0–10%) | 1.000 |
| `gemini-3.8-flash` | Google | 1/1 (100%, 21–100%) | — | — |
| `qwen3.6-27b` | Groq | 1/1 (100%, 21–100%) | 0/3 (0%, 0–56%) | 0.250 |

Intervals are Wilson 95%, ordered by false-page rate. The last two rows carry
*n* = 1: `gemini-3.8-flash` exhausted its 20-request daily cap, and
`qwen3.6-27b` rejects the E1 prompt as too large. **They are listed because
omitting them would be selective reporting, not because they support
anything.**

**The distribution is bimodal, and that is the result.** Pooled across models
the numbers are 84/141 (60%) on milestones and 66/283 (23%) on benign windows —
but **the pooled figure describes no model in the study.** It is the average of
a monitor that pages on 92% of an innocent shift and one that pages on nothing
at all, and reporting it alone would hide the finding rather than state it.

At one end, `gemini-3.1-flash-lite` achieves a perfect 12/12 milestone recall by
paging on **11 of 12 benign windows**. Its recall is free and worth nothing: a
pager that always fires carries no information.

At the other, `ministral-3b` and `ministral-8b` page on **nothing at all** —
0/12 milestones and 0/36 benign windows. This is not a parsing artefact; both
return well-formed verdicts with severity ratings and reasoning. They simply
read the intrusion as an operations problem. On the window containing the first
sandbox RCE, `ministral-8b` returns *"normal operational activity… no signs of
errors, security risks"*; on a window where Python processes jump 16→256 during
credential-access reconnaissance, *"resource contention or scaling issues."*
**A monitor that never pages has a perfect false-page rate**, which is precisely
why false-page rate cannot be read without recall beside it.

Only two models separate the streams at *p* < 0.05: `qwen3.8-27b` (10/12 against
31%, *p* = 0.002) and `gpt-oss-120b` (7/12 against 19%, *p* = 0.024). **Thirteen
do not.** Those two are also the models we could sample most deeply (*n* = 36
benign against *n* = 4–12 for the Google arm), so **significance here tracks
sampling budget as much as model behaviour** and we do not present it as a
ranking.

Figure 1 places every detector and every rule baseline on one pair of axes.
The useful region is the **top-left** — high recall, low false-page — and it is
empty. Models spread instead along and above the diagonal at the trigger-happy
end, or collapse into the bottom-left corner with the blind ones.

Capability does not order this. `gpt-oss-120b` discriminates while
`gpt-oss-20b` — same family, same provider, same serving stack — catches 2 of
12 milestones. Within Mistral the 3b, 8b and 14b models are near-identical and
all near-silent. **Scale did not buy selectivity in either family.**

### 4.3 First-page latency is degenerate on this corpus (E1)

Every E0 detector fires at action **#15–51** of 17,613 — roughly 10,400 actions
before the escalation point at #10,498 — on filler that is byte-identical in
both streams. Any model with a non-zero false-page rate does the same.

On this corpus, therefore, **a first page measures trigger-happiness, not
detection.** We report Escalation Action Index for completeness (Figure 2) and
decline to headline it; the metric pair in §4.2 replaces it. This
reprioritisation is logged as a pre-registration amendment, and both metrics
are reported for every model, so nothing is hidden by the ordering.

**The pre-registered negative-lead-time result.** We committed in advance to
reporting this whichever way it came out, because it is unflattering to the
whole framing of escalation latency. The ground-truth escalation point — the
first sourced pivotal milestone, action #10,498 at 2026-07-11 17:47:30 UTC —
falls **51.4 hours *after* the first exfiltration action** (#1,894, 07-09
14:21). Exfiltration is not the thing a perfectly-calibrated detector gets
ahead of on this incident; by the time the escalation criterion is satisfiable
at all, data has been leaving for more than two days.

Lead time to admin/host-level access is **+10.0 h**, so the criterion is not
useless — it is early for the privilege-escalation milestone and hopelessly
late for the exfiltration one. This is a property of the published phase
windows rather than a defect in the rule, and we declined to reselect a rule
that produces a prettier number.

The two facts in this section compound rather than cancel. The rule that
*should* fire is already 51 hours too late for exfiltration; the detectors that
beat it to the punch do so only by firing on action #15 of 17,613, on filler
identical in both streams. **Neither "page early" nor "page correctly" is
achieved by anything we measured.**

### 4.4 The incoherence test: a null, and a strong asymmetry (E3)

Eleven models across **three providers and five families**, 228 scoreable
moments on byte-identical evidence.

| model | incoherence | escalated | assisted | McNemar *p* |
|---|---|---|---|---|
| `gemini-3.6-flash` | 0/10 | 9/10 (90%) | 10/10 | 1.000 |
| `gemini-3.1-flash-lite` | 0/24 | 21/24 (88%) | 24/24 | 0.250 |
| `gemini-3.5-flash-lite` | 0/24 | 14/24 (58%) | 24/24 | **0.002** |
| `gemma-4-26b-a4b-it` | 0/24 | 14/24 (58%) | 24/24 | **0.002** |
| `qwen3.6-27b` | 0/5 | 2/5 (40%) | 5/5 | 0.250 |
| `gpt-oss-120b` | 0/24 | 9/24 (38%) | 24/24 | **0.0001** |
| `gpt-oss-20b` | 0/21 | 7/21 (33%) | 21/21 | **0.0001** |
| `qwen3.8-27b` | 0/24 | 6/24 (25%) | 24/24 | **<0.0001** |
| `ministral-14b` | 0/24 | 1/24 (4%) | 24/24 | **<0.0001** |
| `ministral-8b` | 0/24 | 0/24 (0%) | 24/24 | **<0.0001** |
| `ministral-3b` | 0/24 | 0/24 (0%) | 24/24 | **<0.0001** |

**Incoherence is zero — 0 of 228.** The pre-registered null holds across every
model, family and provider we could reach. **Not one model, on any moment,
refused to analyse evidence it had just declined to escalate.** The design
commits in advance to E0+E1 carrying the paper in this branch; that commitment
is honoured, and the null is reported as a result.

**The frames disagree, overwhelmingly and in one direction.** Every model
assisted on **228/228** moments. They escalated on **83/228 (36%)**. Every
discordant pair in the entire experiment falls the same way — the model helped
without paging — and the `tension` cell (escalates but will not help) is
**empty across all eleven models**. Seven of eleven are individually
significant at *p* < 0.05.

The failure mode this experiment was built to detect was a model that clams up
in both frames. What it measured is the mirror image: **a model that will
explain an intrusion to you in detail and not think it worth waking anyone
over.** Under-escalation, not refusal, is the safety-relevant behaviour here.

**The two findings reconcile rather than conflict.** The weakest E3 arms are
the strongest E1 cry-wolf models: `gemini-3.1-flash-lite` escalates on 21 of 24
moments and is not individually significant — but it is the same model that
bought 12/12 recall by paging on 11 of 12 innocent windows. **A model that
pages on nearly everything has no headroom to show an escalation deficit.** Its
high escalation rate is a symptom of §4.2, not a counterexample to this
section. Conversely the Mistral models, which page on nothing in E1, escalate
on 0–4% here while assisting on all 72 of their moments — the same behaviour
seen from the other side.

**What was excluded, and whether it was random.** Three `gpt-oss-20b` moments
remain `truncated` after a 3× budget re-run — two `supply_chain`, one `k8s`.
Evidence length is identical across all 24 moments, so prompt size does not
explain it; the model reasoned longest on the late-stage material. **The residue
is not evenly spread across phases** and falls on the higher-consequence ones,
the direction that flatters the model. A further 41 moments (`allam-2-7b`
entirely, most of `qwen3.6-27b`) were lost to a network outage and a
per-request size limit respectively; both are infrastructure, not behaviour,
and both are excluded rather than imputed.

### 4.5 Cost

**$0.00.** Every call ran on a free tier. The binding constraint was
throughput, not price: 10–31 requests per model per day on Google AI Studio,
1,000 on Groq, measured rather than assumed.
