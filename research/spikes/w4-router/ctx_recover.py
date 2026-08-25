"""Recover a floor on peak prompt occupancy for every Q56 cell, from transcripts.

WHY THIS EXISTS.  `tokens_in` in cells.jsonl is SESSION-CUMULATIVE prompt tokens
summed over iterations (harness `result.rs:1-12`) -- it is a cost number, not a
context number.  `peak_prompt_tokens` is the context number, and it is ABSENT
from every Q56 cell -- not through any fault of the descriptor, but because the
metric and the descriptor's optional 4th capture group were BOTH added in
`29703ef` (2026-08-17) and Q56 ran 2026-08-09..15 (W4 F375).  But the datum is
still in the transcript: the
turn-end marker line carries the subject's own gauge, `ctx ~N/60k`.

CORRECTED 2026-08-25 BY `ctx_calibrate.py` (W4 item 2, F368): the paragraph below
claims this number is a FLOOR on the peak.  IT IS NOT.  Calibrated against
`tokens_in / iterations` -- the server's own tokenizer, an exact real-token lower
bound on the peak -- it sits BELOW that bound on 61 of these 945 cells.  The four
mechanisms listed are each real; their sum is not, because `bytes/4` runs HIGH on
code and JSON.  And there is a fifth nobody listed: every cell that produces no
gauge at all is a TIMEOUT, so the population drops the longest-running cells.
Treat the output as an estimate good to about +/-10-20%, not as a bound.

WHAT THIS NUMBER IS, and it was believed to be a FLOOR (harness `main.rs:966-977`):
  1. the gauge OMITS the system prompt and tool schemas, so the run's measured
     `preamble_tokens_in` is added back here;
  2. the preamble is itself a lower bound (a mid-session tool-group open grows it);
  3. granularity is 1,024 tokens above 1k, because the gauge is humanized;
  4. it is a chars/4 estimate, and this corpus measures ~3.39 chars/token, so it
     runs low against a real tokenizer.
Each of the four understates -- but see the correction above: their SUM does not,
so "if it says a cell crossed a threshold, the cell crossed it" is FALSE.

Q56 tasks are ONE turn, and context grows monotonically within a turn, so the
turn-end gauge is that cell's peak.  Multi-turn cells would need the max over
markers, which is what this takes anyway.
"""
import json
import os
import re
import glob

ROOT = r"D:\dev\ABCC_20_powerd_by_claudette"
MARKER = re.compile(r"turn iter=(\d+) in=(\d+) out=(\d+) ctx ~([0-9]+k?)/")


def parse_gauge(tok: str) -> int:
    if tok.endswith("k"):
        return int(tok[:-1]) * 1024
    return int(tok)


def main():
    out = []
    for rundir in sorted(glob.glob(os.path.join(ROOT, "runs", "q56", "w8-*"))):
        meta = json.load(open(os.path.join(rundir, "runmeta.json"), encoding="utf-8"))
        preamble = meta["warmup"]["preamble_tokens_in"]
        run = os.path.basename(rundir)
        for cell in sorted(glob.glob(os.path.join(rundir, "cells", "*"))):
            tpath = os.path.join(cell, "transcript.log")
            if not os.path.isfile(tpath):
                continue
            name = os.path.basename(cell)
            task, _, variant = name.partition("__")
            best = None
            markers = 0
            with open(tpath, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    mm = MARKER.search(line)
                    if not mm:
                        continue
                    markers += 1
                    g = parse_gauge(mm.group(4))
                    if best is None or g > best[0]:
                        best = (g, int(mm.group(1)), int(mm.group(2)), int(mm.group(3)))
            if best is None:
                out.append({"run": run, "task": task, "variant": variant,
                            "markers": 0, "peak_floor": None,
                            "why": "no turn-end marker in transcript"})
                continue
            gauge, iters, tin, tout = best
            out.append({
                "run": run, "task": task, "variant": variant, "markers": markers,
                "gauge": gauge, "preamble": preamble,
                "peak_floor": gauge + preamble,
                "iterations": iters, "tokens_in_cumulative": tin, "tokens_out": tout,
                "granularity": 1024 if gauge >= 1024 else 1,
            })
    p = os.path.join(ROOT, "research", "spikes", "w4-router", "ctx.jsonl")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        for r in out:
            fh.write(json.dumps(r) + "\n")
    ok = [r for r in out if r.get("peak_floor")]
    print(f"cells with transcript: {len(out)}   with a marker: {len(ok)}")
    if ok:
        vals = sorted(r["peak_floor"] for r in ok)
        print(f"peak_floor  min {vals[0]}  median {vals[len(vals)//2]}  max {vals[-1]}")


if __name__ == "__main__":
    main()
