#!/usr/bin/env python3
r"""diagreach.py - did the tool F673 repaired ever get called again, and did the
buggy redactor ever actually fire?

SELFHOST-P5 §4 (F785) proposed a mechanism for F784's interaction: `4687405`
rewrote `diagnostics` to run `cargo fmt --check` and `cargo clippy`, whose output
is a DIFF OF SOURCE and SOURCE CONTEXT, so the buggy `(?i)` redactor would mangle
the tool's own result and a model handed garbage would stop calling it. The
mechanism was reproduced at the desk (15 of 117 `.rs` files rewritten) and
explicitly NOT tested against the log. This is that test.

  IT NEEDS TWO COUNTS AND THE LOG HAS BOTH, because the seam is instrumented.
Every tool result passes `Secrets::scrub` at ONE place (`turn.rs`, ADR-0014 §5)
and a scrub that removed anything appends `Event::Note { "redacted: Nx <kind>" }`
BEFORE the `ToolCallEnded` it belongs to. So the note is attributable to the tool
call in progress, and it has been logged since redaction shipped -- unlike
`output`, which F713 only started recording at `1cfe1ac` (F771). A mechanism that
runs through a mangled tool RESULT must leave a note on that tool.

  THE ZERO THIS REPORTS WOULD BE VACUOUS WITHOUT THE SAME-TIER CONTROL (F775,
and the lesson of a tool-reach zero that was a tool leaving the menu). `bash`,
`run_tests`, `git` and `diagnostics` are one class: `Reach::SpawnsChild`, so
`required_tier()` is `Tier::Exec` for all four, and the Change phase ceiling is
`exec` on every `model_call_started`. If `bash` is being called in the same
attempts, the exec class is on the menu and a zero on `diagnostics` is a CHOICE.

  WHAT THIS CANNOT SEE is redactfold.py's caveat, unchanged: the checkpoint
records the SOURCE and the behaviour comes from the BINARY. Cells are the tree an
attempt was handed. And `brief_recorded` only exists from 09-12 00:32, so the
brief column's denominator is 30 briefs and not 108 attempts.

Read-only. Nothing here writes to the log or to either repository.

Usage:
    diagreach.py              # the per-cell fold, both logs
    diagreach.py --calls      # every diagnostics/run_tests call, with its notes
    diagreach.py --check      # assert the published numbers
"""

import argparse
import collections
import datetime
import hashlib
import json
import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from redactfold import (ANCHOR, DB, control, diagnostics_of,  # noqa: E402
                        redaction_of)

ARM_DB = r"C:\Users\david\AppData\Local\abcc\arm-redact-7fe980f\log.sqlite"

# One class, one tier: `Reach::SpawnsChild` -> `Tier::Exec` (tools.rs:177).
EXEC_CLASS = {"bash", "run_tests", "diagnostics", "git"}
CHECKERS = {"diagnostics", "run_tests"}

# `4687405` landed 2026-09-11 15:26:19 +0300.
DIAG_FIX_MS = int(datetime.datetime(2026, 9, 11, 15, 26, 19).timestamp() * 1000)

#   AS_OF, AND WHY THIS TOOL NOW HAS ONE. The first version was deliberately
# unbounded, on the grounds that the claim is about the LAST call and a bound
# would hide it. Eleven sorties later nine of these figures had moved, and every
# one of them moved because of F792: told to call `diagnostics`, the model called
# it, so the "last call" is no longer seq 7210 and the zero is no longer zero.
#   F764'S RULE IS WHAT MATTERS HERE: PUBLISHED IS NOT EDITED. The figures
# describe the population as it stood at the first landing, and the bound is part
# of the figure. `--since` reads the sorties above it instead.
AS_OF = 13049          # `change_landed` -- the first landing. Waves 1-3 are above it.

