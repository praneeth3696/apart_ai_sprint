# SPRINT_PLAN.md — the execution plan, Fri 11 → Sun 13 Sep 2026

**Written Thu 10 Sep 2026.** This is the *execution* plan. It supersedes
`TIMELINE.md` §2–4 and `PLAN.md` §1–2 (scheduling, roles, run sizing).
It does **not** supersede `PREREGISTRATION.md` or `prompts/RUBRIC.md` — those
are frozen and stay frozen.

Two people. `A` = **Amirtha** (corpus & ground truth). `B` = **Praneeth**
(providers, runs, analysis, report).

---

## PART 0 — Six corrections to make before you write another line of code

These are things I found that are wrong or missing in the current repo. Fix
these first; three of them can cost you the prize.

### 0.1 The track numbers in the repo are wrong

`IDEA.md` says "Primary Track 2 (Incident Analysis & Warning Shot Insights) ×
Secondary Track 5". The live sprint page lists five different tracks:

| # | Track | Its stated judging criterion |
|---|---|---|
| 1 | **Containment Standards** | *"Verifiability without lab network access; realistic lab adoption"* |
| 2 | **Incident Reconstruction & Forecasting** | *"Resolvable questions, actionable checks, predictive causal explanations"* |
| 3 | Regulatory Response | Legal precision; usable with minimal editing |
| 4 | Communication & Warning Shots | Primary-source grounding; demonstrated reach |
| 5 | Open Track | Usable artifact; stated limitations; clear follow-up roadmap |

**Decision: submit to Track 2.** Its criterion is a word-for-word description
of what we produce — "actionable checks" is literally the false-page rate and
the EAI leaderboard.

