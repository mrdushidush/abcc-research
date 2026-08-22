"""One table per question, over whatever result files exist.

    python analyse.py

Nothing here re-runs anything; it reads the JSON the probes wrote. Every rate is
printed with its denominator, and a population that is not present is skipped
rather than assumed empty.
"""

import json

import common as C

FILES = {
    "constructed": C.HERE / "results-constructed.json",
    "k": C.HERE / "results-k.json",
    "q56": C.HERE / "results-q56.json",
    "gentests": C.HERE / "gentests-results.json",
    "v1": C.HERE / "v1-channel-results.json",
}


def load(name):
    p = FILES[name]
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def rule(title):
    print("\n" + title)
    print("-" * len(title))


def instrument_names(rows):
    names = []
    for r in rows:
        for n in r.get("instruments", {}):
            if n not in names:
                names.append(n)
    return names


def discrimination(rows, label):
    """Does the instrument's verdict move with the truth?"""
    names = instrument_names(rows)
    truths = sorted({r["truth"]["verdict"] for r in rows})
    rule(f"{label} — n={len(rows)}, truth: " +
         ", ".join(f"{t}={sum(1 for r in rows if r['truth']['verdict'] == t)}"
                   for t in truths))
    hdr = f"{'instrument':14} {'red|FAIL':>9} {'red|PASS':>9} {'green|FAIL':>11} " \
          f"{'error':>6} {'median ms':>10}  reads"
    print(hdr)
    for n in names:
        red_fail = red_pass = green_fail = err = 0
        ms = []
        for r in rows:
            i = r["instruments"].get(n)
            if not i:
                continue
            t = r["truth"]["verdict"]
            ms.append(i["ms"])
            if i["verdict"] == "error":
                err += 1
                continue
            if i["verdict"] == "red" and t == "FAIL":
                red_fail += 1
            elif i["verdict"] == "red" and t == "PASS":
                red_pass += 1
            elif i["verdict"] == "green" and t == "FAIL":
                green_fail += 1
        n_fail = sum(1 for r in rows if r["truth"]["verdict"] == "FAIL")
        n_pass = sum(1 for r in rows if r["truth"]["verdict"] == "PASS")
        ms.sort()
        med = ms[len(ms) // 2] if ms else 0
        # "reads" is the only thing that matters: does the verdict ever differ
        # between a tree the verifier accepts and one it rejects?
        verdicts = {r["truth"]["verdict"]: set() for r in rows}
        for r in rows:
            i = r["instruments"].get(n)
            if i:
                verdicts[r["truth"]["verdict"]].add(i["verdict"])
        moves = len({frozenset(v) for v in verdicts.values()}) > 1
        print(f"{n:14} {red_fail:>4}/{n_fail:<4} {red_pass:>4}/{n_pass:<4} "
              f"{green_fail:>6}/{n_fail:<4} {err:>6} {med:>10} "
              f" {'differs' if moves else 'IDENTICAL'}")


def truth_reproduction(rows, label):
    rule(f"{label} — does the recorded verdict reproduce?")
    agree = dis = new = 0
    for r in rows:
        rec = r.get("recorded", "-")
        now = r["truth"]["verdict"]
        if rec in ("-", "", None):
            new += 1
        elif rec == now:
            agree += 1
        else:
            dis += 1
            print(f"  DISAGREE {r['id']}: recorded {rec}, now {now}")
    print(f"  reproduced {agree}, disagreed {dis}, "
          f"no verdict recorded {new} (re-measured here)")
    if new:
        print("  cells the run recorded no verdict for:")
        for r in rows:
            if r.get("recorded", "-") in ("-", "", None):
                print(f"    {r['id']:52} status={r.get('status'):9} "
                      f"verifier now says {r['truth']['verdict']}")


def delta_gate(rows, baselines, label):
    """The honest way to gate on a linter: does the change ADD findings?

    An absolute lint gate is useless on a repository that is already red — every
    K fixture is. A delta gate is a different instrument, so it is measured as
    one: the multiset of findings on the changed tree minus the multiset on the
    same tree before the change.
    """
    rule(f"{label} — delta against the unfixed fixture, not an absolute count")
    print(f"{'instrument':14} {'added>0 & FAIL':>15} {'added>0 & PASS':>15} "
          f"{'removed>0':>10}  reads")
    for n in ("ruff", "ruff_all", "mypy_strict"):
        af = ap = rem = 0
        n_fail = n_pass = 0
        seen = False
        for r in rows:
            base = baselines.get((r["task"], n))
            i = r["instruments"].get(n)
            if base is None or not i or "hits" not in i:
                continue
            seen = True
            t = r["truth"]["verdict"]
            n_fail += t == "FAIL"
            n_pass += t == "PASS"
            cur, b = sorted(i["hits"]), sorted(base)
            from collections import Counter

            added = Counter(cur) - Counter(b)
            removed = Counter(b) - Counter(cur)
            if sum(added.values()):
                af += t == "FAIL"
                ap += t == "PASS"
            if sum(removed.values()):
                rem += 1
        if not seen:
            continue
        moves = (af / n_fail if n_fail else 0) != (ap / n_pass if n_pass else 0)
        print(f"{n:14} {af:>7}/{n_fail:<7} {ap:>7}/{n_pass:<7} {rem:>10}  "
              f"{'differs' if moves else 'no separation'}")


def gentests_table(rows):
    rule(f"generated tests — n={len(rows)}")
    print(f"{'arm':9} {'task':34} {'rep':>3} {'unfixed':>8} {'sham':>6} "
          f"{'refsol':>7} {'disc':>5} {'tok':>6} {'wall_s':>7}")
    for r in rows:
        if "error" in r:
            print(f"{r['arm']:9} {r['task']:34} {r['rep']:>3}   ERROR {r['error'][:50]}")
            continue
        s = r.get("scores", {})
        print(f"{r['arm']:9} {r['task']:34} {r['rep']:>3} "
              f"{s.get('unfixed', {}).get('verdict', '-'):>8} "
              f"{s.get('sham', {}).get('verdict', '-'):>6} "
              f"{s.get('refsol', {}).get('verdict', '-'):>7} "
              f"{str(r['discriminates']):>5} "
              f"{r['usage'].get('completion_tokens', 0):>6} {r['wall_s']:>7}")
    for arm in sorted({r["arm"] for r in rows}):
        a = [r for r in rows if r["arm"] == arm and "error" not in r]
        if not a:
            continue
        disc = sum(1 for r in a if r["discriminates"])
        green_unfixed = sum(1 for r in a
                            if r.get("scores", {}).get("unfixed", {}).get("verdict") == "green")
        err = sum(1 for r in a
                  if r.get("scores", {}).get("unfixed", {}).get("verdict") == "error")
        red_refsol = sum(1 for r in a
                         if r.get("scores", {}).get("refsol", {}).get("verdict") == "red")
        green_sham = sum(1 for r in a
                         if r.get("scores", {}).get("sham", {}).get("verdict") == "green")
        empty = sum(1 for r in a if r.get("empty"))
        print(f"\n  {arm}: {disc}/{len(a)} discriminate · "
              f"{green_unfixed}/{len(a)} green on the unfixed tree · "
              f"{green_sham}/{len(a)} PASSED THE SHAM · "
              f"{red_refsol}/{len(a)} red on the reference solution · "
              f"{err}/{len(a)} did not run · {empty}/{len(a)} empty payload")


def v1_table(d):
    rule("v1's validation channel — can it carry these instruments at all?")
    print(f"{'artifact':8} {'candidate':24} {'v1 says':>8} {'exit':>5}  what actually happened")
    for r in d["rows"]:
        print(f"{r['artifact']:8} {r['label']:24} "
              f"{('PASS' if r['v1_success'] else 'FAIL'):>8} {str(r['exit_code']):>5}  "
              f"{r['output'][:70]}")


def main():
    c = load("constructed")
    if c:
        discrimination(c, "constructed artifacts (K fixtures: unfixed / refsol / sham)")
    baselines = {}
    if c:
        for r in c:
            if r["id"] != "unfixed":
                continue
            for n, i in r["instruments"].items():
                if "hits" in i:
                    baselines[(r["task"], n)] = i["hits"]
    k = load("k")
    if k:
        discrimination(k, "real agent workdirs, K suite")
        if baselines:
            delta_gate(k, baselines, "real agent workdirs, K suite")
        truth_reproduction(k, "real agent workdirs, K suite")
    q = load("q56")
    if q:
        discrimination(q, "real agent workdirs, Q56 suite (Rust)")
        truth_reproduction(q, "real agent workdirs, Q56 suite (Rust)")
        for v in sorted({r.get("variant") for r in q}):
            sub = [r for r in q if r.get("variant") == v]
            discrimination(sub, f"  Q56 variant {v}")
    g = load("gentests")
    if g:
        gentests_table(g)
    v = load("v1")
    if v:
        v1_table(v)


if __name__ == "__main__":
    main()
