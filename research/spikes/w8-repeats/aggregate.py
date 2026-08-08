#!/usr/bin/env python3
"""Aggregate N repeat runs of the same W8 cells.

Throwaway-but-reproducible, like every other spike here. It exists because runs 1, 2 and 3 of the
same 31 cells disagreed on the headline (24/24, 22/24, 18/24) with byte-identical delivery, so no
W8 number may be quoted at n=1.

  python aggregate.py ../../../runs

Reads every `runs/w8-*/cells.jsonl`, keeps the runs that carry the same cell set, and reports:

  * per-cell PASS count across runs — the reproducibility signal, and the only honest way to say
    whether a cell "passes";
  * per-variant medians with min-max spread — medians, never means (the spread is wide and the
    distribution is not symmetric);
  * the aggregate denominator under SPEC's rule, taken from the runner's own `in_aggregate` flag
    rather than recomputed here, so this script cannot disagree with the loader.
"""

import collections
import json
import pathlib
import statistics
import sys

METRICS = ("wall_clock_s", "iterations", "tokens_in", "ttfvo_ms", "gate_fires")


def load(runs_dir):
    runs = []
    for d in sorted(pathlib.Path(runs_dir).glob("w8-*")):
        f = d / "cells.jsonl"
        if not f.is_file():
            continue  # a run still in flight has no cells.jsonl yet
        cells = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        meta = json.loads((d / "runmeta.json").read_text(encoding="utf-8"))
        runs.append((d.name, meta, cells))
    return runs


def measured(cell, name):
    m = cell["metrics"].get(name, {})
    return m.get("measured")


def main():
    runs_dir = sys.argv[1] if len(sys.argv) > 1 else "runs"
    runs = load(runs_dir)
    if not runs:
        sys.exit(f"no completed runs under {runs_dir}")

    # Only compare runs that measured the same cells. A partial run is reported and dropped, never
    # silently folded in — a smaller denominator that looks like a worse pass rate is exactly the
    # kind of quiet error this whole exercise exists to catch.
    keys = [frozenset((c["task"], c["variant"]) for c in cells) for _, _, cells in runs]
    common = max(collections.Counter(keys).items(), key=lambda kv: kv[1])[0]
    kept = [r for r, k in zip(runs, keys) if k == common]
    for (name, _, _), k in zip(runs, keys):
        if k != common:
            print(f"  ! dropping {name}: {len(k)} cells, not {len(common)}")

    subjects = {m["subject"]["id"] for _, m, _ in kept}
    models = {m["held"]["model_confirmed"] for _, m, _ in kept}
    ctxs = {m["held"]["num_ctx"] for _, m, _ in kept}
    print(f"n = {len(kept)} runs x {len(common)} cells")
    print(f"subject {'/'.join(sorted(subjects))}  model {'/'.join(sorted(models))}  "
          f"num_ctx {'/'.join(str(c) for c in sorted(ctxs))}")
    if len(subjects) > 1 or len(models) > 1 or len(ctxs) > 1:
        print("  ! these runs do not share their held constants — do not pool them")

    by_cell = collections.defaultdict(list)
    for _, _, cells in kept:
        for c in cells:
            by_cell[(c["task"], c["variant"])].append(c)

    n = len(kept)
    print(f"\n=== per-cell verdicts across {n} runs "
          f"(agg = counts toward the aggregate denominator)\n")
    print(f"{'task':<24}{'variant':<21}{'pass':>5}{'fail':>5}{'inval':>6}  agg  reproducible")
    unstable = 0
    for (task, variant), cs in sorted(by_cell.items()):
        v = collections.Counter(c["status"] for c in cs)
        agg = "yes" if cs[0]["in_aggregate"] else " no"
        stable = max(v.values()) == n
        unstable += 0 if stable else 1
        mark = "" if stable else "  <- flips"
        print(f"{task:<24}{variant:<21}{v['pass']:>5}{v['fail']:>5}{v['invalid']:>6}  {agg}{mark}")

    agg_cells = [cs for cs in by_cell.values() if cs[0]["in_aggregate"]]
    print(f"\naggregate-eligible cells: {len(agg_cells)}")
    per_run = [sum(1 for c in cells if c["in_aggregate"] and c["status"] == "pass")
               for _, _, cells in kept]
    print(f"pass count per run: {per_run}  (median {statistics.median(per_run)}, "
          f"range {min(per_run)}-{max(per_run)} of {len(agg_cells)})")
    print(f"cells whose verdict is not identical across all {n} runs: {unstable} of {len(by_cell)}")

    print(f"\n=== per-variant medians over aggregate-eligible cells, {n} runs pooled\n")
    print(f"{'variant':<21}{'cells':>6}" + "".join(f"{m:>16}" for m in METRICS))
    by_variant = collections.defaultdict(lambda: collections.defaultdict(list))
    for cs in agg_cells:
        for c in cs:
            for m in METRICS:
                x = measured(c, m)
                if x is not None:
                    by_variant[c["variant"]][m].append(x)
    for variant in sorted(by_variant):
        row = f"{variant:<21}{len(by_variant[variant]['wall_clock_s']):>6}"
        for m in METRICS:
            xs = by_variant[variant][m]
            row += f"{statistics.median(xs):>9.1f} ({min(xs):.0f}-{max(xs):.0f})".rjust(16) \
                if xs else "".rjust(16)
        print(row)
    print("\nMedians, never means: the spread in brackets is min-max over every pooled cell.")


if __name__ == "__main__":
    main()