**In the abstract, name the Track 1 crossover explicitly.** Track 1 is judged
on *"verifiability without lab network access."* A replayable action stream
reconstructed entirely from public figures is exactly an instrument for
verifying a containment control without touching the lab's network. Saying
that sentence out loud gets us read favourably by two sets of judges instead
of one. (Track 5's criterion — usable artifact, stated limitations, follow-up
roadmap — we also satisfy, but don't claim three tracks; it reads as hedging.)

### 0.2 The Anthropic filter finding is probably mis-attributed — verify it Friday

`PREREGISTRATION.md` §3a treats **route-invariance** as evidence that the block
is Anthropic's:

> "The block is **not route-specific**: identical via OpenRouter auto-route,
> `Anthropic` direct, and `Amazon Bedrock`."

Route-invariance is the **signature of an aggregator-side filter**, not
evidence against one. If OpenRouter's own moderation layer sits in front of
every route, then auto / Anthropic-direct / Bedrock all block identically —
which is exactly what you observed. OpenRouter documents both an input-side
block (HTTP 403 on flagged prompts) and provider-level output moderation, and
routes requests through its own stack in all three cases.

Two further tells that point the same way:

- Anthropic's **first-party** API signals a model-side decline as
  `stop_reason: "refusal"`, not an OpenAI-style `finish_reason:
  "content_filter"` with zero completion tokens. The signature you logged is
  the aggregator's vocabulary, not Anthropic's.
- Opus 5 read this entire corpus — IMDS curl line, privileged-pod apply,
  `system:masters` chain and all — inside a normal Claude session on
  2026-09-10 and analysed it without hesitation. That is informal, but it is
  hard to square with "Anthropic blocks this content."

**Why this matters more than any other item on this page.** "Anthropic's safety
filter blocks defenders from investigating a real intrusion" is the most
quotable sentence in the draft. If it is actually OpenRouter's filter, a judge
who knows the API surface will spot it, and the whole report's credibility goes
with it. Conversely, correctly attributed it is *still* a strong finding —
arguably a better one, because aggregators are how small defenders and
under-resourced CSIRTs actually reach frontier models, and a moderation layer
they didn't choose is precisely a verification-gap story.

**Friday, first hour, B owns it.** Run the byte-identical prompt through, in
order of preference:
1. Anthropic first-party API (`api.anthropic.com`) if any key or trial credit
   can be obtained.
2. Any non-OpenRouter route to any Claude model.
3. Failing both: the same prompt pasted into a first-party Claude surface
   (claude.ai or Claude Code), screenshotted, reported explicitly as
   *qualitative, non-API evidence*.

Then rewrite §3a to whichever of these three claims survives:
- **(a)** first-party answers, OpenRouter blocks → *"An aggregator moderation
  layer, not the model, blocks defensive SOC triage."* Strongest and cleanest.
- **(b)** first-party also blocks → the original claim stands and is now
  properly established. Even better.
- **(c)** untestable → *"Requests to Claude models via OpenRouter are blocked
  with `finish_reason=content_filter` and zero completion tokens. We could not
  determine which layer imposes the block, and we do not attribute it."*

Option (c) is an honest, publishable claim. Do **not** ship the current wording
un-retested.

### 0.3 The call budget does not close — this is the #1 schedule risk

`PLAN.md` §3 wants ~250 windows. `PREREGISTRATION.md` §8a lists 11 models. E1
runs two streams. That is:

```
250 windows × 2 streams × 11 models = 5,500 calls   (E1 alone)
```

OpenRouter's free tier is rate-limited at roughly **20 requests/minute**, with
a **daily cap that depends on lifetime credit purchased** — on the order of
~50/day for an account that has never funded, ~1000/day above a small
threshold. The repo's account is unfunded and running a negative balance.

**At 50 calls/day, the entire study is 110 days of work.** At 1000/day it is
5.5 days. Neither fits a weekend. Rate limits, not money, are the binding
constraint, and the current plan has no number attached to them.

**Fix, in three parts:**

1. **Measure the real cap before designing the run** (B, Friday hour 1 — see
   §1.1). Everything downstream is sized from that one number.
2. **Broaden the provider pool tonight** (§0.4). Four free providers at
   200–1000 req/day each is a different project from one provider at 50.
3. **Cut the run to fit, by stratified sampling, not by praying.** See §2.

### 0.4 Provider acquisition is tonight's job, not Friday's — and it can restore the frontier arm

`PREREGISTRATION.md` §8c calls this *"worth pursuing before Friday (would
materially strengthen the study)"* and then nobody did it. It is the single
highest-leverage two hours available to this project, because it converts
"we tested 11 obscure free models" into "we tested a frontier model and an
open-weight tier" — and it is Dimension 1 (Impact & Innovation) points, not
just Dimension 2.

Do these tonight, Thursday, in this order. Each is a signup + one curl.

| Provider | What it gets you | Why it's worth the 20 minutes |
|---|---|---|
| **Google AI Studio** | A genuine **frontier arm** (Gemini) at $0, with a free-tier RPD in the hundreds–thousands | Highest value by a wide margin. Restores frontier-vs-open comparison to E4. |
| **GitHub Models** | GPT-class + others, free with the GitHub account this repo already uses | The incident's protagonist family is GPT-class. Having *any* GPT-class arm is a large credibility win. |
| **Groq** | Open-weight models, very high throughput, generous free RPD | Solves the E1 volume problem on its own. |
| **Cerebras** | Same shape as Groq | Redundancy against a 429 wall on Saturday. |
| **Mistral** | European frontier-ish, free tier | Cheap diversity. |
| **Ollama (local, on the Mac)** | Unlimited, deterministic, zero rate limit, works offline | Guarantees the capability-floor arm exists no matter what any provider does on Saturday. Also your rate-limit insurance for re-runs. |

**Record for each: what you got, RPM, RPD, and the date/time you measured it.**
Anything that works gets a timestamped amendment in `PREREGISTRATION.md` §9,
per the rules that document sets for itself.

**Hard rule that does not change:** anything that requires a card is out. The
study stays at $0.00 and that fact stays in the abstract.

### 0.5 You have more time than TIMELINE.md thinks

