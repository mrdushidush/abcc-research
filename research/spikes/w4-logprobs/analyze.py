"""W4 item 4: does a logprob-derived confidence predict whether the attempt was
actually right, and does it beat the counters that are already free?

Population: five repeats of Q56 control behind the recorder, joined to
`cells.jsonl` on (task, variant) inside each repeat.

Three things this has to get right, all of them lessons already paid for:

  * THE INSTRUMENT FIRST.  Every call must satisfy `n_entries ==
    completion_tokens` and carry alternatives on every token; under MTP the
    array is fabricated and a correlation computed from it is a fact about
    draft acceptance.  Checked and printed before any number that depends on it.

  * AUC, NOT rho, AND A BOOTSTRAP (item 3's traps 4 and 5).  Most cells pass, so
    a correlation against a mostly-constant outcome is a weak instrument, and at
    this n an ordering without an interval is a story.

  * THE BOOTSTRAP RESAMPLES TASKS, NOT CELLS.  Five repeats of the same 56 tasks
    are five looks at 56 clusters, not 280 independent trials.  Resampling cells
    would report an interval several times too narrow -- the pooling error
    memory items 26/28/31 keep catching in a new costume.

And it asks the question that actually decides the item, which the pooled
comparison cannot: WITHIN a task that sometimes passes and sometimes fails, is
the failing attempt the less confident one?  That comparison holds task
difficulty exactly constant, and it is the only form in which an in-flight
signal could route anything.
"""
import glob
import json
import math
import os
import random
import statistics
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
BOOT = 10000
SEED = 20260826

random.seed(SEED)