# Measured 2026-09-18 on both logs, over events BELOW AS_OF. If one of these
# moves now, the log's own past moved and every rate quoted from it is stale.
PUBLISHED = {
    "primary_diagnostics_calls": 13,
    "primary_last_diagnostics_seq": 7210,
    "primary_diagnostics_after_fix": 0,
    "primary_bash_after_fix": 151,
    "primary_redaction_notes": 20,
    "primary_notes_on_read_file": 17,
    "primary_notes_on_search": 2,
    "primary_notes_on_a_brief": 1,
    "primary_notes_on_exec_class": 0,
    "primary_briefs": 30,
    "primary_briefs_with_marker": 1,
    # The summary column, per ATTEMPT rather than per call: how many attempts
    # reached for `diagnostics` at least once, OLD summary against NEW.
    "primary_old_attempts": 68,
    "primary_old_reached": 6,
    "old_summary_attempts": 86,
    "old_summary_reached": 7,
    "new_summary_attempts": 39,
    "new_summary_reached": 0,
    "arm_attempts": 18,
    "arm_diagnostics_calls": 3,
    "arm_diagnostics_attempts": 1,
    "arm_redaction_notes": 0,
    # ⚠ VACUOUS AND KEPT AS SUCH: the arm flew a 09-11 binary, which predates
    # `BriefRecorded` entirely, so there are no briefs on that log to carry a
    # marker. Asserting 0 here asserts that the field is still absent.
    "arm_briefs": 0,
    "arm_briefs_with_marker": 0,
    # F790: F784's own anchored cohort, `any checker` decomposed. The tool the
    # two commits changed is zero in BOTH NEW cells; the tool that moves is the
    # other one, by one event against two.
    "anchored_diag_old": "7/60",
    "anchored_diag_new": "0/32",
    "anchored_diag_p": 0.0914,
    "anchored_tests_old": "10/60",
    "anchored_tests_new": "3/32",
    "anchored_tests_p": 0.5311,
    # F786's boundary control: the two cohorts are ADJACENT, so the zero does
    # not predate the commit.
    "boundary_last_old": 7484,
    "boundary_first_new": 7663,
    "boundary_old_tail": 3,
    # The zero read as a rate rather than a count, so nobody has to derive it.
    "new_rate_upper_bound_pct": 8.9,          # anchored, 0 of 32
    "new_rate_upper_bound_pct_all": 7.4,      # unanchored, 0 of 39
}


def rows(db, below=None, above=None):
    con = sqlite3.connect("file:" + db.replace("\\", "/") + "?mode=ro", uri=True)
    out = [(s, json.loads(b), ms) for s, b, ms in
           con.execute("select seq, body, at_ms from event order by seq")]
    if below is not None:
        out = [r for r in out if r[0] < below]
    if above is not None:
        out = [r for r in out if r[0] >= above]
    return out


def when(ms):
    return datetime.datetime.fromtimestamp(ms / 1000).strftime("%m-%d %H:%M:%S")


def tool_of(e):
    """The field is `tool`; `name` is accepted because an older writer used it,
    and a fold keyed on the wrong field reads zero without saying so."""
    return e.get("tool") or e.get("name")


def scan(db, below=None, above=None):
    """Per-attempt tools, notes attributed to the call in progress, and briefs."""
    rs = rows(db, below, above)
    att = {}
    for seq, e, _ in rs:
        if e["kind"] == "attempt_started":
            att[seq] = {"task": e.get("task"), "change": False, "cp": None,
                        "tools": collections.Counter(),
                        "notes": collections.Counter(), "marked_briefs": 0}
    cur = None          # (tool, attempt) of the call whose result is being scrubbed
    notes = []
    briefs = []
    for seq, e, ms in rs:
        a = e.get("attempt")
        if e["kind"] == "tool_call_started":
            cur = (tool_of(e), a)
            if a in att:
                att[a]["tools"][tool_of(e)] += 1
        elif e["kind"] == "attempt_phase_entered" and e.get("phase") == "change":
            if a in att:
                att[a]["change"] = True
        elif e["kind"] == "brief_recorded":
            n = e.get("text", "").count("[redacted]")
            briefs.append((seq, a, when(ms), len(e.get("text", "")), n))
            if a in att and n:
                att[a]["marked_briefs"] += 1
            cur = None      # a brief ends the previous phase's last call
        elif e["kind"] == "note" and str(e.get("text", "")).startswith("redacted:"):
            notes.append((seq, cur, e["text"], when(ms)))
            if cur and cur[1] in att:
                att[cur[1]]["notes"][cur[0]] += 1
    for seq, e, _ in rs:    # checkpoint_taken carries the task, not the attempt
        if e["kind"] == "checkpoint_taken":
            prior = [a for a in att if att[a]["task"] == e.get("task") and a < seq]
            if prior and att[max(prior)]["cp"] is None:
                att[max(prior)]["cp"] = e.get("sha")
    return att, notes, briefs, rs


