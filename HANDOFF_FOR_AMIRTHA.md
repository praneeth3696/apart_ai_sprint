# Handoff → Amirtha, Sun 13 Sep (written Sat 21:30 IST)

Paste this whole file into Claude Code in your clone and it should have enough
to work from. Written by Praneeth's session; **B's lane is the harness,
analysis and report front-half — yours is corpus, ground truth, Related Work
and the source-verification pass.**

Repo: `praneeth3696/apart_ai_sprint` · branch **`b/e1-multiprovider-runner`**
(PR #11, 21 commits). Everything below assumes you're on that branch, not
`main`.

---

## 1. Where the project actually stands

Deadline **Mon 14 Sep 17:29 IST**; we're targeting **Sunday night**.

**We have a submittable paper.** It is drafted end to end in `report/`, the
experiments ran, and the numbers are real. It is not a question of whether we
submit — it's how much better we can make it in the time left.

### The two findings

**1. Models catch the incident and cry wolf.** Across 11 models, 89% of
milestone-carrying attack windows produce a page — and so do ~46% of windows in
a matched *benign* stream with no intrusion in it. Two models significantly
separate the streams (`qwen3.8-27b` p=0.002, `gpt-oss-120b` p=0.008); the rest
don't. `gemini-3.1-flash-lite` gets a perfect 12/12 recall by paging on 11 of
12 innocent windows — recall bought by paging on everything, worth nothing.

**2. The one that's actually novel.** We wrapped **byte-identical evidence** in
two frames — "you are the triage layer, do you page?" vs "I'm on the IR team,
help me analyse this." Incoherence was **zero** (the pre-registered null). But
the frames disagreed sharply and entirely in one direction: models **assisted
on 45/45 moments and escalated on 16** (McNemar exact, p=0.0001). Every
discordant pair the same way, none the reverse.

> The failure mode isn't a model that refuses to discuss the intrusion. It's a
> model that explains it to you fluently while the pager stays silent.
> **Under-escalation, not refusal.** That reframing is the paper's contribution.

Cost so far: **$0.00**, all free tiers.

---

## 2. What's already done — don't redo any of this

- `harness/client.py` — multi-provider routing (Google, Groq, GitHub Models,
  Cerebras, Mistral, Ollama, OpenRouter, Anthropic first-party)
- `harness/e1_escalation.py`, `harness/e3_incoherence.py` — both with
  `--dry-run` (no key, no network), resume-on-gaps, quota handling
- `analysis/stats.py` — Wilson, exact Fisher, exact McNemar (stdlib only)
- `analysis/figures.py` — Figures 1 and 2, PDF + PNG
- `analysis/results_draft.py` → `analysis/RESULTS_DRAFT.md` (**numeric source
  of truth** — the report's numbers are downstream of this)
- `report/` — Abstract (148/150 words), Introduction, Related Work,
  Methodology, Results, Discussion, Limitations & Dual-Use appendix
- `report/check_numbers.py` — **the submission gate**, 36 checks
- `harness/PROVIDERS.md` — measured quotas for every provider
- **215 tests green** (corpus 48 · harness 143 · analysis 24)

Amendments already logged: PREREGISTRATION §9 gained 4 rows (Google arm, Groq
arm, EAI reprioritisation, rubric change); `prompts/RUBRIC.md` gained
`quota_exhausted` with a UTC timestamp; `LIMITATIONS.md` gained a dated §5
reconciliation.

**Heads-up on the rubric:** we added an outcome to the frozen rubric
mid-sprint — `quota_exhausted`, a 429 whose `quotaId` names a per-day window.
It's the free-tier twin of the HTTP 402 that `unaffordable` already covered and
it's excluded from every denominator. No item had been scored when it was
added. It's logged properly, but it touches a frozen instrument, so you should
know rather than find it in a diff. Say if you disagree.

---

## 3. The gaps — honestly

| # | Gap | Owner |
|---|---|---|
| 1 | **E3 rests on 2 models, both GPT-OSS, both Groq.** Biggest vulnerability in the best finding. | **you — §4** |
| 2 | **Related Work has no named citations.** The only thing in the report not sourced to a repo document. | **you — §5** |
| 3 | Prose claims about the incident not yet checked against primary sources | **you — §6** |
| 4 | PREREGISTRATION §4 contradicts itself; §1 "built during the sprint" | **you — §7** |
| 5 | Google E1 arm thin (n=1–12/model). Caps are 10–31 req/model/**day** — cannot reach parity before deadline. | accepted, disclosed |
| 6 | No frontier-proprietary models (no GPT/Claude class) | Praneeth chasing GitHub Models |
| 7 | Page budget unresolved — official template still unpublished | blocked on Apart |

---

## 4. YOUR BIG JOB: run E3 on Gemini, with your own Google key

**This is the highest-value thing anyone can do tomorrow.** E3 is our best
finding and it currently rests on two models from one family on one provider.
If the escalate-vs-assist asymmetry also holds on Gemini — different family,
different provider — the finding stops being "we saw this in GPT-OSS" and
becomes "we see this across families." That's a much stronger paper.

Google meters free tier **per project × model per day**, so **your account is a
completely separate quota from Praneeth's.** You running Gemini while he runs
Groq is two people doing their own work in parallel — not a workaround. We'll
state it in Methodology in one line.

### Setup

```bash
git fetch origin && git checkout b/e1-multiprovider-runner
python3 -m venv .venv && .venv/bin/python3 -m pip install numpy pyyaml pytest matplotlib
printf 'GOOGLE_AI_STUDIO_KEY=your_key_here\n' > .env    # gitignored, never commit
.venv/bin/python3 harness/measure_limits.py             # should show HTTP 200 for google
```

Dry-run first — no key needed, no network, no quota:

```bash
.venv/bin/python3 harness/e3_incoherence.py --dry-run
```

### The real run

```bash
.venv/bin/python3 harness/e3_incoherence.py \
  --models google:gemini-3.1-flash-lite,google:gemini-3.5-flash-lite \
  --max-tokens 6000 --rpm 6
```

Those two are chosen deliberately: they were the only Gemini models that never
hit their daily cap in Praneeth's E1 runs, so they're the most likely to absorb
E3's 48 calls each. **Google's quota resets ~12:30 IST Sunday** — start after
that.

If they finish and quota remains, add more, most interesting first:

```bash
.venv/bin/python3 harness/e3_incoherence.py \
  --models google:gemini-3.6-flash,google:gemma-4-26b-a4b-it \
  --max-tokens 6000 --rpm 6
```

`gemma-4-26b-a4b-it` is especially interesting — open-weight, but served by
Google, so it isolates family from serving stack.

### Things that will happen, and what they mean

- **`quota_exhausted`** — that model is done for the day. The runner moves on
  automatically. Not an error, don't fight it.
- **`truncated`** — the model burned its whole token budget on reasoning and
  emitted nothing. Our defect, never scored. Re-run the same command with
  `--max-tokens 10000`; resume retries only the gaps.
- **Re-running the same command is always safe.** Settled moments are skipped,
  gaps retried, cached calls free.

### Handing the data back

`runs/` is gitignored, so don't try to commit it. Just send Praneeth the file:

```bash
ls -la runs/e3/live/e3_decisions.jsonl
```

It's append-only JSONL deduped last-record-wins, so he literally concatenates
it onto his and the analysis is correct. **Send it as soon as the first model
finishes** — don't wait for the whole run. Partial data that arrives in time
beats complete data that arrives after the report is cut.

---

## 5. Related Work — needs a human with the literature

`report/06_related_work.md` is drafted and grounded in sources that actually
exist in the repo (the HF timeline, the OpenAI incident report, one arXiv
reference). **But its claims about what existing security-refusal benchmarks do
and don't report carry no named citations.** There's a visible note in the
section saying exactly that. Praneeth's session deliberately refused to invent
citations.

What it needs:

- **Named security-refusal benchmarks** — and the specific gap: to our
  knowledge none report a *fabrication rate* or measure escalation against a
  *matched benign control*.
- **Alert fatigue / false-positive burden in SOC literature** — this backs the
  Discussion's claim that a 46% false-page rate degrades response capacity
  rather than adding to it.
- **Prior incident-replay corpora** — anyone else turning post-incident
  write-ups into evaluable artefacts.
- **LLM framing-sensitivity / LLM-as-judge reliability** — this is literally
  what E3 measures, so if there's prior art we should be citing it.

Either attach real citations or soften each claim to "to our knowledge". Both
are fine; inventing a plausible-looking reference is not.

---

## 6. The source-verification pass

You built the corpus and you know `corpus/CITATIONS.md`. Praneeth's session
already verified every *corpus-derived* number mechanically against
`corpus/attack_stream.jsonl` — 17,613 actions, 56 exfil (0.32%), recon 6,191 +
dropper 6,972, 1,092 unclassified, 1,278/1,280 windows, 12 milestone windows,
E3 K=24 with 9 milestones across all ten phases. **All check out.**

What still needs a human: the **prose claims about the incident itself** in
`report/01_introduction.md` and `report/02_methodology.md`. Open the primary
source for each one. Anything we can't point at a source for gets softened or
cut.

---

## 7. Your two documentation fixes

1. **`PREREGISTRATION.md` §4 contradicts itself.** Line 159 says the rule pages
   "≈51.6 h after exfiltration has already begun"; line 161's own quoted
   commitment two lines below still says **"53 hours"**. The report uses
   **51.4 h**, computed directly from `analysis/e0_baselines.json` (escalation
   point #10,498 minus first exfil action #1,894). §4's 51.6 h measures from
   the exfil phase-window opening at 14:11 rather than the first exfil action
   at 14:21. Pick one basis and make all three agree, or the paper and the
   pre-registration will look like they disagree.

2. **`PREREGISTRATION.md` §1** says the corpus was "built during the sprint",
   but the commit timestamps are 07:22–14:42 IST Friday. Confirm the sprint's
   opening time on Discord, then one sentence either way. This is a disclosure
   question, so it's worth being precise.

---

## 8. Rules that will save you pain

- **Never hand-edit numbers in `report/03_results.md`.** They're generated.
  Change the data, re-run the pipeline, let the prose follow.
- **`report/check_numbers.py` is the gate.** Non-zero exit = do not submit. It
  exists because the report silently went stale once already: the Groq arm
  moved pooled false-page 54%→46% and turned "0 of 9 models reach significance"
  into "2 of 10", while the Abstract still asserted the old claim.
- **Don't edit `harness/` or `analysis/` while Praneeth's runs are live.**
  Flag instead. Same courtesy he's extending to `corpus/`.
- Work on `b/e1-multiprovider-runner`, commit in small chunks, stage by
  explicit path (never `git add -A`).
- Run the tests before any commit touching code:
  `(cd corpus && ../.venv/bin/python3 -m pytest -q)` etc.

### The pipeline, whenever data changes

```bash
.venv/bin/python3 analysis/stats.py --eai
.venv/bin/python3 analysis/results_draft.py
.venv/bin/python3 analysis/figures.py
.venv/bin/python3 report/check_numbers.py     # must pass
.venv/bin/python3 report/assemble.py
```

---

## 9. Realistic timeline

| When (IST) | You | Praneeth |
|---|---|---|
| **Sat night** | rest, or start §5 Related Work (no key needed) | E1 + E3 running unattended on Groq |
| **Sun 09:00–12:30** | §5 Related Work · §7 doc fixes | wire GitHub Models / Cerebras / Mistral if keys land |
| **Sun 12:30** | **Google quota resets → launch §4 E3 on Gemini** | E1 gap-fill, regenerate pipeline |
| **Sun 13:00–16:00** | §6 source-verification pass while E3 runs | figures, results reconciliation |
| **Sun ~16:00** | **send `e3_decisions.jsonl`, however far it got** | merge, final pipeline run |
| **Sun 17:00–20:00** | joint read-aloud of the whole report | cut to page budget |
| **Sun ~21:00** | **submit** | |
| **Mon → 17:29** | buffer only — resubmission with an identical title is allowed | |

**The hard rule for Sunday: stop collecting data at 16:00 IST** regardless of
where the runs are. The report is the deliverable, not the dataset. Anything
unfinished becomes a sentence in Limitations, which is already written to
absorb it.

---

## 10. If you only do three things

1. **Run E3 on Gemini after 12:30 Sunday** (§4) — turns the best finding from
   one-family into cross-family.
2. **Fix Related Work's citations** (§5) — the only unsourced thing in the paper.
3. **Send the JSONL by 16:00** even if incomplete (§4).

Everything else is upside.
