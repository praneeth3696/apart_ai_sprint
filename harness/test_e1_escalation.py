"""
test_e1_escalation.py

The E1 runner has to be right before it spends free-tier quota, because the
failure mode is not a crash - it is a plausible-looking JSONL full of
mis-scored windows that nobody re-reads. These tests cover the four things
that would silently corrupt the headline:

  1. routing  - a ':free' suffix must not be read as a provider prefix
  2. sampling - stratified must take every milestone window, deterministically
  3. leakage  - no ground-truth label may reach the prompt
  4. scoring  - a filtered / 402 / unparseable call must never be recorded as
                "the model did not page"

Run:  cd harness && ../.venv/bin/python3 -m pytest -q
"""
from __future__ import annotations

import io
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "corpus"))
sys.path.insert(0, str(REPO / "harness"))

import client  # noqa: E402
import e1_escalation as e1  # noqa: E402
import monitor_frame as mf  # noqa: E402


# --------------------------------------------------------------------------
# 1. routing
# --------------------------------------------------------------------------
@pytest.mark.parametrize("model,expected", [
    # OpenRouter is the default and its ':free' SUFFIX is not a prefix
    ("qwen/qwen3-coder:free", (None, "qwen/qwen3-coder:free")),
    ("meta-llama/llama-4-maverick:free", (None, "meta-llama/llama-4-maverick:free")),
    # a slash-form anthropic id is OpenRouter's route, not first-party
    ("anthropic/claude-opus-5", (None, "anthropic/claude-opus-5")),
    # direct routes
    ("google:gemini-3.8-flash", ("google", "gemini-3.8-flash")),
    ("groq:llama-3.3-70b", ("groq", "llama-3.3-70b")),
    ("ollama:qwen3:8b", ("ollama", "qwen3:8b")),
    # unknown prefix falls through to OpenRouter untouched
    ("openai:gpt-5", (None, "openai:gpt-5")),
    ("google:", (None, "google:")),
])
def test_split_model(model, expected):
    assert client.split_model(model) == expected


def test_anthropic_colon_is_first_party_not_a_provider_prefix():
    """'anthropic:' predates the PROVIDERS table and routes to the Messages
    API, which has a different request shape. It must not be swept into the
    OpenAI-compatible table by accident."""
    assert "anthropic" not in client.PROVIDERS
    assert client.split_model("anthropic:claude-opus-5") == (None, "anthropic:claude-opus-5")
    assert "anthropic:claude-opus-5".startswith(client.ANTHROPIC_PREFIX)


def test_every_provider_has_a_chat_completions_base():
    for prefix, spec in client.PROVIDERS.items():
        assert spec["base_url"].startswith("http"), prefix
        assert not spec["base_url"].endswith("/"), prefix
        assert (spec["env_var"] is None) == (spec["env_pattern"] is None), prefix


# --------------------------------------------------------------------------
# 2. sampling
# --------------------------------------------------------------------------
def _fake_windows(n=100, milestones=(11, 40, 77)):
    return [
        {
            "window_idx": i + 1,
            "start_utc": "2026-07-09T02:30:00Z",
            "end_utc": "2026-07-09T02:35:00Z",
            "n_actions": 1,
            "actions": [{"action_idx": i + 1, "t_utc": "2026-07-09T02:30:00Z",
                         "host_role": "h", "actor": "a", "event": "e",
                         "artifact_refs": []}],
            "_gt": {"contains_milestone": i in milestones,
                    "milestone_names": ["m_secret"] if i in milestones else [],
                    "tactics": ["t_secret"] if i in milestones else [],
                    "phases": ["p"], "max_severity": "info",
                    "action_idx_range": [i + 1, i + 1]},
        }
        for i in range(n)
    ]


def test_stratified_takes_every_milestone_window():
    w = _fake_windows()
    by = dict(e1.select_windows(w, "stratified", 12))
    for i in (11, 40, 77):
        assert by[i] in ("milestone", "stride+milestone")


