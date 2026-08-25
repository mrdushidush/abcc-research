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


def cost_table(arms):
    """What the schema costs. Same model, same trees, same 8,192-token budget —
    the only thing that differs between the two arms is what the schema asks for."""
    hr("what the schema costs: the same 57 trees under two output shapes")
    print(f"{'arm':<9} {'median ctok':>12} {'median reason':>14} "
          f"{'median wall':>12} {'hit the cap':>12} {'empty':>7}")
    for label, rows in arms:
        ct = sorted(r["usage"]["completion_tokens"] for r in rows if r.get("usage"))
        rt = sorted((r["usage"].get("completion_tokens_details") or {})
                    .get("reasoning_tokens", 0) for r in rows if r.get("usage"))
        wl = sorted(r["wall_s"] for r in rows if r.get("wall_s"))
        cap = sum(1 for r in rows
                  if r.get("usage") and r["usage"]["completion_tokens"] >= 8192)
        empty = sum(1 for r in rows if r.get("payload") is None)
        med = lambda xs: xs[len(xs) // 2] if xs else 0
        print(f"{label:<9} {med(ct):>12.0f} {med(rt):>14.0f} "
              f"{med(wl):>11.1f}s {cap:>12} {empty:>7}")
    print()
    print("Every empty payload in both arms is `finish_reason: length` at the cap.")


def derived_gate(edge, check, tax):
    """The gate the check arm licenses, scored over ALL 57 trees rather than over
    the 16 that produced a case — a rate conditioned on answering is not a rate
    (item 26, item 28)."""
    hr("the derived gate over the WHOLE population: 'named a case that discriminates'")
    disc = collections.defaultdict(set)
    for r in check:
        disc[r["tree"]].add(r["status"])
    n = collections.Counter()
    for r in edge:
        sts = disc.get(r["key"], set())
        fired = "discriminates" in sts
        n[(r["truth"], fired)] += 1
    print(f"{'truth':<8} {'gate fires':<12} {'trees':>6}")
    for k in sorted(n, key=lambda k: (k[0], str(k[1]))):
        print(f"{k[0]:<8} {str(k[1]):<12} {n[k]:>6}")
    wrong_hit = n[("FAIL", True)]
    wrong_tot = n[("FAIL", True)] + n[("FAIL", False)]
    right_hit = n[("PASS", True)]
    right_tot = n[("PASS", True)] + n[("PASS", False)]
    print(f"\ncatches {wrong_hit}/{wrong_tot} wrong trees; "
          f"fires on {right_hit}/{right_tot} correct trees")

    hr("the three gates side by side, all scored over all 57 trees")
    def score(rows, fire):
        w = sum(1 for r in rows if r["truth"] == "FAIL" and fire(r))
        wt = sum(1 for r in rows if r["truth"] == "FAIL")
        c = sum(1 for r in rows if r["truth"] == "PASS" and fire(r))
        ct = sum(1 for r in rows if r["truth"] == "PASS")
        return w, wt, c, ct
    verdict = load("judge-verdict.json") or []
    rowsets = [
        ("verdict `call == fail`", verdict,
         lambda r: (r.get("payload") or {}).get("call") == "fail"),
        ("edge `call == fail`", edge,
         lambda r: (r.get("payload") or {}).get("call") == "fail"),
        ("edge named any case", edge,
         lambda r: bool((r.get("payload") or {}).get("cases"))),
        ("edge case discriminates", edge,
         lambda r: "discriminates" in disc.get(r["key"], set())),
    ]
    print(f"{'gate':<26} {'catches wrong':>15} {'fires on correct':>18}")
    for label, rows, fire in rowsets:
        w, wt, c, ct = score(rows, fire)
        print(f"{label:<26} {f'{w}/{wt}':>15} {f'{c}/{ct}':>18}")


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


# Did the pointwise defect list name the PLANTED defect, or something else? The
# distinction matters because the base document is not perfectly faithful
# (docgate.py's KNOWN_DISCREPANCY), so "produced a defect" and "found the plant"
# are different facts. Each entry is the substring that must appear in some
# defect description for the plant to count as named; an entry that stops
# matching raises rather than silently re-scoring the arm.
PLANT_EVIDENCE = {
    "wrong_constant":        "MAX_ATTEMPTS",
    "wrong_constant_padded": "MAX_ATTEMPTS",
    "phantom_symbol":        "is_retryable",
    "wrong_type":            "counts()",
    "reversed_semantics":    "is_chargeable",
    "stale_transition":      None,
    "wrong_default":         None,
    "true_but_incomplete":   None,
}


def docgate_plants(point):
    hr("docgate pointwise: did the defect list name the PLANT?")
    print(f"{'document':<24} {'call':<7} {'defects':>7}  {'names plant':<12} evidence")
    named = tot = 0
    for r in sorted(point, key=lambda r: r["doc"]):
        if not r["defect"]:
            continue
        tot += 1
        want = PLANT_EVIDENCE[r["doc"]]
        text = " ".join(d.get("description", "")
                        for d in ((r["payload"] or {}).get("defects") or []))
        hit = bool(want) and want in text
        if want:
            assert hit, f"{r['doc']}: evidence {want!r} no longer present"
        named += hit
        pay = r["payload"] or {}
        print(f"{r['doc']:<24} {str(pay.get('call')):<7} "
              f"{len(pay.get('defects') or []):>7}  {str(hit):<12} {want or '-'}")
    gated = sum(1 for r in point
                if r["defect"] and (r["payload"] or {}).get("call") == "fail")
    print()
    print(f"named the plant in {named}/{tot} defective documents "
          f"(the padded variant counted separately); gated on it {gated}")


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
        docgate_plants(point)

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
    if v and e:
        cost_table([("verdict", v), ("edge", e)])
    c = load("check-results.json")
    if c:
        check_table(c, tax)
        if e:
            derived_gate(e, c, tax)
    d = load("docgate-results.json")
    if d:
        docgate_tables(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
