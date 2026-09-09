"""
allocate.py

Solves the phase x day action-count allocation matrix: fixed row sums
(phase totals, including the `unclassified` residual row - see
ground_truth.yaml:phase_total_reconciliation) and fixed column sums
(daily totals), respecting per-phase day-eligibility (a phase can only
receive actions on days within its first_seen..last_seen window).

Both margins are published figures pulled directly from ground_truth.yaml,
never hardcoded here, so re-transcribing the source only requires editing
the yaml.

Algorithm:
  1. Seed a real-valued matrix over eligible cells only, weighted by each
     day's total volume, so higher-volume days start with a larger share
     of every phase.
  2. Run iterative proportional fitting (Sinkhorn/RAS) until both margins
     converge. Ineligible cells are re-zeroed every iteration, so IPF can
     never place a phase's actions on a day it wasn't seen.
  3. Round the converged fractional matrix to integers with a
     largest-remainder pass, then a bounded +1/-1 swap repair for any
     residual row/col drift the rounding introduces.
  4. Assert both margins match exactly and no ineligible cell is nonzero.
     build_corpus.py's test suite calls this before generating a single
     action row - if this module's asserts fail, nothing downstream runs.

Run directly (`python allocate.py`) to print the solved matrix.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml

GT_PATH = Path(__file__).parent / "ground_truth.yaml"


def load_ground_truth(path: Path = GT_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_eligibility_mask(gt: dict) -> tuple[list[str], list[str], np.ndarray]:
    phases = [p["name"] for p in gt["phases"]]
    days = [d["date"] for d in gt["daily_volumes"] if isinstance(d, dict) and "date" in d]
    day_index = {d: i for i, d in enumerate(days)}

    mask = np.zeros((len(phases), len(days)), dtype=bool)
    for i, p in enumerate(gt["phases"]):
        for d in p["days_eligible"]:
            mask[i, day_index[d]] = True
    return phases, days, mask


def get_totals(gt: dict) -> tuple[np.ndarray, np.ndarray]:
    row_totals = np.array([p["actions"] for p in gt["phases"]], dtype=float)
    col_totals = np.array(
        [d["actions"] for d in gt["daily_volumes"] if isinstance(d, dict) and "date" in d],
        dtype=float,
    )
    return row_totals, col_totals


def _ipf_seed(mask: np.ndarray, col_totals: np.ndarray) -> np.ndarray:
    seed = mask.astype(float) * col_totals[np.newaxis, :]
    row_sums = seed.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    return seed / row_sums  # normalized per row - IPF rescales to real totals below


def ipf_fit(
    mask: np.ndarray,
    row_totals: np.ndarray,
    col_totals: np.ndarray,
    max_iter: int = 500,
    tol: float = 1e-6,
) -> np.ndarray:
    total_mismatch = abs(row_totals.sum() - col_totals.sum())
    assert total_mismatch < 1e-6, (
        f"row/col totals must match before fitting: "
        f"{row_totals.sum()} vs {col_totals.sum()} (diff {total_mismatch}). "
        f"Check ground_truth.yaml:phase_total_reconciliation - the "
        f"`unclassified` row must absorb any gap between the phase table "
        f"and the daily-volume table before this function is called."
    )

    m = _ipf_seed(mask, col_totals) * row_totals[:, np.newaxis]
    m *= mask

    for _ in range(max_iter):
        row_sums = m.sum(axis=1)
        row_err = row_totals / np.where(row_sums == 0, 1, row_sums)
        m = m * row_err[:, np.newaxis] * mask

        col_sums = m.sum(axis=0)
        col_err = col_totals / np.where(col_sums == 0, 1, col_sums)
        m = m * col_err[np.newaxis, :] * mask

        if np.allclose(m.sum(axis=1), row_totals, atol=tol) and np.allclose(
            m.sum(axis=0), col_totals, atol=tol
        ):
            break
    return m


def controlled_round(
    m: np.ndarray,
    mask: np.ndarray,
    row_totals: np.ndarray,
    col_totals: np.ndarray,
) -> np.ndarray:
    """Round the fractional IPF matrix to integers while preserving both
    margins exactly: floor everything, hand out the leftover units to the
    eligible cells with the largest fractional remainder, then run a
    bounded swap repair for any residual drift."""
    row_totals = row_totals.astype(int)
    col_totals = col_totals.astype(int)

    floored = np.floor(m).astype(int)
    frac = m - floored

    leftover = int(round(row_totals.sum())) - int(floored.sum())
    eligible_idx = np.argwhere(mask)
    frac_at_eligible = frac[mask]
    order = np.argsort(-frac_at_eligible)
    for k in range(leftover):
        i, j = eligible_idx[order[k % len(order)]]
        floored[i, j] += 1

    result = floored.copy()
    for _ in range(20_000):
        row_diff = row_totals - result.sum(axis=1)
        col_diff = col_totals - result.sum(axis=0)
        if np.all(row_diff == 0) and np.all(col_diff == 0):
            break

        moved = False
        i_short_candidates = np.where(row_diff > 0)[0]
        j_short_candidates = np.where(col_diff > 0)[0]
        for i in i_short_candidates:
            for j in j_short_candidates:
                if mask[i, j]:
                    result[i, j] += 1
                    moved = True
                    break
            if moved:
                break
        if moved:
            continue

        i_long_candidates = np.where(row_diff < 0)[0]
        j_long_candidates = np.where(col_diff < 0)[0]
        for i in i_long_candidates:
            for j in j_long_candidates:
                if mask[i, j] and result[i, j] > 0:
                    result[i, j] -= 1
                    moved = True
                    break
            if moved:
                break
        if moved:
            continue

        # last resort: shift one unit within an over-subscribed row from a
        # column that's over its target to one that's under it
        for i in range(mask.shape[0]):
            if row_diff[i] != 0:
                continue
            j_from = next(
                (j for j in range(mask.shape[1]) if mask[i, j] and col_diff[j] < 0 and result[i, j] > 0),
                None,
            )
            j_to = next((j for j in range(mask.shape[1]) if mask[i, j] and col_diff[j] > 0), None)
            if j_from is not None and j_to is not None:
                result[i, j_from] -= 1
                result[i, j_to] += 1
                moved = True
                break
        if not moved:
            raise RuntimeError(
                "controlled_round: no legal repair move found - the "
                "eligibility mask may be too sparse to satisfy both "
                "margins exactly. Check days_eligible windows in "
                "ground_truth.yaml for narrow phases (k8s, supply_chain, "
                "tailscale)."
            )
    return result


def allocate() -> tuple[list[str], list[str], np.ndarray]:
    gt = load_ground_truth()
    phases, days, mask = build_eligibility_mask(gt)
    row_totals, col_totals = get_totals(gt)

    fitted = ipf_fit(mask, row_totals, col_totals)
    integer_matrix = controlled_round(fitted, mask, row_totals, col_totals)

    assert (integer_matrix.sum(axis=1) == row_totals.astype(int)).all(), "phase totals broken after rounding"
    assert (integer_matrix.sum(axis=0) == col_totals.astype(int)).all(), "daily totals broken after rounding"
    assert (integer_matrix[~mask] == 0).all(), "action placed on a day the phase is not eligible for"

    return phases, days, integer_matrix


if __name__ == "__main__":
    phases, days, matrix = allocate()
    header = "phase".ljust(14) + "".join(d.rjust(8) for d in days) + "  total"
    print(header)
    for i, p in enumerate(phases):
        row = matrix[i]
        print(p.ljust(14) + "".join(str(v).rjust(8) for v in row) + f"  {row.sum()}")
    print("-" * len(header))
    col_sums = matrix.sum(axis=0)
    print("total".ljust(14) + "".join(str(v).rjust(8) for v in col_sums) + f"  {matrix.sum()}")
