#!/usr/bin/env python3
"""W6 item 7 — read the four result files and print the tables the doc quotes.

Nothing here calls a model. Every number is a re-reading of a JSON file written
by `judge.py`, `check.py`, `docgate.py` or `taxonomy.py`.

    python analyse.py > analyse-out.txt
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def load(name):
    p = HERE / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def cls_of(tax, sha):
    return (tax or {}).get(sha, {}).get("cls", "?")


def hr(title):
    print("\n" + "=" * 74)
    print(title)
    print("=" * 74)


def judge_table(rows, tax, label):
    """Confusion over the 57 trees, weighted both by tree and by cell."""
    hr(f"{label}: the model's binary call against the suite verifier")
    n = collections.Counter()
    cells = collections.Counter()
    empties = 0
    for r in rows:
        p = r["payload"]
        call = (p or {}).get("call") or "<empty>"
        if p is None:
            empties += 1
        n[(r["truth"], call)] += 1
        cells[(r["truth"], call)] += r["n_cells"]
    print(f"{'truth':<8} {'call':<8} {'trees':>6} {'cells':>6}")
    for k in sorted(n, key=lambda k: (k[0], k[1])):
        print(f"{k[0]:<8} {k[1]:<8} {n[k]:>6} {cells[k]:>6}")
    caught = n[("FAIL", "fail")]
    missed = n[("FAIL", "pass")]
    fp = n[("PASS", "fail")]
    tn = n[("PASS", "pass")]
    print(f"\ncaught {caught}/{caught + missed} wrong trees "
          f"({cells[('FAIL','fail')]}/{cells[('FAIL','fail')] + cells[('FAIL','pass')]} cells); "
          f"false-failed {fp}/{fp + tn} correct trees")
    print(f"empty payloads: {empties}")

    hr(f"{label}: caught, by what decides the failing case (OQ-W6-13's axis)")
    per = collections.defaultdict(lambda: [0, 0, 0, 0])
    for r in rows:
        if r["truth"] != "FAIL":
            continue
        sha = r["key"].split(":")[1]
        c = cls_of(tax, sha)
        call = (r["payload"] or {}).get("call")
        per[c][0] += 1
        per[c][1] += r["n_cells"]
        if call == "fail":
            per[c][2] += 1
            per[c][3] += r["n_cells"]
    order = ["stated", "signalled", "implied", "undecided", "mechanical"]
    print(f"{'class':<12} {'trees':>6} {'caught':>7} {'cells':>6} {'caught':>7}")
    for c in order:
        if c not in per:
            continue
        t, ce, ct, cc = per[c]
        print(f"{c:<12} {t:>6} {ct:>7} {ce:>6} {cc:>7}")
    tot = [sum(v[i] for v in per.values()) for i in range(4)]
    print(f"{'TOTAL':<12} {tot[0]:>6} {tot[2]:>7} {tot[1]:>6} {tot[3]:>7}")


def edge_extra(rows, tax):
    hr("edge arm: the derived gate — 'the reviewer named at least one case'")
    n = collections.Counter()
    cells = collections.Counter()
    for r in rows:
        cases = len((r["payload"] or {}).get("cases") or [])
        v = "fail" if cases else "pass"
        n[(r["truth"], v)] += 1
        cells[(r["truth"], v)] += r["n_cells"]
    print(f"{'truth':<8} {'derived':<8} {'trees':>6} {'cells':>6}")
    for k in sorted(n):
        print(f"{k[0]:<8} {k[1]:<8} {n[k]:>6} {cells[k]:>6}")

    hr("edge arm: does the model's own `call` agree with its own cases?")
    agree = collections.Counter()
    for r in rows:
        p = r["payload"] or {}
        cases = len(p.get("cases") or [])
        call = p.get("call")
        agree[(("cases" if cases else "none"), call)] += 1
    for k in sorted(agree, key=lambda k: (k[0], str(k[1]))):
        print(f"  {k[0]:<6} cases -> call {str(k[1]):<8} {agree[k]}")

    hr("edge arm: cases produced, by class")
    per = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["truth"] != "FAIL":
            continue
        c = cls_of(tax, r["key"].split(":")[1])
        per[c][0] += 1
        per[c][1] += len((r["payload"] or {}).get("cases") or [])
    for c, (t, k) in sorted(per.items()):
        print(f"  {c:<12} {t:>3} trees, {k:>3} cases named")


def check_table(rows, tax):
    hr("check.py: running the reviewer's own cases against agent tree vs reference")
    n = collections.Counter((r["truth"], r["status"]) for r in rows)
    print(f"{'truth':<8} {'status':<14} {'cases':>6}")
    for k in sorted(n):
        print(f"{k[0]:<8} {k[1]:<14} {n[k]:>6}")
    tot = collections.Counter(r["status"] for r in rows)
    print(f"\nall cases: {dict(tot)}  (n={len(rows)})")

    hr("check.py: per tree — did the reviewer name a case that really discriminates?")
    per = collections.defaultdict(set)
    truth = {}
    for r in rows:
        per[r["tree"]].add(r["status"])
        truth[r["tree"]] = r["truth"]
    hit = collections.Counter()
    for tree, sts in per.items():
        good = "discriminates" in sts
        hit[(truth[tree], good)] += 1
    for k in sorted(hit, key=lambda k: (k[0], str(k[1]))):
        print(f"  truth {k[0]:<5} at least one discriminating case: "
              f"{str(k[1]):<6} {hit[k]}")

    hr("check.py: discriminating cases on WRONG trees, by class")
    per_cls = collections.defaultdict(lambda: [0, 0])
    seen = {}
    for r in rows:
        if r["truth"] != "FAIL":
            continue
        c = cls_of(tax, r["tree"].split(":")[1])
        seen.setdefault(r["tree"], c)
        per_cls[c][0] += 1
        if r["status"] == "discriminates":
            per_cls[c][1] += 1
    for c, (a, b) in sorted(per_cls.items()):
        print(f"  {c:<12} {b}/{a} cases discriminate")


def docgate_tables(rows):
    point = [r for r in rows if r["arm"] == "pointwise"]
    if point:
        hr("docgate pointwise: a planted falsehood in a real document")
        print(f"{'document':<24} {'needs code':<11} {'call':<7} {'defects':>7}  kind")
        for r in sorted(point, key=lambda r: r["doc"]):
            p = r["payload"] or {}
            print(f"{r['doc']:<24} {str(r['needs_code']):<11} "
                  f"{str(p.get('call')):<7} {len(p.get('defects') or []):>7}  {r['kind']}")
        planted = [r for r in point if r["defect"] and "padded" not in r["doc"]]
        caught = [r for r in planted
                  if (r["payload"] or {}).get("call") == "fail"]
        clean = [r for r in point if not r["defect"]]
        cfp = [r for r in clean if (r["payload"] or {}).get("call") == "fail"]
        print(f"\ncaught {len(caught)}/{len(planted)} planted defects; "
              f"false-failed {len(cfp)}/{len(clean)} faithful documents")

    pos = [r for r in rows if r["arm"] == "position"]
    if pos:
        hr("docgate position: the same pair in both slots")
        by = collections.defaultdict(dict)
        for r in pos:
            defect = r["A"] if r["A"] != "faithful" else r["B"]
            slot = "defect_first" if r["A"] != "faithful" else "faithful_first"
            by[defect][slot] = (r["choice"], r["correct"])
        print(f"{'defect':<22} {'defect first':<22} {'faithful first':<22} stable")
        agree = 0
        for d, v in sorted(by.items()):
            a = v.get("defect_first", ("-", "-"))
            b = v.get("faithful_first", ("-", "-"))
            ok_a = a[0] == a[1]
            ok_b = b[0] == b[1]
            same = ok_a == ok_b
            agree += same
            print(f"{d:<22} chose {str(a[0]):<3} (right={str(ok_a):<5}) "
                  f"chose {str(b[0]):<3} (right={str(ok_b):<5}) {same}")
        right = sum(1 for r in pos if r["choice"] == r["correct"])
        print(f"\ncorrect in {right}/{len(pos)} orderings; "
              f"order-stable on {agree}/{len(by)} pairs")
        chose_a = sum(1 for r in pos if r["choice"] == "A")
        chose_b = sum(1 for r in pos if r["choice"] == "B")
        eq = sum(1 for r in pos if r["choice"] == "equal")
        print(f"slot preference: A {chose_a}, B {chose_b}, equal {eq}")

    verb = [r for r in rows if r["arm"] == "verbosity"]
    if verb:
        hr("docgate verbosity: padding against nothing, and padding against truth")
        for r in sorted(verb, key=lambda r: r["key"]):
            print(f"  A={r['A']:<24} B={r['B']:<24} chose {str(r['choice']):<6} "
                  f"expected {r['correct']}")


def main():
    tax_raw = load("taxonomy-results.json")
    tax = {r["sha"]: r for r in tax_raw["rows"]} if tax_raw else {}
    if tax_raw:
        hr("OQ-W6-13: what the 29 clean-arm failures are")
        print(f"{'class':<12} {'trees':>6} {'cells':>6}")
        for c in ["stated", "signalled", "implied", "undecided", "mechanical"]:
            print(f"{c:<12} {tax_raw['trees'].get(c, 0):>6} "
                  f"{tax_raw['cells'].get(c, 0):>6}")
        print(f"{'TOTAL':<12} {sum(tax_raw['trees'].values()):>6} "
              f"{sum(tax_raw['cells'].values()):>6}")

    v = load("judge-verdict.json")
    if v:
        judge_table(v, tax, "verdict arm")
    e = load("judge-edge.json")
    if e:
        judge_table(e, tax, "edge arm")
        edge_extra(e, tax)
    c = load("check-results.json")
    if c:
        check_table(c, tax)
    d = load("docgate-results.json")
    if d:
        docgate_tables(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
