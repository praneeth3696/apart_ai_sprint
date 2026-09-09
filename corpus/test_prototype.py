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
from escalation import escalation_point, pivotal_fraction
from generate_phase import (
    GROUND_TRUTH_ONLY_FIELDS,
    generate_phase,
    render_for_model,
)
from templates import PHASE_TEMPLATES

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

    placed_names = [r["milestone_name"] for r in placed]
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
        name = r["milestone_name"]
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
        name = r["milestone_name"]
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


# --- semantic / fidelity assertions -------------------------------------
# The seven structural tests above all passed on a corpus whose escalation
# ground truth fired at action #2 on an invented row. Structure being right
# is not the same as the data being fit for purpose; these check the latter.


def test_no_filler_template_carries_a_pivotal_tactic(gt):
    """Catches the bug at its source. If a template bank ever regains a
    Credential Access / Privilege Escalation entry, the escalation ground
    truth silently becomes an artifact of random.seed() again."""
    if not gt["corpus_fidelity_constraints"]["filler_may_carry_pivotal_tactic"]:
        pivotal = set(gt["corpus_fidelity_constraints"]["pivotal_tactics"])
        for phase_name, bank in PHASE_TEMPLATES.items():
            offenders = [t["event"] for t in bank if t["mitre_tactic"] in pivotal]
            assert not offenders, (
                f"{phase_name} filler bank carries pivotal tactic(s) - these "
                f"belong to milestones only: {offenders}"
            )


def test_escalation_point_lands_on_a_sourced_milestone(rows, gt):
    esc = escalation_point(rows, gt)
    assert esc is not None, "no escalation point found in the k8s phase"
    assert esc["is_milestone"], (
        f"escalation ground truth landed on action #{esc['action_idx']}, "
        f"which is synthetic filler ({esc['event'][:60]!r}) - the "
        f"pre-registered E1 trigger must be a sourced event, not an "
        f"artifact of random.seed()"
    )
    assert esc["citation"].startswith("ground_truth.yaml#milestones"), (
        f"escalation row's citation is not a milestone reference: {esc['citation']!r}"
    )


def test_pivotal_tactic_fraction_under_cap(rows, gt):
    """IDEA.md's framing depends on pivotal actions being the needle, not
    the haystack. Pre-fix this phase ran at 38%."""
    cap = gt["corpus_fidelity_constraints"]["max_pivotal_tactic_fraction_per_phase"]
    frac = pivotal_fraction(rows, gt)
    assert frac <= cap, (
        f"{frac:.1%} of rows carry a pivotal tactic, over the {cap:.0%} cap - "
        f"the needle has become the haystack"
    )


def test_model_visible_projection_leaks_no_ground_truth(rows):
    """render_for_model() is the only sanctioned path from corpus to prompt.
    If it ever emits a scoring field, every model result is invalid: with the
    milestone-anchored rule, mitre_tactic alone identifies the page point."""
    visible = render_for_model(rows)
    assert len(visible) == len(rows)
    for v in visible:
        leaked = set(v) & set(GROUND_TRUTH_ONLY_FIELDS)
        assert not leaked, f"model-visible row leaks ground truth: {leaked}"


def test_milestone_event_text_does_not_announce_itself(rows, gt):
    """The event string is read verbatim by the model. It must not name the
    milestone, say MILESTONE, or quote the source - an earlier version wrote
    '[MILESTONE: imds_credentials] \"On worker startup...\"' into this field."""
    names = {m["name"] for m in gt["milestones"]}
    for r in rows:
        ev = r["event"]
        assert "MILESTONE" not in ev.upper(), (
            f"action #{r['action_idx']} announces itself as a milestone: {ev[:70]!r}"
        )
        for n in names:
            assert n not in ev, (
                f"action #{r['action_idx']} names milestone {n!r} in its event text"
            )


def test_milestone_and_filler_events_are_indistinguishable_in_shape(rows):
    """A milestone row that is 5x longer than every filler row is a length
    side-channel, whatever the text says."""
    ms = [len(r["event"]) for r in rows if r["is_milestone"]]
    fl = [len(r["event"]) for r in rows if not r["is_milestone"]]
    assert ms and fl
    ratio = (sum(ms) / len(ms)) / (sum(fl) / len(fl))
    assert 0.4 <= ratio <= 2.5, (
        f"milestone events average {sum(ms)/len(ms):.0f} chars vs filler "
        f"{sum(fl)/len(fl):.0f} (ratio {ratio:.2f}) - length alone separates them"
    )


def test_every_pivotal_row_is_a_milestone(rows, gt):
    pivotal = set(gt["corpus_fidelity_constraints"]["pivotal_tactics"])
    strays = [
        r["action_idx"] for r in rows
        if r.get("mitre_tactic") in pivotal and not r["is_milestone"]
    ]
    assert not strays, (
        f"{len(strays)} filler rows carry a pivotal tactic (action_idx "
        f"{strays[:10]}) - fabricated pivotal events in a corpus whose "
        f"claim is that its structure is sourced"
    )