The deadline is **Sunday 13 Sep, 11:59 PM AoE**. AoE is UTC−12, so in IST that
is:

> **Monday 14 September, 5:29 PM IST.**

That is roughly **17 extra hours** beyond "Sunday night". Plan to **submit
Sunday night IST** anyway — resubmission with the identical title is explicitly
allowed and replaces your files — and treat Monday morning as the buffer that
absorbs one disaster. Do not spend the buffer in advance.

### 0.6 Report length is 8 pages maximum

The sprint page says *"8-page maximum research report (PDF) on official
template"*, and artifacts go in a **linked repository or appendix, not embedded
in the report**. `guidelines.txt` says "most strong projects are 4 to 8 pages" —
8 is the ceiling, not the target. Aim for 7 including references. Section 5 has
the page budget.

---

## PART 1 — Scope: what we are actually shipping

### 1.1 The experiment set (changed from PLAN.md)

| ID | Name | Status | Why |
|---|---|---|---|
| **E0** | **Rule-baseline detectors** | **NEW — added** | See §1.2. Costs $0 API, ~2h of code, and it is what turns every other number into a *finding*. |
| **E1** | Escalation latency + false-page rate | **P0, headline** | Unchanged, but resized (§2.3). |
| **E3** | Incoherence 2×2 | **P0, second result** | K reduced 40 → **24**. |
| **ER** | Reachability (filter/refusal) arm | **P0, promoted** | Was folded into other experiments; it's a standalone result and needs the §0.2 fix. |
| **E2** | Forensic assistance under refusal | **P1, cut down** | 6 families × 4 rungs × 2 framings is **48 prompts/model**, all needing hand-scoring. Cut to **3 families × 2 rungs × 2 framings = 12**. |
| **E4** | Effective Forensic Yield | **P1, free** | Derived from E2, no extra calls. |
| — | Attacker-mirror, fabrication rate, Responder Mode spec | **P2** | Cut freely from Saturday 21:00. |
| — | Anything interpretability | **CUT** | Do not start. Unchanged from PLAN.md. |

### 1.2 E0 — the addition that earns its place

**Run three non-LLM detectors over the exact same two streams:**

1. `sev_threshold` — page when a window contains any action whose
   `gt_severity` ≥ high. *(Cheating detector: it reads ground truth. It is the
   upper bound — "what if you already knew.")*
2. `volume_spike` — page when a window's action count exceeds *k*·(rolling
   median). Pure statistics, no semantics. **This is the detector HF's real
   stack most resembles.**
3. `keyword_sigma` — a hand-written ~15-rule keyword/regex set over the `event`
   text (IMDS address, `--as=system:`, `hostPath`, `privileged: true`,
   `kubectl exec`, token mint, tailscale up, …). This is a Sigma rule in
   spirit: what a competent SOC engineer writes in an afternoon.

Report EAI and false-page rate for each, on the same axes as the models.

**Why this is worth two hours.** Right now the paper can say *"model X pages at
window 12 with a 6% false-page rate."* A judge has no idea whether that is good.
With E0 it says:

> *"A fifteen-line keyword rule pages 40 windows earlier than the best model
> and at one-third the false-page rate. The LLM triage layer is not buying you
> detection — it is buying you a rate limit."*

or the reverse, which is equally publishable:

> *"Every rule baseline either misses the campaign entirely or pages on 30% of
> benign windows. Only the LLM arm separates them."*

Either sentence is a **finding**. Neither is available without the baselines.
It also directly answers SecureLayer7's *"which action number does your control
fire on?"* — the question the whole corpus exists to make askable — for a
control that is not a model. That is Track 1's criterion satisfied inside a
Track 2 paper, for two hours of work and zero API calls.

**B owns E0.** It reads `.jsonl` and writes JSON. It touches no provider, no
async code, and no corpus internals — a clean, self-contained first task.

### 1.3 The headline sentence you are hunting

Write these on paper now. Everything Friday and Saturday exists to fill one of
these blanks. If by Saturday 21:00 you cannot say one out loud with numbers in
it, stop running and start writing.

