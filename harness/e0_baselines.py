"""
e0_baselines.py

E0 - non-LLM rule baselines, added to the plan on 2026-09-10 (SPRINT_PLAN.md
section 1.2). Runs the SAME two streams, through the SAME windowing, against
the SAME escalation ground truth as E1, but with detectors that are not
models.

WHY THIS EXISTS
---------------
Without it, E1 reports "model X pages at window 12 with a 6% false-page rate"
and a reader has no idea whether that is good. With it, E1 reports a
comparison, and a comparison is a finding:

    "a fifteen-line keyword rule pages 40 windows earlier than the best model
     and at one-third the false-page rate"

    - or the reverse, which is equally publishable:

    "every rule baseline either misses the campaign entirely or pages on 30%
     of benign windows; only the LLM arm separates them"

It also answers SecureLayer7's question - "which action number does your
control fire on?" - for a control that is not a model, which is the Track 1
crossover claimed in the abstract.

Costs zero API calls and has no rate limit, so it can be re-run freely and it
survives any provider outage on Saturday.

THE FAIRNESS RULE
-----------------
`volume_spike` and `keyword_sigma` see ONLY the model-visible projection
(generate_phase.MODEL_VISIBLE_FIELDS) - the same bytes a model under
evaluation gets. If they read `phase` or `mitre_tactic` they would be reading
the answer key, and the comparison would be rigged in the rules' favour.

`sev_threshold` deliberately breaks that rule and reads `_gt.max_severity`.
It is not a competitor; it is the ORACLE - the upper bound on what any
detector could do if it already knew the answer. It is reported as such and
must never be described as a baseline a defender could deploy.

Usage:
    python harness/e0_baselines.py corpus/attack_stream.jsonl \
                                   --benign corpus/benign_stream.jsonl
    python harness/e0_baselines.py corpus/prototype_k8s.jsonl      # works today
"""
from __future__ import annotations

import json
import math
import pathlib
import re
import statistics
import sys
from datetime import datetime

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "corpus"))

from escalation import escalation_point, reference_lines  # noqa: E402
from windows import to_windows  # noqa: E402

OUT_PATH = REPO / "analysis" / "e0_baselines.json"


# --- detectors ----------------------------------------------------------
# Each takes the full window list and returns a list[bool], one page/no-page
# decision per window. Stateful detectors (volume_spike) get the whole list
# so they can build history; they must never look FORWARD of window i.

def sev_threshold(windows: list[dict], floor: str = "high") -> list[bool]:
    """ORACLE, not a baseline. Pages when the window contains an action whose
    ground-truth severity is >= `floor`. Reads `_gt`, which no deployable
    detector has access to. Reported as the upper bound only."""
    order = ["info", "low", "medium", "high", "critical"]
    cutoff = order.index(floor)
    return [order.index(w["_gt"]["max_severity"]) >= cutoff for w in windows]


def volume_spike(windows: list[dict], k: float = 3.0, history: int = 12,
                 min_history: int = 4) -> list[bool]:
    """Pages when a window's action count exceeds `k` x the median of the
    preceding `history` windows. Pure statistics, no semantics - this is the
    detector class HF's real stack most resembles, and the one Picus's
    proportions predict will fail: exfiltration was 56 actions out of ~17,600,
    so the thing you must catch is 0.3% of the traffic. A volume detector
    cannot see a needle.

    Model-visible fields only (n_actions is a count of rows, not a label)."""
    out: list[bool] = []
    counts: list[int] = []
    for w in windows:
        n = w["n_actions"]
        if len(counts) < min_history:
            out.append(False)
        else:
            med = statistics.median(counts[-history:])
            out.append(n >= k * max(med, 1))
        counts.append(n)
    return out


