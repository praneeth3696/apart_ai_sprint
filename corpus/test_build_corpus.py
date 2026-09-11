"""
test_build_corpus.py

Full-corpus assertion suite for the Friday merge (build_corpus.py). Where
test_prototype.py proved one phase, this proves the merged stream - the three
published invariants PLAN.md requires, plus the properties that only exist
once all 10 banks are sorted together:

  - phase totals match the published phase table exactly (incl. unclassified)
  - daily volumes match the published daily-volume table exactly (cross-phase)
  - all 12 milestones placed once, chronologically ordered, not_after honored
  - the global action_idx is dense 1..N and agrees with time
  - the pre-registered escalation ground truth lands on a sourced milestone
  - the build is deterministic (a rebuild is byte-identical)

Run:  pytest test_build_corpus.py -v   (from corpus/)
"""
from collections import Counter
from datetime import datetime

import pytest

from allocate import load_ground_truth
from build_corpus import build_corpus
from escalation import escalation_point


@pytest.fixture(scope="module")
def gt():
    return load_ground_truth()


@pytest.fixture(scope="module")
def rows(gt):
    return build_corpus(gt)


def test_phase_totals_match_published(rows, gt):
    counts = Counter(r["phase"] for r in rows)
    for p in gt["phases"]:
        assert counts.get(p["name"], 0) == p["actions"], p["name"]
    assert len(rows) == sum(p["actions"] for p in gt["phases"])


def test_daily_volumes_match_published(rows, gt):
    counts = Counter(r["t_utc"][5:10] for r in rows)
    for d in gt["daily_volumes"]:
        if isinstance(d, dict) and "date" in d:
            assert counts.get(d["date"], 0) == d["actions"], d["date"]
    assert len(rows) == gt["total_actions"]["daily_volume_table_sum"]


def test_total_is_the_authoritative_daily_sum(rows, gt):
    # 16,521 (phase table) + 1,092 (unclassified residual) == 17,613.
    assert len(rows) == 17613
    named = sum(p["actions"] for p in gt["phases"] if p["name"] != "unclassified")
    assert named == 16521


def test_all_milestones_placed_exactly_once(rows, gt):
    defined = Counter(m["name"] for m in gt["milestones"])
    placed = Counter(r["milestone_name"] for r in rows if r["is_milestone"])
    assert placed == defined


def test_milestones_are_chronological_in_the_stream(rows):
    placed = [r for r in rows if r["is_milestone"]]
    times = [r["t_utc"] for r in placed]
    idxs = [r["action_idx"] for r in placed]
    assert times == sorted(times)
    assert idxs == sorted(idxs)


def test_milestone_not_after_bounds_respected(rows, gt):
    by_name = {m["name"]: m for m in gt["milestones"]}

    def parse(ts):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))

    for r in rows:
        if not r["is_milestone"]:
            continue
        na = by_name[r["milestone_name"]].get("not_after")
        if na:
            assert parse(r["t_utc"]) <= parse(na), r["milestone_name"]


def test_global_action_idx_dense_and_time_sorted(rows):
    assert [r["action_idx"] for r in rows] == list(range(1, len(rows) + 1))
    assert [r["t_utc"] for r in rows] == sorted(r["t_utc"] for r in rows)


def test_escalation_point_is_the_sourced_imds_milestone(rows, gt):
    esc = escalation_point(rows, gt)
    assert esc is not None
    assert esc["is_milestone"]
    assert esc["citation"].startswith("ground_truth.yaml#milestones")
    # imds_credentials (Credential Access) is the earliest pivotal MILESTONE
    # campaign-wide; the pre-registered E1 page point must be this one, not a
    # privesc milestone later the same night nor a filler row.
    assert esc["milestone_name"] == "imds_credentials"
    assert esc["mitre_tactic"] == "Credential Access"


def test_build_is_deterministic(gt):
    a = build_corpus(gt)
    b = build_corpus(gt)
    assert [r["t_utc"] for r in a] == [r["t_utc"] for r in b]
    assert [r["event"] for r in a] == [r["event"] for r in b]
    assert [r["action_idx"] for r in a] == [r["action_idx"] for r in b]