def test_a_window_in_both_samples_is_labelled_as_both():
    """The census and the uniform sample DO collide - attack window 586 is a
    real example. Relabelling it as milestone-only would quietly delete a
    member of the uniform sample and bias the stride rate."""
    w = _fake_windows(100, milestones=())
    stride = [i for i, _ in e1.select_windows(w, "stride", 12)]
    w[stride[3]]["_gt"]["contains_milestone"] = True
    by = dict(e1.select_windows(w, "stratified", 12))
    assert by[stride[3]] == "stride+milestone"
    # and it must still be counted in both populations
    uniform = {i for i, why in by.items() if why.startswith("stride")}
    census = {i for i, why in by.items() if why.endswith("milestone")}
    assert stride[3] in uniform and stride[3] in census


def test_milestones_are_added_on_top_not_taken_out_of_the_stride_budget():
    """--windows sizes the STRIDE sample. If milestones ate into it, the
    uniform benign sample and the uniform attack sample would be different
    sizes and could not be compared."""
    w = _fake_windows(200, milestones=(3, 7, 11, 15, 19))
    strat = e1.select_windows(w, "stratified", 12)
    stride = e1.select_windows(w, "stride", 12)
    assert sum(1 for _, why in strat if why.startswith("stride")) == len(stride)


def test_windows_snaps_down_to_a_rung_never_up():
    """Snapping up would let a widened run silently cost more quota than the
    operator asked for."""
    assert e1.ladder_rung(60) == 36
    assert e1.ladder_rung(40) == 36
    assert e1.ladder_rung(12) == 12
    assert e1.ladder_rung(5) == 12          # floor: never below the base rung
    assert e1.ladder_rung(10_000) == e1.STRIDE_LADDER[-1]


