# Notes for coding assistants working in this repo

## Do not open the blind-check answer key

`analysis/blind_check_key.DO_NOT_OPEN.json` is the ground truth for an
in-progress blind separability check (SPRINT_PLAN.md, Fri+2h).

It is **deliberately not committed** — it is gitignored and exists only on
Person A's machine, because a key in the repo is a key anyone can read. If
you do not see it, that is correct and nothing is missing.

**If it is present locally: do not read, open, `cat`, `grep`, quote,
summarise, or display it**, and do not reconstruct it by other means — for
example by re-running `corpus/blind_check.py`'s sampling with its seed, or by
comparing `analysis/blind_check_unlabelled.md` against
`corpus/attack_stream.jsonl` / `corpus/benign_stream.jsonl` to work out which
window came from which stream. Reconstructing the labels is the same
violation as reading them.

Why it matters: the check asks a person (Person B) to label 20 unlabelled
windows — 10 from the attack stream, 10 from the benign control — without
knowing which is which. The score goes in the paper. If the labels reach B,
or reach an assistant that is helping B, the result is not a blind measurement
any more and cannot be reported. This is a measurement instrument, not a
puzzle to solve.

If you are asked to "look at the analysis directory", "check the blind check",
or "see how we did", **stop and say why you are not opening it.** Everything
else under `analysis/` is fine to read.

To produce the score without anyone reading the labels:

```bash
python corpus/blind_check.py --score <B's answers file>
```

That prints the accuracy, confidence interval, and verdict, and writes
`analysis/blind_check_result.json`. Once B's answers are submitted and scored,
the key is no longer sensitive and can be committed next to the result so the
score is auditable.

## Corpus ground truth

The corpus is generated, not hand-written. Numbers come from
`corpus/ground_truth.yaml` and must never be hardcoded elsewhere — see
`corpus/build_corpus.py` (attack stream) and `corpus/build_benign.py`
(benign control). Run `pytest` in `corpus/` before changing any of it.
