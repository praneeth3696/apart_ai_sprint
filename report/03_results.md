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

### 4.2 Models catch the incident and also page on the control (E1)

| model | provider | milestone hit (census) | benign false-page (uniform) | sep. | Fisher *p* |
|---|---|---|---|---|---|
| `gemini-3-flash-preview` | Google | 10/10 (100%, 72–100%) | 6/10 (60%, 31–83%) | +40% | 0.087 |
| `gemini-3.1-flash-lite` | Google | 12/12 (100%, 76–100%) | 11/12 (92%, 65–99%) | +8% | 1.000 |
| `gemini-3.5-flash` | Google | 6/6 (100%, 61–100%) | 5/7 (71%, 36–92%) | +29% | 0.462 |
| `gemini-3.5-flash-lite` | Google | 11/12 (92%, 65–99%) | 10/12 (83%, 55–95%) | +8% | 1.000 |
| `gemini-3.6-flash` | Google | 9/10 (90%, 60–98%) | 4/10 (40%, 17–69%) | +50% | 0.057 |
| `gemini-3.7-flash` | Google | 3/5 (60%, 23–88%) | 1/4 (25%, 5–70%) | +35% | 0.524 |
| `gemini-3.8-flash` | Google | 1/1 (100%, 21–100%) | — | — | — |
| `gemma-4-26b-a4b-it` | Google | 11/12 (92%, 65–99%) | 7/12 (58%, 32–81%) | +33% | 0.155 |
| `gpt-oss-120b` | Groq | 7/11 (64%, 35–85%) | 6/33 (18%, 9–34%) | +45% | **0.008** |
| `qwen3.8-27b` | Groq | 3/3 (100%, 44–100%) | 6/21 (29%, 14–50%) | +71% | **0.042** |

Intervals are Wilson 95%. **Pooled: milestone 73/82 (89%), benign false-page
56/121 (46%).**

Models find the incident — 89% of milestone-carrying windows produce a page —
and they also page on **46% of an innocent shift**. This is the E0 result
surviving contact with frontier models: `keyword_sigma`'s inability to separate
the streams is not an artefact of it being a crude rule.

**Significance: 2 of 10 models reach *p* < 0.05** on the milestone-versus-benign
contrast — `gpt-oss-120b` (*p* = 0.008) and `qwen3.8-27b` (*p* = 0.042), the two
models with the deepest benign sampling. **Eight do not**, and the two that do
are exactly the two we could afford to sample properly: they carry *n* = 33 and
*n* = 21 benign windows against *n* = 4–12 for the Google arm. That is a
statement about our budget, not about those models being different in kind — so
we report the **gradient across models** as the finding and do not dress a
*p* = 0.057 elsewhere as a result.

The gradient is not monotone in capability, which is the substantive point.
`gemini-3.1-flash-lite` scores a perfect 12/12 on milestones while paging on 11
of 12 benign windows — recall bought by paging on nearly everything, worth
nothing operationally. At the other end `gpt-oss-120b` reaches 7/11 at an 18%
false-page rate and `qwen3.8-27b` 3/3 at 29%. Figure 1 puts every detector on
one pair of axes; distance **above** the diagonal is the only thing on it worth
having, and several models sit close to it.

### 4.3 First-page latency is degenerate on this corpus (E1)

Every E0 detector fires at action **#15–51** of 17,613 — roughly 10,400 actions
before the escalation point at #10,498 — on filler that is byte-identical in
both streams. Any model with a non-zero false-page rate does the same.

On this corpus, therefore, **a first page measures trigger-happiness, not
detection.** We report Escalation Action Index for completeness (Figure 2) and
decline to headline it; the metric pair in §4.2 replaces it. This
reprioritisation is logged as a pre-registration amendment, and both metrics
are reported for every model, so nothing is hidden by the ordering.

### 4.4 The incoherence test returns its pre-registered null (E3)

| model | incoherence | escalated | refused to assist | McNemar *p* |
|---|---|---|---|---|
| `gpt-oss-120b` | **0/24** (0%, 0–14%) | 9/24 = 38% | 0/24 = 0% | 0.0001 |
| `gpt-oss-20b` | **0/21** (0%, 0–15%) | 7/21 = 33% | 0/21 = 0% | 0.0001 |

**Pooled: 0 of 45 scoreable cells are INCOHERENT.** No model in this roster
refused to analyse evidence it had just declined to escalate. This is the
pre-registered null and it is a result: the design commits in advance to E0+E1
carrying the paper in this branch, and refusal-driven incoherence is simply not
what these models do.

**But the two frames do not agree, and the asymmetry runs opposite to the
concern that motivated the test.** On byte-identical evidence, `gpt-oss-120b`
assists on **24/24** moments and escalates on **9/24**; `gpt-oss-20b` assists on
21/21 and escalates on 7/21. Every discordant pair falls the same way — 15 and
14 moments respectively where the model helped without paging, **zero** in the
reverse direction (McNemar exact, *p* = 0.0001 both).

The failure mode this study set out to find was a model that clams up in both
frames. What it measured instead is a model that will **explain an intrusion to
you in detail and not think it worth waking anyone over**. Under-escalation, not
refusal, is the safety-relevant behaviour here.

**What was excluded, and whether it was random.** Three moments on
`gpt-oss-20b` remain unscoreable as `truncated` even after re-running at a 3×
token budget — the model spent its entire budget on reasoning tokens and
emitted no content, which the rubric classes as our defect and never scores.
**These exclusions are not evenly spread across phases: two are `supply_chain`
and one is `k8s`.** Evidence length is identical across all 24 moments (10 rows
each), so prompt size does not explain it; the model simply reasoned longest on
the late-stage material. The residue therefore falls on the
higher-consequence phases — the direction that **flatters** the model, since
those are the moments where failing to escalate would matter most. We state it
rather than averaging over it.

### 4.5 Cost

**$0.00.** Every call ran on a free tier. The binding constraint was
throughput, not price: 10–31 requests per model per day on Google AI Studio,
1,000 on Groq, measured rather than assumed.
