"""
build_windows.py

Emit the windowed artifacts the E1/E3 harnesses consume:

    corpus/windows/attack_windows.json  5-minute alert windows over attack_stream
    corpus/windows/benign_windows.json  the same over benign_stream (the control)
    corpus/windows/e3_moments.json      K=24 moments, stratified across phases

(paths per SPRINT_PLAN.md's "Windowed sets | corpus/windows/" row)

Windowing is the SOC abstraction (PLAN.md), so both streams go through the
SAME `windows.to_windows` - if the two were windowed differently, every
false-page comparison would be confounded by the binning.

Each emitted record keeps the model-visible evidence and the ground truth in
SEPARATE keys (`actions`/`evidence` vs `_gt`). Nothing downstream may pass
`_gt` to a model; that separation is the whole reason windows.py projects
through render_for_model.

Usage:
    python build_windows.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from windows import moments_stratified_by_phase, to_windows

CORPUS = Path(__file__).parent
OUT_DIR = CORPUS / "windows"   # a plain dir, NOT a package - see windows/README.md
ATTACK_STREAM = CORPUS / "attack_stream.jsonl"
BENIGN_STREAM = CORPUS / "benign_stream.jsonl"
ATTACK_WINDOWS = OUT_DIR / "attack_windows.json"
BENIGN_WINDOWS = OUT_DIR / "benign_windows.json"
E3_MOMENTS = OUT_DIR / "e3_moments.json"

WINDOW_MINUTES = 5
K_MOMENTS = 24
MOMENT_SPAN = 10


def _load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.open(encoding="utf-8")]


def _write(obj, path: Path) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def main() -> None:
    attack = _load(ATTACK_STREAM)
    benign = _load(BENIGN_STREAM)

    attack_w = to_windows(attack, minutes=WINDOW_MINUTES)
    benign_w = to_windows(benign, minutes=WINDOW_MINUTES)
    moments = moments_stratified_by_phase(attack, k=K_MOMENTS, span=MOMENT_SPAN)

    # Invariants worth failing on rather than discovering in the E1 run.
    assert sum(w["n_actions"] for w in attack_w) == len(attack), "attack windows dropped actions"
    assert sum(w["n_actions"] for w in benign_w) == len(benign), "benign windows dropped actions"
    assert all(not w["_gt"]["contains_milestone"] for w in benign_w), (
        "a benign window contains a milestone - the control is not benign"
    )
    covered = {m["anchor_phase"] for m in moments}
    expected = {r["phase"] for r in attack}
    assert covered == expected, (
        f"moments miss phase(s) {sorted(expected - covered)} - the point of "
        f"stratifying is that exfil/supply_chain/tailscale are represented"
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write(attack_w, ATTACK_WINDOWS)
    _write(benign_w, BENIGN_WINDOWS)
    _write(moments, E3_MOMENTS)

    print(f"attack : {len(attack):>6} actions -> {len(attack_w):>5} windows  ({ATTACK_WINDOWS.name})")
    print(f"benign : {len(benign):>6} actions -> {len(benign_w):>5} windows  ({BENIGN_WINDOWS.name})")
    print(f"  attack windows containing a milestone: "
          f"{sum(1 for w in attack_w if w['_gt']['contains_milestone'])}")
    print(f"  actions/window  attack min {min(w['n_actions'] for w in attack_w)} "
          f"max {max(w['n_actions'] for w in attack_w)} | "
          f"benign min {min(w['n_actions'] for w in benign_w)} "
          f"max {max(w['n_actions'] for w in benign_w)}")

    print(f"\n{len(moments)} E3 moments ({E3_MOMENTS.name}), anchor phase distribution:")
    dist = Counter(m["anchor_phase"] for m in moments)
    for phase, n in sorted(dist.items(), key=lambda kv: (-kv[1], kv[0])):
        ms = sum(1 for m in moments if m["anchor_phase"] == phase and m["anchor_is_milestone"])
        print(f"  {phase:<14} {n:>2}  ({ms} milestone-anchored)")
    print(f"  moments containing >=1 milestone: "
          f"{sum(1 for m in moments if m['_gt']['contains_milestone'])}/{len(moments)}")
    print(f"  moments at the escalation point   : "
          f"{sum(1 for m in moments if m['_gt']['is_escalation_point'])}")


if __name__ == "__main__":
    main()
