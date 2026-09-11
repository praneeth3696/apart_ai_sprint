"""
test_windows.py

Assertions for the windowing layer and the K=24 phase-stratified E3 sampler
(SPRINT_PLAN.md: "stratified across phases - include exfil, supply_chain,
tailscale, not just k8s").

Run:  pytest test_windows.py -v   (from corpus/)
"""
import pytest

from allocate import load_ground_truth
from build_benign import build_benign
from build_corpus import build_corpus
from generate_phase import GROUND_TRUTH_ONLY_FIELDS, MODEL_VISIBLE_FIELDS
from windows import moments_stratified_by_phase, to_windows

K = 24
SPAN = 10


@pytest.fixture(scope="module")
def gt():
    return load_ground_truth()


@pytest.fixture(scope="module")
def attack(gt):
    return build_corpus(gt)


@pytest.fixture(scope="module")
def benign(gt):
    return build_benign(gt)


@pytest.fixture(scope="module")
def moments(attack):
    return moments_stratified_by_phase(attack, k=K, span=SPAN)


def test_windowing_conserves_every_action(attack, benign):
    for rows in (attack, benign):
        assert sum(w["n_actions"] for w in to_windows(rows)) == len(rows)


def test_both_streams_use_identical_windowing(attack, benign):
    # If the streams were binned differently the false-page comparison would
    # be confounded by the binning rather than by the content.
    a, b = to_windows(attack), to_windows(benign)
    assert {w["end_utc"] > w["start_utc"] for w in a + b} == {True}
    assert all(w["n_actions"] > 0 for w in a + b)  # empty windows are dropped


def test_no_benign_window_contains_a_milestone(benign):
    assert all(not w["_gt"]["contains_milestone"] for w in to_windows(benign))


def test_moments_returns_exactly_k(moments):
    # Regression: an earlier version silently dropped colliding slices and
    # returned 22. Edge anchors all clamp to start 0, so collisions are normal
    # and must be backfilled, not discarded.
    assert len(moments) == K


def test_every_phase_is_represented(moments, attack):
    covered = {m["anchor_phase"] for m in moments}
    assert covered == {r["phase"] for r in attack}


def test_the_named_high_consequence_phases_appear(moments):
    covered = {m["anchor_phase"] for m in moments}
    for phase in ("exfil", "supply_chain", "tailscale", "k8s", "c2", "evasion"):
        assert phase in covered, f"{phase} missing - this is the bug being fixed"


def test_moments_are_distinct_slices(moments):
    ranges = [tuple(m["_gt"]["action_idx_range"]) for m in moments]
    assert len(set(ranges)) == len(ranges)


def test_not_every_moment_contains_a_milestone(moments):
    """Validity requirement, not aesthetics: if every moment were pivotal, a
    model that always escalates would score perfectly."""
    n_ms = sum(1 for m in moments if m["_gt"]["contains_milestone"])
    assert 0 < n_ms < len(moments)


def test_some_moments_are_milestone_anchored(moments):
    assert any(m["anchor_is_milestone"] for m in moments)


def test_moment_spans_are_the_requested_width(moments):
    assert all(len(m["evidence"]) == SPAN for m in moments)


def test_anchor_really_belongs_to_its_declared_phase(moments):
    for m in moments:
        assert m["anchor_phase"] in m["_gt"]["phases"], (
            f"moment {m['moment_idx']} claims anchor phase {m['anchor_phase']} "
            f"but its slice covers {m['_gt']['phases']}"
        )


def test_evidence_leaks_no_ground_truth(moments, attack, benign):
    allowed, forbidden = set(MODEL_VISIBLE_FIELDS), set(GROUND_TRUTH_ONLY_FIELDS)
    blocks = [m["evidence"] for m in moments]
    blocks += [w["actions"] for w in to_windows(attack)]
    blocks += [w["actions"] for w in to_windows(benign)]
    for block in blocks:
        for a in block:
            assert not (set(a) - allowed), f"unexpected field: {set(a) - allowed}"
            assert not (set(a) & forbidden), f"ground truth leaked: {set(a) & forbidden}"