- **H-A (precision):** *"Across N models replaying a reconstructed 17,613-action
  intrusion, the median model paged at action ___ — ___ hours before
  cluster-admin — and also paged on ___% of matched benign windows. A
  fifteen-line keyword rule paged at action ___ with a ___% false-page rate."*
- **H-B (attribution):** *"Requests to page an on-call engineer about a
  Kubernetes audit log are blocked before reaching the model on ___ of ___
  attempts via a major API aggregator, while a purpose-built safety classifier
  rates 10/10 of the identical prompts safe."*
- **H-C (coherence):** *"On ___ of ___ matched incident moments, the same model
  shown the same bytes judged them not worth waking anyone for and too
  dangerous to discuss."*
- **H-D (the honest null):** *"The 2026 double failure does not reproduce on
  the models we could reach at zero cost: incoherence 0/___ , and every model
  paged. The gap has moved from escalation to precision — here is the eval that
  keeps it there."*

`PREREGISTRATION.md` §3b already tells you H-C is probably a null and H-A is
the live one. **That is fine and it is pre-registered.** The 5th-place team in
the last sprint won on "none of the three claims survived verification." Apart's
judges reward a claim you tested until it broke.

### 1.4 Numbers you already own (from the frozen pre-registration)

Put these in the report on Friday; they need no runs:

- Escalation ground truth resolves to `imds_credentials`, 2026-07-11T17:47:30Z.
- Lead time to admin/host-level access: **+10.0 h**.
- Lead time to first exfil: **−51.6 h** — *"even a perfectly-calibrated
  detector pages 51 hours after exfiltration has already begun."* This is the
  single best sentence currently in the repo and it costs zero API calls.
- These three figures were CORRECTED 2026-09-11 (PREREGISTRATION.md 9):
  a milestone sat in the wrong phase and was being dropped silently,
  which re-anchored the interpolated escalation timestamp. The rule,
  the milestone identity and every sign are unchanged; only the
  magnitudes moved.
- Phase table sums to 16,521; daily-volume table sums to 17,613; residual 1,092
  absorbed as `unclassified`. Publishing that reconciliation is itself a
  contribution — nobody else will have noticed the source contradicts itself.

---

## PART 2 — Roles and the seam between them

The seam is chosen so that **neither person ever blocks on the other's
uncommitted code.** A hands B `.jsonl` files. B hands A numbers. That's it.

### Person A — Amirtha — Corpus & Ground Truth

Owns everything under `corpus/`, plus report Methodology / Related Work /
Limitations.

| Deliverable | File | Definition of done |
|---|---|---|
| 9 remaining template banks + benign bank | `corpus/templates.py` | `PHASE_TEMPLATES` has all 10 keys + `BENIGN_TEMPLATES`; no filler carries a pivotal tactic; `pytest` green |
| Full-corpus merge | `corpus/build_corpus.py` | Writes `attack_stream.jsonl` (17,613 rows, global `action_idx` after global time-sort) |
| Benign baseline stream | same file | Writes `benign_stream.jsonl`, same hosts/tools/volume envelope, `gt_malicious=false` throughout |
| Full assertion suite | `corpus/test_prototype.py` | Extends the existing 17 assertions to the full corpus: 9 phase totals exact, 5 daily volumes exact, per-phase first/last, milestone ordering, pivotal-tactic ceiling, **no ground-truth field survives `render_for_model`** |
| Windowed sets | `corpus/windows/` | `attack_windows.json`, `benign_windows.json`, `e3_moments.json` (K=24) |
| Answer keys | `corpus/answer_keys/*.json` | For the 3 surviving E2 families only |
| Citations | `corpus/CITATIONS.md` | Every structural parameter → published source sentence. Already largely done; finish it. |
| Report prose | report | Methodology, Related Work, Limitations |

### Person B — Praneeth — Providers, Runs & Analysis

Owns `harness/`, `analysis/`, and the report's front half.

