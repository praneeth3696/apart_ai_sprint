"""
build_corpus.py

The Friday run (TIMELINE.md). generate_phase.py proved the pipeline on one
phase; this merges all 10 banks into the single attack stream:

    1. generate every phase + the `unclassified` residual row,
    2. global time-sort across phases,
    3. assign the GLOBAL action_idx (the per-phase index generate_phase
       writes is local and is overwritten here - see its docstring),
    4. write corpus/attack_stream.jsonl,
    5. assert the three published invariants PLAN.md requires: phase totals,
       daily volumes, and milestone placement/order.

The assertions are the point of this file, not a sanity garnish. Every
number they check against is read from ground_truth.yaml, never hardcoded
here, so the only way to change an expected count is to edit the source.

Usage:
    python build_corpus.py            -> writes attack_stream.jsonl + prints summary
    pytest test_build_corpus.py       -> runs the same assertions as tests
"""
from __future__ import annotations

import json
import random
from collections import Counter
from datetime import datetime
from pathlib import Path

from allocate import allocate, load_ground_truth
from escalation import escalation_point, pivotal_fraction, reference_lines
from generate_phase import generate_phase

OUT_PATH = Path(__file__).parent / "attack_stream.jsonl"

# One seed for the whole build so a rebuild is byte-identical. generate_phase
# uses the module-global `random`, so seeding here - once, before the fixed
# phase-order loop below - makes every phase's filler placement deterministic.
# (generate_phase.py sets its own seed at import for the standalone prototype;
# this reseed is the "re-seed per run for the real build" its comment asks for.)
BUILD_SEED = 20260904


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def build_corpus(gt: dict | None = None) -> list[dict]:
    """Generate, merge, globally sort, and globally index all phases. Returns
    the full ground-truth rows (NOT the model-visible projection - windowing
    calls generate_phase.render_for_model on these later)."""
    gt = gt or load_ground_truth()
    # `allocate()` fixes the phase list/order and the day columns; iterating it
    # (rather than PHASE_TEMPLATES.keys()) keeps generation order stable and
    # tied to the same solved matrix generate_phase places against.
    phases, _days, _matrix = allocate()

    random.seed(BUILD_SEED)
    rows: list[dict] = []
    for phase in phases:
        rows.extend(generate_phase(phase))

    # Global time-sort. Python's sort is stable, so rows sharing a timestamp
    # keep their generation order (phase order, then within-phase order) -
    # a deterministic, documented tie-break rather than an arbitrary one.
    rows.sort(key=lambda r: r["t_utc"])
    for i, r in enumerate(rows, start=1):
        r["action_idx"] = i

    _assert_phase_totals(rows, gt)
    _assert_daily_volumes(rows, gt)
    _assert_milestone_order(rows, gt)
    _assert_action_idx_dense_and_time_sorted(rows)
    return rows


# --- assertions ---------------------------------------------------------
# Each reads its expected values straight from ground_truth.yaml.

def _assert_phase_totals(rows: list[dict], gt: dict) -> None:
    """Every phase (the 9 kill-chain phases AND the `unclassified` residual)
    contributes exactly its published action count. This is the constraint
    the phase table (16,521) pins; the `unclassified` row (1,092) is what
    makes the two published tables reconcilable - see
    ground_truth.yaml:phase_total_reconciliation."""
    counts = Counter(r["phase"] for r in rows)
    for p in gt["phases"]:
        got = counts.get(p["name"], 0)
        assert got == p["actions"], (
            f"phase {p['name']}: generated {got}, published total is "
            f"{p['actions']} (ground_truth.yaml:phases). A phase total drifting "
            f"means generate_phase placed the wrong count - do not adjust the "
            f"published figure."
        )
    # No stray phase labels the yaml doesn't define.
    unknown = set(counts) - {p["name"] for p in gt["phases"]}
    assert not unknown, f"rows carry phase label(s) not in ground_truth.yaml: {unknown}"

    expected_total = sum(p["actions"] for p in gt["phases"])
    assert len(rows) == expected_total, (
        f"corpus has {len(rows)} rows, phase totals sum to {expected_total}"
    )


def _assert_daily_volumes(rows: list[dict], gt: dict) -> None:
    """Each calendar day carries exactly its published volume, summed across
    ALL phases. This is the cross-phase check the single-phase prototype could
    not make (test_prototype.py header): it is only satisfiable because the
    `unclassified` row absorbs the 1,092-action gap between the phase table
    and the daily-volume table."""
    counts = Counter(r["t_utc"][5:10] for r in rows)  # "MM-DD"
    daily = [d for d in gt["daily_volumes"] if isinstance(d, dict) and "date" in d]
    for d in daily:
        got = counts.get(d["date"], 0)
        assert got == d["actions"], (
            f"day {d['date']}: {got} actions across all phases, published "
            f"daily volume is {d['actions']} (ground_truth.yaml:daily_volumes)"
        )
    # No actions landed on a day outside the published daily-volume table.
    unknown_days = set(counts) - {d["date"] for d in daily}
    assert not unknown_days, f"actions on day(s) not in the daily-volume table: {unknown_days}"

    expected_total = gt["total_actions"]["daily_volume_table_sum"]
    assert len(rows) == expected_total, (
        f"corpus has {len(rows)} rows, daily-volume table sums to "
        f"{expected_total} (this is the authoritative total per "
        f"ground_truth.yaml:total_actions)"
    )


