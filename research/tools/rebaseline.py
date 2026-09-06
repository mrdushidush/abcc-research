#!/usr/bin/env python3
"""Read one abcc log and answer: what changed between two populations?

Built for W1-P1, the 2026-09-06 re-baseline. The August population and the
September one live in the same log, so the split is by date rather than by
anything the log labels — which is the honest cut, because nothing in the
record says "this attempt ran against that build".

Prints, per population: the ending distribution, the wall clock, the silences,
and the two instruments that read zero in the assessment (review_recorded and
control_requested).

    python rebaseline.py --log <path> --split 2026-09-01
"""
import argparse
import collections
import datetime as dt
import json
import sqlite3


def day(ms: int) -> str:
    return dt.datetime.fromtimestamp(ms / 1000, dt.UTC).strftime("%Y-%m-%d")


def load(path: str):
    c = sqlite3.connect(path)
    return [
        (seq, task, at_ms, json.loads(body))
        for seq, task, at_ms, body in c.execute(
            "SELECT seq, task, at_ms, body FROM event ORDER BY seq"
        )
    ], c


def population(rows, split: str, after: bool):
    """Events whose day is >= split (after) or < split (before)."""
    return [r for r in rows if (day(r[2]) >= split) == after]


def endings(rows):
    out = collections.Counter()
    for _, _, _, e in rows:
        if e["kind"] != "attempt_ended":
            continue
        o = e["outcome"]
        why = o.get("why")
        why = why.get("why") if isinstance(why, dict) else why
        out[(o.get("outcome"), why)] += 1
    return out


def attempt_spans(rows):
    """(task, seconds) per attempt, paired started -> ended."""
    open_at, spans = {}, []
    for _, task, at_ms, e in rows:
        if e["kind"] == "attempt_started":
            open_at[task] = at_ms
        elif e["kind"] == "attempt_ended" and task in open_at:
            spans.append((task, (at_ms - open_at.pop(task)) / 1000.0))
    return spans


def silences(rows):
    """Every gap between consecutive events, and how many were marked."""
    gaps = []
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        gaps.append(((b[2] - a[2]) / 1000.0, a[3]["kind"], b[3]["kind"]))
    return gaps


def marks_during_tool_calls(rows):
    """🚨 F625/F592's own instrument: liveness marks that name a tool call.

    Before tonight there could be none, because the mark was written from
    inside a loop that blocked for the whole idle gap. A non-zero count here is
    the repair working in the field rather than in a test.
    """
    writing = [
        e["note"]
        for _, _, _, e in rows
        if e["kind"] == "liveness_mark" and "writing a tool call" in e.get("note", "")
    ]
    quiet = [e for _, _, _, e in rows if e["kind"] == "liveness_mark" and "quiet for" in e.get("note", "")]
    return writing, quiet


def report(name, rows):
    print(f"\n{'=' * 62}\n{name}: {len(rows)} events")
    if not rows:
        return
    print(f"  {day(rows[0][2])} -> {day(rows[-1][2])}")

    end = endings(rows)
    total = sum(end.values())
    print(f"\n  attempts ended: {total}")
    for (o, w), n in sorted(end.items(), key=lambda kv: -kv[1]):
        share = f"{100 * n / total:.0f}%" if total else "-"
        print(f"    {n:3}  {share:>4}  {o or '-':14} {w or ''}")
    ok = sum(n for (o, _), n in end.items() if o == "success")
    if total:
        print(f"  SUCCESS RATE: {ok}/{total} = {100 * ok / total:.1f}%")

    spans = [s for _, s in attempt_spans(rows)]
    if spans:
        spans.sort()
        print(
            f"\n  attempt wall clock: n={len(spans)} "
            f"min {spans[0]:.0f}s  p50 {spans[len(spans) // 2]:.0f}s  "
            f"max {spans[-1]:.0f}s  total {sum(spans) / 60:.0f} min"
        )

    gaps = silences(rows)
    over = [g for g in gaps if g[0] > 10]
    if gaps:
        allg = sorted(g[0] for g in gaps)
        print(
            f"  gaps: {len(gaps)}, {len(over)} over 10 s, "
            f"p50 {allg[len(allg) // 2] * 1000:.0f} ms, max {allg[-1]:.0f} s"
        )

    writing, quiet = marks_during_tool_calls(rows)
    print(f"\n  liveness marks naming a tool call (F625): {len(writing)}")
    for note in writing[:4]:
        print(f"    {note}")
    print(f"  liveness marks reporting quiet (F592):     {len(quiet)}")

    for kind, label in [
        ("review_recorded", "review_recorded (W13's ladder)"),
        ("control_requested", "control_requested (agency)"),
        ("phase_nudged", "phase_nudged (ADR-0016)"),
        ("rung_recorded", "rung_recorded (the gate ran)"),
    ]:
        n = sum(1 for _, _, _, e in rows if e["kind"] == kind)
        print(f"  {label:34} {n}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--split", default="2026-09-01")
    a = ap.parse_args()

    rows, conn = load(a.log)
    report(f"BEFORE {a.split}", population(rows, a.split, after=False))
    report(f"FROM {a.split}", population(rows, a.split, after=True))

    print(f"\n{'=' * 62}\ntask states now")
    for state, n in collections.Counter(
        json.loads(s)["state"] for (s,) in conn.execute("SELECT state FROM task")
    ).most_common():
        print(f"  {n:3}  {state}")