| Deliverable | File | Definition of done |
|---|---|---|
| Provider roster + measured limits | `harness/PROVIDERS.md` | Per provider: model IDs, RPM, RPD, measured when |
| First-party filter re-test (§0.2) | `harness/test_anthropic_surface.py` | One of the three claims in §0.2 is established, with evidence |
| Multi-provider client | `harness/client.py` | Existing cached client extended with a provider-router + backoff. **Do not rewrite it — it already handles caching, filter detection and 402.** |
| **E0 baselines** | `harness/e0_baselines.py` | Three detectors, EAI + false-page for each, output to `analysis/e0.json` |
| E1 runner | `harness/e1_escalation.py` | Adapt `e3_incoherence_smoke.py`'s monitor path; add rolling summary; cache-on-receipt |
| E3 runner | `harness/e3_incoherence.py` | Generalise the smoke test to K=24 × N models |
| E2 runner | `harness/e2_refusal.py` | 12 prompts × N models, P1 |
| Stats | `analysis/stats.py` | Wilson CI, McNemar, Cohen's κ |
| **Figure 1** | `analysis/figures/f1_eai.png` | The paper's front page (§4.1) |
| Report prose | report | Abstract, Intro, Results, figures, submission |

### Joint, both required (do not delegate these)

- **Fri +2h:** 20-window blind separability check on the benign stream.
- **Sat midday:** scoring calibration on 40 E2 items → Cohen's κ.
- **Sun midday:** the read-aloud pass. Every factual claim about the incident
  gets its primary source opened and checked live.
- **Sun:** the Limitations & Dual-Use appendix.

---

## PART 3 — The hour-by-hour

Clock shown as **T+h from sprint open**, with an IST wall clock assuming the
sprint opens Fri 11 Sep 18:00 IST. **Adjust the IST column if the open time
differs — the T+ column is what matters.**

### THURSDAY 10 SEP — tonight, ~2.5 hours, both of you

This is not optional prep. Two of these three items are on the critical path
for Friday morning.

| Who | Task | Time |
|---|---|---|
| **B** | **§0.4 provider run.** Sign up: Google AI Studio → GitHub Models → Groq → Cerebras → Mistral. One successful chat completion from each. Write `harness/PROVIDERS.md`. | 90 min |
| **B** | `ollama pull` two small models as offline insurance (e.g. an 8B and a 3B). | 15 min, runs unattended |
| **A** | Write **two** template banks — `recon` and `dropper` — as the pattern for the other seven. These two are 13,163 of the 17,613 actions, so getting their shape right matters most. | 45 min |
| **A** | Sanity-read `PREREGISTRATION.md` §3a against §0.2 above and decide what wording you are prepared to defend. | 15 min |
| **Both** | Read `PRIMER.md` (the companion doc). B reads all of it; A skims §6–8. | 30 min |
| **Both** | Download the official report template from the **Guidelines tab** (not from any acceptance email — the FAQ says acceptance-email templates are stale). Put it in the repo. | 10 min |

> **Disclosure discipline.** Everything done tonight is *tooling and account
> setup* — it produces no reported number. That keeps it inside
> `PREREGISTRATION.md` §1's disclosure line. If any of tonight's calls produces
> a number you want to report, it goes in §1 as pre-sprint work, explicitly.
> Undisclosed prior work is a disqualification risk; the sentence costs nothing.

---

### FRIDAY 11 SEP — build, and get E1 running before you sleep

**Exit condition: E1 is running unattended overnight.** Nothing else on Friday
matters as much. If T+8h arrives and E1 is not running, stop building anything
else and get it running.

