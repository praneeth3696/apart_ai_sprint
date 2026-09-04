# TIMELINE — 2 people, 8 prep days + 3 sprint days

**Today:** Thu 3 Sep 2026 · **Sprint:** Fri 11 Sep 18:00 → Sun 13 Sep (submission cutoff Sunday)

**A** = Harness & Runs · **B** = Corpus & Evidence

---

## 1. Pre-sprint · Thu 3 Sep → Thu 10 Sep

> **Disclosure rule.** Apart allows building on prior work but requires you to *clearly identify what is new during the sprint*; undisclosed prior work risks disqualification. So: pre-sprint = **reading, tooling, and a one-phase feasibility prototype only.** The full corpus and every reported experiment are built during the sprint. State this in the report in one plain sentence. Do not blur it.

| Day | A — Harness | B — Corpus & Evidence |
|---|---|---|
| **Thu 3 – Fri 4** | OpenRouter account, credits, hard cap. Skeleton async client with caching + retry. | Read HF technical timeline and initial disclosure end to end. Start `CITATIONS.md` — pull every number verbatim with its source sentence. |
| **Sat 5 – Sun 6** | Confirm all 6 models reachable. Verify GLM-5.2 access specifically (this is the one that will surprise you). Test strict-JSON responses. | Read OpenAI disclosure + updates, Anthropic's review, Elastic, SecureLayer7. Draft prompt taxonomy: 6 task families × 4 rungs × 2 framings. |
| **Mon 7** | Wilson intervals + McNemar working on dummy data. Cost model per experiment. | Read METR investigation spec, GovAI incident analysis, *Defensive Refusal Bias*, Gray Swan. Write the Related Work paragraph now, while it is fresh. |
| **Tue 8** | **Feasibility spike:** 2 models × 1 task × 3 prompts (bare / defender / attacker). Does anything refuse at all? | Prototype corpus generator for **one phase only** (Kubernetes, 87 actions — smallest useful). Prove the marginal-matching assertions work. |
| **Wed 9** | **Incoherence smoke test:** 1 model, 5 moments, both frames. Is the effect visible at all? Adjust prompt wording if the monitor frame is not being taken seriously. | Freeze the scoring rubric. Write answer-key format. Repo scaffold pushed. |
| **Thu 10** | Overnight run capacity checked. Rate limits measured per model. | **Both: write and freeze `PREREGISTRATION.md`** — hypotheses, metrics, escalation ground truth, rubric, model list. Commit it before the sprint opens. This is worth real points. |

**Pre-sprint go/no-go, Wed 9 evening.** If the incoherence smoke test shows *nothing* — models escalate sensibly and assist willingly — pivot the headline to E1 escalation latency + false-page precision (still a strong Track 2 paper) and say so in the pre-registration. Better to learn this on the 9th than the 12th.

---

## 2. Day 1 · Fri 11 Sep — build and smoke-test everything

| Block | A | B |
|---|---|---|
| **Open – +3h** | `e1_escalation.py`: streaming monitor loop with rolling summary, strict JSON parse, cache-on-receipt | Generate the **full 17,600-action attack stream**; assertion suite green on all phase counts, time windows, daily volumes, milestone ordering |
| **+3h – +6h** | `e3_incoherence.py`: paired-frame runner over identical evidence blocks | Generate the **benign baseline stream**; verify it is not trivially separable (spot-check 20 windows blind between the two of you) |
| **+6h – +8h** | End-to-end smoke: 1 model × 20 windows × both streams. Fix the JSON parsing that will break. | Window both streams to ~250 records. Build the 40 matched E3 moments + answer keys. |
| **Before sleep** | **Launch the full E1 run overnight, all 6 models, both streams.** This is the single most important scheduling decision of the sprint. | Draft Introduction + Related Work into the report template. |

**Day 1 exit condition:** E1 is running unattended. If it is not, you have lost Saturday — stop building anything else and get it running.

---

## 3. Day 2 · Sat 12 Sep — run, score, and get the headline