# ---------------------------------------------------------------- loading ----
def jsonl(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("{"):
                yield json.loads(line)


def load_calls():
    """recorder rows -> {(rep, task): [call, ...]} in emission order."""
    by_cell = defaultdict(list)
    probes = 0
    for path in sorted(glob.glob(os.path.join(HERE, "lp-rep*.jsonl"))):
        rep = int(os.path.basename(path).split("rep")[1].split(".")[0])
        for r in jsonl(path):
            if not r.get("task"):
                probes += 1          # model-confirm probe + warmup, no cell
                continue
            by_cell[(rep, r["task"])].append(r)
    for v in by_cell.values():
        v.sort(key=lambda r: r["seq"])
    return by_cell, probes


def load_cells():
    """harness cells -> {(rep, task): cell}."""
    out = {}
    for d in sorted(glob.glob(os.path.join(ROOT, "runs", "w4-lp-r*"))):
        rep = int(os.path.basename(d).split("-r")[-1])
        for cp in sorted(glob.glob(os.path.join(d, "w8-*", "cells.jsonl"))):
            for c in jsonl(cp):
                if c.get("variant") != "control":
                    continue
                out[(rep, c["task"])] = c
    return out


def metric(cell, name):
    m = (cell.get("metrics") or {}).get(name) or {}
    return m.get("measured")


# --------------------------------------------------------------- features ----
def _q(xs, p):
    if not xs:
        return None
    s = sorted(xs)
    i = max(0, min(len(s) - 1, int(round(p * (len(s) - 1)))))
    return s[i]


def _split_trace(call):
    """Index of the first token after the reasoning trace.

    The array covers reasoning tokens as well as the answer, so a per-call mean
    silently mixes the two.  llama-server returns `reasoning_content`
    separately, and the trace terminator appears in the token stream.
    """
    toks = call.get("tokens") or []
    for i, t in enumerate(toks):
        if t and "</think>" in t:
            return i + 1
    return 0 if not (call.get("reasoning_chars") or 0) else len(toks)


def _agg(lps, margins, prefix):
    lps = [x for x in lps if x is not None]
    margins = [x for x in margins if x is not None]
    f = {}
    if lps:
        f[prefix + "mean_lp"] = sum(lps) / len(lps)
        f[prefix + "min_lp"] = min(lps)
        f[prefix + "p10_lp"] = _q(lps, 0.10)
        f[prefix + "sum_lp"] = sum(lps)
        f[prefix + "frac_lp_lt_half"] = sum(1 for v in lps if v < math.log(0.5)) / len(lps)
        f[prefix + "n_tokens"] = len(lps)
    if margins:
        f[prefix + "mean_margin"] = sum(margins) / len(margins)
        f[prefix + "p10_margin"] = _q(margins, 0.10)
        f[prefix + "frac_margin_lt_1"] = sum(1 for v in margins if v < 1.0) / len(margins)
    return f


# The turns that actually change the tree.  "Worker output" in the sense §11
# means is the EDIT, not the reads and not the trace, so it gets its own bucket:
# a mean over the whole cell dilutes the tokens of the diff with hundreds of
# tokens of reasoning and file-reading.
# The observed vocabulary across every recorded run here is bash(218),
# read_file(211), apply_diff(133), run_tests(31), glob_search(26),
# write_file(18), list_dir(10), grep_search(3).  `bash` is deliberately NOT a
# mutator: it is used for both reading and writing and counting it as an edit
# would put shell inspection in the same bucket as the diff.
MUTATORS = {"apply_diff", "write_file", "create_file", "edit_file", "str_replace"}


def features(calls, cell):
    """Every candidate signal for one cell, plus the free counters it must beat."""
    all_lp, all_mg, ans_lp, ans_mg, tr_lp = [], [], [], [], []
    edit_lp, edit_mg = [], []
    for c in calls:
        lps, mgs = c.get("logprobs") or [], c.get("margins") or []
        all_lp += lps
        all_mg += mgs
        i = _split_trace(c)
        ans_lp += lps[i:]
        ans_mg += mgs[i:]
        tr_lp += lps[:i]
        if MUTATORS.intersection(c.get("tool_names") or []):
            edit_lp += lps[i:]
            edit_mg += mgs[i:]
    f = {}
    f.update(_agg(edit_lp, edit_mg, "edit_"))
    f.update(_agg(all_lp, all_mg, "all_"))
    f.update(_agg(ans_lp, ans_mg, "ans_"))
    f.update(_agg(tr_lp, [], "trace_"))
    if calls:
        last = calls[-1]
        f.update(_agg(last.get("logprobs") or [], last.get("margins") or [], "last_"))
        first = calls[0]
        f.update(_agg(first.get("logprobs") or [], first.get("margins") or [], "first_"))
    f["n_calls"] = len(calls)
    # Free STRUCTURAL signals, costing nothing and needing no serving change:
    # a turn that came back with no content and no tool call, a turn that hit
    # the generation ceiling, and the subject's own empty-turn retry firing
    # (it doubles `max_tokens`, so a value above the configured 8192 IS the
    # retry).  These are in the table because a logprob has to beat them, not
    # only beat the counters.
    f["free_n_length_stops"] = sum(
        1 for c in calls if c.get("finish_reason") == "length")
    f["free_n_empty_turns"] = sum(
        1 for c in calls
        if not c.get("content_chars") and not c.get("n_tool_calls"))
    f["free_retry_fired"] = 1.0 if any(
        (c.get("max_tokens") or 0) > 8192 for c in calls) else 0.0
    f["free_max_reasoning_chars"] = float(
        max([c.get("reasoning_chars") or 0 for c in calls] or [0]))
    # Occupancy, EXACTLY, not the subject's printed gauge.  Item 1's F362 put
    # occupancy at the top of the free in-flight signals (+0.405) and item 2's
    # F368 found the gauge sits below a true token bound on 61 of 945 cells.
    # `usage.prompt_tokens` on each call is that true bound, per call, free.
    prompts = [(c.get("usage") or {}).get("prompt_tokens") for c in calls]
    prompts = [p for p in prompts if p]
    if prompts:
        f["free_peak_prompt_tokens"] = float(max(prompts))
        f["free_total_prompt_tokens"] = float(sum(prompts))
    # the free counters already on disk -- item 1's F362 ordering
    for name in ("iterations", "tokens_out", "tokens_in", "tokens_in_net",
                 "wall_clock_s", "turns", "ttfvo_ms"):
        v = metric(cell, name)
        if v is not None:
            f["free_" + name] = float(v)
    return f


# ---------------------------------------------------------------- scoring ----
def auc(scores, labels):
    """P(score of a positive > score of a negative), ties at 0.5.

    `labels` is 1 for the event being predicted (here: the attempt FAILED)."""
    pos = [s for s, y in zip(scores, labels) if y]
    neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(pos) * len(neg))