| T+ | IST | A — Corpus | B — Runs |
|---|---|---|---|
| 0 – 1h | 18:00 | Finish `recon`/`dropper` banks; start the other 7 | **§1.1 rate-limit measurement.** Fire calls at each provider until you hit a wall. Record RPM/RPD. **Then and only then, fix N (models) and W (windows) for E1.** |
| 1 – 2h | 19:00 | All 10 attack banks done; `pytest` green | **§0.2 first-party filter re-test.** Settle the attribution question. Amend `PREREGISTRATION.md` §9 with a timestamp. |
| 2 – 4h | 20:00 | `build_corpus.py`: merge all phases, global time-sort, assign global `action_idx`, write `attack_stream.jsonl`. Assertions on phase totals + daily volumes + milestone order. | `e0_baselines.py` against `prototype_k8s.jsonl` first (it exists now), then re-point at the full stream when A lands it. **This is your warm-up and it is on the critical path for the paper's interpretation.** |
| 4 – 5h | 22:00 | **Benign stream.** Same hosts, same tools, comparable volume envelope, `gt_malicious=false`. | Extend `client.py` to route across providers with per-provider backoff. Keep cache-on-receipt exactly as it is. |
| 5 – 6h | 23:00 | **JOINT: blind separability check.** A prints 20 windows, 10 from each stream, shuffled, unlabelled. B labels them. If B gets >90%, the benign stream is trivially separable and the control is worthless — fix the templates, not the labels. Record the score; it goes in the report. | (same) |
| 6 – 7h | 00:00 | Window both streams. Emit `attack_windows.json`, `benign_windows.json`, `e3_moments.json` (K=24, stratified across phases — include exfil, supply_chain, tailscale, not just k8s) | `e1_escalation.py`: monitor loop, rolling summary, strict-JSON parse with the one re-ask from `RUBRIC.md` §1, cache-on-receipt |
| 7 – 8h | 01:00 | Draft Intro + Related Work into the template | **Smoke E1: 1 model × 20 windows × both streams.** Fix the JSON parsing that *will* break. |
| **8h** | **02:00** | — | **🚨 LAUNCH FULL E1 OVERNIGHT.** All models, both streams. This is the most important scheduling decision of the sprint. |

**Friday sizing rule.** Once you know the daily cap `C` and model count `N`:

```
windows_per_stream  =  (C_total_across_providers × 0.5)  /  (2 × N)
```

The 0.5 reserves half of Saturday's budget for E3, E2, and re-runs. If that
formula gives you fewer than 40 windows per stream, **cut models before you cut
windows** — a latency curve needs resolution more than it needs a wide roster.
Sample windows **stratified**: every milestone-carrying window, plus a random
sample of the rest, plus a benign sample matched on window size. Say so in the
Methodology; stratified sampling is a design choice, not a shortcut.

---

### SATURDAY 12 SEP — run, score, and get the number

**Exit condition: you can say a headline sentence out loud with a number in
it.** If you cannot by 21:00, cut E2/E4 and spend Sunday making E0+E1+E3
excellent.

| T+ | IST | A | B |
|---|---|---|---|
| 14 – 17h | 08:00 | Build the 12 E2 prompts (3 families × 2 rungs × 2 framings) + answer keys | Triage the overnight E1 run: failures, unparseables, empty cells. Re-run **gaps only** — the cache means this is cheap. Compute EAI, lead times, false-page rates + Wilson CIs. |
| 17 – 19h | 11:00 | Finish answer keys | **Launch E3 (K=24 × all models).** Then queue E2 behind it. |
| 19 – 21h | 13:00 | **JOINT: calibration.** Both independently score the same 40 E2 items on outcome / correctness / quality. Compute Cohen's κ per axis. If κ < 0.6, reconcile the rubric and re-score — and report the pre-reconciliation κ too. | (same) |
| 21 – 24h | 15:00 | Bulk-score E2; start fabrication counting (P2) | **Produce Figure 1.** Then Incoherence Rates + Wilson + McNemar. |
| 24 – 27h | 18:00 | Write the Results section around the numbers that now exist | EFY table. **Then hand-verify three headline numbers against three raw cached responses in `runs/`.** Every paper that gets caught has an unverified number in it. |
| **27h** | **21:00** | Draft `LIMITATIONS.md` in full | **🛑 HARD STOP ON API RUNS.** Sunday is writing. |