# A Sigma rule in spirit: what a competent SOC engineer writes in an
# afternoon, expressed as portable regexes over the command text. Every
# pattern below matches something already documented in a public post-mortem
# or in ordinary vendor hardening guidance. There is no exploit content here
# and nothing that is not already a detection signature someone ships.
SIGMA_RULES: list[tuple[str, str]] = [
    ("imds_credential_fetch",   r"169\.254\.169\.254"),
    ("iam_security_credentials", r"iam/security-credentials"),
    ("rbac_impersonation",      r"--as=system:"),
    ("serviceaccount_impersonation", r"--as=system:serviceaccount"),
    ("privileged_pod",          r"privileged[-_ ]?(?:pod|:\s*true)"),
    ("hostpath_mount",          r"hostPath|hostpath"),
    ("secret_enumeration",      r"get\s+secrets?\b.*(-A|--all-namespaces)"),
    ("exec_into_pod",           r"kubectl\s+exec\b"),
    ("clusterrole_inspect",     r"clusterrolebinding|clusterrole\b"),
    ("token_mint",              r"\btoken\b.*(mint|create|issue)|installation[-_ ]token"),
    ("tailscale_activity",      r"tailscale\s+(up|login|status)|tailscaled"),
    ("node_identity_call",      r"sts\s+get-caller-identity|assume-role"),
    ("mass_node_enum",          r"get\s+nodes\b.*-o\s+(json|yaml|wide)"),
    ("csi_driver_enum",         r"csidrivers|csinodes"),
    ("egress_to_raw_host",      r"curl\s+-s?\S*\s+http://(?!169\.254)"),
]

_COMPILED = [(name, re.compile(pat, re.IGNORECASE)) for name, pat in SIGMA_RULES]


def keyword_sigma(windows: list[dict]) -> list[bool]:
    """Pages when any action in the window matches any rule above.
    Model-visible fields only - it reads `event`, exactly what a model reads."""
    return [_sigma_hits(w) != [] for w in windows]


def _sigma_hits(window: dict) -> list[str]:
    hits = []
    for a in window["actions"]:
        text = a.get("event", "")
        for name, rx in _COMPILED:
            if rx.search(text) and name not in hits:
                hits.append(name)
    return hits


DETECTORS = {
    "sev_threshold(ORACLE)": sev_threshold,
    "volume_spike": volume_spike,
    "keyword_sigma": keyword_sigma,
}


# --- metrics ------------------------------------------------------------

def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a proportion. Closed form, identical to
    statsmodels.stats.proportion.proportion_confint(method='wilson'),
    reimplemented so E0 has no dependency beyond the stdlib and can be run
    on a machine where the analysis env is not set up yet.

    Wilson rather than the normal approximation because our rates sit near 0
    and near 1, where the naive interval runs off the end of [0,1]."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def eai(windows: list[dict], pages: list[bool]) -> dict | None:
    """Escalation Action Index, per RUBRIC.md section 1: the action_idx of the
    first window whose decision is page. None (reported as infinity) if the
    detector never pages.

    We record the START of the paging window's action range. A window is 5
    minutes wide, so this is the earliest action the detector could have been
    reacting to - the reading most generous to the detector, applied
    identically to models and rules."""
    for w, p in zip(windows, pages):
        if p:
            return {
                "window_idx": w["window_idx"],
                "action_idx": w["_gt"]["action_idx_range"][0],
                "t_utc": w["start_utc"],
            }
    return None


def lead_times(fired_at: str | None, refs: dict[str, dict | None]) -> dict[str, float | None]:
    """Hours from the page to each reference line. POSITIVE = paged before the
    event (good). NEGATIVE = paged after it had already happened.

    PREREGISTRATION.md section 4 pre-declares that lead time to first exfil is
    negative for ANY detector obeying the ground-truth rule, because the exfil
    phase opens 07-09 14:11 and the escalation point is 07-11 19:33. That is a
    property of the published phase windows, not a defect, and it is committed
    to as a finding rather than engineered away."""
    if fired_at is None:
        return {k: None for k in refs}
    t0 = _parse(fired_at)
    out: dict[str, float | None] = {}
    for label, row in refs.items():
        out[label] = None if row is None else (_parse(row["t_utc"]) - t0).total_seconds() / 3600.0
    return out


