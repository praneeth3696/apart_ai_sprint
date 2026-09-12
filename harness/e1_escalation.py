"""
e1_escalation.py

E1 - Escalation latency and false-page rate. The headline experiment
(PLAN.md 4 "E1 - Escalation latency"; RUBRIC.md 1).

WHAT IT DOES
------------
Walks a windowed stream in order. For window n the model is shown a rolling
summary of windows 1..n-1 plus window n, in the monitor frame, and must return
strict JSON:

    {"severity": "...", "page_oncall": true|false, "rationale": "..."}

Run over both streams - `corpus/windows/attack_windows.json` and the matched
benign control `corpus/windows/benign_windows.json` - with the same prompt and
the same everything. The benign stream is the false-page denominator, and it is
usable because the blind separability check passed (analysis/blind_check_result
.json: 14/20, CI95 [48.1%, 85.5%], not distinguishable from chance).

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
**It computes no metrics.** It writes one raw decision per (model, stream,
window) to JSONL and stops. EAI, lead time, milestone hit rate, false-page
rate and their Wilson intervals are all `analysis/stats.py`'s job.

That split is deliberate. HANDOFF 5 records an open decision - first-page EAI
is degenerate on this corpus, because every E0 detector fires at action #15-51
on filler that is identical in both streams, so "first page" measures
trigger-happiness rather than detection - and the proposed replacement pair is
milestone-window hit rate against benign false-page rate. That decision needs
Amirtha's agreement and is not settled. Recording raw decisions means it does
not have to be settled before the run, and it cannot be quietly re-decided
after seeing the numbers either, because the decision lives in a separate file
with its own diff.

GROUND TRUTH NEVER REACHES THE MODEL
------------------------------------
Each window carries a `_gt` block. It is copied into the output record under
`gt` so analysis is self-contained, and it is asserted out of the prompt at
runtime (see `_assert_no_gt_leak`). The evidence the model sees is rendered by
`corpus/windows.render_evidence_block` from model-visible fields only.

USAGE
-----
    # no key needed, no network, exercises every parse and failure branch
    python harness/e1_escalation.py --dry-run

    # smoke: one model, 20 windows, both streams
    python harness/e1_escalation.py --models google:gemini-3.8-flash \\
        --windows 20 --select stride

    # the real run
    python harness/e1_escalation.py --models <a,b,c> --windows 60 --rpm 12
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import sys
import time
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "corpus"))
sys.path.insert(0, str(REPO / "harness"))

from client import ApiError, call  # noqa: E402
from monitor_frame import (  # noqa: E402
    E1_MONITOR_FRAME,
    MAX_TOKENS,
    REASK_SUFFIX,
    classify,
    parse_monitor,
)
from windows import render_evidence_block  # noqa: E402

WINDOW_FILES = {
    "attack": REPO / "corpus" / "windows" / "attack_windows.json",
    "benign": REPO / "corpus" / "windows" / "benign_windows.json",
}

# How much of the past the rolling summary carries. Bounded on purpose: an
# unbounded digest of 1,277 prior windows would dwarf the current window in the
# prompt and make the measurement a test of long-context retrieval instead of
# triage. These caps are part of the protocol - record them, don't tune them
# per model.
HISTORY_TOP_HOSTS = 8
HISTORY_TOP_ACTORS = 8
HISTORY_TAIL_EVENTS = 8
HISTORY_EVENT_CHARS = 110


# ---------------------------------------------------------------------------
# Rolling summary
# ---------------------------------------------------------------------------
class RollingSummary:
    """Deterministic digest of every window seen so far.

    Built from model-visible fields only (`action_idx`, `t_utc`, `host_role`,
    `actor`, `event`) and never from `_gt`. It is computed locally rather than
    asked of the model, which makes it free, reproducible, and identical on a
    re-run - so a cached window prompt stays cache-valid.

    It accumulates over ALL preceding windows, including ones this run did not
    sample. The monitor is supposed to have been watching the whole shift; if
    the digest skipped the unsampled windows, a stride sample and a full run
    would be answering different questions.
    """

    def __init__(self) -> None:
        self.hosts: collections.Counter = collections.Counter()
        self.actors: collections.Counter = collections.Counter()
        self.n_windows = 0
        self.n_actions = 0
        self.first_t: str | None = None
        self.last_t: str | None = None
        self.tail: collections.deque = collections.deque(maxlen=HISTORY_TAIL_EVENTS)

    def add(self, window: dict) -> None:
        self.n_windows += 1
        for a in window["actions"]:
            self.hosts[a["host_role"]] += 1
            self.actors[a["actor"]] += 1
            self.n_actions += 1
            if self.first_t is None:
                self.first_t = a["t_utc"]
            self.last_t = a["t_utc"]
            self.tail.append(a)

    def render(self) -> str:
        if self.n_windows == 0:
            return ("WHAT YOU HAVE SEEN SO FAR: nothing. This is the first "
                    "window of your shift.")
        lines = [
            f"WHAT YOU HAVE SEEN SO FAR - windows 1-{self.n_windows} "
            f"({self.n_actions:,} actions, {self.first_t[:19]}Z to {self.last_t[:19]}Z)",
            "",
            "  hosts by volume:",
        ]
        for host, n in self.hosts.most_common(HISTORY_TOP_HOSTS):
            lines.append(f"    {n:>7,}  {host}")
        if len(self.hosts) > HISTORY_TOP_HOSTS:
            lines.append(f"    (+{len(self.hosts) - HISTORY_TOP_HOSTS} more hosts)")
        lines += ["", "  actors by volume:"]
        for actor, n in self.actors.most_common(HISTORY_TOP_ACTORS):
            lines.append(f"    {n:>7,}  {actor}")
        if len(self.actors) > HISTORY_TOP_ACTORS:
            lines.append(f"    (+{len(self.actors) - HISTORY_TOP_ACTORS} more actors)")
        lines += ["", f"  the last {len(self.tail)} events before this window:"]
        for a in self.tail:
            ev = a["event"]
            if len(ev) > HISTORY_EVENT_CHARS:
                ev = ev[:HISTORY_EVENT_CHARS - 1] + "…"
            lines.append(f"    {a['action_idx']:<6} {a['t_utc'][:19]}  "
                         f"{a['host_role']:<24}  {ev}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Window selection
# ---------------------------------------------------------------------------
def select_windows(windows: list[dict], mode: str, n: int) -> list[tuple[int, str]]:
    """Return [(list_position, why_selected)] in stream order.

    Deterministic - no seed, no sampler to re-run. Modes:

      all         every window.
      head        the first n. Debugging only; it never reaches the incident.
      stride      n evenly spaced across the stream. Unbiased, order-preserving,
                  and the right sample for the benign false-page rate.
      stratified  every milestone-carrying window, plus a stride fill to n.
                  (default)

    Why `stratified` is the default: only 12 of the attack stream's 1,278
    windows carry a milestone. A 50-window uniform sample expects to catch 0.5
    of them, so the milestone hit rate - the metric HANDOFF 5 proposes as the
    headline - would be unmeasurable. Taking all 12 makes it a census.

    The cost is that the attack sample is then NOT uniform, so a pooled "page
    rate over the attack sample" is biased upward. Every record carries
    `selected_by`, and the manifest carries the counts, so analysis must slice
    on it rather than pool. The benign stream has no milestone windows at all,
    so there `stratified` degenerates to `stride` and the false-page
    denominator stays uniform.
    """
    total = len(windows)
    if mode == "all" or n >= total:
        return [(i, "all") for i in range(total)]
    if mode == "head":
        return [(i, "head") for i in range(n)]

    forced: dict[int, str] = {}
    if mode == "stratified":
        forced = {i: "milestone" for i, w in enumerate(windows)
                  if w["_gt"]["contains_milestone"]}

    n_stride = max(n - len(forced), 0)
    chosen = dict(forced)
    if n_stride:
        # Evenly spaced positions over the whole stream, midpoint-offset so the
        # sample does not cling to index 0.
        for j in range(n_stride):
            i = min(int((j + 0.5) * total / n_stride), total - 1)
            chosen.setdefault(i, "stride")
    return [(i, chosen[i]) for i in sorted(chosen)]


class StreamWalker:
    """One stream's windows, its selection, and its rolling history.

    Exists so the driver can alternate between the attack and benign streams
    while each stream's digest still accumulates over ALL of its own preceding
    windows, in order. The cursor only ever moves forward, which is what makes
    interleaving safe.
    """

    def __init__(self, windows: list[dict], sel: list[tuple[int, str]]):
        self.windows = windows
        self.sel = sel
        self.hist = RollingSummary()
        self.cursor = 0

    def _advance_to(self, pos: int) -> None:
        while self.cursor < pos:
            self.hist.add(self.windows[self.cursor])
            self.cursor += 1

    def prompt_for(self, pos: int) -> str:
        self._advance_to(pos)
        return build_prompt(self.windows[pos], self.hist)

    def consume(self, pos: int) -> None:
        """Fold this window into the history now that we are done with it."""
        self._advance_to(pos)
        if self.cursor == pos:
            self.hist.add(self.windows[pos])
            self.cursor += 1


def interleave(walkers: dict[str, StreamWalker]) -> list[tuple[str, int, str]]:
    """[(stream, position, why)] round-robin across streams, each stream still
    in its own order.

    Under a per-model daily quota the run does not decide when it stops - the
    provider does. Finishing the whole attack stream before starting benign
    would mean an exhausted model contributes a milestone hit rate with no
    false-page rate to compare it against, which is half a datapoint. Taking
    them in turn means whenever the quota dies, both streams are covered to
    roughly the same depth.
    """
    queues = {s: list(w.sel) for s, w in walkers.items()}
    order = list(walkers)
    out: list[tuple[str, int, str]] = []
    while any(queues.values()):
        for s in order:
            if queues[s]:
                pos, why = queues[s].pop(0)
                out.append((s, pos, why))
    return out


# ---------------------------------------------------------------------------
# Prompting
# ---------------------------------------------------------------------------
def _assert_no_gt_leak(prompt: str, window: dict) -> None:
    """Ground truth must never reach a model under evaluation
    (corpus/windows/README.md). Assert it, don't assume it - the milestone
    names and tactic labels are exactly the answer we are measuring."""
    gt = window["_gt"]
    for name in list(gt["milestone_names"]) + list(gt["tactics"]):
        if name and name in prompt:
            raise AssertionError(
                f"ground-truth label {name!r} leaked into the window "
                f"{window['window_idx']} prompt"
            )


def build_prompt(window: dict, history: RollingSummary) -> str:
    evidence = render_evidence_block(window["actions"])
    label = (f"window {window['window_idx']}, "
             f"{window['start_utc'][:19]}Z to {window['end_utc'][:19]}Z, "
             f"{window['n_actions']} actions")
    prompt = E1_MONITOR_FRAME.format(
        history=history.render(), window_label=label, evidence=evidence)
    assert evidence in prompt
    _assert_no_gt_leak(prompt, window)
    return prompt


# ---------------------------------------------------------------------------
# Dry-run mock
# ---------------------------------------------------------------------------
def mock_call(model: str, messages: list[dict], *, exp: str, **kw) -> dict:
    """A deterministic stand-in for client.call that makes NO network call.

    Its job is not to be realistic - it is to drive every branch of the
    response handling below at least once, so the parsing is proven before a
    single unit of free-tier quota is spent on it. The distribution of shapes
    is keyed off a hash of the prompt, so a dry run is reproducible and a
    re-ask (different prompt) reliably lands on a different shape than the
    original ask.
    """
    prompt = messages[-1]["content"]
    h = int(hashlib.sha256((model + prompt).encode()).hexdigest(), 16)
    reasking = prompt.endswith(REASK_SUFFIX)
    base = {"model_requested": model, "model_returned": model + "-mock",
            "provider": "MOCK (--dry-run, no network)",
            "t_utc": datetime.now(timezone.utc).isoformat(),
            "refusal_field": None, "finish_reason": "stop",
            "native_finish_reason": "stop",
            "usage": {"prompt_tokens": len(prompt) // 4,
                      "completion_tokens": 40, "cost": 0},
            "generation_id": f"mock-{h % 10**8}", "_cache_hit": False}
    page = (h >> 8) % 100 < 30
    sev = ["info", "low", "medium", "high", "critical"][(h >> 16) % 5]
    good = json.dumps({"severity": sev, "page_oncall": page,
                       "rationale": "mock rationale"})

    shape = h % 100
    if shape < 3:                                    # platform filter
        return {**base, "content": None, "finish_reason": "content_filter",
                "refusal_field": "mock policy string"}
    if shape < 5:                                    # budget exhausted
        return {**base, "content": None, "finish_reason": "length"}
    if shape < 7:                                    # model declines to engage
        return {**base, "content": "I'm sorry, I can't help with analysing "
                                   "intrusion activity."}
    if shape < 10:                                   # 402 -> unaffordable
        raise ApiError(f"{model}: mock HTTP 402", status=402)
    if shape < 12:                                   # hard transport failure
        raise ApiError(f"{model}: mock HTTP 500", status=500)
    if shape < 22 and not reasking:                  # prose-wrapped, recoverable
        return {**base, "content": f"Here is my assessment:\n```json\n{good}\n```"}
    if shape < 30 and not reasking:                  # unparseable, re-ask fixes
        return {**base, "content": "Severity looks medium; I would not page."}
    if shape < 32:                                   # unparseable even on re-ask
        return {**base, "content": "no json here either"}
    return {**base, "content": good}


# ---------------------------------------------------------------------------
# One window
# ---------------------------------------------------------------------------
def _error_outcome(e: ApiError) -> str:
    """Map a failed call onto an outcome that is NOT a model behaviour.

    All three of these leave `page_oncall` as None, so no denominator can pick
    them up by accident (RUBRIC.md 0: "unaffordable items are excluded from
    every denominator... Reporting a 402 as a refusal would manufacture a
    finding out of our own budget"). The same reasoning covers a free tier's
    daily cap - the only difference from a 402 is which of money or quota ran
    out first.
    """
    if e.status == 402:
        return "unaffordable"
    if e.quota_scope == "day":
        return "quota_exhausted"
    return "error"


def run_window(caller, model: str, stream: str, window: dict, prompt: str,
               selected_by: str, max_tokens: int) -> dict:
    """One monitor call, with RUBRIC.md 1's single re-ask on unparseable JSON.

    Returns a raw decision record. `outcome` uses the RUBRIC.md 0 vocabulary
    plus `unparseable` (RUBRIC.md 1) and `error`; `page_oncall` is None for
    every outcome that is not a model verdict, so analysis cannot silently
    count a filtered call as "did not page".
    """
    gt = window["_gt"]
    rec: dict = {
        "exp": "e1",
        "model": model,
        "stream": stream,
        "window_idx": window["window_idx"],
        "action_idx_start": gt["action_idx_range"][0],
        "action_idx_end": gt["action_idx_range"][1],
        "start_utc": window["start_utc"],
        "end_utc": window["end_utc"],
        "n_actions": window["n_actions"],
        "selected_by": selected_by,
        "prompt_chars": len(prompt),
        "reask": False,
        "outcome": None,
        "page_oncall": None,
        "severity": None,
        "rationale": None,
        "raw_head": None,
        "model_returned": None,
        "provider": None,
        "usage": None,
        "t_utc": None,
        "cached": False,
        "gt": gt,          # for analysis only; never sent to the model
    }

    def attempt(text: str) -> dict:
        return caller(model, [{"role": "user", "content": text}],
                      exp=f"e1_{stream}", max_tokens=max_tokens)

    try:
        api = attempt(prompt)
    except ApiError as e:
        rec["outcome"] = _error_outcome(e)
        rec["raw_head"] = str(e)[:200]
        rec["t_utc"] = datetime.now(timezone.utc).isoformat()
        return rec

    rec.update(model_returned=api.get("model_returned"),
               provider=api.get("provider"), usage=api.get("usage"),
               t_utc=api.get("t_utc"), cached=bool(api.get("_cache_hit")))

    status, note = classify(api)
    rec["raw_head"] = note
    if status != "ok":
        rec["outcome"] = status          # filtered | truncated | refused
        return rec

    parsed = parse_monitor(str(api["content"]))
    if parsed is None:
        # RUBRIC.md 1: exactly one re-ask, same prompt plus the one line.
        rec["reask"] = True
        try:
            api2 = attempt(prompt + REASK_SUFFIX)
        except ApiError as e:
            rec["outcome"] = _error_outcome(e)
            rec["raw_head"] = str(e)[:200]
            return rec
        rec.update(model_returned=api2.get("model_returned"),
                   provider=api2.get("provider"), usage=api2.get("usage"),
                   t_utc=api2.get("t_utc"),
                   cached=bool(api.get("_cache_hit")) and bool(api2.get("_cache_hit")))
        status2, note2 = classify(api2)
        rec["raw_head"] = note2
        if status2 != "ok":
            rec["outcome"] = status2
            return rec
        parsed = parse_monitor(str(api2["content"]))
        if parsed is None:
            rec["outcome"] = "unparseable"
            return rec

    rec["outcome"] = "comply"
    rec["page_oncall"] = parsed["page_oncall"]
    rec["severity"] = parsed.get("severity")
    rec["rationale"] = str(parsed.get("rationale", ""))[:400]
    return rec


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def summarise(records: list[dict]) -> str:
    """A rolling look at what the run is producing. NOT the paper's metrics -
    see the module docstring. It exists so a bad run is visible in minute two
    rather than at breakfast."""
    out = []
    by = collections.defaultdict(list)
    for r in records:
        by[(r["model"], r["stream"])].append(r)
    for (model, stream), rs in sorted(by.items()):
        outcomes = collections.Counter(r["outcome"] for r in rs)
        verdicts = [r for r in rs if r["outcome"] == "comply"]
        paged = [r for r in verdicts if r["page_oncall"]]
        first = min((r["action_idx_start"] for r in paged), default=None)
        ms = [r for r in verdicts if r["gt"]["contains_milestone"]]
        ms_hit = sum(1 for r in ms if r["page_oncall"])
        line = (f"  {model:<28} {stream:<7} "
                f"n={len(rs):<4} verdicts={len(verdicts):<4} "
                f"paged={len(paged):<4} "
                f"first_page_action={first if first is not None else '-':<8}")
        if ms:
            line += f" milestone_hits={ms_hit}/{len(ms)}"
        out.append(line)
        bad = {k: v for k, v in outcomes.items() if k != "comply"}
        if bad:
            out.append(f"  {'':<28} {'':<7} non-verdicts: "
                       + ", ".join(f"{k}={v}" for k, v in sorted(bad.items())))
    return "\n".join(out)


def _rel(path: pathlib.Path) -> str:
    """Repo-relative for display where possible, absolute otherwise - --out may
    legitimately point outside the repo."""
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path.resolve())


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--models", default="google:gemini-3.8-flash",
                   help="comma-separated model ids (client.py routing applies)")
    p.add_argument("--streams", default="attack,benign")
    p.add_argument("--windows", type=int, default=60,
                   help="windows per stream (ignored by --select all)")
    p.add_argument("--select", default="stratified",
                   choices=["stratified", "stride", "all", "head"])
    p.add_argument("--rpm", type=float, default=0,
                   help="throttle to at most this many requests/minute (0 = off)")
    p.add_argument("--max-calls", type=int, default=0,
                   help="hard stop after this many API calls (0 = no cap)")
    p.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    p.add_argument("--dry-run", action="store_true",
                   help="mock provider: no network, no key, no quota spent")
    p.add_argument("--out", default=None)
    p.add_argument("--force", action="store_true",
                   help="re-do windows already present in the output file")
    args = p.parse_args(argv)

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    streams = [s.strip() for s in args.streams.split(",") if s.strip()]
    caller = mock_call if args.dry_run else call

    out_dir = REPO / "runs" / "e1" / ("dryrun" if args.dry_run else "live")
    # A relative --out is relative to the repo root, not to the shell's cwd -
    # the runners get invoked from harness/ and corpus/ as often as from root.
    out_path = ((REPO / args.out) if args.out else out_dir / "e1_decisions.jsonl").resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    done: set[tuple] = set()
    if out_path.is_file() and not args.force:
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done.add((r["model"], r["stream"], r["window_idx"]))

    t0 = time.time()
    print(f"E1 escalation  {datetime.now(timezone.utc).isoformat()}")
    print(f"  models   : {', '.join(models)}")
    print(f"  streams  : {', '.join(streams)}")
    print(f"  select   : {args.select} (n={args.windows} per stream)")
    print(f"  provider : {'MOCK - no network, no quota' if args.dry_run else 'live'}")
    print(f"  out      : {_rel(out_path)}"
          + (f"  (resuming, {len(done)} already done)" if done else ""))
    print()

    plan: dict[str, tuple] = {}
    for stream in streams:
        windows = json.loads(WINDOW_FILES[stream].read_text(encoding="utf-8"))
        sel = select_windows(windows, args.select, args.windows)
        plan[stream] = (windows, sel)
        counts = collections.Counter(why for _, why in sel)
        print(f"  {stream:<7} {len(windows)} windows -> {len(sel)} selected  "
              + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print()

    records: list[dict] = []
    n_calls = 0
    stopped = ""
    exhausted: list[str] = []
    fh = out_path.open("a", encoding="utf-8")
    try:
        for model in models:
            walkers = {s: StreamWalker(*plan[s]) for s in streams}
            for stream, pos, why in interleave(walkers):
                walker = walkers[stream]
                w = walker.windows[pos]
                if (model, stream, w["window_idx"]) in done:
                    walker.consume(pos)
                    continue
                if args.max_calls and n_calls >= args.max_calls:
                    stopped = f"--max-calls={args.max_calls}"
                    break

                prompt = walker.prompt_for(pos)
                t_call = time.time()
                rec = run_window(caller, model, stream, w, prompt, why,
                                 args.max_tokens)
                walker.consume(pos)
                n_calls += 1 + int(rec["reask"])
                rec["run_utc"] = datetime.now(timezone.utc).isoformat()
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
                records.append(rec)

                page = rec["page_oncall"]
                mark = "PAGE" if page else ("----" if page is False else "  ? ")
                flag = "*" if w["_gt"]["contains_milestone"] else " "
                print(f"{flag} {model:<26} {stream:<7} "
                      f"w{w['window_idx']:<5} act{rec['action_idx_start']:<6} "
                      f"{mark} {rec['outcome']:<15} "
                      f"sev={str(rec['severity']):<9} "
                      f"{(rec['rationale'] or rec['raw_head'] or '')[:52]}")

                if rec["outcome"] == "quota_exhausted":
                    # The provider, not us, decided this model is finished for
                    # today. Grinding the remaining windows would just log the
                    # same 429 fifty more times.
                    exhausted.append(model)
                    print(f"  -> {model}: free-tier daily quota exhausted, "
                          f"moving to the next model")
                    break

                if args.rpm and not rec["cached"]:
                    gap = 60.0 / args.rpm - (time.time() - t_call)
                    if gap > 0:
                        time.sleep(gap)
                if len(records) % 25 == 0:
                    print("\n  --- rolling ---")
                    print(summarise(records))
                    print()
            if stopped:
                break
    except KeyboardInterrupt:
        stopped = "interrupted"
        print("\ninterrupted - decisions written so far are on disk; "
              "re-run the same command to resume")
    finally:
        fh.close()

    if stopped:
        print(f"\nstopped: {stopped}")
    if exhausted:
        print("\ndaily free-tier quota exhausted for: " + ", ".join(exhausted))
        print("re-run the same command after the quota resets; finished "
              "windows are skipped and cached calls are free.")

    print("\n=== this run ===")
    print(summarise(records) or "  (nothing new; everything was already done)")

    manifest = {
        "exp": "e1",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "models": models,
        "streams": streams,
        "select": args.select,
        "windows_requested": args.windows,
        "max_tokens": args.max_tokens,
        "rpm": args.rpm,
        "api_calls_this_run": n_calls,
        "quota_exhausted_models": exhausted,
        "stopped": stopped or None,
        "interleaved_streams": True,
        "records_this_run": len(records),
        "elapsed_s": round(time.time() - t0, 1),
        "selection": {
            s: dict(collections.Counter(why for _, why in plan[s][1]))
            for s in streams
        },
        "history_caps": {
            "top_hosts": HISTORY_TOP_HOSTS, "top_actors": HISTORY_TOP_ACTORS,
            "tail_events": HISTORY_TAIL_EVENTS, "event_chars": HISTORY_EVENT_CHARS,
        },
        "note": (
            "Raw per-window decisions only. No metric is computed here - see "
            "analysis/stats.py and HANDOFF.md 5 (the EAI-vs-milestone-hit-rate "
            "decision). Under select=stratified the attack sample is NOT "
            "uniform: all milestone windows are taken. Slice on selected_by; "
            "do not pool."
        ),
        "out": _rel(out_path),
    }
    man_path = out_path.with_name(out_path.stem + "_manifest.json")
    man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nwrote {_rel(out_path)}")
    print(f"wrote {_rel(man_path)}")
    print(f"api calls this run: {n_calls}  elapsed: {manifest['elapsed_s']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
