"""
test_build_benign.py

Assertion suite for the false-page control (build_benign.py). The benign
stream is the negative slice; its job is to be indistinguishable from the
attack stream on every surface feature and to differ only in the absence of
milestones. These tests enforce exactly that, and cross-check the pairing
against build_corpus.py where it matters.

Run:  pytest test_build_benign.py -v   (from corpus/)
"""
from collections import Counter

import pytest

from allocate import load_ground_truth
from build_benign import MILESTONE_ONLY_INDICATORS, build_benign
from build_corpus import build_corpus
from escalation import escalation_point, pivotal_fraction
from generate_phase import GROUND_TRUTH_ONLY_FIELDS, render_for_model
from templates import ACTORS, HOST_ROLES


@pytest.fixture(scope="module")
def gt():
    return load_ground_truth()


@pytest.fixture(scope="module")
def rows(gt):
    return build_benign(gt)


def test_volume_envelope_matches_published(rows, gt):
    phase_counts = Counter(r["phase"] for r in rows)
    for p in gt["phases"]:
        assert phase_counts.get(p["name"], 0) == p["actions"], p["name"]
    day_counts = Counter(r["t_utc"][5:10] for r in rows)
    for d in gt["daily_volumes"]:
        if isinstance(d, dict) and "date" in d:
            assert day_counts.get(d["date"], 0) == d["actions"], d["date"]
    assert len(rows) == gt["total_actions"]["daily_volume_table_sum"]


def test_volume_envelope_is_identical_to_attack_stream(gt):
    # The whole point of the control: the two streams share a per-day and
    # per-phase envelope, so volume/shape cannot separate them.
    attack = build_corpus(gt)
    benign = build_benign(gt)
    assert Counter(r["phase"] for r in attack) == Counter(r["phase"] for r in benign)
    assert Counter(r["t_utc"][5:10] for r in attack) == Counter(r["t_utc"][5:10] for r in benign)
    assert len(attack) == len(benign)


def test_everything_is_benign(rows):
    assert all(r["gt_malicious"] is False for r in rows)
    assert all(r["is_milestone"] is False for r in rows)
    assert all(r["milestone_name"] is None for r in rows)
    assert all(r["gt_severity"] == "info" for r in rows)


def test_no_attck_labels(rows):
    assert all(r["mitre_technique"] is None and r["mitre_tactic"] is None for r in rows)


def test_no_escalation_point_and_zero_pivotal(rows, gt):
    # A benign stream has no sourced pivotal action; the correct page count is
    # 0 and escalation_point must return None (any page here is a false page).
    assert escalation_point(rows, gt) is None
    assert pivotal_fraction(rows, gt) == 0.0


def test_identities_are_shared_not_benign_only(rows):
    # host_role and actor are model-visible; a benign-only value would let the
    # blind check separate the streams on one field (templates.py RULE 4).
    assert {r["host_role"] for r in rows} <= set(HOST_ROLES)
    assert {r["actor"] for r in rows} <= set(ACTORS)


def test_no_milestone_owned_indicator_leaks_into_benign(rows):
    for r in rows:
        for ind in MILESTONE_ONLY_INDICATORS:
            assert ind not in r["event"], (r["action_idx"], ind)


def test_action_idx_dense_and_time_sorted(rows):
    assert [r["action_idx"] for r in rows] == list(range(1, len(rows) + 1))
    assert [r["t_utc"] for r in rows] == sorted(r["t_utc"] for r in rows)


def test_model_visible_projection_leaks_no_ground_truth(rows):
    # Same guarantee build_corpus's rows give: the sanctioned corpus->prompt
    # path emits no scoring field.
    for v in render_for_model(rows):
        assert not (set(v) & set(GROUND_TRUTH_ONLY_FIELDS))


def test_build_is_deterministic(gt):
    a = build_benign(gt)
    b = build_benign(gt)
    assert [r["t_utc"] for r in a] == [r["t_utc"] for r in b]
    assert [r["event"] for r in a] == [r["event"] for r in b]
    assert [r["action_idx"] for r in a] == [r["action_idx"] for r in b]