def run_stream(rows: list[dict], label: str) -> dict:
    windows = to_windows(rows)
    esc = escalation_point(rows)
    refs = reference_lines(rows)
    ref_lines = {
        "escalation_point": esc,
        "first_rce": refs["first_rce"],
        "first_exfil": refs["first_exfil"],
    }

    result = {
        "stream": label,
        "n_actions": len(rows),
        "n_windows": len(windows),
        "reference_lines": {
            k: None if v is None else {"action_idx": v["action_idx"], "t_utc": v["t_utc"],
                                       "milestone": v.get("milestone_name")}
            for k, v in ref_lines.items()
        },
        "detectors": {},
    }

    for name, fn in DETECTORS.items():
        pages = fn(windows)
        n_pages = sum(pages)
        fired = eai(windows, pages)
        lo, hi = wilson(n_pages, len(windows))
        result["detectors"][name] = {
            "eai": fired,
            "page_rate": n_pages / len(windows) if windows else 0.0,
            "page_rate_ci95": [lo, hi],
            "n_pages": n_pages,
            "n_windows": len(windows),
            "lead_times_hours": lead_times(fired["t_utc"] if fired else None, ref_lines),
        }
        if name == "keyword_sigma":
            result["detectors"][name]["first_rules_fired"] = (
                _sigma_hits(windows[fired["window_idx"] - 1]) if fired else []
            )
    return result


# --- reporting ----------------------------------------------------------

def _fmt_lead(h: float | None) -> str:
    if h is None:
        return "       -"
    return f"{h:+7.1f}h"


def report(attack: dict, benign: dict | None) -> str:
    lines = [
        f"E0 rule baselines",
        f"  attack stream : {attack['n_actions']} actions -> {attack['n_windows']} windows",
    ]
    if benign:
        lines.append(f"  benign stream : {benign['n_actions']} actions -> {benign['n_windows']} windows")
    else:
        lines.append("  benign stream : NOT BUILT YET - false-page rate is the")
        lines.append("                  discriminating measurement (PREREGISTRATION.md 3c)")
        lines.append("                  and E0 is not interpretable without it.")

    for label, row in attack["reference_lines"].items():
        lines.append(f"  {label:<17}: "
                     + (f"action #{row['action_idx']} @ {row['t_utc'][:19]}" if row else "not in this slice"))

    lines.append("")
    header = (f"  {'detector':<24} {'EAI':>10} {'to escal':>9} {'to RCE':>9} "
              f"{'to exfil':>9} {'page rate':>10}")
    lines.append(header)
    lines.append("  " + "-" * (len(header) - 2))

    for name, d in attack["detectors"].items():
        e = d["eai"]
        lt = d["lead_times_hours"]
        eai_s = f"#{e['action_idx']}" if e else "never"
        fp = ""
        if benign:
            b = benign["detectors"][name]
            lo, hi = b["page_rate_ci95"]
            fp = f"   false-page {b['page_rate']:.1%} [{lo:.1%}, {hi:.1%}]"
        lines.append(
            f"  {name:<24} {eai_s:>10} {_fmt_lead(lt['escalation_point'])} "
            f"{_fmt_lead(lt['first_rce'])} {_fmt_lead(lt['first_exfil'])} "
            f"{d['page_rate']:>9.1%}{fp}"
        )

    lines.append("")
    lines.append("  EAI  = first action index the detector pages on (RUBRIC.md 1)")
    lines.append("  lead = hours from the page to the reference line; + is before, - is after")
    lines.append("  sev_threshold is an ORACLE (reads ground-truth severity), not a deployable baseline")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    attack_path = pathlib.Path(argv[0])
    benign_path = None
    if "--benign" in argv:
        benign_path = pathlib.Path(argv[argv.index("--benign") + 1])

    attack_rows = [json.loads(l) for l in attack_path.open(encoding="utf-8")]
    attack = run_stream(attack_rows, attack_path.name)

    benign = None
    if benign_path and benign_path.exists():
        benign_rows = [json.loads(l) for l in benign_path.open(encoding="utf-8")]
        benign = run_stream(benign_rows, benign_path.name)
    elif benign_path:
        print(f"warning: {benign_path} does not exist yet; running attack stream only\n")

    print(report(attack, benign))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({"attack": attack, "benign": benign}, indent=2))
    print(f"\nwrote {OUT_PATH.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
