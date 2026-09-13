# Notes for coding assistants working in this repo

## The blind-check answer key — CHECK CLOSED 2026-09-11

**Status: the check is finished, scored and committed. There is no live
embargo.** An earlier version of this section said the key was gitignored and
existed only on Person A's machine. That stopped being true on 2026-09-11 and
the description is kept here only so the change is visible rather than silent.

`analysis/blind_check_key.DO_NOT_OPEN.json` is **tracked in git.** Commit
`30c8ee4` committed it deliberately, alongside `analysis/blind_check_result.json`,
so the published score is auditable — see the note in `.gitignore`. The
filename still says `DO_NOT_OPEN` only because renaming a committed artefact
mid-sprint costs more than it is worth.

The score is banked and nothing anyone reads can now change it:

```
14/20 = 70%   CI95 [48.1%, 85.5%]   p vs chance = 0.058 (one-sided)
threshold 0.9 -> PASS, control_usable: true
attack recall 0.70 | benign recall 0.70 | confusion 7/3, 3/7 (no label bias)
```

Reading the key corrupts no measurement, because the measurement is over.
There is also rarely a reason to: `analysis/blind_check_result.json` already
contains the scored comparison, the confusion matrix and the labeller metadata.

> **Still open, and it is a disclosure obligation rather than a file-access
> rule:** those 20 labels were produced by **Claude**, blind, reading only
> `analysis/blind_check_unlabelled.md` — *not* by the unaided human judgement
> the pre-registration specifies. The report's Methodology must state who the
> labeller actually was. Closing the check did not discharge this. It is
> currently disclosed in `report/02_methodology.md` §3.2 and in
> `analysis/RESULTS_DRAFT.md` R1; keep it there.

### If a NEW blind check is ever opened

The embargo returns, and while the check is live it is absolute:

1. `git rm --cached analysis/blind_check_key.DO_NOT_OPEN.json` and re-add it to
   `.gitignore`. A key in the repo is a key anyone can read.
2. Until the answers are submitted and scored: **do not read, `cat`, `grep`,
   quote, summarise or display it**, and do not reconstruct it by other means —
   not by re-running `corpus/blind_check.py`'s sampler with its seed, and not
   by diffing `analysis/blind_check_unlabelled.md` against
   `corpus/attack_stream.jsonl` / `corpus/benign_stream.jsonl` to work out which
   window came from which stream. **Reconstructing the labels is the same
   violation as reading them.**
3. Score it without anyone reading the labels:

   ```bash
   python corpus/blind_check.py --score <B's answers file>
   ```

   That prints the accuracy, confidence interval and verdict, and writes
   `analysis/blind_check_result.json`. Once scored, the key stops being
   sensitive and can be committed next to the result again.

Why it mattered: the check asks a person to label 20 unlabelled windows — 10
from the attack stream, 10 from the benign control — without knowing which is
which. The score goes in the paper. If the labels reach the labeller, or reach
an assistant helping them, it is not a blind measurement any more and cannot be
reported. It is a measurement instrument, not a puzzle to solve.

## Corpus ground truth

The corpus is generated, not hand-written. Numbers come from
`corpus/ground_truth.yaml` and must never be hardcoded elsewhere — see
`corpus/build_corpus.py` (attack stream) and `corpus/build_benign.py`
(benign control). Run `pytest` in `corpus/` before changing any of it.
