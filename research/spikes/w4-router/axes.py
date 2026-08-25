"""W4 item 2: are DIFFICULTY and REQUIRED CONTEXT two axes or one?

RESEARCH_BRIEF.md 11 asks W4 to "separate the two things V1 conflated: task
difficulty and required context length ... V1 mapped both onto one 8K/16K/32K
axis".  Item 1 measured both on Q56 and found the complexity score predicts
neither.  This asks the sharper question: given a real corpus, WHAT SETS
occupancy, what sets difficulty, and do the two move together?

Inputs, all already measured:
  * `ctx_calib.jsonl`   -- per cell: recovered peak occupancy (gauge+preamble),
                           `mean_real` (an EXACT real-token floor on the peak),
                           iterations, cumulative tokens, status, arm.
  * the corpus itself   -- per task: fixture bytes / files / lines, prompt words.

Everything is reported PER SUITE and, inside Q56 and U100, PER ARM, because 672
of the 952 Q56 cells come from arms built to stop the agent editing (memory item
26/28/31).  A pooled rate here would be a fact about the arm mix.
"""
import json
import os
import glob
import statistics as st

ROOT = r"D:\dev\ABCC_20_powerd_by_claudette"
SPIKE = os.path.join(ROOT, "research", "spikes", "w4-router")

TEXT_EXT = {".rs", ".py", ".ts", ".js", ".tsx", ".jsx", ".go", ".java", ".c", ".h", ".cpp",
            ".toml", ".json", ".yaml", ".yml", ".md", ".txt", ".jsonl", ".cfg", ".ini",
            ".sh", ".sql", ".html", ".css"}


def spearman(xs, ys):
    """Rank correlation, average ranks for ties. Returns None below n=3."""
    n = len(xs)
    if n < 3:
        return None

    def rank(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = rank(xs), rank(ys)
    mx, my = st.fmean(rx), st.fmean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx) ** 0.5
    dy = sum((b - my) ** 2 for b in ry) ** 0.5
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def fixture_profile(suite, task):
    """Bytes, files and lines the agent could read, plus the prompt's word count.

    Counts the WHOLE fixture tree, because the agent starts with a directory it has
    not read: what bounds occupancy is what it *could* pull in, not what it did.
    Binary-ish files are counted in bytes but not lines.
    """
    tdir = os.path.join(ROOT, "corpus", "suites", suite, "tasks", task)
    fdir = os.path.join(tdir, "fixture")
    total, files, lines, biggest = 0, 0, 0, 0
    for dirpath, _dirnames, filenames in os.walk(fdir):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:
                sz = os.path.getsize(p)
            except OSError:
                continue
            total += sz
            files += 1
            biggest = max(biggest, sz)
            if os.path.splitext(fn)[1].lower() in TEXT_EXT:
                try:
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        lines += sum(1 for _ in fh)
                except OSError:
                    pass
    ppath = os.path.join(tdir, "prompt.txt")
    words = 0
    if os.path.isfile(ppath):
        words = len(open(ppath, encoding="utf-8", errors="replace").read().split())
    return {"fixture_bytes": total, "fixture_files": files, "fixture_lines": lines,
            "fixture_largest_bytes": biggest, "prompt_words": words}


