"""W4 item 2, move 1: CALIBRATE the recovered occupancy gauge before extending it.

F363 ("context is a constant; 0 of 945 cells exceed 16K") rests entirely on
`ctx_recover.py`, which parses the subject's own `ctx ~N/...` gauge out of Q56
transcripts.  Before item 2 builds a routing input on that number, the number has
to be checked against something that was not itself.

TWO CHECKS, and they answer different questions.

CHECK A -- PARSER FIDELITY.  48 cells (K-series + W11 budget sweep) carry
`peak_prompt_tokens` NATIVELY, because their subject descriptor
(`claudette-af3f804.toml:49`) declares the optional 4th capture group that
`claudette-fc1ea22.toml:42` -- the Q56 subject -- does not.  Run the transcript
recovery over those and diff it against the field the harness wrote live.
WARNING: this is a WEAK check by construction.  `main.rs:985` computes the native
field as `peak_ctx + preamble_tokens_in`, which is the SAME arithmetic over the
SAME gauge.  Agreement proves the transcript parser is faithful; it proves
nothing about the gauge.  Stated here so the result is not over-read.

CHECK B -- THE GAUGE AGAINST A REAL TOKENIZER.  The same marker line carries a
second, INDEPENDENT instrument that item 1 read only as cost:
    `in=` is `summary.usage.input_tokens` (claudette `repl.rs:203-214`) -- the
    SERVER's tokenizer count, summed over the turn's iterations.
    `ctx ~` is `estimate_session_tokens` (`compact.rs:27`, `:433-446`) -- a
    `bytes/4 + 1` per-block heuristic that omits the system prompt and tools.
So `mean_prompt_tokens = tokens_in / iterations` is an EXACT real-token lower
bound on the largest single prompt of the session (a mean never exceeds a max).
If `peak_floor < mean_prompt_tokens`, the recovered number is NOT a floor on the
real peak and F363 must be qualified in place.

CHECK C -- HOW FAR ABOVE THE MEAN THE REAL PEAK SITS.  Within one turn the
prompt grows monotonically, so a_1 <= ... <= a_N with sum `tokens_in`.  Under a
linear-growth model a_N = 2*mean - a_1, with a_1 ~ preamble + the task prompt.
That is an ESTIMATE, not a bound, and it is reported as one.
"""
import json
import os
import re
import glob
import statistics as st

ROOT = r"D:\dev\ABCC_20_powerd_by_claudette"
SPIKE = os.path.join(ROOT, "research", "spikes", "w4-router")
MARKER = re.compile(r"turn iter=(\d+) in=(\d+) out=(\d+).*?ctx ~([0-9]+k?)/([0-9]+k?)")


def parse_gauge(tok):
    return int(tok[:-1]) * 1024 if tok.endswith("k") else int(tok)


def scan_transcript(path):
    """Max gauge over turn-end markers, plus the last marker's cumulative counts."""
    best = None
    last = None
    windows = set()
    n = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            mm = MARKER.search(line)
            if not mm:
                continue
            n += 1
            g = parse_gauge(mm.group(4))
            windows.add(mm.group(5))
            last = (int(mm.group(1)), int(mm.group(2)), int(mm.group(3)))
            if best is None or g > best:
                best = g
    return best, last, windows, n


def metric(cell, key):
    m = cell.get("metrics", {}).get(key, {})
    return m.get("measured")


