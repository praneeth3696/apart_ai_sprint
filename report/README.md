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
| `06_related_work_STUB.md` | **A** | **STUB — not drafted.** Brief inside the file |
| `02_methodology.md` | B | **done** |
| `03_results.md` | B | **done** — regenerate numbers from `analysis/RESULTS_DRAFT.md` after any new run |
| `04_discussion.md` | B | **done** |
| `05_limitations_dualuse.md` | B | **done** — required and scored |

## Before submitting

1. **Re-run the pipeline and reconcile the numbers.** Results prose was written
   against a specific run. Any new E1/E3 data changes it:
   ```bash
   python analysis/stats.py --eai && python analysis/results_draft.py
   python analysis/figures.py
   ```
   Then diff `analysis/RESULTS_DRAFT.md` against §4 and the Abstract.
   **`RESULTS_DRAFT.md` is ground truth; the prose is downstream of it.**
   The pooled false-page figure has already moved once (66% → 54%) as Groq
   data landed, so assume it has moved again.
2. **Official template.** Still "Coming Soon" on the Guidelines tab when this
   was written. Page estimate is **6.9–9.9** depending on column count.
   If it is single-column and the appendix counts toward the 8 pages, cut in
   this order — least damage to the score first:
   - Methodology §3.1 corpus provenance detail (~150 words)
   - Discussion §5 paragraph 1, which restates Results (~90 words)
   - Introduction contributions list, compress to prose (~120 words)
   - **Do not cut** the Limitations appendix (required and scored), the
     ORACLE disclaimers, the labeller disclosure, or the E3 truncation
     caveat.
3. **Figures.** `analysis/figures/figure1_detection_vs_false_page.pdf` is the
   front-page figure; `figure2_eai_timeline.pdf` supports §4.3.
4. **Checklist** from the guidelines: PDF on the official template; abstract
   ≤150 words; author names and affiliations; Limitations and Dual-Use
   appendix; no novel installation recipes released without review.

## One norm to check before cross-posting

The sprint guidelines say that for **LessWrong** write-ups specifically:
*"don't use LLMs for writing on LessWrong, only use LLMs to find problems in
your drafts, not to draft it."* These sections were **drafted by an LLM**. That
is not a problem for the sprint PDF, but if this is cross-posted to LessWrong
it needs to be rewritten by a human first, or the norm is being broken.