---

### SUNDAY 13 SEP — write, and stop building

| T+ | IST | A | B |
|---|---|---|---|
| 38 – 41h | 08:00 | Report body: Methodology → Results → Discussion | Finalise figures (F1 EAI chart, F2 2×2 heatmap, F3 EFY-vs-refusal scatter). Clean `harness/`. Write the reproduce-in-one-command block. |
| 41 – 43h | 11:00 | **Limitations & Dual-Use appendix**, in full. Plus the one-sentence pre-sprint disclosure. | README: headline sentence + Figure 1 **above the fold**. Purge any secrets from `runs/`. Add a licence. |
| 43 – 45h | 13:00 | **Abstract, ≤150 words.** Write it last. Cut it twice. Must contain: the headline number, the word "reconstruction", the $0 constraint, and the Track 1 crossover sentence. | `responder_mode/SPEC.md` — **P2, only if everything above is done** |
| 45 – 46h | 15:00 | **JOINT: read the PDF aloud to each other, once, end to end.** Open the primary source for every factual claim about the incident, live. Fix the three things you find. | (same) |
| 46 – 47h | 16:00 | Final checklist (§6) | Optional 3–5 min video — **only** if P0+P1 are complete |
| **47h** | **17:00** | — | **SUBMIT.** |

**Sunday's only rule:** no new experiments after Saturday night, no matter how
good the idea is. You can resubmit with the identical title until 5:29 PM IST
Monday. Ship first, refine after.

---

## PART 4 — Presentation: the third of the score that is cheapest to max

Dimension 3 is worth as much as Execution and is almost free. Judges read the
README before the PDF.

### 4.1 Figure 1 — the paper's front page

One chart. Build it Saturday afternoon and put it above the fold in both the
README and the PDF.

```
  x-axis: action_idx  (0 ────────────────────────────────► 17,613)
  y-axis: one row per detector, models and rules interleaved

  keyword_sigma      ●
  volume_spike                      ●
  gemini-*                    ●
  nemotron-ultra                        ●
  gpt-class-*                     ●
  lfm-2.5-2.6b                                              ✕ never pages
                     ┊       ┊      ┊                    ┊
                  first    cred-  cluster-             first
                   RCE    access   admin               exfil
                                                    (t = −51.6h)

  Right-hand gutter: false-page rate on the benign stream, per row.
```

The two axes together are the entire paper: **when** it fires, and **how often
it fires when it shouldn't**. A judge who reads nothing else understands the
contribution.

### 4.2 Title

State the finding, not the topic. Apart's own publishing guidance says so, and
every top-5 title from the last sprint obeys it:

- ✅ *"Removing a secret loyalty blind erases who it served, and usually not
  the loyalty"* — 3rd place
- ✅ *"A Broad Secret Loyalty Evades an Adversarial Audit"* — 2nd place

So: not *"The Verification Gap"*. Something shaped like
*"Every model we could reach pages on the Hugging Face intrusion — and on 31%
of benign windows."*

Pick the title **Sunday morning, after you have the number.** Do not pick it now.

### 4.3 Report page budget (8 max, target 7)

| Pages | Section |
|---|---|
| 0.75 | Introduction — the sub-problem, why it matters, which track |
| 0.5 | Related Work — Elastic, SecureLayer7, *Defensive Refusal Bias*, Gray Swan, CoSAI, METR. **Say plainly what is new here.** |
| 1.5 | The corpus — construction, the 16,521 vs 17,613 reconciliation, the citation ledger, "scaffold not telemetry" |
| 1.25 | Method — E0/E1/E3/ER protocols, the outcome taxonomy, the $0 constraint |
| 2.5 | **Results** — Figure 1, false-page table, 2×2, reachability table |
| 0.75 | Discussion — what a defender should do Monday morning; what a month of follow-up adds |
| 0.5 | **Limitations & Dual-Use** (required, and scored) |
| 0.25 | References |