def collect(run_globs, label):
    rows = []
    for pat in run_globs:
        for run_dir in sorted(glob.glob(os.path.join(ROOT, pat))):
            meta_p = os.path.join(run_dir, "runmeta.json")
            cells_p = os.path.join(run_dir, "cells.jsonl")
            if not (os.path.isfile(meta_p) and os.path.isfile(cells_p)):
                continue
            meta = json.load(open(meta_p, encoding="utf-8"))
            preamble = meta["warmup"]["preamble_tokens_in"]
            subject = meta.get("subject", {}).get("id")
            run = os.path.basename(run_dir)
            family = os.path.basename(os.path.dirname(run_dir))
            for line in open(cells_p, encoding="utf-8"):
                c = json.loads(line)
                name = c["task"] + "__" + c["variant"]
                tpath = os.path.join(run_dir, "cells", name, "transcript.log")
                if not os.path.isfile(tpath):
                    continue
                gauge, last, windows, nmark = scan_transcript(tpath)
                # `mean_prompt_tokens` post-dates the Q56 runs, so those cells do not carry it.
                # It is `tokens_in / iterations` and both of those ARE on every cell, so derive
                # it rather than losing the whole population -- and fall back to the transcript's
                # own last marker where even those are absent.
                iters = metric(c, "iterations")
                tin = metric(c, "tokens_in")
                if (iters is None or tin is None) and last is not None:
                    iters, tin = last[0], last[1]
                mean_real = metric(c, "mean_prompt_tokens")
                if mean_real is None and iters and tin:
                    mean_real = tin / iters
                rows.append({
                    "pop": label, "family": family, "run": run, "subject": subject,
                    "suite": c.get("suite"), "task": c["task"], "variant": c["variant"],
                    "status": c.get("status"),
                    "preamble": preamble,
                    "markers": nmark,
                    "windows": sorted(windows),
                    "gauge": gauge,
                    "recovered_peak": None if gauge is None else gauge + preamble,
                    "native_peak": metric(c, "peak_prompt_tokens"),
                    "iterations": iters,
                    "tokens_in": tin,
                    "mean_prompt_tokens": mean_real,
                    "mean_was_derived": metric(c, "mean_prompt_tokens") is None,
                    "last_marker": last,
                })
    return rows


def pct(vals, p):
    v = sorted(vals)
    if not v:
        return None
    k = min(len(v) - 1, int(round((p / 100.0) * (len(v) - 1))))
    return v[k]


def describe(name, vals, fmt="{:.0f}"):
    if not vals:
        print("  " + name + ": (none)")
        return
    print("  {}: n={}  min {}  p50 {}  p90 {}  max {}  mean {}".format(
        name, len(vals), fmt.format(min(vals)), fmt.format(pct(vals, 50)),
        fmt.format(pct(vals, 90)), fmt.format(max(vals)), fmt.format(st.fmean(vals))))


