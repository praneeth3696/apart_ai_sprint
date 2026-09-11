"""
generate_phase.py

Feasibility prototype (TIMELINE.md, Tue 8): generate a full action-row
stream for ONE phase and prove the whole pipeline - allocation, milestone
anchoring, schema fill, assertions - actually works before scaling to all
9 phases + `unclassified` and 17,613 actions on Friday.

Defaults to k8s (87 actions) because PLAN.md already picked it as "the
smallest useful" phase for this exact spike.

Usage:
    python generate_phase.py [phase_name]
    -> writes corpus/prototype_{phase}.jsonl
"""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from allocate import allocate, load_ground_truth
from templates import PHASE_TEMPLATES, render_event

random.seed(20260904)  # deterministic for the prototype; re-seed per run for the real build

OUT_DIR = Path(__file__).parent


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _fmt(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _day_bounds(date_str: str, phase_first: datetime, phase_last: datetime) -> tuple[datetime, datetime]:
    """Intersect a calendar day ('MM-DD', year 2026 implicit) with the phase's overall window."""
    month, day = date_str.split("-")
    day_start = datetime(2026, int(month), int(day), 0, 0, 0, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1) - timedelta(seconds=1)
    return max(day_start, phase_first), min(day_end, phase_last)


def _fill_missing_milestone_times(milestones: list[dict], phase_first: datetime, phase_last: datetime) -> list[dict]:
    """Milestones with t_utc: null still have a fixed `order`. Interpolate a
    timestamp between their known neighbors so ORDER is preserved even
    without an exact clock time - this is the property PLAN.md actually
    requires ("milestone ordering is preserved and timestamped"), not that
    every millisecond be sourced.

    When several consecutive milestones are all missing a timestamp, they
    are spread across the gap between the surrounding known anchors rather
    than all placed at one midpoint (an earlier version did that, and two
    k8s milestones landed on an identical estimated second as a result).

    A milestone may also carry an explicit `not_after` bound sourced from
    the record itself (e.g. admin_host_level_access_multi_cluster's "under
    13 hours" claim) - that is a real constraint, not decoration. A bound
    on a LATER milestone in a run must also constrain every EARLIER one in
    that run, since order is preserved (item k must sit strictly before
    item k+1). A first attempt at this only checked each milestone's own
    bound going forward and missed that: it placed hostpath_escape (no
    bound of its own) at 06:41, one hour past admin_host_level_access's
    05:07 not_after, because nothing propagated that downstream bound
    backward onto hostpath_escape's own placement. Fixed with a backward
    pass that tightens each slot's effective upper bound to the minimum of
    its own not_after and every later slot's in the same run."""
    known = [(i, _parse(m["t_utc"])) for i, m in enumerate(milestones) if m.get("t_utc")]
    out = [dict(m) for m in milestones]

    i = 0
    while i < len(out):
        if out[i].get("t_utc"):
            out[i]["t_utc_estimated"] = False
            i += 1
            continue
        # find the run of consecutive missing-timestamp milestones starting at i
        j = i
        while j < len(out) and not out[j].get("t_utc"):
            j += 1
        prev_t = next((t for k, t in reversed(known) if k < i), phase_first)
        next_t = next((t for k, t in known if k >= j), phase_last)

        # backward pass: each slot's effective upper bound is the tightest
        # not_after among itself and every later slot in this run
        effective_upper = [None] * (j - i)
        running_upper = next_t
        for k in range(j - 1, i - 1, -1):
            if out[k].get("not_after"):
                running_upper = min(running_upper, _parse(out[k]["not_after"]))
            effective_upper[k - i] = running_upper

        cursor = prev_t
        for idx, k in enumerate(range(i, j)):
            m = out[k]
            upper = effective_upper[idx]
            assert upper > cursor, (
                f"{m['name']}: effective upper bound {_fmt(upper)} leaves no "
                f"room after {_fmt(cursor)} - the sourced constraints are "
                f"mutually inconsistent, fix ground_truth.yaml"
            )
            est = cursor + (upper - cursor) / 2
            m["t_utc"] = _fmt(est)
            m["t_utc_estimated"] = True
            cursor = est
        i = j
    return out


def generate_phase(phase_name: str = "k8s") -> list[dict]:
    gt = load_ground_truth()
    phases, days, matrix = allocate()

    phase_cfg = next(p for p in gt["phases"] if p["name"] == phase_name)
    # `unclassified` is not a kill-chain phase and has no published first/last
    # seen - it is the residual absorbing the 1,092-action gap between the two
    # published tables. Fall back to the campaign window rather than crashing
    # in _parse(None).
    phase_first = _parse(phase_cfg["first_seen"] or gt["campaign_window"]["start_utc"])
    phase_last = _parse(phase_cfg["last_seen"] or gt["campaign_window"]["end_utc"])
    # Malicious by default; `unclassified` sets it false in ground_truth.yaml.
    # Read it, never assume it - these 1,092 rows are 6.2% of the corpus and
    # mislabelling them would corrupt every gt_malicious-derived number.
    phase_malicious = phase_cfg.get("gt_malicious", True)
    phase_idx = phases.index(phase_name)
    day_counts = dict(zip(days, matrix[phase_idx].tolist()))

    milestones = sorted(
        (m for m in gt["milestones"] if m["phase"] == phase_name),
        key=lambda m: m["order"],
    )
    milestones = _fill_missing_milestone_times(milestones, phase_first, phase_last)

    templates = PHASE_TEMPLATES[phase_name]
    rows: list[dict] = []

    for date_str, n_slots in day_counts.items():
        n_slots = int(n_slots)
        if n_slots == 0:
            continue
        day_lo, day_hi = _day_bounds(date_str, phase_first, phase_last)
        day_milestones = [m for m in milestones if day_lo <= _parse(m["t_utc"]) <= day_hi]
        n_filler = n_slots - len(day_milestones)
        assert n_filler >= 0, (
            f"{phase_name} on {date_str}: {len(day_milestones)} milestones "
            f"don't fit in {n_slots} allocated slots - widen the allocation "
            f"or check milestone dates against day boundaries."
        )

        span_seconds = (day_hi - day_lo).total_seconds()
        filler_times = sorted(
            day_lo + timedelta(seconds=random.uniform(0, span_seconds))
            for _ in range(n_filler)
        )

        for m in day_milestones:
            tpl = random.choice(templates)
            # MITRE tag comes from the milestone's OWN entry in
            # ground_truth.yaml, never from the randomly-picked filler
            # template - an earlier version of this function fell back to
            # tpl["mitre_technique"] here, which silently tagged e.g. a
            # Discovery-tactic recon milestone as "Credential Access"
            # because that's what the unrelated filler template happened
            # to carry. If a milestone genuinely has no MITRE mapping yet,
            # leave it null rather than borrow one - this field feeds
            # escalation_ground_truth's page-trigger rule directly.
            rows.append({
                "t_utc": m["t_utc"],
                "phase": phase_name,
                "host_role": tpl["host_role"],
                "actor": tpl["actor"],
                # `telemetry` renders the milestone as a plausible log line.
                # It must NOT name the milestone or quote the source: an
                # earlier version wrote "[MILESTONE: imds_credentials] <source
                # quote>" into this field, which is the answer key written
                # into the text a model under evaluation reads.
                "event": m["telemetry"],
                "artifact_refs": [f"log://{phase_name}/{_parse(m['t_utc']).strftime('%Y%m%d')}/ms-{m['name'][:12]}.json"],
                "milestone_name": m["name"],
                "mitre_technique": m.get("mitre_technique"),
                "mitre_tactic": m.get("mitre_tactic"),
                "mitre_confidence": m.get("mitre_confidence", "unmapped"),
                "gt_malicious": phase_malicious,
                "gt_severity": phase_cfg["default_severity"],
                "citation": f"ground_truth.yaml#milestones[{m['name']}]",
                "is_milestone": True,
                "t_utc_estimated": m["t_utc_estimated"],
            })

        for t in filler_times:
            tpl = random.choice(templates)
            rows.append({
                "t_utc": _fmt(t),
                "phase": phase_name,
                "host_role": tpl["host_role"],
                "actor": tpl["actor"],
                # render_event fills {placeholders} per row. Without it the
                # bulk phases would be ~14 fixed strings repeated hundreds of
                # times each, which is its own separability signal and does
                # not look like a log (templates.py RULE 5).
                "event": render_event(tpl["event"], random),
                "artifact_refs": [f"log://{phase_name}/{t.strftime('%Y%m%d')}/{random.randint(1000, 9999)}.json"],
                "milestone_name": None,
                "mitre_technique": tpl["mitre_technique"],
                "mitre_tactic": tpl["mitre_tactic"],
                "mitre_confidence": "synthetic",
                "gt_malicious": phase_malicious,
                "gt_severity": tpl.get("severity", phase_cfg["default_severity"]),
                "citation": "synthetic filler - template bank, not sourced (scaffold per PLAN.md)",
                "is_milestone": False,
                "t_utc_estimated": False,
            })

    rows.sort(key=lambda r: r["t_utc"])
    for i, r in enumerate(rows, start=1):
        # LOCAL index for this single-phase prototype only. The real build
        # merges all phases + unclassified, sorts by t_utc, THEN assigns
        # the global action_idx.
        r["action_idx"] = i

    return rows


# --- model-visible projection -------------------------------------------
# Fields a model under evaluation is allowed to see. Everything else in a
# row is ground truth or scoring metadata. With the milestone-anchored
# escalation rule in force, "carries a pivotal tactic" is equivalent to
# "is the action we page on", so leaking mitre_tactic alone hands over the
# answer key. `phase` leaks too - "phase: exfil" is the finding, stated.
MODEL_VISIBLE_FIELDS = (
    "action_idx",
    "t_utc",
    "host_role",
    "actor",
    "event",
    "artifact_refs",
)

GROUND_TRUTH_ONLY_FIELDS = (
    "phase",
    "mitre_technique",
    "mitre_tactic",
    "mitre_confidence",
    "gt_malicious",
    "gt_severity",
    "citation",
    "is_milestone",
    "milestone_name",
    "t_utc_estimated",
)


def render_for_model(rows: list[dict]) -> list[dict]:
    """Project rows down to the fields a model may see. Every prompt-building
    path MUST go through this - never hand a raw corpus row to a model."""
    return [{k: r[k] for k in MODEL_VISIBLE_FIELDS if k in r} for r in rows]


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "k8s"
    rows = generate_phase(phase)
    out_path = OUT_DIR / f"prototype_{phase}.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    n_milestones = sum(1 for r in rows if r["is_milestone"])
    n_estimated = sum(1 for r in rows if r["t_utc_estimated"])
    print(f"wrote {len(rows)} actions to {out_path}")
    print(f"window: {rows[0]['t_utc']} -> {rows[-1]['t_utc']}")
    print(f"milestones placed: {n_milestones} ({n_estimated} with estimated, not sourced, timestamps)")