def spearman(xs, ys):
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
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else None


def cluster_boot_auc(rows, key, n=BOOT):
    """Bootstrap AUC by resampling TASKS with replacement, not cells."""
    by_task = defaultdict(list)
    for r in rows:
        by_task[r["task"]].append(r)
    tasks = sorted(by_task)
    out = []
    for _ in range(n):
        draw = [random.choice(tasks) for _ in tasks]
        s, y = [], []
        for t in draw:
            for r in by_task[t]:
                if r["f"].get(key) is None:
                    continue
                s.append(r["f"][key])
                y.append(r["fail"])
        a = auc(s, y)
        if a is not None:
            out.append(a)
    out.sort()
    if not out:
        return None, None
    return out[int(0.025 * len(out))], out[int(0.975 * len(out)) - 1]


def cluster_boot_delta(rows, key_a, key_b, n=BOOT):
    """Paired difference AUC(a) - AUC(b) on the same resampled tasks."""
    by_task = defaultdict(list)
    for r in rows:
        by_task[r["task"]].append(r)
    tasks = sorted(by_task)
    out = []
    for _ in range(n):
        draw = [random.choice(tasks) for _ in tasks]
        sa, sb, y = [], [], []
        for t in draw:
            for r in by_task[t]:
                if r["f"].get(key_a) is None or r["f"].get(key_b) is None:
                    continue
                sa.append(r["f"][key_a])
                sb.append(r["f"][key_b])
                y.append(r["fail"])
        aa, ab = auc(sa, y), auc(sb, y)
        if aa is not None and ab is not None:
            out.append(aa - ab)
    out.sort()
    if not out:
        return None, None, None
    return (statistics.median(out), out[int(0.025 * len(out))],
            out[int(0.975 * len(out)) - 1])


