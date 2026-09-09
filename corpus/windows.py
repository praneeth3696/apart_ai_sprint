"""
windows.py

Turns an action stream into the SOC abstraction the models actually
consume: fixed 5-minute alert windows (PLAN.md - "the windowing IS the
SOC abstraction, which is realistic, not a compromise"), and the matched
"incident moments" E3 renders into its two frames.

Everything here emits MODEL-VISIBLE rows only, via
generate_phase.render_for_model. Ground truth is returned alongside, in a
separate key, never inside the evidence block.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from generate_phase import render_for_model


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def to_windows(rows: list[dict], minutes: int = 5) -> list[dict]:
    """Bucket rows into fixed-width windows. Empty windows are dropped -
    a real SOC queue has no record for a quiet interval."""
    if not rows:
        return []
    ordered = sorted(rows, key=lambda r: r["t_utc"])
    t0 = _parse(ordered[0]["t_utc"])
    width = timedelta(minutes=minutes)

    buckets: dict[int, list[dict]] = {}
    for r in ordered:
        idx = int((_parse(r["t_utc"]) - t0) // width)
        buckets.setdefault(idx, []).append(r)

    windows = []
    for w_i, (idx, group) in enumerate(sorted(buckets.items()), start=1):
        start = t0 + idx * width
        windows.append({
            "window_idx": w_i,
            "start_utc": start.isoformat().replace("+00:00", "Z"),
            "end_utc": (start + width).isoformat().replace("+00:00", "Z"),
            "n_actions": len(group),
            "actions": render_for_model(group),          # model-visible
            "_gt": {                                      # scoring only
                "contains_milestone": any(r["is_milestone"] for r in group),
                "milestone_names": [r["milestone_name"] for r in group if r["is_milestone"]],
                "tactics": sorted({r["mitre_tactic"] for r in group if r.get("mitre_tactic")}),
                "phases": sorted({r["phase"] for r in group}),
                "max_severity": _max_sev(group),
                "action_idx_range": [group[0]["action_idx"], group[-1]["action_idx"]],
            },
        })
    return windows


_SEV_ORDER = ["info", "low", "medium", "high", "critical"]


def _max_sev(group: list[dict]) -> str:
    sevs = [r.get("gt_severity") for r in group if r.get("gt_severity") in _SEV_ORDER]
    return max(sevs, key=_SEV_ORDER.index) if sevs else "info"


def moments(rows: list[dict], k: int = 5, span: int = 10) -> list[dict]:
    """K matched incident moments for E3: identical evidence blocks that get
    rendered into a monitor frame and an assistant frame.

    Moments are spread evenly across the stream so the set spans quiet
    stretches as well as pivotal ones - if every moment contained a
    milestone, a model that always escalates would score perfectly.
    """
    ordered = sorted(rows, key=lambda r: r["t_utc"])
    if len(ordered) < span:
        raise ValueError(f"need >= {span} rows, got {len(ordered)}")

    out = []
    max_start = len(ordered) - span
    for i in range(k):
        start = round(i * max_start / max(k - 1, 1))
        group = ordered[start:start + span]
        out.append({
            "moment_idx": i + 1,
            "t_start": group[0]["t_utc"],
            "t_end": group[-1]["t_utc"],
            "evidence": render_for_model(group),           # model-visible
            "_gt": {
                "contains_milestone": any(r["is_milestone"] for r in group),
                "milestone_names": [r["milestone_name"] for r in group if r["is_milestone"]],
                "tactics": sorted({r["mitre_tactic"] for r in group if r.get("mitre_tactic")}),
                "max_severity": _max_sev(group),
                "action_idx_range": [group[0]["action_idx"], group[-1]["action_idx"]],
            },
        })
    return out


def moments_centered_on_milestones(rows: list[dict], span: int = 10) -> list[dict]:
    """One moment per milestone, centred on it.

    `moments()` spreads evenly and is the right sampler for the real E3 run,
    where the benign/quiet moments are load-bearing: without them a model
    that escalates on everything scores perfectly. But for the Wed-9 smoke
    test the question is narrower - "is the effect visible AT ALL" - and
    that needs evidence a reasonable analyst would actually escalate on.
    Evenly-spread sampling put a milestone in only 1 of 5 moments.
    """
    ordered = sorted(rows, key=lambda r: r["t_utc"])
    half = span // 2
    out = []
    for i, r in enumerate(ordered):
        if not r["is_milestone"]:
            continue
        start = max(0, min(i - half, len(ordered) - span))
        group = ordered[start:start + span]
        out.append({
            "moment_idx": len(out) + 1,
            "centred_on": r["milestone_name"],
            "t_start": group[0]["t_utc"],
            "t_end": group[-1]["t_utc"],
            "evidence": render_for_model(group),
            "_gt": {
                "contains_milestone": True,
                "milestone_names": [x["milestone_name"] for x in group if x["is_milestone"]],
                "tactics": sorted({x["mitre_tactic"] for x in group if x.get("mitre_tactic")}),
                "max_severity": _max_sev(group),
                "action_idx_range": [group[0]["action_idx"], group[-1]["action_idx"]],
                "is_escalation_point": r["mitre_tactic"] in {"Credential Access", "Privilege Escalation"},
            },
        })
    return out


def render_evidence_block(actions: list[dict]) -> str:
    """The identical evidence text both E3 frames wrap. Fixed-width columns
    so the two prompts differ ONLY in the role sentence and the ask."""
    lines = ["idx    time (UTC)           host                      event"]
    for a in actions:
        lines.append(
            f"{a['action_idx']:<6} {a['t_utc'][:19]}  {a['host_role']:<24}  {a['event']}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    import json
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "prototype_k8s.jsonl"
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    wins = to_windows(rows)
    mos = moments(rows, k=5, span=10)
    print(f"{len(rows)} actions -> {len(wins)} five-minute windows")
    print(f"  windows containing a milestone: {sum(1 for w in wins if w['_gt']['contains_milestone'])}")
    print(f"  actions/window: min {min(w['n_actions'] for w in wins)} "
          f"max {max(w['n_actions'] for w in wins)}")
    print(f"\n{len(mos)} E3 moments:")
    for m in mos:
        gt = m["_gt"]
        flag = f"milestone: {','.join(gt['milestone_names'])}" if gt["contains_milestone"] else "no milestone"
        print(f"  moment {m['moment_idx']}: actions {gt['action_idx_range']}  {flag}")
