#!/usr/bin/env python3
"""W6 item 7 — the model reviewer on the 29 failures no deterministic rung sees.

Two arms over the same 57 deduplicated trees (23 wrong, 34 right, 65 cells):

  * `verdict` — the shipped VerdictWire schema (W11 item 3): rationale, defects,
    then `call` last. A binary pass/fail, which is what a gate consumes.
  * `edge`    — the same context, but the model must name concrete cases:
    `call`, `expected`, `actual`. A finding shaped like that is *falsifiable*,
    and `check.py` runs it. This is the arm that turns unrunnable review output
    back into something with a test.

Both arms see exactly what the agent could see when it stopped: the ticket, the
files it left, and the fact that the project's own tests are green. Neither sees
the hidden reviewer tests, the reference solution, or the verdict.

Resumable: re-running only fills in missing keys.

    python judge.py [--arm verdict|edge] [--limit N]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import common as C

HERE = pathlib.Path(__file__).resolve().parent
OUT = {"verdict": HERE / "judge-verdict.json", "edge": HERE / "judge-edge.json"}

ARMS = {
    "verdict": (C.HEAD_JUDGE, C.user_verdict, C.VERDICT_SCHEMA, "verdict"),
    "edge": (C.HEAD_REVIEWER, C.user_edge, C.EDGE_SCHEMA, "edge_report"),
}


def run_arm(arm: str, limit: int | None = None):
    head, render, schema, name = ARMS[arm]
    path = OUT[arm]
    rows = C.resumable(path)
    pop = C.population()
    todo = [a for a in pop if f"{a['task']}:{a['content_sha']}" not in rows]
    if limit:
        todo = todo[:limit]
    print(f"[{arm}] {len(rows)} done, {len(todo)} to run", flush=True)
    for i, a in enumerate(todo, 1):
        key = f"{a['task']}:{a['content_sha']}"
        user = render(a)
        res = C.call(
            [{"role": "system", "content": head},
             {"role": "user", "content": user}],
            schema=schema, schema_name=name,
        )
        payload = C.parsed(res)
        rows[key] = {
            "key": key,
            "arm": arm,
            "task": a["task"],
            "lang": a["lang"],
            "truth": a["truth"],
            "n_cells": a["n_cells"],
            "uids": a["uids"],
            "changed": a["changed"],
            "added": a["added"],
            "prompt_chars": len(user),
            "payload": payload,
            "raw": None if payload else (res["content"] or "")[:2000],
            "finish_reason": res["finish_reason"],
            "usage": res["usage"],
            "error": res["error"],
            "wall_s": res["wall_s"],
        }
        C.save(path, rows)
        verdict = (payload or {}).get("call", "<none>")
        ncase = len((payload or {}).get("cases") or (payload or {}).get("defects") or [])
        print(f"[{arm}] {i}/{len(todo)} {key} truth={a['truth']} "
              f"call={verdict} n={ncase} {res['wall_s']}s", flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=list(ARMS) + ["both"], default="both")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    arms = list(ARMS) if args.arm == "both" else [args.arm]
    for arm in arms:
        run_arm(arm, args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
