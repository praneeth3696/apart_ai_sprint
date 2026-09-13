"""
figures.py

The paper's figures. Reads `analysis/e1_stats.json` (written by `stats.py`) and
recomputes the E0 rule baselines so models and rules land on the same axes.

FIGURE 1 — detection against false alarms. The paper's front page.
------------------------------------------------------------------
PLAN.md §4 originally specified the front page as an EAI timeline. That figure
is still produced (Figure 2) but it is no longer the headline, because on this
corpus first-page EAI is degenerate: every E0 detector fires at action #15–51,
~10,400 actions before the escalation point, on filler byte-identical in both
streams. See HANDOFF.md §5 and PREREGISTRATION.md §9 (2026-09-12).

What replaced it is the pair that actually separates a useful monitor from a
useless one:

    y = milestone-window hit rate   (did it catch the incident?)
    x = benign false-page rate      (does it cry wolf?)

The diagonal is the line of no discrimination — a detector on it pages just as
readily on innocent traffic as on the 12 windows that carry a milestone, and
has no information in it whatever its recall. Distance ABOVE the diagonal is
the only thing on this chart that is worth anything.

DESIGN NOTES (dataviz skill)
----------------------------
Colour encodes the ARM, not the model: frontier / open-weight / rule baseline.
That is a deliberate three-slot palette. A scatter puts every pair of colours
side by side, and the validated palette only clears the all-pairs CVD and
normal-vision floors for its first three slots — so one hue per model (14 of
them) would be unreadable for a colourblind reader and merely ugly for
everyone else. Individual models are identified by direct labels, which is
also the relief the aqua slot's sub-3:1 contrast requires, and marker SHAPE
carries the arm a second time so identity never rests on colour alone.

Light-mode only, deliberately: the output is a figure in a print PDF, so
there is no viewer theme to follow.

Usage:
    python analysis/stats.py            # first — writes e1_stats.json
    python analysis/figures.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
from matplotlib.lines import Line2D      # noqa: E402

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "analysis"))
sys.path.insert(0, str(REPO / "harness"))
sys.path.insert(0, str(REPO / "corpus"))

import stats as S                                            # noqa: E402
from e0_baselines import keyword_sigma, sev_threshold, volume_spike  # noqa: E402

STATS = REPO / "analysis" / "e1_stats.json"
FIGDIR = REPO / "analysis" / "figures"

# ---- palette (dataviz skill reference instance, validated all-pairs) -------
SURFACE = "#fcfcfb"
PAGE = "#f9f9f7"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
ARMS = {
    "frontier":  {"c": "#2a78d6", "m": "o", "label": "Frontier (Gemini, Google AI Studio)"},
    "open":      {"c": "#eb6834", "m": "s", "label": "Open-weight (Gemma, GPT-OSS, Qwen, Ministral)"},
    "rule":      {"c": "#1baf7a", "m": "^", "label": "Non-LLM rule baseline (E0)"},
}

plt.rcParams.update({
    "font.family": ["DejaVu Sans"],
    "font.size": 9,
    "figure.facecolor": PAGE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK2,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "grid.color": GRID,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def short(model: str) -> str:
    """A label a reader can match to the table without the provider prefix."""
    return model.split(":", 1)[-1].split("/")[-1]


def arm_of(model: str) -> str:
    name = model.lower()
    if any(k in name for k in ("gemma", "gpt-oss", "qwen", "allam", "ministral")):
        return "open"
    if model.startswith("google:gemini"):
        return "frontier"
    return "open"


# ---------------------------------------------------------------------------
def e0_points() -> list[dict]:
    """Recompute the rule baselines onto the SAME axes as the models.

    `analysis/e0_baselines.json` stores aggregate page rates, not per-window
    decisions, so the milestone hit rate is not recoverable from it — the
    detectors are re-run here instead. They cost no API calls, so this is free.

    Denominators, stated because they differ: the milestone hit rate is over
    all 12 milestone windows, which is the SAME census the models faced. The
    benign false-page rate is over all 1,280 benign windows rather than the
    models' 36-window sample — a larger sample of the same estimand, which is
    strictly better information, and the wider model intervals show the cost
    of not being able to afford it.
    """
    aw = json.loads((REPO / "corpus" / "windows" / "attack_windows.json")
                    .read_text(encoding="utf-8"))
    bw = json.loads((REPO / "corpus" / "windows" / "benign_windows.json")
                    .read_text(encoding="utf-8"))
    detectors = {
        "sev_threshold (ORACLE)": sev_threshold,
        "volume_spike": volume_spike,
        "keyword_sigma": keyword_sigma,
    }
    out = []
    for label, fn in detectors.items():
        a_pages = fn(aw)
        b_pages = fn(bw)
        ms = [p for w, p in zip(aw, a_pages) if w["_gt"]["contains_milestone"]]
        hit = S.rate(sum(ms), len(ms))
        fp = S.rate(sum(b_pages), len(b_pages))
        out.append({"label": label, "arm": "rule", "hit": hit, "fp": fp,
                    "oracle": "ORACLE" in label})
    return out


def model_points(stats: dict) -> list[dict]:
    out = []
    for model, s in stats["per_model"].items():
        hit, fp = s["milestone_hit_rate"], s["benign_false_page_rate"]
        if not hit["n"] or not fp["n"]:
            continue          # nothing to plot without both coordinates
        out.append({"label": short(model), "arm": arm_of(model),
                    "hit": hit, "fp": fp, "oracle": False})
    return out


# ---------------------------------------------------------------------------
def figure1(points: list[dict], path: pathlib.Path) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 6.1))
    ax.set_axisbelow(True)
    ax.grid(True, linewidth=0.6)

    # the line of no discrimination
    ax.plot([0, 1], [0, 1], linestyle=(0, (5, 4)), color=MUTED, linewidth=1.2,
            zorder=1)
    ax.annotate("no discrimination\n(pages as readily on benign\nas on milestones)",
                xy=(0.80, 0.80), xytext=(0.90, 0.52), color=MUTED, fontsize=7.2,
                ha="right", va="top",
                arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.8,
                                shrinkA=0, shrinkB=4))

    for p in points:
        spec = ARMS[p["arm"]]
        x, y = p["fp"]["rate"], p["hit"]["rate"]
        # Wilson intervals, drawn thin and behind the marks — the n here is
        # 10-36 and hiding that would be the dishonest choice.
        ax.plot([p["fp"]["ci95"][0], p["fp"]["ci95"][1]], [y, y],
                color=spec["c"], linewidth=1.0, alpha=0.35, zorder=2,
                solid_capstyle="butt")
        ax.plot([x, x], [p["hit"]["ci95"][0], p["hit"]["ci95"][1]],
                color=spec["c"], linewidth=1.0, alpha=0.35, zorder=2,
                solid_capstyle="butt")
        ax.scatter([x], [y], s=95, marker=spec["m"], color=spec["c"],
                   edgecolors=SURFACE, linewidths=1.6, zorder=4)

    # Direct labels. Also the relief the aqua slot's sub-3:1 contrast requires.
    _place_labels(ax, _merge_colocated(points))

    ax.set_xlim(-0.04, 1.04)
    ax.set_ylim(-0.04, 1.08)
    ax.set_xticks([0, .25, .5, .75, 1])
    ax.set_yticks([0, .25, .5, .75, 1])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    # Placed explicitly rather than via set_xlabel: with a figure-level legend
    # below the axes, matplotlib's own x-label placement kept landing on top
    # of it. Explicit y means the two cannot argue.
    fig.text(0.545, 0.168, "Benign false-page rate  →  cries wolf more often",
             color=INK2, fontsize=9, ha="center", va="center")
    ax.set_ylabel("Milestone-window hit rate  →  catches more of the incident",
                  color=INK2, labelpad=8)
    # Figure-level so it can use the full width; at axes-level it started at
    # the axes edge and ran off the right of the canvas.
    # Title states what the chart shows, and it changed once the Mistral arm
    # landed: "every model catches the intrusion" became false the moment a
    # model that catches none of it appeared in the bottom-left.
    fig.text(0.012, 0.968,
             "A useful monitor belongs in the top-left. Almost nothing is there.",
             color=INK, fontsize=11, fontweight="bold", va="center")
    fig.text(0.012, 0.933,
             "Models fail in both directions: paging on everything, or on nothing at all.",
             color=INK2, fontsize=8.5, va="center")

    # Legend OUTSIDE the axes. In-plot it sat on top of volume_spike at
    # (1.2%, 8%) — the one deployable rule baseline, and the point that shows
    # it catches 1 of 12 milestones. A legend that hides a datum is a bug.
    handles = [Line2D([], [], marker=s["m"], color="none",
                      markerfacecolor=s["c"], markeredgecolor=SURFACE,
                      markeredgewidth=1.4, markersize=9, label=s["label"])
               for s in ARMS.values()]
    leg = fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False,
                     fontsize=7.4, handletextpad=0.5, columnspacing=1.1,
                     bbox_to_anchor=(0.5, 0.098))
    for txt in leg.get_texts():
        txt.set_color(INK2)

    fig.text(0.012, 0.012,
             "Bars are Wilson 95% intervals. Hit rate is a census of all 12 "
             "milestone-carrying attack windows; false-page rate is a\n"
             "uniform sample of the matched benign control "
             "(n=12–36 per model; n=1,280 for the rule baselines).\n"
             "sev_threshold reads ground-truth severity: an upper bound, "
             "not a deployable detector.",
             fontsize=6.4, color=MUTED, va="bottom")
    # Four stacked bands, each given its own space: plot | x-label | legend |
    # footnote. Set explicitly rather than by tight_layout, and saved without
    # bbox_inches="tight" — each of those re-solves the layout on its own, and
    # between them they kept walking the legend on top of the x-axis label.
    fig.subplots_adjust(left=0.105, right=0.985, top=0.885, bottom=0.235)
    for ext in ("pdf", "png"):
        fig.savefig(path.with_suffix("." + ext), dpi=220, facecolor=PAGE)
    plt.close(fig)


# Rough data-space size of one 7.2pt character and one text line, on this
# figure's scale. Only needs to be close enough to keep boxes apart.
_CH_W, _LINE_H = 0.0118, 0.031


def _merge_colocated(points: list[dict], tol: float = 0.012) -> list[dict]:
    """Collapse points that sit on top of each other into one label.

    ministral-3b and ministral-8b both score 0/12 and 0/36 — they are the same
    dot, and two labels for one dot is unreadable. Merging says the true thing
    more clearly than stacking: these models are indistinguishable here.
    """
    out: list[dict] = []
    for p in points:
        for q in out:
            if (abs(p["fp"]["rate"] - q["fp"]["rate"]) < tol
                    and abs(p["hit"]["rate"] - q["hit"]["rate"]) < tol
                    and p["arm"] == q["arm"]):
                q["label"] = f"{q['label']} / {p['label'].split('-')[-2]}" \
                    if q["label"].count("/") < 2 else q["label"]
                break
        else:
            out.append(dict(p))
    return out


def _place_labels(ax, points: list[dict]) -> None:
    """Greedy label placement with a real bounding-box test.

    Labels must miss each other AND every data marker — this dataset piles most
    of its points into the top-right corner, so the naive "nudge up and right"
    version produced two overlapping pairs.
    """
    boxes: list[tuple[float, float, float, float]] = []
    for p in points:                       # markers are obstacles too
        x, y = p["fp"]["rate"], p["hit"]["rate"]
        boxes.append((x - 0.014, y - 0.020, x + 0.014, y + 0.020))

    def free(b) -> bool:
        return all(b[2] < o[0] or b[0] > o[2] or b[3] < o[1] or b[1] > o[3]
                   for o in boxes)

    for p in sorted(points, key=lambda d: (-d["hit"]["rate"], d["fp"]["rate"])):
        x, y = p["fp"]["rate"], p["hit"]["rate"]
        w, h = _CH_W * len(p["label"]), _LINE_H
        best = None
        for dy in (0.030, -0.038, 0.062, -0.070, 0.094, -0.102, 0.126, -0.134):
            for ha, dx in (("left", 0.018), ("right", -0.018),
                           ("left", 0.055), ("right", -0.055)):
                cx, cy = x + dx, y + dy
                x0 = cx if ha == "left" else cx - w
                y0 = cy - h / 2
                box = (x0, y0, x0 + w, y0 + h)
                # keep it on the canvas as well as off its neighbours
                if box[0] < -0.03 or box[2] > 1.05 or box[3] > 1.09:
                    continue
                if free(box):
                    best = (cx, cy, ha, box)
                    break
            if best:
                break
        if best is None:                   # nowhere clean; place and accept it
            best = (x + 0.018, y + 0.030, "left",
                    (x + 0.018, y + 0.013, x + 0.018 + w, y + 0.047))
        cx, cy, ha, box = best
        boxes.append(box)
        ax.annotate(p["label"], xy=(x, y), xytext=(cx, cy), ha=ha,
                    va="center", fontsize=7.2, color=INK2, zorder=5)


# ---------------------------------------------------------------------------
def figure2(stats: dict, path: pathlib.Path) -> None:
    """The EAI timeline PLAN.md §4 asked for — reported, but not as the
    headline. Its message is the clustering at the far left: every detector,
    model and rule alike, fires within the first ~50 actions of a 17,613-action
    stream, thousands of actions before anything worth paging about."""
    eai = stats.get("eai") or {}
    e0 = json.loads((REPO / "analysis" / "e0_baselines.json").read_text())
    refs = e0["attack"]["reference_lines"]

    rows = [(short(m), r["eai_action_idx"], arm_of(m))
            for m, r in eai.items() if r.get("eai_action_idx")]
    for label, det in e0["attack"]["detectors"].items():
        if det.get("eai"):
            rows.append((label, det["eai"]["action_idx"], "rule"))
    if not rows:
        return
    rows.sort(key=lambda r: r[1])

    fig_h = max(3.0, 0.34 * len(rows) + 2.2)
    fig, ax = plt.subplots(figsize=(7.2, fig_h))
    ax.set_axisbelow(True)
    ax.grid(True, axis="x", linewidth=0.6)

    for name, ref in (("first RCE", refs.get("first_rce")),
                      ("first exfil", refs.get("first_exfil")),
                      ("escalation point", refs.get("escalation_point"))):
        if not ref:
            continue
        crit = name == "escalation point"
        ax.axvline(ref["action_idx"], color="#d03b3b" if crit else MUTED,
                   linewidth=1.4 if crit else 1.0,
                   linestyle="-" if crit else (0, (4, 3)), zorder=1)
        ax.annotate(f"{name}\n#{ref['action_idx']:,}",
                    xy=(ref["action_idx"], len(rows) - 0.35),
                    xytext=(4, 0), textcoords="offset points",
                    fontsize=7, color="#d03b3b" if crit else MUTED,
                    va="top", ha="left")

    for i, (name, idx, arm) in enumerate(rows):
        spec = ARMS[arm]
        ax.plot([0, idx], [i, i], color=GRID, linewidth=1.0, zorder=2)
        ax.scatter([idx], [i], s=80, marker=spec["m"], color=spec["c"],
                   edgecolors=SURFACE, linewidths=1.5, zorder=4)

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=7.5, color=INK2)
    ax.set_ylim(-0.8, len(rows) - 0.2)
    ax.set_xlim(-300, 18200)
    ax.set_xlabel("Action index in the 17,613-action attack stream", color=INK2,
                  labelpad=8)
    fig.text(0.012, 1 - 0.30 / fig_h,
             "First page fires within the first ~50 actions — 10,000 before "
             "the escalation point",
             color=INK, fontsize=10.5, fontweight="bold", va="center")
    fig.text(0.012, 0.018,
             "Escalation Action Index: the first window each detector paged on, "
             "over the uniform attack sample. Reported for completeness — on this\ncorpus a "
             "first page measures trigger-happiness rather than detection, "
             "which is why Figure 1 and not this is the headline.",
             fontsize=6.4, color=MUTED, va="bottom")
    bottom = min(0.30, 1.15 / fig_h)
    fig.subplots_adjust(left=0.24, right=0.985, top=1 - 0.85 / fig_h, bottom=bottom)
    for ext in ("pdf", "png"):
        fig.savefig(path.with_suffix("." + ext), dpi=220, facecolor=PAGE)
    plt.close(fig)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--stats", default=str(STATS))
    p.add_argument("--outdir", default=str(FIGDIR))
    args = p.parse_args(argv)

    sp = pathlib.Path(args.stats)
    if not sp.is_file():
        print(f"no stats at {sp} — run analysis/stats.py first", file=sys.stderr)
        return 1
    st = json.loads(sp.read_text(encoding="utf-8"))
    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    pts = model_points(st) + e0_points()
    figure1(pts, outdir / "figure1_detection_vs_false_page")
    print(f"wrote {(outdir / 'figure1_detection_vs_false_page.pdf').relative_to(REPO)} (+ .png)")
    print(f"  {len(pts)} points: "
          + ", ".join(f"{k}={sum(1 for q in pts if q['arm'] == k)}" for k in ARMS))
    if st.get("eai"):
        figure2(st, outdir / "figure2_eai_timeline")
        print(f"wrote {(outdir / 'figure2_eai_timeline.pdf').relative_to(REPO)} (+ .png)")
    else:
        print("  (no EAI in stats — re-run: python analysis/stats.py --eai)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