def _assert_milestone_order(rows: list[dict], gt: dict) -> None:
    """Milestone placement invariants across the merged stream:

      - every milestone defined in ground_truth.yaml appears exactly once
        (the merge is where a dropped milestone finally shows up as a count
        mismatch - this is exactly how tailscale_key_extracted's phase bug
        was caught, per generate_phase.py's placement assertion),
      - milestone rows are chronologically ordered in the stream, i.e.
        monotonic in t_utc and therefore in action_idx,
      - the pre-registered escalation ground truth lands on a SOURCED
        milestone, not synthetic filler.

    It deliberately does NOT assert the stream order equals the `order`
    field's sequence: `order` is the GLOBAL kill-chain sequence and is not
    chronological (tailscale_key_extracted is order 11 at 07-11 20:18, before
    node_impersonation, order 6 at 23:50). Placement is by clock; `order` is
    the published chain label. See generate_phase._phase_sequence."""
    defined = [m["name"] for m in gt["milestones"]]
    placed = [r for r in rows if r["is_milestone"]]
    placed_names = [r["milestone_name"] for r in placed]

    assert Counter(placed_names) == Counter(defined), (
        f"milestone SET/multiplicity differs.\n"
        f"  defined ({len(defined)}): {sorted(defined)}\n"
        f"  placed  ({len(placed_names)}): {sorted(placed_names)}\n"
        f"A milestone defined but not placed means its t_utc falls outside "
        f"its phase window; a duplicate means it was placed under two phases."
    )

    times = [r["t_utc"] for r in placed]
    assert times == sorted(times), (
        f"milestone rows are not in chronological order in the stream: "
        f"{list(zip(placed_names, times))}"
    )
    idxs = [r["action_idx"] for r in placed]
    assert idxs == sorted(idxs), "milestone action_idx sequence is not monotonic"

    # not_after bounds are sourced constraints (e.g.
    # admin_host_level_access_multi_cluster's "under 13 hours"); re-check them
    # on the merged corpus, not just per phase.
    by_name = {m["name"]: m for m in gt["milestones"]}
    for r in placed:
        na = by_name[r["milestone_name"]].get("not_after")
        if na:
            assert _parse(r["t_utc"]) <= _parse(na), (
                f"{r['milestone_name']} placed at {r['t_utc']}, past its "
                f"sourced not_after bound {na}"
            )

    # Pre-registered E1 trigger must be a documented milestone, campaign-wide.
    esc = escalation_point(rows, gt)
    assert esc is not None, "no escalation point in the full corpus"
    assert esc["is_milestone"] and esc["citation"].startswith("ground_truth.yaml#milestones"), (
        f"escalation ground truth landed on action #{esc['action_idx']} "
        f"({'milestone' if esc['is_milestone'] else 'FILLER'}, citation "
        f"{esc['citation']!r}) - the E1 page point must be a sourced milestone"
    )


def _assert_action_idx_dense_and_time_sorted(rows: list[dict]) -> None:
    """The global action_idx is 1..N dense and its order agrees with time -
    the property everything downstream (windowing, escalation index,
    PREREGISTRATION.md's frozen number) relies on."""
    assert [r["action_idx"] for r in rows] == list(range(1, len(rows) + 1)), (
        "global action_idx is not dense 1..N"
    )
    assert [r["t_utc"] for r in rows] == sorted(r["t_utc"] for r in rows), (
        "action_idx order disagrees with t_utc order"
    )


def write_corpus(rows: list[dict], out_path: Path = OUT_PATH) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _summary(rows: list[dict], gt: dict) -> str:
    counts = Counter(r["phase"] for r in rows)
    daily = Counter(r["t_utc"][5:10] for r in rows)
    esc = escalation_point(rows, gt)
    refs = reference_lines(rows)
    frac = pivotal_fraction(rows, gt)
    cap = gt["corpus_fidelity_constraints"]["max_pivotal_tactic_fraction_per_phase"]

    lines = [
        f"wrote {len(rows)} actions -> {OUT_PATH.name}",
        f"window: {rows[0]['t_utc']} -> {rows[-1]['t_utc']}",
        "",
        "per phase:",
    ]
    for p in gt["phases"]:
        lines.append(f"  {p['name']:<14} {counts[p['name']]:>6}")
    lines.append("per day:")
    for d in gt["daily_volumes"]:
        if isinstance(d, dict) and "date" in d:
            lines.append(f"  {d['date']:<14} {daily[d['date']]:>6}")

    n_ms = sum(1 for r in rows if r["is_milestone"])
    lines.append("")
    lines.append(f"milestones placed: {n_ms}/{len(gt['milestones'])}")
    if esc:
        lines.append(
            f"escalation point : action #{esc['action_idx']} @ {esc['t_utc']}  "
            f"[{esc['milestone_name']} / {esc['mitre_tactic']}]"
        )
    for label, r in refs.items():
        lines.append(
            f"{label:<17}: action #{r['action_idx']} @ {r['t_utc']}" if r
            else f"{label:<17}: not present"
        )
    status = "OK" if frac <= cap else "OVER CAP"
    lines.append(f"pivotal fraction : {frac:.2%} (cap {cap:.0%}) [{status}]")
    return "\n".join(lines)


if __name__ == "__main__":
    gt = load_ground_truth()
    rows = build_corpus(gt)
    write_corpus(rows)
    print(_summary(rows, gt))