def fisher(a, b, c, d):
    """Two-sided Fisher exact on [[a, b], [c, d]]. No scipy on this box."""
    from math import comb

    n = a + b + c + d
    rowa, cola = a + b, a + c
    lo = max(0, cola - (n - rowa))
    hi = min(rowa, cola)
    total = sum(comb(rowa, i) * comb(n - rowa, cola - i) for i in range(lo, hi + 1))
    obs = comb(rowa, a) * comb(n - rowa, cola - a)
    tail = sum(comb(rowa, i) * comb(n - rowa, cola - i) for i in range(lo, hi + 1)
               if comb(rowa, i) * comb(n - rowa, cola - i) <= obs)
    return tail / total


def cells(att):
    out = collections.defaultdict(list)
    for a, r in sorted(att.items()):
        red, diag = redaction_of(r["cp"]), diagnostics_of(r["cp"])
        if red is None or diag is None:
            out[("unreadable", None)].append(a)
            continue
        out[(red, diag)].append(a)
    return out


def table(att, cs, title):
    print()
    print(title)
    print(f"{'redaction':<11} {'summary':<8} {'att':>4} {'chg':>4} {'diagnostics':>12}"
          f" {'run_tests':>10} {'bash':>6} {'notes':>6} {'briefs[r]':>10}")
    order = [("none", False), ("none", True), ("buggy", False), ("buggy", True),
             ("fixed", False), ("fixed", True), ("unreadable", None)]
    for key in order:
        ids = cs.get(key)
        if not ids:
            continue
        red, diag = key
        lbl = "-" if diag is None else ("NEW" if diag else "OLD")
        chg = sum(1 for a in ids if att[a]["change"])

        def g(t, ids=ids):
            return sum(att[a]["tools"][t] for a in ids)

        nts = sum(sum(att[a]["notes"].values()) for a in ids)
        mb = sum(att[a]["marked_briefs"] for a in ids)
        print(f"{red:<11} {lbl:<8} {len(ids):>4} {chg:>4} {g('diagnostics'):>12}"
              f" {g('run_tests'):>10} {g('bash'):>6} {nts:>6} {mb:>10}")


def upper_bound(n, alpha=0.05):
    """The one-sided 95% upper bound on a rate given 0 of n.

      THE ZERO IS EXACT AS A COUNT AND WEAK AS A RATE, and a reader who is shown
    only `0/32` will read the second meaning. 0 of 32 bounds the rate at 8.9%,
    which does not exclude the 11.7% it is being compared against.
    """
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if (1 - mid) ** n > alpha else (lo, mid)
    return lo


def power(p_old, p_new, ns, trials=20000, seed=11726):
    """Simulated power for the summary-sentence arm nobody should fly.

      COSTED BEFORE IT IS PROPOSED (F772's lesson). The first draft of the P6
    prose guessed 25-30 per arm from nothing and was wrong by more than 2x.
    """
    import random
    rnd = random.Random(seed)
    out = {}
    for n in ns:
        hit = 0
        for _ in range(trials):
            a = sum(rnd.random() < p_old for _ in range(n))
            c = sum(rnd.random() < p_new for _ in range(n))
            if fisher(a, n - a, c, n - c) < 0.05:
                hit += 1
        out[n] = hit / trials
    return out


def anchored(db):
    """The task ids carrying F780's anchored prompt, so this fold can be read
    against F784's own cohort rather than beside it."""
    con = sqlite3.connect("file:" + db.replace("\\", "/") + "?mode=ro", uri=True)
    return {t for t, p in con.execute("select id, prompt from task")
            if hashlib.sha1((p or "").encode()).hexdigest()[:8] == ANCHOR}


