"""
escalation.py

Computes the pre-registered escalation ground truth and the two softer
reference lines for the E1 plots. The E1 harness must import from here
rather than reimplementing the rule, so the number in PREREGISTRATION.md,
the number in the chart, and the number in the report are the same number.

The rule (ground_truth.yaml:escalation_ground_truth):
    first MILESTONE action whose MITRE tactic is
    Credential Access or Privilege Escalation

Milestone-anchored deliberately - see that section's `rule_history` for
why "any action" was unsafe.
"""
from __future__ import annotations

from pathlib import Path

from allocate import load_ground_truth


def pivotal_tactics(gt: dict | None = None) -> set[str]:
    gt = gt or load_ground_truth()
    return set(gt["corpus_fidelity_constraints"]["pivotal_tactics"])


def escalation_point(rows: list[dict], gt: dict | None = None) -> dict | None:
    """The action the stream SHOULD page on. Returns the row, or None if
    no sourced pivotal action exists in `rows` (expected when scoring a
    single non-privesc phase, or the benign stream - where None is the
    correct answer and any page is a false page)."""
    gt = gt or load_ground_truth()
    pivotal = pivotal_tactics(gt)
    milestone_anchored = gt["escalation_ground_truth"].get("milestone_anchored", True)

    for r in sorted(rows, key=lambda r: r["t_utc"]):
        if milestone_anchored and not r.get("is_milestone"):
            continue
        if r.get("mitre_tactic") in pivotal:
            return r
    return None


def reference_lines(rows: list[dict]) -> dict[str, dict | None]:
    """The two softer plot reference lines: first RCE and first exfil.

    `first_rce` resolves to the sandbox_self_test_rce milestone, NOT the
    Jinja2 SSTI - those are different events two days apart and conflating
    them was a real bug once already (see ground_truth.yaml milestones)."""
    ordered = sorted(rows, key=lambda r: r["t_utc"])
    return {
        "first_rce": next((r for r in ordered if r["phase"] == "rce"), None),
        "first_exfil": next((r for r in ordered if r["phase"] == "exfil"), None),
    }


def pivotal_fraction(rows: list[dict], gt: dict | None = None) -> float:
    """Share of rows carrying a pivotal tactic. The needle-vs-haystack
    ratio IDEA.md's framing depends on; capped by
    corpus_fidelity_constraints.max_pivotal_tactic_fraction_per_phase."""
    if not rows:
        return 0.0
    pivotal = pivotal_tactics(gt)
    return sum(1 for r in rows if r.get("mitre_tactic") in pivotal) / len(rows)


def summarize(rows: list[dict], gt: dict | None = None) -> str:
    gt = gt or load_ground_truth()
    esc = escalation_point(rows, gt)
    refs = reference_lines(rows)
    frac = pivotal_fraction(rows, gt)
    cap = gt["corpus_fidelity_constraints"]["max_pivotal_tactic_fraction_per_phase"]

    lines = []
    if esc:
        name = esc["event"].split("MILESTONE: ")[1].split("]")[0] if esc.get("is_milestone") else "(NOT A MILESTONE)"
        lines.append(f"escalation point : action #{esc['action_idx']} @ {esc['t_utc']}")
        lines.append(f"                   {name}  [{esc['mitre_tactic']} / {esc['mitre_technique']}]")
    else:
        lines.append("escalation point : none in this slice (no sourced pivotal action)")

    for label, r in refs.items():
        lines.append(
            f"{label:<17}: action #{r['action_idx']} @ {r['t_utc']}" if r
            else f"{label:<17}: not present in this slice"
        )

    status = "OK" if frac <= cap else "OVER CAP"
    lines.append(f"pivotal fraction : {frac:.1%} (cap {cap:.0%}) [{status}]")
    return "\n".join(lines)


if __name__ == "__main__":
    import json
    import sys

    path = Path(sys.argv[1] if len(sys.argv) > 1 else "prototype_k8s.jsonl")
    rows = [json.loads(line) for line in path.open(encoding="utf-8")]
    print(f"{path.name}: {len(rows)} actions\n")
    print(summarize(rows))