# ------------------------------------------------------------------- main ----
def main():
    calls, probes = load_calls()
    cells = load_cells()
    print("=" * 78)
    print("POPULATION")
    print("=" * 78)
    print("recorder cells: %d   harness cells: %d   non-cell calls (probe+warmup): %d"
          % (len(calls), len(cells), probes))

    # ---- instrument check, before anything that depends on it --------------
    n_calls = ok_len = ok_alts = bad_http = aborted = 0
    fabricated = []
    for cl in calls.values():
        for c in cl:
            n_calls += 1
            if c.get("client_gone"):
                aborted += 1
            if c.get("http") != 200:
                bad_http += 1
                continue
            ct = (c.get("usage") or {}).get("completion_tokens")
            ne = c.get("n_entries") or 0
            if ct is not None and ne == ct:
                ok_len += 1
            if ne and c.get("n_with_alts") == ne:
                ok_alts += 1
            elif ne:
                fabricated.append((c.get("task"), ne, c.get("n_with_alts")))
    print("\nINSTRUMENT: %d completion calls · array length == completion_tokens on "
          "%d · alternatives on every token in %d · non-200 %d · aborted "
          "because the subject went away %d"
          % (n_calls, ok_len, ok_alts, bad_http, aborted))
    if fabricated:
        print("  !! %d calls carry entries WITHOUT alternatives on every token — "
              "that is F387's fabricated array and it must not be scored: %s"
              % (len(fabricated), fabricated[:5]))
    scored = n_calls - bad_http
    if ok_len != scored:
        print("  note: %d of %d calls have an array length that differs from "
              "completion_tokens (seen: off-by-one on a tool-call turn). Small "
              "counts here are a reporting quirk; a LARGE count would mean the "
              "array does not describe the emitted text." % (scored - ok_len, scored))
    if scored and (scored - ok_len) > 0.01 * scored:
        print("  !! more than 1%% of calls disagree with completion_tokens -- "
              "every number below is suspect")

    # ---- assemble ----------------------------------------------------------
    rows = []
    dropped = defaultdict(int)
    for key, cl in sorted(calls.items()):
        cell = cells.get(key)
        if not cell:
            dropped["no harness cell"] += 1
            continue
        st = cell.get("status")
        if st not in ("pass", "fail"):
            # timeouts and errors are NOT failures of the fix; every one of
            # them is named rather than quietly excluded
            dropped[str(st)] += 1
            continue
        rows.append({"rep": key[0], "task": key[1], "status": st,
                     "fail": 1 if st == "fail" else 0,
                     "f": features(cl, cell)})
    if dropped:
        print("dropped: " + ", ".join("%s x%d" % (k, v)
                                      for k, v in sorted(dropped.items())))
    if not rows:
        print("\nno cells with an outcome yet — run campaign.sh first.")
        return
    nfail = sum(r["fail"] for r in rows)
    print("\nusable cells %d over %d tasks · fail %d (%.1f%%) · pass rate %.1f%%"
          % (len(rows), len(set(r["task"] for r in rows)), nfail,
             100.0 * nfail / len(rows), 100.0 * (1 - nfail / len(rows))))
    per_rep = defaultdict(lambda: [0, 0])
    for r in rows:
        per_rep[r["rep"]][0] += 1
        per_rep[r["rep"]][1] += 1 - r["fail"]
    print("per repeat (pass/n): " + "  ".join(
        "r%d %d/%d" % (k, v[1], v[0]) for k, v in sorted(per_rep.items())))
    print("recorded control runs for comparison: 49/56, 50/56, 48/56")
    subject_drift(rows)

    if nfail < 3:
        print("\ntoo few failures to score anything.")
        return

    # ---- discrimination ----------------------------------------------------
    keys = sorted({k for r in rows for k in r["f"]})
    print("\n" + "=" * 78)
    print("DISCRIMINATION -- AUC for predicting FAIL, 95%% CI by bootstrap over "
          "TASKS (%d resamples)" % BOOT)
    print("=" * 78)
    print("%-26s %8s %8s %20s %8s" % ("signal", "AUC", "rho", "95% CI", "n"))
    table = []
    for k in keys:
        s = [r["f"][k] for r in rows if r["f"].get(k) is not None]
        y = [r["fail"] for r in rows if r["f"].get(k) is not None]
        if len(set(s)) < 2:
            continue
        a = auc(s, y)
        if a is None:
            continue
        # orient every signal so that HIGHER means "more likely to fail"
        flip = a < 0.5
        s2 = [-v for v in s] if flip else s
        a2 = auc(s2, y)
        rho = spearman(s2, y)
        sub = [{"task": r["task"], "fail": r["fail"],
                "f": {k: (-r["f"][k] if flip else r["f"][k])}}
               for r in rows if r["f"].get(k) is not None]
        lo, hi = cluster_boot_auc(sub, k)
        table.append({"key": k, "flipped": flip, "auc": a2, "rho": rho,
                      "lo": lo, "hi": hi, "n": len(s)})
    table.sort(key=lambda t: -t["auc"])
    for t in table:
        print("%-26s %8.3f %8s %20s %8d%s"
              % (t["key"], t["auc"],
                 "%.3f" % t["rho"] if t["rho"] is not None else "-",
                 "[%.3f, %.3f]" % (t["lo"], t["hi"]) if t["lo"] is not None else "-",
                 t["n"], "  (lower=worse)" if t["flipped"] else ""))
    beats = [t for t in table if t["lo"] is not None and t["lo"] > 0.5]
    print("\nsignals whose 95%% CI excludes the coin: %d of %d%s"
          % (len(beats), len(table),
             (" -- " + ", ".join(t["key"] for t in beats)) if beats else ""))

    # ---- best logprob signal vs best free counter --------------------------
    # A `*_n_tokens` feature is a TOKEN COUNT, not a confidence: it is derived
    # from the logprob array here only because that is where the tokens were
    # counted, and `usage.completion_tokens` gives it for nothing on the
    # deployed path.  Crediting logprobs for it would be crediting them for
    # arithmetic that needs no logprobs, so it counts as free.
    def is_free(k):
        return k.startswith("free_") or k.endswith("_n_tokens") or k == "n_calls"

    lp_best = next((t for t in table if not is_free(t["key"])), None)
    free_best = next((t for t in table if is_free(t["key"])), None)
    if lp_best and free_best:
        print("\n" + "=" * 78)
        print("THE COMPARISON THAT DECIDES IT")
        print("=" * 78)
        print("best logprob signal : %-22s AUC %.3f" % (lp_best["key"], lp_best["auc"]))
        print("best free counter   : %-22s AUC %.3f" % (free_best["key"], free_best["auc"]))
        sub = []
        for r in rows:
            fa, fb = r["f"].get(lp_best["key"]), r["f"].get(free_best["key"])
            if fa is None or fb is None:
                continue
            sub.append({"task": r["task"], "fail": r["fail"],
                        "f": {"a": -fa if lp_best["flipped"] else fa,
                              "b": -fb if free_best["flipped"] else fb}})
        med, lo, hi = cluster_boot_delta(sub, "a", "b")
        print("paired difference   : %+.3f  95%% CI [%+.3f, %+.3f]  -> %s"
              % (med, lo, hi,
                 "separable from zero" if (lo > 0 or hi < 0) else "SPANS ZERO"))

    # ---- the within-task comparison ---------------------------------------
    print("\n" + "=" * 78)
    print("WITHIN-TASK: on tasks that both pass and fail across the repeats, is "
          "the FAILING attempt the less confident one?")
    print("=" * 78)
    by_task = defaultdict(list)
    for r in rows:
        by_task[r["task"]].append(r)
    mixed = {t: v for t, v in by_task.items()
             if 0 < sum(x["fail"] for x in v) < len(v)}
    print("tasks with both outcomes: %d of %d" % (len(mixed), len(by_task)))
    if mixed:
        print("%-26s %8s %8s %8s %10s" %
              ("signal", "lower", "higher", "tie", "sign test"))
        print("  (a signal is listed only where at least 5 mixed tasks separate "
              "the two outcomes; with %d mixed tasks a two-sided sign test "
              "cannot reach 0.05 below n=6 anyway)" % len(mixed))
        for k in keys:
            lower = higher = tie = 0
            for t, v in mixed.items():
                fs = [x["f"].get(k) for x in v if x["fail"]]
                ps = [x["f"].get(k) for x in v if not x["fail"]]
                fs = [x for x in fs if x is not None]
                ps = [x for x in ps if x is not None]
                if not fs or not ps:
                    continue
                mf, mp = sum(fs) / len(fs), sum(ps) / len(ps)
                if mf < mp:
                    lower += 1
                elif mf > mp:
                    higher += 1
                else:
                    tie += 1
            n = lower + higher
            if n < 5:
                continue
            # two-sided sign test
            p = 2.0 * sum(math.comb(n, i) for i in range(0, min(lower, higher) + 1)) / (2.0 ** n)
            p = min(1.0, p)
            print("%-26s %8d %8d %8d %10.3f" % (k, lower, higher, tie, p))
        print("\n'lower' = the failing attempt scored lower on that signal. For a "
              "confidence signal to mean anything, failing attempts must be "
              "LESS confident, consistently, at a p the sign test can see.")

    per_call_runaway(calls)

    with open(os.path.join(HERE, "cell-features.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print("\nwrote cell-features.jsonl (%d cells)" % len(rows))


def subject_drift(rows):
    """Did the three forced changes move the SUBJECT, per task, or only the
    timeout column?

    F390 established that the endpoint moves outcomes on the expensive tasks.
    This is the same question asked over every task with a label in both
    populations: the recorded controls are three Q56 control runs on `:1234`
    with streaming and MTP on, this campaign is the same tasks on the bare
    endpoint.  Reported as a per-task pass-rate comparison rather than a pooled
    one, because a pooled rate is exactly what hides a treatment (memory items
    26/28/31).
    """
    rec = defaultdict(list)
    for d in sorted(glob.glob(os.path.join(ROOT, "runs", "q56", "w8-17868*"))):
        cp = os.path.join(d, "cells.jsonl")
        if not os.path.isfile(cp):
            continue
        for c in jsonl(cp):
            if c.get("variant") == "control" and c.get("status") in ("pass", "fail"):
                rec[c["task"]].append(1 if c["status"] == "pass" else 0)
    here = defaultdict(list)
    for r in rows:
        here[r["task"]].append(0 if r["fail"] else 1)
    both = sorted(set(rec) & set(here))
    if not both:
        return
    moved_up, moved_down, same = [], [], 0
    for t in both:
        a = sum(rec[t]) / len(rec[t])
        b = sum(here[t]) / len(here[t])
        if b > a:
            moved_up.append((t, a, b))
        elif b < a:
            moved_down.append((t, a, b))
        else:
            same += 1
    print("\nSUBJECT DRIFT vs the recorded controls, per task (%d tasks labelled in "
          "both): unchanged %d · better here %d · worse here %d"
          % (len(both), same, len(moved_up), len(moved_down)))
    for name, g in (("better on the bare endpoint", moved_up),
                    ("worse on the bare endpoint", moved_down)):
        if g:
            print("  %-28s %s" % (name, ", ".join(
                "%s %.0f%%->%.0f%%" % (t, 100 * a, 100 * b)
                for t, a, b in sorted(g)[:12])))
    print("  ⚠ a task missing here timed out and carries no label at all; it is "
          "absent from this comparison, not counted as a failure.")


PREFIX = 200


def per_call_runaway(calls):
    """A second question the same data answers, and a better-powered one.

    F390 made the runaway turn expensive: a call that overruns `max_tokens`
    carrying no content is scored as an empty turn, and the retry chain then
    spends ~640 s.  So ask the in-flight question that has an actual use --
    read the first PREFIX tokens, and predict whether THIS CALL will end at the
    ceiling with nothing to show.  The unit is a call rather than a cell, so
    there are an order of magnitude more of them, and the decision it would
    drive (stop this turn now) is one a router could actually take.

    The comparison that matters is against a FREE structural signal that needs
    no logprobs at all: by token PREFIX, has the reasoning trace closed?
    """
    units = []
    for (rep, task), cl in calls.items():
        for c in cl:
            toks = c.get("tokens") or []
            lps = c.get("logprobs") or []
            mgs = c.get("margins") or []
            if len(toks) < PREFIX or c.get("http") != 200:
                continue
            head_lp = [x for x in lps[:PREFIX] if x is not None]
            head_mg = [x for x in mgs[:PREFIX] if x is not None]
            if not head_lp:
                continue
            closed = any(t and "</think>" in t for t in toks[:PREFIX])
            f = {"head_mean_lp": sum(head_lp) / len(head_lp),
                 "head_min_lp": min(head_lp),
                 "head_p10_lp": _q(head_lp, 0.10),
                 "head_frac_lp_lt_half": sum(1 for v in head_lp if v < math.log(0.5))
                 / len(head_lp),
                 "free_trace_still_open": 0.0 if closed else 1.0}
            if head_mg:
                f["head_mean_margin"] = sum(head_mg) / len(head_mg)
                f["head_p10_margin"] = _q(head_mg, 0.10)
            runaway = 1 if (c.get("finish_reason") == "length"
                            and not c.get("content_chars")
                            and not c.get("n_tool_calls")) else 0
            units.append({"task": task, "fail": runaway, "f": f})

    print("\n" + "=" * 78)
    print("PER-CALL: read the first %d tokens — will THIS turn run away?" % PREFIX)
    print("=" * 78)
    n_ev = sum(u["fail"] for u in units)
    print("calls of at least %d tokens: %d · runaway turns: %d (%.1f%%)"
          % (PREFIX, len(units), n_ev,
             100.0 * n_ev / len(units) if units else 0.0))
    if n_ev < 5 or len(units) - n_ev < 5:
        print("too few events to score.")
        return
    keys = sorted({k for u in units for k in u["f"]})
    print("%-26s %8s %20s" % ("signal", "AUC", "95% CI"))
    out = []
    for k in keys:
        s = [u["f"][k] for u in units if u["f"].get(k) is not None]
        y = [u["fail"] for u in units if u["f"].get(k) is not None]
        if len(set(s)) < 2:
            continue
        a = auc(s, y)
        flip = a < 0.5
        sub = [{"task": u["task"], "fail": u["fail"],
                "f": {k: (-u["f"][k] if flip else u["f"][k])}}
               for u in units if u["f"].get(k) is not None]
        lo, hi = cluster_boot_auc(sub, k)
        out.append((max(a, 1 - a), k, lo, hi, flip))
    out.sort(reverse=True)
    for a, k, lo, hi, flip in out:
        print("%-26s %8.3f %20s%s"
              % (k, a, "[%.3f, %.3f]" % (lo, hi) if lo is not None else "-",
                 "  (lower=worse)" if flip else ""))
    beats = [k for a, k, lo, hi, _ in out if lo is not None and lo > 0.5]
    print("\nintervals excluding the coin: %d of %d%s"
          % (len(beats), len(out), (" — " + ", ".join(beats)) if beats else ""))

    # the same paired test as the cell-level comparison: best logprob signal
    # against the free structural one, on the same resampled tasks
    lp_best = next(((a, k, flip) for a, k, _, _, flip in out
                    if k.startswith("head_")), None)
    fr = next(((a, k, flip) for a, k, _, _, flip in out
               if k == "free_trace_still_open"), None)
    if lp_best and fr:
        sub = []
        for u in units:
            fa, fb = u["f"].get(lp_best[1]), u["f"].get(fr[1])
            if fa is None or fb is None:
                continue
            sub.append({"task": u["task"], "fail": u["fail"],
                        "f": {"a": -fa if lp_best[2] else fa,
                              "b": -fb if fr[2] else fb}})
        med, lo, hi = cluster_boot_delta(sub, "a", "b")
        print("\nbest logprob (%s, AUC %.3f) minus free 'trace still open' "
              "(AUC %.3f): %+.3f  95%% CI [%+.3f, %+.3f]  -> %s"
              % (lp_best[1], lp_best[0], fr[0], med, lo, hi,
                 "separable from zero" if (lo > 0 or hi < 0) else "SPANS ZERO"))
        print("⚠ 'trace still open at token %d' and 'the trace ran to the ceiling' "
              "are related by construction — the cheapest predictor of a long "
              "trace is that it is already long. That is not a defect of the "
              "comparison, it is the point: the free signal needs no logprobs, "
              "no serving change and no 1.18×." % PREFIX)


if __name__ == "__main__":
    main()