def decompose(att, arm_att, anc, arm_anc):
    """F784's 2x2, with `any checker` split back into the two tools it pools.

      THIS IS THE WHOLE OF F790. F784's metric is F765's -- `diagnostics` OR
    `run_tests` -- and the two tools have different histories, so a cell rate
    over their union is an average of a step function and some noise.
    """
    cs, acs = cells(att), cells(arm_att)

    def sub(src, ids, a):
        return [src[i] for i in ids if src[i]["task"] in a and src[i]["change"]]

    groups = [
        ("none/OLD", "OLD", sub(att, cs.get(("none", False), []), anc)),
        ("buggy/OLD arm", "OLD", sub(arm_att, acs.get(("buggy", False), []), arm_anc)),
        ("buggy/NEW", "NEW", sub(att, cs.get(("buggy", True), []), anc)),
        ("fixed/NEW", "NEW", sub(att, cs.get(("fixed", True), []), anc)),
    ]
    print()
    print("F784's ANCHORED 2x2, with `any checker` decomposed (F790)")
    print(f"{'cell':<14} {'n':>3} | {'diagnostics':>14} {'run_tests':>14}"
          f" {'either = F784':>14}")
    for name, _, g in groups:
        def r(k, g=g):
            return f"{k}/{len(g)} {100 * k / len(g):4.1f}%"

        d = sum(1 for x in g if x["tools"]["diagnostics"])
        t = sum(1 for x in g if x["tools"]["run_tests"])
        e = sum(1 for x in g if x["tools"]["diagnostics"] or x["tools"]["run_tests"])
        print(f"{name:<14} {len(g):>3} | {r(d):>14} {r(t):>14} {r(e):>14}")
    old = [x for _, lbl, g in groups if lbl == "OLD" for x in g]
    new = [x for _, lbl, g in groups if lbl == "NEW" for x in g]
    out = {}
    for tool in ("diagnostics", "run_tests"):
        o = sum(1 for x in old if x["tools"][tool])
        n = sum(1 for x in new if x["tools"][tool])
        p = fisher(o, len(old) - o, n, len(new) - n)
        out[tool] = (o, len(old), n, len(new), p)
        print(f"  {tool:12s} OLD {o}/{len(old)} vs NEW {n}/{len(new)}   p = {p:.4f}")
    print("  -> diagnostics is zero in BOTH NEW cells: a step on the summary axis,")
    print("     not an interaction. F784's collapse is 1 event against 2, in run_tests.")
    o, on_, n_, nn_, _ = out["diagnostics"]
    print(f"  the zero as a RATE: 0 of {nn_} bounds it at <= "
          f"{upper_bound(nn_) * 100:.1f}% (one-sided 95%), which does NOT exclude")
    print(f"     the OLD {o / on_ * 100:.1f}%. EXACT AS A COUNT, WEAK AS A RATE - and P6's"
          " claims rest on the count.")
    return out