Artifacts go in the **linked repo**, not embedded — the sprint page says so
explicitly.

---

## PART 5 — Risk register (revised)

| Risk | P | Mitigation | Owner |
|---|---|---|---|
| **Rate limits eat Saturday** | **High** | §0.4 multi-provider + §1.1 measure-first sizing + cache-on-receipt + Ollama fallback | B |
| **Filter finding is mis-attributed and a judge catches it** | **Med-High** | §0.2 — settle it Friday hour 2, or downgrade the claim to route-level | B |
| Corpus not finished Friday | Med | Template banks are 10-line dicts — generate them with Claude in parallel. Fallback: documented 5-phase subset (rce, k8s, supply_chain, tailscale, exfil), which `TIMELINE.md` §5 already blesses. **Honest partial beats fabricated complete.** | A |
| Benign stream trivially separable | Med | The T+5h blind check catches it while there is still time to fix templates | Joint |
| Incoherence ≈ 0 | **Confirmed likely** | Already pre-registered as branch H-D. E0+E1 carry the paper. | — |
| Another team does the defender's-dilemma project | **High — the sprint page names it** | Four things they will not have: the **released corpus**, the **matched benign control**, the **rule baselines**, and the **filtered ≠ refused distinction**. Lead with all four. | Joint |
| Two of you score E2 differently | Med | Saturday calibration on 40 items; report κ honestly even if mediocre | Joint |
| Scope creep back to interpretability | Med | It is CUT. A has veto. | A |
| Losing a day | Med | B protects E0 + E1. A protects the corpus. Everything else goes. | — |

---

## PART 6 — Submission checklist

- [ ] Report PDF on the **official template**, fetched from the **Guidelines tab**
- [ ] **≤ 8 pages**
- [ ] Abstract **≤ 150 words**, containing: headline number · "reconstruction" · "$0" · Track 1 crossover
- [ ] Title states the finding, with a number
- [ ] Author names + affiliations (both of you)
- [ ] **Limitations & Dual-Use Considerations appendix** — required *and* scored
- [ ] Pre-sprint disclosure sentence present and unambiguous (`PREREGISTRATION.md` §1)
- [ ] Prior work built on is disclosed
- [ ] No novel installation recipes released
- [ ] Public GitHub repo linked; `.env` gitignored; `runs/` scrubbed of keys
- [ ] `PREREGISTRATION.md` visible at repo root with the amendment log filled in
- [ ] Figure 1 above the fold in the README
- [ ] Track: **2**, with Track 1 crossover named in the abstract
- [ ] Optional 3–5 min video (only if P0+P1 done)
- [ ] **Submitted by Sunday night IST.** Buffer to Mon 14 Sep 17:29 IST (AoE) is insurance, not schedule.

---

## PART 7 — What actually wins this

The prize table is $1000 / $500 / $300 / $100 / $100. Realistically, five things
put a project in that band, and you already have three of them:

1. **A real artifact.** The corpus is one, and it is the thing HF and
   SecureLayer7 publicly asked for. ✅ mostly built
2. **A control.** The matched benign stream. Most teams will report activation
   rate with no false-positive denominator, and the rubric names
   *"false-positive rate on matched controls"* explicitly. ⏳ Friday
3. **A number nobody else can produce.** False-page rate, and correctness scored
   against a key you own because you generated the corpus. ⏳ Saturday
4. **Honesty that reads as rigour, not hedging.** The `filtered` / `refused` /
   `truncated` / `unaffordable` taxonomy is genuinely better than the published
   refusal benchmarks, and disclosing your own 300-token truncation bug is the
   kind of thing that made last sprint's winners win. ✅ already written
5. **A finding stated in one sentence with a number in it.** ⏳ Saturday 21:00

The two things most likely to cost you the band, in order: **the rate-limit
wall on Saturday** (§0.3, §0.4) and **a mis-attributed filter claim** (§0.2).
Both are fixable before the sprint opens. Fix them tonight.
