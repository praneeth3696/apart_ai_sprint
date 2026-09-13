# Finding the Gemini E3 file

## What it is

A **JSONL** file — one JSON object per line, 48 lines (24 moments × 2 models),
roughly **60–70 KB**. Default location in her clone:

```
runs/e3/live/e3_decisions.jsonl
```

with `e3_decisions_manifest.json` sitting next to it. `runs/` is **gitignored**,
which is exactly why it didn't travel with PR #12.

Each line looks like this (one moment, one model):

```json
{"exp":"e3","model":"google:gemini-3.1-flash-lite","moment_idx":1,
 "anchor_phase":"unclassified","anchor_action_idx":1,"anchor_is_milestone":false,
 "n_evidence":10,"monitor_outcome":"comply","assistant_outcome":"comply",
 "escalates":false,"severity":"low","refuses":false,"cell":"coherent-calm",
 "monitor_rationale":"...","assistant_head":"...","provider":"Google AI Studio",
 "model_returned":"gemini-3.1-flash-lite","gt":{...}}
```

The two giveaways: the string `"exp":"e3"` and
`"model":"google:gemini-3.1-flash-lite"`.

## 1. Find it by content, not by name

Name doesn't matter — search for what's inside. From her repo root:

```bash
grep -rl '"exp": *"e3"' . 2>/dev/null | grep -v '^./\.git/'
```

Wider net, in case it was moved or renamed anywhere under home:

```bash
grep -rl 'gemini-3.1-flash-lite' ~ --include='*.jsonl' --include='*.json' \
     --include='*.txt' --include='*.log' 2>/dev/null | head -20
```

By shape rather than content:

```bash
find ~ -name '*.jsonl' -size +20k -newermt 2026-09-12 2>/dev/null | head -20
```

Also worth checking: `~/Downloads`, `~/Desktop`, a `runs/` folder in a *second*
clone, or wherever her Claude Code session had its working directory — it may
not be the same clone she made the PR from.

## 2. If the file is gone but the CACHE survived — rebuild it free

This is the likely rescue. The harness caches **every API response on receipt**,
separately from the decisions file. Check:

```bash
ls runs/e3_monitor/ runs/e3_assistant/ 2>/dev/null
```

If she sees `google_gemini-3.1-flash-lite/` and `google_gemini-3.5-flash-lite/`
directories with `.json` files in them, everything is recoverable. **Re-run the
exact original command** — every call is a cache hit, so it costs **zero API
calls, no quota, and finishes in seconds**:

```bash
.venv/bin/python3 harness/e3_incoherence.py \
  --models google:gemini-3.1-flash-lite,google:gemini-3.5-flash-lite \
  --max-tokens 6000 --rpm 8
```

It rewrites `runs/e3/live/e3_decisions.jsonl` from cache. Confirm with:

```bash
grep -c . runs/e3/live/e3_decisions.jsonl        # expect 48
```

## 3. If both the file and the cache are gone — just re-run it

It's only 48 calls and her quota reset ~12 hours ago. Same command as above.
Ten minutes, $0.00. **Do not spend an hour hunting for a file that costs ten
minutes to regenerate.**

## 4. Sending it

Any channel is fine — it's plain text, no secrets in it (no API keys, no
credentials; just model outputs and window metadata).

```bash
cp runs/e3/live/e3_decisions.jsonl ~/Desktop/amirtha_e3_gemini.jsonl
```

Praneeth only needs the path once it's on his machine; the merge is a single
`cat` because the file is append-only and deduped last-record-wins.

## Sanity check before sending

```bash
python3 - <<'PY'
import json, collections
c = collections.Counter()
for line in open("runs/e3/live/e3_decisions.jsonl"):
    if line.strip(): c[json.loads(line)["model"]] += 1
for m, n in sorted(c.items()): print(f"{m:<36} {n}")
PY
```

Expect exactly:

```
google:gemini-3.1-flash-lite         24
google:gemini-3.5-flash-lite         24
```

If a model shows fewer than 24, that's fine — send it anyway. Partial data that
arrives in time beats complete data that arrives after the report is cut.