| Block | A | B |
|---|---|---|
| **Morning** | Triage the overnight E1 run: failures, refusals-to-parse, empty cells. Re-run gaps only. Compute EAI, lead times, false-page rates. | Build the E2 prompt set: 6 families × 4 rungs × 2 framings, rendered and reviewed |
| **Midday** | **Launch E3 (incoherence) across all 6 models — this is the headline, it runs first.** Then queue E2. | **Joint: scoring calibration.** Both independently score the same 60 E2 items. Compute Cohen's κ. Reconcile the rubric if κ < 0.6. Do not skip this. |
| **Afternoon** | Compute Incoherence Rates + Wilson CIs + McNemar. **Produce the E1 chart** (EAI markers, phase reference lines) — the paper's front page. | Bulk-score E2. Build the answer-key comparison. Start fabrication-rate counting. |
| **Evening** | EFY table. Sanity-check every headline number by hand against three raw cached responses. | Write the Results section around the numbers that now exist. |
| **Hard stop** | **All API runs finish tonight.** Sunday is writing only. | Draft `LIMITATIONS.md` in full. |

**Day 2 exit condition:** you can state the headline sentence out loud, with a number in it. If you cannot, cut E2/E4 immediately and spend Sunday making E1+E3 excellent.

---

## 4. Day 3 · Sun 13 Sep — write, and stop building

| Block | A | B |
|---|---|---|
| **Morning** | Finalise figures (E1 latency chart, E3 2×2 heatmap, EFY-vs-refusal scatter). Clean `harness/`, write reproduce-in-one-command. | Write the report body: Methodology → Results → Discussion |
| **Midday** | Repo hygiene: README with headline + chart above the fold, purge secrets from `runs/`, licence, `PREREGISTRATION.md` visible at root | Write **Limitations & Dual-Use Considerations** appendix in full. Write the pre-sprint disclosure sentence. |
| **Early afternoon** | `responder_mode/SPEC.md` — P2, only if everything above is done | **Abstract, ≤150 words**, with the headline number in it. Write it last, cut it twice. |
| **Mid afternoon** | **Joint: read the PDF aloud to each other once.** Every factual claim about the incident gets a primary-source link checked live. Fix the three things you find. | |
| **T–3h** | Optional 3–5 min video demo — only if P0+P1 are complete | Final checklist pass against PLAN.md §7 |
| **T–2h** | **SUBMIT.** Do not wait for the last hour. You can resubmit with the same title if you improve it. | |

**The only Sunday rule that matters:** no new experiments after Saturday night, no matter how good the idea is. Resubmission is allowed with the identical title — so ship at T–2h and refine after if you must.

---

## 5. Contingencies

| If… | Then |
|---|---|
| Friday runs into the night on plumbing | Cut model count from 6 → 4. Keep GLM-5.2 and the refusing assistant family. Never cut those two. |
| E3 shows no incoherence | Headline becomes E1: *"models detect the intrusion but will not page — or page on everything."* Pre-registration already covers this branch, so it reads as a finding, not a rescue. |
| GLM-5.2 unavailable | Substitute the nearest open-weight comparable and **say so in the abstract** — the provenance claim weakens but does not break; the coherence result is untouched. |
| One person loses a day | Person A protects E1 + E3 and drops everything else. The corpus for a 4-phase subset is enough for both. |
| Corpus assertions will not converge | Ship a documented 4-phase subset (RCE, K8s, supply-chain, exfil) rather than a fudged full stream. Honest partial beats fabricated complete, and the rubric explicitly rewards that. |

---

## 6. Effort estimate

| Workstream | A | B |
|---|---|---|
| Pre-sprint | ~14 h | ~16 h |
| Day 1 | ~9 h | ~9 h |
| Day 2 | ~10 h | ~10 h |
| Day 3 | ~7 h | ~8 h |
| **Total** | **~40 h** | **~43 h** |

Tight but real for two people, *provided* the pre-sprint week actually happens. The prep week is not optional padding — it is what converts a 3-day scramble into a 3-day execution.
