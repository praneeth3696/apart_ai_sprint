# report/

Sections are separate files so they can be drafted, reviewed and committed
independently. `assemble.py` is the only place the running order lives; it
concatenates into `REPORT.md` and estimates pages.

```bash
python report/assemble.py
```

## Status

| file | owner | status |
|---|---|---|
| `00_abstract.md` | B | **done** — 145 words against the 150-word limit |
| `01_introduction.md` | B | **done** |
| `06_related_work.md` | B (was A's) | **drafted** — but see the citation caveat below |
| `02_methodology.md` | B | **done** |
| `03_results.md` | B | **done** — regenerate numbers from `analysis/RESULTS_DRAFT.md` after any new run |
| `04_discussion.md` | B | **done** |
| `05_limitations_dualuse.md` | joint | **done** — required and scored. §A.1–A.3 derive from the repo's pre-results `LIMITATIONS.md`; §A.4 is post-run |

## Before submitting

1. **Verify the numbers mechanically. Do not eyeball them.**
   ```bash
   python analysis/stats.py --eai && python analysis/results_draft.py
   python analysis/figures.py
   python report/check_numbers.py      # <- this one is the gate
   ```
   `check_numbers.py` cross-checks every headline figure in `report/` against
   `analysis/e1_stats.json`: each row of the per-model table, the pooled
   figures, the significance count, the E3 totals, and that no model in the
   data is missing from the table. **It exists because the report silently went
   stale once already** — the Groq arm moved pooled false-page 54% → 46% and
   turned "0 of 9 models reach significance" into "2 of 10", while the Abstract
   and Introduction still asserted the old claim. Treat a non-zero exit as
   blocking.

2. **Related Work needs citations.** `06_related_work.md` is grounded in the
   two verified primary sources and one arXiv reference already used in the
   repo. Its claims about *what existing security-refusal benchmarks do and do
   not report* are stated from our own reading and are **not backed by named
   citations**. Before submission either attach specific benchmarks or soften
   to "to our knowledge". A visible note in the section says so.

3. **Page budget.** Estimate is **7.9–11.5 pages** (text 5,340 words + ~0.8
   page of figures) depending on whether the template is one or two columns,
   and on whether the required appendix counts toward the 8 pages. The template
   was still "Coming Soon" when this was written. **If it is single-column, or
   the appendix counts, cut in this order:**
   - Methodology §3.1 corpus provenance detail — the repo has it in full
   - Appendix §A.1–A.3 — these derive from `LIMITATIONS.md`, which is linked
   - Discussion ¶1, which restates Results
   - Introduction contributions list → prose
   - **Do not cut:** the significance framing, the ORACLE disclaimers, the
     labeller disclosure, the E3 phase-clustered truncation note, or §A.4.

4. **Checklist** (guidelines): PDF on the official template; abstract ≤150
   words (**currently 148**); author names and affiliations; Limitations and
   Dual-Use appendix; artifacts **linked, not embedded**; no novel installation
   recipes released without review.

## One norm to check before cross-posting

The sprint guidelines say that for **LessWrong** write-ups specifically:
*"don't use LLMs for writing on LessWrong, only use LLMs to find problems in
your drafts, not to draft it."* These sections were **drafted by an LLM**. Fine
for the sprint PDF; if this is cross-posted to LessWrong it needs a human
rewrite first, or the norm is being broken.
