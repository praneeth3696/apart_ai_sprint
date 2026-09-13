"""
check_numbers.py

Verifies that every headline figure in report/ still matches
analysis/e1_stats.json. Run it before every commit that touches the report,
and again immediately before submitting.

WHY THIS EXISTS
---------------
The report is prose; the data is a growing append-only log. On 2026-09-12 the
Groq arm landed between the Results section being written and being read back,
and three things silently became false:

    pooled benign false-page   54% -> 46%
    models reaching p < 0.05   0 of 9 -> 2 of 10
    gpt-oss-120b Fisher p      0.143 -> 0.008

The Abstract and Introduction both asserted "no model reaches significance".
That is exactly the kind of claim that survives a tired proofread and does not
survive a reviewer. A human diffing two tables at 2am will miss it; a script
will not.

WHAT IT CHECKS
--------------
1. Every row of the per-model table in 03_results.md, against e1_stats.json:
   milestone k/n, benign k/n, and Fisher p.
2. The pooled figures and the significance count, wherever they are asserted
   across all section files.
3. That the model roster in the table matches the roster in the data.

It does NOT check prose claims that are not numeric. Those still need a human.

Usage:
    python analysis/stats.py --eai      # refresh the data first
    python report/check_numbers.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
STATS = REPO / "analysis" / "e1_stats.json"
SECTIONS = sorted((REPO / "report").glob("0*.md"))

FAIL: list[str] = []
OK: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    (OK if ok else FAIL).append(f"{label}{(' — ' + detail) if detail else ''}")


def short(model: str) -> str:
    """Match the table's display name. Mistral ids carry a `-latest` suffix
    that the paper drops for readability, so normalise it away."""
    name = model.split(":", 1)[-1].split("/")[-1]
    return name[:-len("-latest")] if name.endswith("-latest") else name


def main() -> int:
    if not STATS.is_file():
        print(f"no {STATS} — run analysis/stats.py --eai first", file=sys.stderr)
        return 2
    st = json.loads(STATS.read_text(encoding="utf-8"))
    per = st["per_model"]
    by_short = {short(m): s for m, s in per.items()}

    results_full = (REPO / "report" / "03_results.md").read_text(encoding="utf-8")
    # Scope the E1 table scan to the E1 section. The E3 table has the same
    # `| model | .. | k/n | k/n | p |` shape and was being parsed as E1 rows.
    m0 = re.search(r"^### 4\.2\b", results_full, re.M)
    m1 = re.search(r"^### 4\.3\b", results_full, re.M)
    results = results_full[m0.start():m1.start()] if (m0 and m1) else results_full
    all_text = "\n".join(p.read_text(encoding="utf-8") for p in SECTIONS)

    # ---- 1. the per-model table -------------------------------------------
    # | `model` | provider | 10/10 (100%, 72–100%) | 6/10 (60%, 31–83%) | +40% | 0.087 |
    # | `model` | provider | k/n (..) | k/n (..) | [sep |] p |
    row = re.compile(
        r"^\|\s*`([^`]+)`\s*\|[^|]*\|\s*\**(\d+)/(\d+)\**[^|]*\|"
        r"\s*(?:\**(\d+)/(\d+)\**[^|]*|—\s*)\|"
        r"(?:[^|]*\|)?\s*\**(?:<)?([0-9.]+|—)\**\s*\|", re.M)
    seen = set()
    for m in row.finditer(results):
        name, mk, mn, bk, bn, p = m.groups()
        seen.add(name)
        s = by_short.get(name)
        if s is None:
            check(f"table row `{name}`", False, "not present in e1_stats.json")
            continue
        exp_m = (s["milestone_hit_rate"]["k"], s["milestone_hit_rate"]["n"])
        check(f"`{name}` milestone", (int(mk), int(mn)) == exp_m,
              f"report {mk}/{mn}, data {exp_m[0]}/{exp_m[1]}")
        if bk is not None:
            exp_b = (s["benign_false_page_rate"]["k"], s["benign_false_page_rate"]["n"])
            check(f"`{name}` benign", (int(bk), int(bn)) == exp_b,
                  f"report {bk}/{bn}, data {exp_b[0]}/{exp_b[1]}")
        if p != "—" and s["fisher_milestone_vs_benign"] is not None:
            check(f"`{name}` Fisher p", abs(float(p) - s["fisher_milestone_vs_benign"]) < 5e-4,
                  f"report {p}, data {s['fisher_milestone_vs_benign']:.3f}")

    missing = set(by_short) - seen
    check("every model in the data appears in the table", not missing,
          f"missing: {sorted(missing)}")

    # ---- 2. pooled figures, asserted anywhere -----------------------------
    mk = sum(s["milestone_hit_rate"]["k"] for s in per.values())
    mn = sum(s["milestone_hit_rate"]["n"] for s in per.values())
    bk = sum(s["benign_false_page_rate"]["k"] for s in per.values())
    bn = sum(s["benign_false_page_rate"]["n"] for s in per.values())

    for label, pat, exp in (
        ("pooled milestone k/n", rf"\b{mk}/{mn}\b", f"{mk}/{mn}"),
        ("pooled benign k/n", rf"\b{bk}/{bn}\b", f"{bk}/{bn}"),
    ):
        check(label, re.search(pat, all_text) is not None,
              f"expected {exp} to appear somewhere in report/")

    for label, val, kind in (("pooled milestone %", round(100 * mk / mn), "milestone"),
                             ("pooled benign %", round(100 * bk / bn), "benign")):
        check(label, re.search(rf"\b{val}%", all_text) is not None,
              f"expected {val}% ({kind}) to appear in report/")

    # ---- 3. the significance count ----------------------------------------
    sig = [m for m, s in per.items()
           if s["fisher_milestone_vs_benign"] is not None
           and s["fisher_milestone_vs_benign"] < 0.05]
    n_models = len(per)
    claim = re.search(r"(\d+)\s+of\s+(\d+)\s+models\s+reach", all_text)
    if claim:
        check("significance count", (int(claim.group(1)), int(claim.group(2)))
              == (len(sig), n_models),
              f"report says {claim.group(1)} of {claim.group(2)}, "
              f"data says {len(sig)} of {n_models} ({', '.join(short(m) for m in sig) or 'none'})")
    else:
        check("significance count is stated at all", False,
              f"no 'N of M models reach' sentence found; data says {len(sig)} of {n_models}")

    # The old false claim, in every phrasing we actually used.
    for bad in (r"no model reaches statistical significance",
                r"no model reaches significance",
                r"\bnone\b[^.]{0,40}reach[^.]{0,20}significan"):
        if re.search(bad, all_text, re.I) and sig:
            check("stale 'no model is significant' claim", False,
                  f"report still says it, but {len(sig)} model(s) now do")

    # ---- 4. E3 ------------------------------------------------------------
    e3 = (st.get("e3") or {}).get("per_model", {})
    if e3:
        inc = sum(s["incoherence_rate"]["k"] for s in e3.values())
        tot = sum(s["incoherence_rate"]["n"] for s in e3.values())
        esc = sum(s["escalated"]["k"] for s in e3.values())
        ass = sum(s["refused_to_assist"]["n"] - s["refused_to_assist"]["k"]
                  for s in e3.values())
        assn = sum(s["refused_to_assist"]["n"] for s in e3.values())
        check("E3 pooled incoherence", re.search(rf"\b{inc} of {tot}\b|{inc}/{tot}\b", all_text) is not None,
              f"expected {inc}/{tot}")
        check("E3 assisted/escalated", re.search(rf"\b{ass}/{assn}\b", all_text) is not None,
              f"expected assisted {ass}/{assn}, escalated {esc}")

    # ---- report -----------------------------------------------------------
    print(f"checked against {STATS.relative_to(REPO)} "
          f"({st['n_records_after_dedupe']} settled E1 records)\n")
    for line in OK:
        print(f"  ok    {line}")
    if FAIL:
        print()
        for line in FAIL:
            print(f"  STALE {line}")
        print(f"\n{len(FAIL)} stale figure(s). Fix report/ before committing.")
        return 1
    print(f"\nall {len(OK)} checks pass — report matches the data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
