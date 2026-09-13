# Merging the Gemini E3 arm — instructions for B's session

Written by Amirtha's session, 2026-09-12 ~23:55 IST. **Read all of §0 before
running anything.** The data file is not in git; it arrives separately.

---

## 0. What this is, and the one trap in it

48 new E3 records (2 Gemini models x K=24) join the 45 existing GPT-OSS records.
The analysis pipeline **regenerates itself** from the JSONL — `stats.py` reads
`runs/e3/live/e3_decisions.jsonl`, writes `analysis/e1_stats.json`, and
`03_results.md` is generated downstream. **That part needs no hand-editing and
must not get any.**

**The trap:** five *hand-written* prose files quote the old E3 numbers and will
NOT regenerate. `check_numbers.py` catches two of them and will **not** catch
the other three, because they are qualitative claims rather than numbers — most
importantly a Limitations paragraph that currently says the Gemini question is
"untested", which after this merge is false. This is the same staleness that bit
the report once already during the Groq merge. §3 lists every site.

Do **not** hand-edit `report/03_results.md` at any point.

---

## 1. Merge the data

`e3_decisions.jsonl` is append-only and deduped **last-record-wins**, so
concatenation is the whole merge. No merge logic, no ordering requirement.

```bash
cat /path/to/amirtha_e3_decisions.jsonl >> runs/e3/live/e3_decisions.jsonl
wc -l runs/e3/live/e3_decisions.jsonl      # expect +48
```

Sanity check before spending any more time — expect exactly four models:

```bash
python3 - <<'PY'
import json, collections
c = collections.Counter()
for l in open("runs/e3/live/e3_decisions.jsonl"):
    d = json.loads(l); c[d["model"]] += 1
for m, n in sorted(c.items()): print(f"{m:<36} {n}")
PY
```

Expect `groq:openai/gpt-oss-120b`, `groq:openai/gpt-oss-20b`,
`google:gemini-3.1-flash-lite` (24), `google:gemini-3.5-flash-lite` (24).

## 2. Regenerate, in this order

```bash
python3 analysis/stats.py --eai
python3 analysis/results_draft.py
python3 analysis/figures.py
python3 report/check_numbers.py      # WILL FAIL here - that is expected, see §3
```

`check_numbers.py` fails at this point because the regenerated data no longer
matches the hand-written prose. That failure is the signal to do §3, not a bug.

## 3. The five prose sites

Expected merged values — **verify against the regenerated `analysis/e1_stats.json`
rather than trusting these. If they differ, the data is right and these notes are
wrong; follow the data.**

| quantity | old | merged |
|---|---|---|
| scoreable moments | 45 | **93** |
| assisted | 45/45 | **93/93** |
| escalated | 16 | **51** |
| incoherent | 0/45 | **0/93** |
| McNemar exact, pooled | p=0.0001 | **p=4.5e-13** (b=42, c=0) |

Per-arm, for the prose that needs it:

| arm | scoreable | assisted | escalated | McNemar |
|---|---|---|---|---|
| `gemini-3.1-flash-lite` | 24 | 24/24 | 21 | b=3, c=0, p=0.25 |
| `gemini-3.5-flash-lite` | 24 | 24/24 | 14 | b=10, c=0, **p=0.00195** |
| Gemini pooled | 48 | 48/48 | 35 | b=13, c=0, **p=0.000244** |
| GPT-OSS pooled | 45 | 45/45 | 16 | p=0.0001 |

### 3.1 `report/00_abstract.md:18` — numbers, gate catches this
Currently: *"assisted on 45/45 moments while escalating on 16 (p=0.0001)"*.
Update all three figures. **The abstract is 148/150 words — it has 2 words of
headroom.** If the cross-family claim will not fit, change the numbers only and
leave the framing to Results; do not push it over budget.

### 3.2 `report/05_limitations_dualuse.md:132` — THE IMPORTANT ONE, gate does NOT catch this
The paragraph currently reads *"E3 covers two models from one family on one
provider"* and ends *"Whether Gemini models show the same asymmetry is untested
and is the first thing we would run next."*

**That is now false and must be rewritten, not deleted.** The honest replacement
covers: E3 now spans **four models, two families, two providers**; the direction
replicates and the pooled asymmetry strengthens; **but the effect size is
markedly weaker on Gemini (35/48 escalated, 73%, vs 16/45, 36%)**; and
`gemini-3.1-flash-lite` alone is **not** individually significant (p=0.25).

The residual limitation is real and should replace the retired one: still no
frontier-*proprietary* model, and the Gemini arm is frontier-*flash*.

### 3.3 `report/04_discussion.md:30`
*"It did not happen once in 45 scoreable moments"* -> 93.

Consider adding one sentence here, because it reconciles the paper's two
findings rather than leaving them in tension: `gemini-3.1-flash-lite` escalates
on 21 of 24 and is the weakest E3 arm **because** it is the cry-wolf model from
E1 — the one that bought 12/12 recall by paging on 11 of 12 innocent windows. A
model that pages on nearly everything has no headroom to show an escalation
deficit. Its high escalation rate is a symptom of Finding 1, not a
counterexample to Finding 2. Saying this is stronger than letting a reader find
it.

### 3.4 `report/06_related_work.md:34`
*"In 45 scoreable moments, not one model declined"* -> 93. The claim itself
survives and gets stronger; only the denominator moves.

### 3.5 `report/02_methodology.md` — two spots
- §3.8, ~line 155: *"two models on the same windows"* -> four.
- §3.7 roster prose: Google is no longer "E1 only" — it now carries an E3 arm.
  The free-tier/two-account disclosure is **already written** (§3.7, added in
  PR #12); do not duplicate it.

## 4. Close it out

```bash
python3 report/check_numbers.py     # MUST exit 0
python3 report/assemble.py
(cd corpus && python3 -m pytest -q) && python3 -m pytest -q analysis harness
```

Then re-read §3.2 and §3.3 once by eye. The gate proves the *numbers* agree; it
cannot prove the *claims* do, and the two claims most likely to be wrong after
this merge are the ones it does not check.

## 5. Already done in PR #12 — do not redo

- `PREREGISTRATION.md` §9: amendment admitting Google to the **E3** roster,
  marked **After** with the selection rationale. The prior 10:30 row covered E1
  only.
- `PREREGISTRATION.md` §4: lead-time basis reconciled to 51.4 h.
- `report/02_methodology.md` §3.7: two-account free-tier disclosure.
- `report/06_related_work.md`: 11 verified citations.

## 6. Still open, and NOT safe for an agent to close alone

`PREREGISTRATION.md` §1 says the corpus was "built during the sprint", but the
corpus commits are 07:22-14:42 IST Friday and §1's own header declares the
sprint opening as **Fri 11 Sep 18:00**. This is a disclosure question about our
own conduct. It needs the Discord opening time and both authors' agreement —
**do not let an agent pick a wording for this.**