def main():
    native = collect(["runs/k-*/w8-*", "runs/w11-b*/w8-*"], "native")
    q56 = collect(["runs/q56/w8-*"], "q56")
    # U100 -- move 2's population.  The 5 top-level `runs/w8-*` and the 3 complete
    # `runs/prefix-invalid/*` runs are 31 cells each; the two short prefix-invalid runs
    # (9 and 2 cells) are aborted and carry no cells.jsonl, so they contribute nothing.
    u100 = collect(["runs/w8-*", "runs/prefix-invalid/w8-*"], "u100")
    rows = native + q56 + u100

    print("=" * 78)
    print("CHECK A - parser fidelity: recovered vs the natively captured field")
    print("=" * 78)
    both = [r for r in native if r["native_peak"] is not None and r["recovered_peak"] is not None]
    print("cells scanned in the native population: {}".format(len(native)))
    print("cells carrying BOTH a native field and a recovered value: {}".format(len(both)))
    exact = [r for r in both if abs(r["native_peak"] - r["recovered_peak"]) < 0.5]
    diff = [r for r in both if abs(r["native_peak"] - r["recovered_peak"]) >= 0.5]
    print("  exact agreement: {} / {}".format(len(exact), len(both)))
    for r in diff:
        print("  MISMATCH {}/{}__{}: native {} vs recovered {} (gauge {} + preamble {}, markers {})".format(
            r["run"], r["task"], r["variant"], r["native_peak"], r["recovered_peak"],
            r["gauge"], r["preamble"], r["markers"]))
    missing_native = [r for r in native if r["native_peak"] is None]
    print("  native field ABSENT on {} of {} native-population cells:".format(
        len(missing_native), len(native)))
    for r in missing_native:
        print("    {}/{}__{}  markers={} gauge={} status={} subject={}".format(
            r["run"], r["task"], r["variant"], r["markers"], r["gauge"], r["status"], r["subject"]))
    wins = {}
    for r in rows:
        for w in r["windows"]:
            wins[w] = wins.get(w, 0) + 1
    print("  gauge denominators seen across all {} scanned cells: {}".format(len(rows), wins))

    print()
    print("=" * 78)
    print("CHECK B - the gauge against the server's own tokenizer")
    print("=" * 78)
    for pop, label in ((native, "native (K + W11, af3f804)"), (q56, "q56 (fc1ea22)"),
                       (u100, "u100 (fc1ea22)")):
        usable = [r for r in pop
                  if r["recovered_peak"] and r["mean_prompt_tokens"] and r["iterations"]]
        print("\n{}: {} cells with both instruments".format(label, len(usable)))
        if not usable:
            continue
        describe("recovered_peak  (gauge+preamble, chars/4)",
                 [r["recovered_peak"] for r in usable])
        describe("mean_prompt_tokens (REAL tokens, exact floor on peak)",
                 [r["mean_prompt_tokens"] for r in usable])
        ratio = [r["recovered_peak"] / r["mean_prompt_tokens"] for r in usable]
        describe("ratio recovered_peak / mean_real", ratio, "{:.3f}")
        below = [r for r in usable if r["recovered_peak"] < r["mean_prompt_tokens"]]
        print("  cells where the RECOVERED PEAK IS BELOW THE REAL MEAN "
              "(so it is not a floor on the peak): {} / {} = {:.1f}%".format(
                  len(below), len(usable), 100.0 * len(below) / len(usable)))
        if below:
            worst = sorted(below, key=lambda r: r["recovered_peak"] / r["mean_prompt_tokens"])[:5]
            for r in worst:
                print("    {}/{}__{}: recovered {} < real mean {:.0f} (iters {}, tokens_in {}) ratio {:.3f}".format(
                    r["run"], r["task"], r["variant"], r["recovered_peak"],
                    r["mean_prompt_tokens"], r["iterations"], r["tokens_in"],
                    r["recovered_peak"] / r["mean_prompt_tokens"]))
        one_iter = [r for r in usable if r["iterations"] == 1]
        print("  cells with exactly ONE iteration (mean == peak exactly): {}".format(len(one_iter)))
        if one_iter:
            rr = [r["recovered_peak"] / r["mean_prompt_tokens"] for r in one_iter]
            describe("    ratio on those (a DIRECT gauge calibration)", rr, "{:.3f}")

    print()
    print("=" * 78)
    print("CHECK C - where the real peak lands, thresholds re-tested in real tokens")
    print("=" * 78)
    for pop, label in ((native, "native (K + W11)"), (q56, "q56"), (u100, "u100")):
        usable = [r for r in pop
                  if r["mean_prompt_tokens"] and r["iterations"] and r["recovered_peak"]]
        if not usable:
            continue
        print("\n{}: {} cells".format(label, len(usable)))
        for name, f in (
            ("recovered_peak (F363's number)", lambda r: r["recovered_peak"]),
            ("mean_real (exact floor on peak)", lambda r: r["mean_prompt_tokens"]),
            ("linear-model peak estimate 2*mean - preamble",
             lambda r: 2 * r["mean_prompt_tokens"] - r["preamble"]),
        ):
            vals = [f(r) for r in usable]
            describe(name, vals)
            for th in (8192, 16384, 32768):
                over = sum(1 for v in vals if v > th)
                print("      > {:>5}: {:>4} / {}  ({:.1f}%)".format(
                    th, over, len(vals), 100.0 * over / len(vals)))

    out = os.path.join(SPIKE, "ctx_calib.jsonl")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print("\nwrote {}  ({} rows)".format(out, len(rows)))


if __name__ == "__main__":
    main()