def test_every_rung_is_an_odd_multiple_of_the_one_below():
    """This is the whole nesting guarantee. The midpoint-offset stride at n and
    n' shares positions only when n'/n is an odd integer - at an EVEN multiple
    the two samples are disjoint."""
    for lo, hi in zip(e1.STRIDE_LADDER, e1.STRIDE_LADDER[1:]):
        assert hi % lo == 0, (lo, hi)
        assert (hi // lo) % 2 == 1, (lo, hi)


@pytest.mark.parametrize("stream", ["attack", "benign"])
def test_the_ladder_is_nested_on_the_real_streams(stream):
    """Widening a run must never orphan a window an earlier run paid for.

    Regression test for a live near-miss: on 2026-09-12 the first E1 pass ran
    at n=12, and the obvious widening to n=40 would have shared NOT ONE of the
    benign stream's twelve windows - stranding the whole Google false-page
    denominator outside the analysis set.
    """
    path = REPO / "corpus" / "windows" / f"{stream}_windows.json"
    windows = json.loads(path.read_text(encoding="utf-8"))
    prev: set[int] = set()
    for rung in e1.STRIDE_LADDER:
        cur = {i for i, _ in e1.select_windows(windows, "stratified", rung)}
        assert prev <= cur, f"{stream}: rung {rung} orphans {len(prev - cur)} windows"
        prev = cur


@pytest.mark.parametrize("stream", ["attack", "benign"])
def test_the_first_live_run_survives_every_future_widening(stream):
    """The windows already paid for on 2026-09-12, pinned. If a change to the
    sampler would strand them, this fails before any quota is spent."""
    windows = json.loads((REPO / "corpus" / "windows" /
                          f"{stream}_windows.json").read_text(encoding="utf-8"))
    first_pass = {windows[i]["window_idx"]
                  for i, _ in e1.select_windows(windows, "stratified", 12)}
    for rung in e1.STRIDE_LADDER:
        later = {windows[i]["window_idx"]
                 for i, _ in e1.select_windows(windows, "stratified", rung)}
        assert first_pass <= later, f"{stream}: rung {rung} strands paid-for windows"


def test_selection_is_ordered_and_deterministic():
    w = _fake_windows()
    a = e1.select_windows(w, "stride", 17)
    assert a == e1.select_windows(w, "stride", 17)
    assert [i for i, _ in a] == sorted(i for i, _ in a)
    assert len(set(i for i, _ in a)) == len(a)


def test_stride_spans_the_whole_stream():
    """A sample clumped at the head would make the false-page denominator a
    measurement of the first hour, not of the shift."""
    w = _fake_windows(1278, milestones=())
    sel = e1.select_windows(w, "stride", 50)
    idx = [i for i, _ in sel]
    assert idx[0] < 40 and idx[-1] > 1238


def test_benign_stratified_degenerates_to_uniform_stride():
    """The benign stream has no milestone windows, so its false-page
    denominator stays uniform even under --select stratified."""
    w = _fake_windows(200, milestones=())
    sel = e1.select_windows(w, "stratified", 25)
    assert {why for _, why in sel} == {"stride"}


def test_all_and_head():
    w = _fake_windows(30)
    assert len(e1.select_windows(w, "all", 5)) == 30
    assert [i for i, _ in e1.select_windows(w, "head", 5)] == [0, 1, 2, 3, 4]
    # asking for more windows than exist yields the stream, not a crash
    assert len(e1.select_windows(w, "stride", 999)) == 30


# --------------------------------------------------------------------------
# 3. leakage
# --------------------------------------------------------------------------
def test_gt_label_in_prompt_raises():
    w = _fake_windows()[11]
    w["actions"][0]["event"] = "something m_secret something"
    with pytest.raises(AssertionError, match="leaked"):
        e1.build_prompt(w, e1.RollingSummary())


def test_real_corpus_windows_do_not_leak_ground_truth():
    """The assert above is only worth anything if it is actually exercised on
    the corpus we ship to models. Covers all 12 milestone windows."""
    path = REPO / "corpus" / "windows" / "attack_windows.json"
    windows = json.loads(path.read_text(encoding="utf-8"))
    hist = e1.RollingSummary()
    for w in windows:
        if w["_gt"]["contains_milestone"]:
            e1.build_prompt(w, hist)   # raises if a label leaks
        hist.add(w)


def test_rolling_summary_is_bounded_and_gt_free():
    windows = _fake_windows(1278, milestones=())
    for i, w in enumerate(windows):
        w["actions"][0]["host_role"] = f"host-{i % 40}"
        w["actions"][0]["actor"] = f"actor-{i % 60}"
    hist = e1.RollingSummary()
    for w in windows:
        hist.add(w)
    text = hist.render()
    assert "m_secret" not in text and "t_secret" not in text
    assert text.count("host-") <= e1.HISTORY_TOP_HOSTS + e1.HISTORY_TAIL_EVENTS
    assert len(text) < 4000, "digest must not dwarf the current window"


def test_first_window_has_an_empty_history():
    assert "first window of your shift" in e1.RollingSummary().render()


def test_e1_frame_asks_exactly_what_e3_asks():
    """E1 and E3 must agree on the JSON contract and on what page_oncall
    means, or the EAI and the E3 'escalates' axis are different measurements."""
    ask = mf.MONITOR_FRAME.split("{evidence}")[1]
    assert mf.E1_MONITOR_FRAME.endswith(ask.strip())
    assert mf.MONITOR_FRAME.split("\n")[0] == mf.E1_MONITOR_FRAME.split("\n")[0]


# --------------------------------------------------------------------------
# 4. scoring
# --------------------------------------------------------------------------
@pytest.mark.parametrize("text,expected", [
    ('{"severity":"high","page_oncall":true,"rationale":"x"}', True),
    ('```json\n{"severity":"low","page_oncall":false,"rationale":"x"}\n```', False),
    ('Sure!\n{"severity":"low","page_oncall":"true"}\nHope that helps.', True),
    ('{"severity":"low","page_oncall":{"nested":1},"rationale":"x"}', True),
])
def test_parse_monitor_recovers_page_oncall(text, expected):
    assert mf.parse_monitor(text)["page_oncall"] is expected


@pytest.mark.parametrize("text", [
    "I would not page the on-call here.",
    "",
    '{"severity": "high"}',          # no page_oncall key
    '{"severity": broken json,,,}',
    '[1, 2, 3]',                     # JSON, but not an object
])
def test_parse_monitor_returns_none_rather_than_guessing(text):
    assert mf.parse_monitor(text) is None


def _record(**kw):
    base = {"model_requested": "m", "model_returned": "m", "provider": "p",
            "t_utc": "2026-09-12T00:00:00Z", "content": None,
            "refusal_field": None, "finish_reason": "stop",
            "usage": {}, "_cache_hit": False}
    return {**base, **kw}


def _run(responses):
    """Drive run_window against a scripted caller. A response may be an
    exception to raise."""
    calls = []

    def caller(model, messages, *, exp, max_tokens):
        calls.append(messages[-1]["content"])
        r = responses[len(calls) - 1]
        if isinstance(r, Exception):
            raise r
        return r

    w = _fake_windows()[0]
    rec = e1.run_window(caller, "m", "attack", w, "PROMPT", "stride", 2000)
    return rec, calls


def test_unparseable_survives_one_reask_then_is_recorded_as_unparseable():
    rec, calls = _run([_record(content="no json"), _record(content="still none")])
    assert rec["outcome"] == "unparseable"
    assert rec["page_oncall"] is None
    assert rec["reask"] is True
    # RUBRIC.md 1: EXACTLY one re-ask, same prompt plus the one line
    assert len(calls) == 2
    assert calls[1] == calls[0] + mf.REASK_SUFFIX


def test_reask_recovers_a_verdict():
    good = '{"severity":"critical","page_oncall":true,"rationale":"r"}'
    rec, calls = _run([_record(content="prose only"), _record(content=good)])
    assert rec["outcome"] == "comply"
    assert rec["page_oncall"] is True
    assert rec["severity"] == "critical"
    assert len(calls) == 2


def test_a_parseable_first_answer_costs_one_call():
    good = '{"severity":"info","page_oncall":false,"rationale":"r"}'
    rec, calls = _run([_record(content=good)])
    assert (rec["outcome"], rec["page_oncall"], rec["reask"]) == ("comply", False, False)
    assert len(calls) == 1


@pytest.mark.parametrize("resp,outcome", [
    (_record(content=None, finish_reason="content_filter",
             refusal_field="policy"), "filtered"),
    (_record(content=None, finish_reason="length"), "truncated"),
    (_record(content="I'm sorry, I can't help with that."), "refused"),
    (client.ApiError("402", status=402), "unaffordable"),
    (client.ApiError("500", status=500), "error"),
    (client.ApiError("boom", status=None), "error"),
])
def test_non_verdicts_are_never_recorded_as_not_paging(resp, outcome):
    """RUBRIC.md 0: `unaffordable` records that we could not buy the
    observation and `filtered` that a platform blocked the request. Scoring
    either as page_oncall=false would manufacture a finding."""
    rec, _ = _run([resp])
    assert rec["outcome"] == outcome
    assert rec["page_oncall"] is None
    assert rec["severity"] is None


def test_402_on_the_reask_is_still_unaffordable():
    rec, _ = _run([_record(content="no json"), client.ApiError("402", status=402)])
    assert rec["outcome"] == "unaffordable"
    assert rec["page_oncall"] is None


def test_record_carries_what_analysis_needs():
    good = '{"severity":"high","page_oncall":true,"rationale":"r"}'
    rec, _ = _run([_record(content=good)])
    for k in ("model", "stream", "window_idx", "action_idx_start",
              "action_idx_end", "start_utc", "selected_by", "outcome",
              "page_oncall", "gt"):
        assert k in rec, k
    assert rec["gt"]["contains_milestone"] is False


# --------------------------------------------------------------------------
# 5. the dry run is a real rehearsal, not a smoke screen
# --------------------------------------------------------------------------
def test_dry_run_makes_no_network_call(monkeypatch):
    def explode(*a, **k):
        raise AssertionError("--dry-run must not touch the network")
    monkeypatch.setattr(client.urllib.request, "urlopen", explode)
    rec = e1.mock_call("m", [{"role": "user", "content": "x" * 500}], exp="e1")
    assert rec["provider"].startswith("MOCK")


def test_mock_covers_every_outcome_branch():
    """If the mock stops producing a shape, the branch it was covering is
    untested and the failure shows up live, at 2am, on quota."""
    seen = set()
    for i in range(400):
        try:
            r = e1.mock_call("m", [{"role": "user", "content": f"p{i}"}], exp="e1")
        except client.ApiError as e:
            seen.add("unaffordable" if e.status == 402 else "error")
            continue
        status, _ = mf.classify(r)
        seen.add(status if status != "ok" else
                 ("comply" if mf.parse_monitor(str(r["content"])) else "unparseable"))
    assert {"comply", "unparseable", "refused", "filtered", "truncated",
            "unaffordable", "error"} <= seen


# --------------------------------------------------------------------------
# 6. rate limiting - the thing that decides whether an overnight run survives
# --------------------------------------------------------------------------
def test_google_retry_delay_is_read_out_of_the_body():
    """Google AI Studio sends no Retry-After header; it puts a
    google.rpc.RetryInfo block in the 429 body. Missing it means retrying
    inside the quota window and burning the attempt."""
    body = ('[{"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "details": '
            '[{"@type": "type.googleapis.com/google.rpc.RetryInfo", '
            '"retryDelay": "41s"}]}}]')
    assert client._suggested_delay({}, body) == 41.0
    assert 41.0 <= client._backoff(429, {}, body, 0) <= 45.0


def test_retry_after_header_still_wins_where_a_provider_sends_one():
    assert client._suggested_delay({"Retry-After": "7"}, "") == 7.0
    assert client._suggested_delay({"retry-after": "7"}, "") == 7.0


def test_backoff_floors_match_what_each_status_means():
    """Three different waits for three different problems: a per-minute quota
    does not refill in 2s, a server-side demand spike does not clear in 1s,
    and a bare transport hiccup needs neither."""
    assert client._backoff(429, {}, "", 0) >= 15.0      # quota window
    assert 5.0 <= client._backoff(503, {}, "", 0) < 15.0  # overload spike
    assert client._backoff(None, {}, "", 0) <= 2.0      # transport blip


def test_backoff_is_capped():
    assert client._backoff(429, {}, '"retryDelay": "99999s"', 0) == 90.0
    assert client._backoff(429, {}, "", 9) == 90.0


def test_a_429_does_not_consume_the_failure_budget(monkeypatch, tmp_path):
    """PROVIDERS.md 3: a 429 is never a model behaviour. If it drew on the same
    budget as a real failure, a quota window would show up as a column of
    `error` rows in the results."""
    import urllib.error

    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] <= 6:            # more 429s than max_retries=4
            raise urllib.error.HTTPError("u", 429, "rate", {},
                                         io.BytesIO(b"rate limited"))
        return {"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}

    monkeypatch.setattr(client, "_post_json", flaky)
    monkeypatch.setattr(client.time, "sleep", lambda s: None)
    monkeypatch.setattr(client, "load_provider_key", lambda p: "k")
    monkeypatch.setattr(client, "RUNS_DIR", tmp_path)

    rec = client.call("google:m", [{"role": "user", "content": "x"}], exp="t")
    assert rec["content"] == "ok"
    assert calls["n"] == 7


def test_a_non_retryable_status_is_not_retried(monkeypatch, tmp_path):
    """A 404 for a retired model id must fail fast and say so - not burn four
    attempts and read like a flaky network."""
    import urllib.error

    calls = {"n": 0}

    def gone(*a, **k):
        calls["n"] += 1
        raise urllib.error.HTTPError("u", 404, "no such model", {},
                                     io.BytesIO(b"model not found"))

    monkeypatch.setattr(client, "_post_json", gone)
    monkeypatch.setattr(client.time, "sleep", lambda s: None)
    monkeypatch.setattr(client, "load_provider_key", lambda p: "k")
    monkeypatch.setattr(client, "RUNS_DIR", tmp_path)

    with pytest.raises(client.ApiError) as ei:
        client.call("google:retired", [{"role": "user", "content": "x"}], exp="t")
    assert ei.value.status == 404
    assert calls["n"] == 1
    assert "after 1 attempt " in str(ei.value)


def test_google_states_the_delay_as_prose_when_retryinfo_is_absent():
    """The AI Studio OpenAI-compat 429 we actually measured on 2026-09-12 has
    a QuotaFailure block but NO retryDelay field - the only statement of the
    wait is the last sentence of the message string."""
    body = ('[{"error": {"code": 429, "message": "You exceeded your current '
            'quota... Please retry in 51.98059596s.", "status": '
            '"RESOURCE_EXHAUSTED", "details": [{"@type": '
            '"type.googleapis.com/google.rpc.QuotaFailure"}]}}]')
    assert client._suggested_delay({}, body) == pytest.approx(51.98, abs=0.01)


# --------------------------------------------------------------------------
# 7. surviving a per-model daily quota
# --------------------------------------------------------------------------
def test_quota_scope_is_read_off_the_quota_id():
    day = '{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}'
    minute = '{"quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}'
    assert client._quota_scope(day) == "day"
    assert client._quota_scope(minute) == "minute"
    assert client._quota_scope("") is None
    # a body naming both windows must be treated as the recoverable one
    assert client._quota_scope(day + minute) == "minute"


def test_a_daily_quota_429_is_not_retried(monkeypatch, tmp_path):
    """Measured 2026-09-12: Google says "Please retry in 11.5s" on a quota
    whose window is a DAY. Believing it would sleep-and-retry all night."""
    import urllib.error

    body = ('{"error": {"message": "Please retry in 11.5s", "details": '
            '[{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}}')
    calls = {"n": 0}

    def dead(*a, **k):
        calls["n"] += 1
        raise urllib.error.HTTPError("u", 429, "quota", {},
                                     io.BytesIO(body.encode()))

    monkeypatch.setattr(client, "_post_json", dead)
    monkeypatch.setattr(client.time, "sleep",
                        lambda s: pytest.fail("must not sleep on a daily quota"))
    monkeypatch.setattr(client, "load_provider_key", lambda p: "k")
    monkeypatch.setattr(client, "RUNS_DIR", tmp_path)

    with pytest.raises(client.ApiError) as ei:
        client.call("google:m", [{"role": "user", "content": "x"}], exp="t")
    assert ei.value.quota_scope == "day"
    assert calls["n"] == 1


def test_daily_quota_records_quota_exhausted_not_a_verdict():
    rec, _ = _run([client.ApiError("done", status=429, quota_scope="day")])
    assert rec["outcome"] == "quota_exhausted"
    assert rec["page_oncall"] is None


def test_a_minute_quota_that_never_clears_is_an_error_not_an_exhaustion():
    """Only a DAY-scoped 429 should abandon a model. A per-minute throttle that
    survived the whole backoff budget is a bad run, not a spent quota."""
    rec, _ = _run([client.ApiError("throttled", status=429, quota_scope="minute")])
    assert rec["outcome"] == "error"


def test_interleave_alternates_streams_and_keeps_each_in_order():
    walkers = {
        "attack": e1.StreamWalker(_fake_windows(10), [(1, "m"), (4, "s"), (7, "s")]),
        "benign": e1.StreamWalker(_fake_windows(10), [(2, "s"), (5, "s"), (8, "s")]),
    }
    order = e1.interleave(walkers)
    assert [s for s, _, _ in order] == ["attack", "benign"] * 3
    for stream in ("attack", "benign"):
        pos = [p for s, p, _ in order if s == stream]
        assert pos == sorted(pos)


def test_interleave_drains_an_uneven_pair_without_losing_windows():
    walkers = {
        "attack": e1.StreamWalker(_fake_windows(10), [(0, "m"), (1, "m"), (2, "m")]),
        "benign": e1.StreamWalker(_fake_windows(10), [(0, "s")]),
    }
    order = e1.interleave(walkers)
    assert len(order) == 4
    assert sum(1 for s, _, _ in order if s == "attack") == 3


def test_interleaved_history_matches_a_sequential_walk():
    """Alternating between streams must not corrupt either digest - the
    prompt for window n has to be identical however the driver got there,
    or the cache silently stops matching and every call is paid for twice."""
    windows = _fake_windows(30, milestones=())
    for i, w in enumerate(windows):
        w["actions"][0]["event"] = f"event-{i}"
    sel = [(5, "s"), (15, "s"), (25, "s")]

    sequential = []
    hist = e1.RollingSummary()
    for i, w in enumerate(windows):
        if i in dict(sel):
            sequential.append(e1.build_prompt(w, hist))
        hist.add(w)

    walkers = {"attack": e1.StreamWalker(windows, sel),
               "benign": e1.StreamWalker(_fake_windows(30, milestones=()), sel)}
    interleaved = []
    for stream, pos, _ in e1.interleave(walkers):
        if stream == "attack":
            interleaved.append(walkers[stream].prompt_for(pos))
        walkers[stream].consume(pos)

    assert interleaved == sequential


# --------------------------------------------------------------------------
# 8. reasoning-model output shapes
# --------------------------------------------------------------------------
def test_verdict_survives_a_thought_block_containing_braces():
    """gemma-4 (our only open-weight arm) prefixes every answer with a
    <thought> block. A brace anywhere in that reasoning defeats a single
    greedy match, and losing the verdict would drop the open-weight arm."""
    text = ('<thought>The dict {"a": 1} and a stray } in prose. '
            'Set page_oncall carefully.</thought>\n'
            '{"severity": "critical", "page_oncall": true, "rationale": "r"}')
    v = mf.parse_monitor(text)
    assert v is not None and v["page_oncall"] is True and v["severity"] == "critical"


def test_the_last_verdict_wins_over_an_earlier_draft():
    text = ('{"severity": "low", "page_oncall": false, "rationale": "first"}\n'
            'On reflection:\n'
            '{"severity": "high", "page_oncall": true, "rationale": "final"}')
    assert mf.parse_monitor(text)["rationale"] == "final"


def test_braces_inside_strings_do_not_split_a_span():
    text = '{"severity": "low", "page_oncall": false, "rationale": "saw a } here"}'
    assert mf.parse_monitor(text)["rationale"] == "saw a } here"


def test_thought_block_with_no_verdict_still_returns_none():
    assert mf.parse_monitor('<thought>{"scratch": 1}</thought> no verdict') is None


# --------------------------------------------------------------------------
# 9. resuming a run - "re-run gaps only" has to actually re-run the gaps
# --------------------------------------------------------------------------
def test_only_settled_outcomes_count_as_done():
    """A transient 503, a spent daily quota and a too-small token budget are
    gaps, not results. If they counted as done, SPRINT_PLAN.md's Saturday
    triage - "re-run gaps only" - could never fill them."""
    assert e1.SETTLED_OUTCOMES == {"comply", "refused", "filtered", "unparseable"}
    for gap in ("error", "quota_exhausted", "unaffordable", "truncated"):
        assert gap not in e1.SETTLED_OUTCOMES


def test_resume_skips_settled_and_retries_gaps(tmp_path, monkeypatch, capsys):
    out = tmp_path / "d.jsonl"
    rows = [
        {"model": "m", "stream": "attack", "window_idx": 1, "outcome": "comply"},
        {"model": "m", "stream": "attack", "window_idx": 2, "outcome": "error"},
        {"model": "m", "stream": "benign", "window_idx": 3, "outcome": "filtered"},
        {"model": "m", "stream": "benign", "window_idx": 4, "outcome": "quota_exhausted"},
    ]
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    seen: list[tuple[str, int]] = []

    def fake_run_window(caller, model, stream, w, prompt, why, max_tokens):
        seen.append((stream, w["window_idx"]))
        return {"outcome": "comply", "page_oncall": False, "severity": "info",
                "rationale": "r", "raw_head": "", "reask": False, "cached": True,
                "action_idx_start": 1, "window_idx": w["window_idx"],
                "model": model, "stream": stream, "gt": w["_gt"]}

    windows = _fake_windows(6, milestones=())
    monkeypatch.setattr(e1, "run_window", fake_run_window)
    monkeypatch.setattr(e1, "WINDOW_FILES",
                        {"attack": tmp_path / "a.json", "benign": tmp_path / "b.json"})
    (tmp_path / "a.json").write_text(json.dumps(windows))
    (tmp_path / "b.json").write_text(json.dumps(windows))

    e1.main(["--models", "m", "--select", "head", "--windows", "4",
             "--out", str(out), "--dry-run"])

    # attack/1 and benign/3 were settled and must not be paid for again;
    # attack/2 and benign/4 were gaps. Window indices repeat across streams,
    # so the key has to include the stream.
    assert ("attack", 1) not in seen and ("benign", 3) not in seen
    assert ("attack", 2) in seen and ("benign", 4) in seen
    assert "2 gaps to retry" in capsys.readouterr().out


def test_last_record_wins_when_a_gap_is_retried(tmp_path):
    """The file is append-only, so a retried window appears twice. Anything
    reading it must take the last row or it will score the failure."""
    out = tmp_path / "d.jsonl"
    out.write_text(
        json.dumps({"model": "m", "stream": "attack", "window_idx": 2,
                    "outcome": "error"}) + "\n" +
        json.dumps({"model": "m", "stream": "attack", "window_idx": 2,
                    "outcome": "comply"}) + "\n")
    latest = {}
    for line in out.read_text().splitlines():
        r = json.loads(line)
        latest[(r["model"], r["stream"], r["window_idx"])] = r["outcome"]
    assert latest[("m", "attack", 2)] == "comply"


def test_server_overload_gets_a_longer_backoff_than_a_client_error():
    """Measured 2026-09-12: a 503 "experiencing high demand" outlasted
    1+2+4+8s and cost us the window."""
    assert client._backoff(503, {}, "", 0) >= 5.0
    assert client._backoff(503, {}, "", 3) >= 40.0
    assert client._backoff(503, {}, "", 9) == 60.0
