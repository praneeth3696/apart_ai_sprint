"""
test_prototype.py

Feasibility-spike assertions (TIMELINE.md, Tue 8) for the k8s-only
prototype. Run:  pytest test_prototype.py -v   (from corpus/)

This is a SUBSET of the eventual build_corpus.py assertion suite, scoped
to what a single-phase prototype can actually prove:
  - action count matches the published phase total exactly
  - every row falls inside the published first/last window
  - per-day counts match allocate.py's solved matrix
  - action_idx is dense and time-sorted
  - milestones appear, in the right order, correctly tagged
  - every row satisfies the full schema
  - no filler row is dressed up as a sourced fact

It CANNOT prove: cross-phase daily totals (needs all 9 phases +
`unclassified` generated together - that's the Friday run), or the true
global escalation ground truth (needs the whole corpus, not one phase).
"""
from datetime import datetime

import pytest

from allocate import allocate, load_ground_truth
from generate_phase import generate_phase

PHASE = "k8s"


@pytest.fixture(scope="module")
def gt():
    return load_ground_truth()


@pytest.fixture(scope="module")
def phase_cfg(gt):
    return next(p for p in gt["phases"] if p["name"] == PHASE)


@pytest.fixture(scope="module")
def rows():
    return generate_phase(PHASE)


def test_count_matches_published_total(rows, phase_cfg):
    assert len(rows) == phase_cfg["actions"]


def test_all_rows_within_published_window(rows, phase_cfg):
    first = datetime.fromisoformat(phase_cfg["first_seen"].replace("Z", "+00:00"))
    last = datetime.fromisoformat(phase_cfg["last_seen"].replace("Z", "+00:00"))
    for r in rows:
        t = datetime.fromisoformat(r["t_utc"].replace("Z", "+00:00"))
        assert first <= t <= last, (
            f"{r['t_utc']} outside published window "
            f"{phase_cfg['first_seen']}..{phase_cfg['last_seen']}"
        )


def test_daily_counts_match_allocation_matrix(rows):
    phases, days, matrix = allocate()
    phase_idx = phases.index(PHASE)
    expected = dict(zip(days, matrix[phase_idx].tolist()))

    actual: dict[str, int] = {}
    for r in rows:
        date_key = r["t_utc"][5:10]  # "MM-DD"
        actual[date_key] = actual.get(date_key, 0) + 1

    for day, expected_n in expected.items():
        assert actual.get(day, 0) == expected_n, (
            f"{day}: expected {expected_n}, got {actual.get(day, 0)}"
        )


def test_action_idx_is_dense_and_time_sorted(rows):
    idxs = [r["action_idx"] for r in rows]
    assert idxs == list(range(1, len(rows) + 1))
    times = [r["t_utc"] for r in rows]
    assert times == sorted(times)


def test_milestones_present_correctly_ordered_and_tagged(rows, gt):
    expected_milestones = sorted(
        (m for m in gt["milestones"] if m["phase"] == PHASE),
        key=lambda m: m["order"],
    )
    placed = [r for r in rows if r["is_milestone"]]
    assert len(placed) == len(expected_milestones), (
        f"expected {len(expected_milestones)} {PHASE} milestones, "
        f"placed {len(placed)}"
    )

    placed_names = [r["event"].split("MILESTONE: ")[1].split("]")[0] for r in placed]
    expected_names = [m["name"] for m in expected_milestones]
    assert placed_names == expected_names, (
        f"milestone ORDER not preserved: placed {placed_names}, "
        f"expected {expected_names}"
    )

    for r in placed:
        assert r["phase"] == PHASE


def test_every_row_has_full_schema(rows):
    required = {
        "action_idx", "t_utc", "phase", "host_role", "actor", "event",
        "artifact_refs", "mitre_technique", "gt_malicious", "gt_severity",
        "citation",
    }
    for r in rows:
        missing = required - r.keys()
        assert not missing, f"row {r['action_idx']} missing fields: {missing}"


def test_milestone_mitre_tags_come_from_ground_truth_not_random_filler(rows, gt):
    by_name = {m["name"]: m for m in gt["milestones"] if m["phase"] == PHASE}
    for r in rows:
        if not r["is_milestone"]:
            continue
        name = r["event"].split("MILESTONE: ")[1].split("]")[0]
        expected = by_name[name]
        assert r["mitre_technique"] == expected.get("mitre_technique"), (
            f"{name}: row has mitre_technique={r['mitre_technique']!r}, "
            f"ground_truth.yaml says {expected.get('mitre_technique')!r} - "
            f"looks like it was borrowed from a filler template again"
        )
        assert r["mitre_tactic"] == expected.get("mitre_tactic")


def test_estimated_milestones_respect_their_own_not_after_bound(rows, gt):
    from datetime import datetime as dt

    by_name = {m["name"]: m for m in gt["milestones"] if m["phase"] == PHASE}
    for r in rows:
        if not r["is_milestone"]:
            continue
        name = r["event"].split("MILESTONE: ")[1].split("]")[0]
        not_after = by_name[name].get("not_after")
        if not_after:
            bound = dt.fromisoformat(not_after.replace("Z", "+00:00"))
            actual = dt.fromisoformat(r["t_utc"].replace("Z", "+00:00"))
            assert actual <= bound, (
                f"{name}: placed at {r['t_utc']}, past its sourced "
                f"not_after bound {not_after}"
            )


def test_no_two_rows_share_a_timestamp(rows):
    times = [r["t_utc"] for r in rows]
    dupes = {t for t in times if times.count(t) > 1}
    assert not dupes, f"duplicate timestamps: {dupes}"


def test_filler_rows_never_masquerade_as_sourced(rows):
    for r in rows:
        if not r["is_milestone"]:
            citation = r["citation"].lower()
            assert "synthetic" in citation or "not sourced" in citation, (
                f"row {r['action_idx']} is filler but its citation doesn't "
                f"say so: {r['citation']!r}"
            )