def boundary(att, rs):
    """The control that could kill F786: does the zero predate the commit?

      THE LAST CALL AND THE COMMIT ARE THREE DAYS APART, so a reader is owed the
    attempts in between. There are none -- the two cohorts are ADJACENT in the
    log, which independently reproduces F767's `a7663`.
    """
    cs = cells(att)
    t0 = {s: ms for s, e, ms in rs if e["kind"] == "attempt_started"}
    old = sorted(a for a in cs.get(("none", False), []) if att[a]["change"])
    new = sorted(cs.get(("buggy", True), []) + cs.get(("fixed", True), []))
    last_d = max((s for s, e, _ in rs if e["kind"] == "tool_call_started"
                  and tool_of(e) == "diagnostics"), default=None)
    tail = [a for a in old if a > last_d]
    print()
    print("THE BOUNDARY CONTROL (F786) - is the zero older than 4687405?")
    print(f"  last OLD-summary Change attempt   a{old[-1]:<8} {when(t0[old[-1]])}")
    print(f"  4687405 lands                     {'':<9} {when(DIAG_FIX_MS)}")
    print(f"  first NEW-summary attempt         a{new[0]:<8} {when(t0[new[0]])}")
    print(f"  attempts in between               "
          f"{sum(1 for a in old + new if t0[old[-1]] < t0[a] < t0[new[0]])}")
    print(f"  OLD attempts after the last call  {len(tail)}"
          f" ({sum(1 for a in tail if att[a]['tools']['diagnostics'])} reached it)")
    return old[-1], new[0], len(tail)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--calls", action="store_true")
    p.add_argument("--power", action="store_true")
    p.add_argument("--since", action="store_true",
                   help=f"read the sorties at or above AS_OF ({AS_OF}) instead")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    print()
    print("diagreach - the F785 mechanism, asked of the log that instruments it")
    print()
    control()

    lo, hi = (AS_OF, None) if args.since else (None, AS_OF)
    att, notes, briefs, rs = scan(DB, below=hi, above=lo)
    arm_att, arm_notes, arm_briefs, arm_rs = scan(ARM_DB)
    print(f"  primary log bounded: {'seq >= ' + str(AS_OF) if args.since else 'seq < ' + str(AS_OF)}")

    table(att, cells(att),
          f"PRIMARY LOG - all {len(att)} attempts by the tree they were handed")
    table(arm_att, cells(arm_att),
          "ARM LOG (4687405^ = 7fe980f: buggy redactor + OLD summary)")

    # THE SUMMARY COLUMN, per ATTEMPT. `4687405` changed two things at once --
    # the command and the sentence the model reads when it chooses -- and this
    # pools the two logs on the one axis that separates: OLD sentence vs NEW.
    cs, acs = cells(att), cells(arm_att)
    groups = [
        ("OLD", "primary none/OLD", [att[a] for a in cs.get(("none", False), [])]),
        ("OLD", "arm buggy/OLD", [arm_att[a] for a in acs.get(("buggy", False), [])]),
        ("NEW", "primary buggy/NEW", [att[a] for a in cs.get(("buggy", True), [])]),
        ("NEW", "primary fixed/NEW", [att[a] for a in cs.get(("fixed", True), [])]),
    ]
    print()
    print("THE SUMMARY COLUMN, per attempt - did this attempt reach for diagnostics?")
    print(f"{'summary':<8} {'cohort':<20} {'att':>4} {'reached':>8} {'rate':>7}")
    pooled = {"OLD": [0, 0], "NEW": [0, 0]}
    for lbl, name, rs_ in groups:
        r = sum(1 for x in rs_ if x["tools"]["diagnostics"])
        pooled[lbl][0] += len(rs_)
        pooled[lbl][1] += r
        rate = f"{r / len(rs_) * 100:.1f}%" if rs_ else "-"
        print(f"{lbl:<8} {name:<20} {len(rs_):>4} {r:>8} {rate:>7}")
    for lbl in ("OLD", "NEW"):
        n, r = pooled[lbl]
        print(f"{lbl:<8} {'POOLED':<20} {n:>4} {r:>8} {r / n * 100:>6.1f}%")
    on, orr = pooled["OLD"]
    nn, nr = pooled["NEW"]
    print(f"  Fisher exact, two-sided, {orr}/{on} vs {nr}/{nn}: "
          f"p = {fisher(orr, on - orr, nr, nn - nr):.4f}")
    print("  (!) OBSERVATIONAL. The summary column is confounded with the calendar,")
    print("    the subject, the task family and the seeding. Not an arm.")

    after = [(s, e, ms) for s, e, ms in rs
             if e["kind"] == "tool_call_started" and ms >= DIAG_FIX_MS]
    ac = collections.Counter(tool_of(e) for _, e, _ in after)
    last_d = max((s for s, e, _ in rs if e["kind"] == "tool_call_started"
                  and tool_of(e) == "diagnostics"), default=None)
    total_d = sum(1 for _, e, _ in rs if e["kind"] == "tool_call_started"
                  and tool_of(e) == "diagnostics")
    print()
    print(f"THE ZERO AND ITS CONTROL, primary log, after 4687405 ({when(DIAG_FIX_MS)}):")
    print(f"  diagnostics calls, whole log      {total_d:>6}   last at seq {last_d}")
    print(f"  diagnostics calls after the fix   {ac['diagnostics']:>6}")
    for t in ("bash", "run_tests", "git"):
        label = t + " calls after the fix"
        print(f"  {label:<33} {ac[t]:>6}   <- same class, same tier")

    on_exec = sum(1 for _, cur, _, _ in notes if cur and cur[0] in EXEC_CLASS)
    print()
    print(f"REDACTION NOTES, primary log: {len(notes)}")
    per = collections.Counter(cur[0] if cur else None for _, cur, _, _ in notes)
    for t, n in per.most_common():
        print(f"  {str(t):<14} {n:>4}")
    print(f"  on the exec class (bash/run_tests/diagnostics/git): {on_exec}")
    print(f"ARM LOG redaction notes: {len(arm_notes)}"
          f"   (the buggy redactor was INSTALLED and never FIRED)")

    dec = decompose(att, arm_att, anchored(DB), anchored(ARM_DB))
    bnd = boundary(att, rs)

    marked = [b for b in briefs if b[4]]
    print()
    print(f"BRIEFS: {len(briefs)} recorded on the primary log, "
          f"{len(marked)} carrying [redacted]")
    for seq, a, w, ln, n in marked:
        print(f"  seq {seq} a{a} {w} len={ln} markers={n}")
    print(f"       {len(arm_briefs)} on the arm log, "
          f"{sum(1 for b in arm_briefs if b[4])} carrying [redacted]")

    if args.calls:
        print()
        print("EVERY CHECKER CALL, both logs")
        for name, r in (("primary", rs), ("arm", arm_rs)):
            for i, (s, e, ms) in enumerate(r):
                if e["kind"] != "tool_call_started" or tool_of(e) not in CHECKERS:
                    continue
                nt = []
                end = None
                for s2, e2, _ in r[i + 1:i + 80]:
                    if e2["kind"] == "note" and str(e2.get("text", "")).startswith("redacted:"):
                        nt.append(e2["text"])
                    if e2["kind"] == "tool_call_ended":
                        end = e2
                        break
                out = (end or {}).get("output")
                print(f"  {name:8s} seq {s:6d} a{e.get('attempt')} {tool_of(e):12s}"
                      f" {when(ms)} exit={(end or {}).get('exit')}"
                      f" outlen={len(out) if out else 0} notes={nt or '-'}")

    if args.power:
        ao, aon, _, _, _ = dec["diagnostics"]
        print()
        print("POWER of the arm P6 recommends NOT flying, two-sided Fisher at 0.05")
        print(f"{'per arm':>8} {'anchored ' + str(ao) + '/' + str(aon):>16}"
              f" {'unanchored ' + str(orr) + '/' + str(on):>18}")
        ns = (15, 20, 25, 30, 40, 50, 60, 80)
        anc_p = power(ao / aon, 0.0, ns)
        una_p = power(orr / on, 0.0, ns)
        for n in ns:
            print(f"{n:>8} {anc_p[n]:>16.3f} {una_p[n]:>18.3f}")
        print("  -> 120-160 attempts total on the FAVOURABLE cohort, more than F772")
        print("     priced the commit arm at; on the broader one it is worse still.")

    if args.check:
        got = {
            "primary_diagnostics_calls": total_d,
            "primary_last_diagnostics_seq": last_d,
            "primary_diagnostics_after_fix": ac["diagnostics"],
            "primary_bash_after_fix": ac["bash"],
            "primary_redaction_notes": len(notes),
            "primary_notes_on_exec_class": on_exec,
            "primary_notes_on_read_file": per["read_file"],
            "primary_notes_on_search": per["search"],
            "primary_notes_on_a_brief": per[None],
            "primary_briefs": len(briefs),
            "primary_briefs_with_marker": len(marked),
            "primary_old_attempts": len(cs.get(("none", False), [])),
            "primary_old_reached": sum(
                1 for a in cs.get(("none", False), []) if att[a]["tools"]["diagnostics"]),
            "old_summary_attempts": on,
            "old_summary_reached": orr,
            "new_summary_attempts": nn,
            "new_summary_reached": nr,
            "arm_attempts": len(arm_att),
            "arm_diagnostics_calls": sum(a["tools"]["diagnostics"]
                                         for a in arm_att.values()),
            "arm_diagnostics_attempts": sum(
                1 for a in arm_att.values() if a["tools"]["diagnostics"]),
            "arm_redaction_notes": len(arm_notes),
            "anchored_diag_old": f"{dec['diagnostics'][0]}/{dec['diagnostics'][1]}",
            "anchored_diag_new": f"{dec['diagnostics'][2]}/{dec['diagnostics'][3]}",
            "anchored_diag_p": round(dec["diagnostics"][4], 4),
            "anchored_tests_old": f"{dec['run_tests'][0]}/{dec['run_tests'][1]}",
            "anchored_tests_new": f"{dec['run_tests'][2]}/{dec['run_tests'][3]}",
            "anchored_tests_p": round(dec["run_tests"][4], 4),
            "boundary_last_old": bnd[0],
            "boundary_first_new": bnd[1],
            "boundary_old_tail": bnd[2],
            "new_rate_upper_bound_pct": round(
                upper_bound(dec["diagnostics"][3]) * 100, 1),
            "new_rate_upper_bound_pct_all": round(upper_bound(nn) * 100, 1),
            "arm_briefs": len(arm_briefs),
            "arm_briefs_with_marker": sum(1 for b in arm_briefs if b[4]),
        }
        bad = 0
        print()
        print("--check")
        for k, want in PUBLISHED.items():
            ok = got[k] == want
            bad += not ok
            print(f"  {'ok   ' if ok else 'DRIFT'} {k:<32} want {want!r} got {got[k]!r}")
        if bad:
            print()
            print(f"{bad} figure(s) moved. Every rate quoted from this tool is stale.")
            return 1
        print()
        print(f"all {len(PUBLISHED)} reproduce.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
