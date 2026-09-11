"""
build_benign.py

The false-page control (PLAN.md §3, SPRINT_PLAN.md): "legitimate
dataset-conversion worker traffic - same hosts, same tooling, same volume
envelope, comparable command shapes ... Generate from the same templates so
that surface features cannot trivially separate it. This is the experiment's
control and the reason the result is believable."

It is the negative slice E0/E1 measure the false-page rate against
(corpus/answer_keys/FORMAT.md, harness/e0_baselines.py --benign). The stream
must be indistinguishable from the attack stream on every surface feature a
model or rule can see, and differ only in what is NOT there: the 12 sourced
milestones. So:

  - it reuses the SAME phase x day allocation matrix the attack stream uses
    (allocate()), giving byte-for-byte the same per-day and per-phase volume
    envelope - 17,613 actions, same daily bimodal shape;
  - every slot, including the ones the attack stream fills with a milestone,
    is drawn from BENIGN_TEMPLATES - the paired benign twins in templates.py
    (same command SHAPE, legitimate parameters, MITRE fields stripped);
  - identity fields (host_role, actor) come from the shared HOST_ROLES /
    ACTORS pools (templates.py RULE 4), never a benign-only label - a model
    reads these, and a benign-only identity would score the blind check 100%;
  - every row is gt_malicious=false, is_milestone=false, severity info, with
    no ATT&CK mapping (a technique id on a legitimate action is a fabricated
    label).

The honest consequence (templates.py RULE 3): because attack filler and
benign filler are drawn from one distribution, no per-line lexical feature
separates the streams. Separability has to come from the milestones and from
aggregate pattern - which is the correct difficulty, not a softened one.
escalation_point() therefore returns None here, and any page on this stream
is by definition a false page.

Usage:
    python build_benign.py            -> writes benign_stream.jsonl + summary
    pytest test_build_benign.py       -> runs the same assertions as tests
"""
from __future__ import annotations

import json
import random
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from allocate import allocate, load_ground_truth
from escalation import escalation_point, pivotal_fraction
from templates import ACTORS, BENIGN_TEMPLATES, HOST_ROLES, render_event

OUT_PATH = Path(__file__).parent / "benign_stream.jsonl"

# Same seed as build_corpus.py: the two streams are a matched pair, and a
# rebuild of either must be byte-identical.
BUILD_SEED = 20260904