def main():
    rows = [json.loads(l) for l in open(os.path.join(SPIKE, "ctx_calib.jsonl"), encoding="utf-8")]
    prof = {}
    for r in rows:
        key = (r["suite"], r["task"])
        if key not in prof:
            prof[key] = fixture_profile(*key)
        r.update(prof[key])

    print("=" * 78)
    print("0 - the fixture, per suite: what the agent is handed before it reads a line")
    print("=" * 78)
    for suite in ("q56", "u100", "k"):
        ts = sorted({t for (s, t) in prof if s == suite})
        if not ts:
            continue
        b = [prof[(suite, t)]["fixture_bytes"] for t in ts]
        f = [prof[(suite, t)]["fixture_files"] for t in ts]
        ln = [prof[(suite, t)]["fixture_lines"] for t in ts]
        w = [prof[(suite, t)]["prompt_words"] for t in ts]
        print("  {:5} {:3} tasks | fixture bytes min {:>7} med {:>7} max {:>7} "
              "| files med {:>3} max {:>3} | lines med {:>5} max {:>6} | prompt words med {:>3}".format(
                  suite, len(ts), min(b), int(st.median(b)), max(b),
                  int(st.median(f)), max(f), int(st.median(ln)), max(ln), int(st.median(w))))

    print()
    print("=" * 78)
    print("1 - WHAT SETS OCCUPANCY: the fixture, or the effort spent inside it?")
    print("=" * 78)
    print("   rho over CELLS, within one suite and one arm, so neither suite mix nor")
    print("   arm mix can carry the number.")
    for suite, pop in (("q56", "q56"), ("u100", "u100"), ("k", "native")):
        arms = sorted({r["variant"] for r in rows if r["suite"] == suite})
        for arm in arms:
            cells = [r for r in rows
                     if r["suite"] == suite and r["variant"] == arm and r["recovered_peak"]]
            if len(cells) < 8:
                continue
            occ = [r["recovered_peak"] for r in cells]
            print("\n  {} / {} (n={} cells, {} tasks)".format(
                suite, arm, len(cells), len({r["task"] for r in cells})))
            for name, key in (("fixture_bytes", "fixture_bytes"),
                              ("fixture_files", "fixture_files"),
                              ("fixture_lines", "fixture_lines"),
                              ("prompt_words", "prompt_words"),
                              ("iterations (rounds actually run)", "iterations"),
                              ("tokens_in (cumulative COST)", "tokens_in")):
                xs = [r[key] for r in cells]
                if any(x is None for x in xs):
                    continue
                rho = spearman(xs, occ)
                print("      rho(occupancy, {:<34}) = {}".format(
                    name, "n/a" if rho is None else "{:+.3f}".format(rho)))

    print()
    print("=" * 78)
    print("2 - VARIANCE DECOMPOSITION: is occupancy a property of the TASK or of the RUN?")
    print("=" * 78)
    print("   If occupancy is a fixture property it is nearly constant within a task and")
    print("   varies between tasks. If it is an effort property the reverse holds.")
    for suite, arm in (("q56", "control"), ("q56", "deny-first-edit"),
                       ("u100", "control"), ("k", "control")):
        cells = [r for r in rows
                 if r["suite"] == suite and r["variant"] == arm and r["recovered_peak"]]
        if len(cells) < 8:
            continue
        by_task = {}
        for r in cells:
            by_task.setdefault(r["task"], []).append(r["recovered_peak"])
        grand = st.fmean([v for vs in by_task.values() for v in vs])
        n = sum(len(v) for v in by_task.values())
        between = sum(len(v) * (st.fmean(v) - grand) ** 2 for v in by_task.values())
        within = sum(sum((x - st.fmean(v)) ** 2 for x in v) for v in by_task.values())
        tot = between + within
        multi = {t: v for t, v in by_task.items() if len(v) > 1}
        spread = [max(v) - min(v) for v in multi.values()]
        print("\n  {} / {}: {} cells over {} tasks".format(suite, arm, n, len(by_task)))
        print("      between-task variance share: {:.1%}   within-task: {:.1%}".format(
            between / tot if tot else 0, within / tot if tot else 0))
        if spread:
            print("      within-task spread (max-min) over {} repeated tasks: "
                  "med {:.0f}  max {:.0f} tokens".format(
                      len(multi), st.median(spread), max(spread)))
        tmeans = sorted(st.fmean(v) for v in by_task.values())
        print("      per-task mean occupancy: min {:.0f}  med {:.0f}  max {:.0f}  "
              "(max/min = {:.2f}x)".format(
                  tmeans[0], st.median(tmeans), tmeans[-1], tmeans[-1] / tmeans[0]))

    print()
    print("=" * 78)
    print("3 - DO THE TWO AXES MOVE TOGETHER? occupancy vs difficulty, per arm")
    print("=" * 78)
    print("   Difficulty = the task's pass rate in that arm. A task is a point.")
    for suite in ("q56", "u100", "k"):
        for arm in sorted({r["variant"] for r in rows if r["suite"] == suite}):
            cells = [r for r in rows if r["suite"] == suite and r["variant"] == arm]
            by_task = {}
            for r in cells:
                by_task.setdefault(r["task"], []).append(r)
            tasks = [t for t, v in by_task.items() if len(v) >= 2]
            if len(tasks) < 5:
                continue
            passr, occ, fbytes, words, iters = [], [], [], [], []
            for t in tasks:
                v = by_task[t]
                passr.append(sum(1 for r in v if r["status"] == "pass") / len(v))
                o = [r["recovered_peak"] for r in v if r["recovered_peak"]]
                occ.append(st.fmean(o) if o else 0)
                fbytes.append(v[0]["fixture_bytes"])
                words.append(v[0]["prompt_words"])
                it = [r["iterations"] for r in v if r["iterations"]]
                iters.append(st.fmean(it) if it else 0)
            print("\n  {} / {} ({} tasks, pass rate {:.1%} pooled)".format(
                suite, arm, len(tasks), st.fmean(passr)))
            for name, xs in (("mean occupancy", occ), ("fixture_bytes", fbytes),
                             ("prompt_words", words), ("mean iterations", iters)):
                rho = spearman(xs, passr)
                print("      rho({:<16}, pass rate) = {}".format(
                    name, "n/a" if rho is None else "{:+.3f}".format(rho)))
            rho = spearman(fbytes, occ)
            print("      rho(fixture_bytes  , mean occupancy) = {}".format(
                "n/a" if rho is None else "{:+.3f}".format(rho)))

    out = os.path.join(SPIKE, "axes.jsonl")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print("\nwrote {} ({} rows)".format(out, len(rows)))


if __name__ == "__main__":
    main()