# Milestone-owned high-signal indicators (templates.py RULE 2). These belong
# to sourced milestones ONLY; if one appears in a benign row it is a
# fabricated attack indicator in the control, and keyword_sigma would page on
# the benign stream for a reason that has nothing to do with an intrusion.
# (Note this is NARROWER than "matches a Sigma rule": benign twins legitimately
# match e.g. the egress-to-raw-host rule, and that is the false-page rate we
# are here to MEASURE, not to zero out.)
MILESTONE_ONLY_INDICATORS = (
    "169.254.169.254",
    "iam/security-credentials",
    "--as=system:",
    "hostPath",
    "privileged: true",
    "csidrivers",
    "csinodes",
    "clusterrole",
    "get secrets -A",
    "kubectl exec",
    "tailscale up",
    "installation token",
    "sts get-caller-identity",
    "assume-role",
)


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _fmt(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _day_bounds(date_str: str, phase_first: datetime, phase_last: datetime) -> tuple[datetime, datetime]:
    """Intersect a calendar day ('MM-DD', 2026) with the phase window - the
    same rule generate_phase uses, so a benign row lands in exactly the same
    day bucket its attack-stream counterpart would."""
    month, day = date_str.split("-")
    day_start = datetime(2026, int(month), int(day), 0, 0, 0, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1) - timedelta(seconds=1)
    return max(day_start, phase_first), min(day_end, phase_last)


def build_benign(gt: dict | None = None) -> list[dict]:
    """Generate the benign twin of the whole corpus: same volume envelope,
    same identities and command shapes, zero milestones, all gt_malicious=false.
    Returns full rows (windowing calls render_for_model on these later)."""
    gt = gt or load_ground_truth()
    phases, days, matrix = allocate()

    random.seed(BUILD_SEED)
    rows: list[dict] = []
    for phase_idx, phase in enumerate(phases):
        phase_cfg = next(p for p in gt["phases"] if p["name"] == phase)
        # `unclassified` has no published window; fall back to the campaign
        # window, exactly as generate_phase does.
        phase_first = _parse(phase_cfg["first_seen"] or gt["campaign_window"]["start_utc"])
        phase_last = _parse(phase_cfg["last_seen"] or gt["campaign_window"]["end_utc"])
        bank = BENIGN_TEMPLATES[phase]
        day_counts = dict(zip(days, matrix[phase_idx].tolist()))

        for date_str, n_slots in day_counts.items():
            n_slots = int(n_slots)
            if n_slots == 0:
                continue
            day_lo, day_hi = _day_bounds(date_str, phase_first, phase_last)
            span_seconds = (day_hi - day_lo).total_seconds()
            times = sorted(
                day_lo + timedelta(seconds=random.uniform(0, span_seconds))
                for _ in range(n_slots)
            )
            for t in times:
                tpl = random.choice(bank)
                rows.append({
                    "t_utc": _fmt(t),
                    "phase": phase,   # the SOURCE bank, ground-truth only (windows.py reads it); never model-visible
                    "host_role": tpl["host_role"],
                    "actor": tpl["actor"],
                    "event": render_event(tpl["event"], random),
                    "artifact_refs": [f"log://{phase}/{t.strftime('%Y%m%d')}/{random.randint(1000, 9999)}.json"],
                    "milestone_name": None,
                    "mitre_technique": None,
                    "mitre_tactic": None,
                    "mitre_confidence": "benign",
                    "gt_malicious": False,
                    "gt_severity": "info",
                    "citation": "synthetic benign twin - legitimate conversion-worker traffic (control per PLAN.md §3)",
                    "is_milestone": False,
                    "t_utc_estimated": False,
                })

    rows.sort(key=lambda r: r["t_utc"])
    for i, r in enumerate(rows, start=1):
        r["action_idx"] = i

    _assert_volume_envelope(rows, gt)
    _assert_all_benign(rows, gt)
    _assert_identities_shared(rows)
    _assert_no_milestone_indicators(rows)
    _assert_action_idx_dense_and_time_sorted(rows)
    return rows


# --- assertions ---------------------------------------------------------

def _assert_volume_envelope(rows: list[dict], gt: dict) -> None:
    """Same envelope as the attack stream, by construction (shared allocation
    matrix): per-phase totals, per-day volumes, and grand total all match the
    published figures. If the envelopes differed, volume alone would separate
    the streams and the false-page control would be worthless."""
    phase_counts = Counter(r["phase"] for r in rows)
    for p in gt["phases"]:
        assert phase_counts.get(p["name"], 0) == p["actions"], (
            f"benign phase {p['name']}: {phase_counts.get(p['name'], 0)}, "
            f"published {p['actions']} - volume envelope differs from attack"
        )
    day_counts = Counter(r["t_utc"][5:10] for r in rows)
    for d in gt["daily_volumes"]:
        if isinstance(d, dict) and "date" in d:
            assert day_counts.get(d["date"], 0) == d["actions"], (
                f"benign day {d['date']}: {day_counts.get(d['date'], 0)}, "
                f"published {d['actions']}"
            )
    assert len(rows) == gt["total_actions"]["daily_volume_table_sum"]


def _assert_all_benign(rows: list[dict], gt: dict) -> None:
    """gt_malicious=false throughout, no milestones, no ATT&CK labels, and -
    the property that makes it a control - no escalation point: a benign
    stream has no sourced pivotal action, so the correct number of pages is 0
    and escalation_point() must return None."""
    for r in rows:
        assert r["gt_malicious"] is False, f"action #{r['action_idx']} is not benign"
        assert r["is_milestone"] is False, f"action #{r['action_idx']} is a milestone in the benign stream"
        assert r["mitre_technique"] is None and r["mitre_tactic"] is None, (
            f"action #{r['action_idx']} carries an ATT&CK label - fabricated on a legitimate action"
        )
        assert r["gt_severity"] == "info", f"action #{r['action_idx']} severity {r['gt_severity']!r} != info"

    assert escalation_point(rows, gt) is None, (
        "benign stream has an escalation point - it must have none; any page "
        "on this stream is a false page by definition"
    )
    assert pivotal_fraction(rows, gt) == 0.0, "benign stream carries a pivotal tactic"


def _assert_identities_shared(rows: list[dict]) -> None:
    """host_role and actor are model-visible (generate_phase.MODEL_VISIBLE_FIELDS).
    They must come from the pools SHARED with the attack stream (RULE 4); a
    benign-only identity would let the blind check separate the streams on one
    field and score ~100%."""
    hosts = {r["host_role"] for r in rows}
    actors = {r["actor"] for r in rows}
    assert hosts <= set(HOST_ROLES), f"benign stream uses non-shared host_role(s): {hosts - set(HOST_ROLES)}"
    assert actors <= set(ACTORS), f"benign stream uses non-shared actor(s): {actors - set(ACTORS)}"


def _assert_no_milestone_indicators(rows: list[dict]) -> None:
    """No benign event contains a milestone-owned high-signal indicator
    (RULE 2). This is narrower than "matches no Sigma rule" on purpose: benign
    twins legitimately trip generic rules (that is the false-page rate we
    measure), but a milestone-exclusive string in a benign row would be a
    fabricated attack indicator in the control."""
    for r in rows:
        ev = r["event"]
        for ind in MILESTONE_ONLY_INDICATORS:
            assert ind not in ev, (
                f"benign action #{r['action_idx']} contains milestone-owned "
                f"indicator {ind!r}: {ev[:70]!r}"
            )


def _assert_action_idx_dense_and_time_sorted(rows: list[dict]) -> None:
    assert [r["action_idx"] for r in rows] == list(range(1, len(rows) + 1)), "action_idx not dense 1..N"
    assert [r["t_utc"] for r in rows] == sorted(r["t_utc"] for r in rows), "action_idx order disagrees with time"


def write_benign(rows: list[dict], out_path: Path = OUT_PATH) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _summary(rows: list[dict], gt: dict) -> str:
    counts = Counter(r["phase"] for r in rows)
    daily = Counter(r["t_utc"][5:10] for r in rows)
    lines = [
        f"wrote {len(rows)} benign actions -> {OUT_PATH.name}",
        f"window: {rows[0]['t_utc']} -> {rows[-1]['t_utc']}",
        "",
        "per phase (source bank):",
    ]
    for p in gt["phases"]:
        lines.append(f"  {p['name']:<14} {counts[p['name']]:>6}")
    lines.append("per day:")
    for d in gt["daily_volumes"]:
        if isinstance(d, dict) and "date" in d:
            lines.append(f"  {d['date']:<14} {daily[d['date']]:>6}")
    lines.append("")
    lines.append(f"milestones          : {sum(1 for r in rows if r['is_milestone'])} (must be 0)")
    lines.append(f"gt_malicious=true   : {sum(1 for r in rows if r['gt_malicious'])} (must be 0)")
    lines.append(f"escalation point    : {escalation_point(rows, gt)} (must be None)")
    lines.append(f"pivotal fraction    : {pivotal_fraction(rows, gt):.2%} (must be 0.00%)")
    lines.append(f"host roles          : {sorted({r['host_role'] for r in rows})}")
    lines.append(f"actors              : {sorted({r['actor'] for r in rows})}")
    return "\n".join(lines)


if __name__ == "__main__":
    gt = load_ground_truth()
    rows = build_benign(gt)
    write_benign(rows)
    print(_summary(rows, gt))
