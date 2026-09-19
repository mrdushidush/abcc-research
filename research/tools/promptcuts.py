# -*- coding: utf-8 -*-
"""Every call the server cut the prompt of, counted with the PHASE as the unit.

    python research/tools/promptcuts.py            # the table
    python research/tools/promptcuts.py --check    # the control, published numbers

F744 proved the argument: `Body`'s only mutation is `append`, so `prompt_tokens` --
the server's own measurement of that object -- cannot fall, and a fall means the
prompt was cut before it was measured. This is the instrument for the other half,
and it exists because the first version of it got the denominator wrong.

TWO TRAPS, both of which produced a confident wrong number (F748, F749):

  * THE APPEND-ONLY OBJECT IS THE PHASE'S BODY, NOT THE ATTEMPT'S.
    `abcc-drive/src/lib.rs` builds `Body::opening` INSIDE `phase()`, so Localize,
    Change and the Judge each start fresh. Keyed on the attempt the archive
    reports 117 falls over 86 of 98 attempts; 103 of those are BODY RESETS, and
    the largest of them -- the 38,006 that was published as the deepest
    truncation -- is a `change` -> `judge` boundary (F750).
  * COMPARE AGAINST THE PHASE'S HIGH WATER, NOT THE PREVIOUS CALL.
    A cut is a STATE: once the body outgrows the window every later call is cut
    too while its reported count climbs again. Previous-call finds 23 rows,
    high-water finds 74, on the same events.

Read-only. Nothing here writes to the log.
"""
import collections
import json
import sqlite3
import sys

DB = r"C:\Users\david\AppData\Local\abcc\abcc-1ae35b6091a63e2c\log.sqlite"

# The seq the published numbers were measured AT. Everything at or above it is a
# later sortie, so `--check` bounds the cohorts below it (F764).
#   WITHOUT THIS THE CONTROL EATS ITSELF, and this file is the second instrument
# to need the lesson: unbounded, `--check` reports DRIFT on three figures the
# moment anybody flies -- correctly, because the A4 arm really did add attempts
# on 09-14. A control that fails whenever somebody uses the system gets switched
# off within a week, and the drift it was built to catch goes with it. The
# published figures describe a population as of a moment; the bound is part of
# the figure, not a convenience.
#   11726 is the first `task_created` of the SELFHOST batch and is the SAME
# boundary `toolreach.py:69` carries, deliberately: two controls over one log
# that disagree about when "now" was are two answers waiting to be quoted
# against each other. Verified 2026-09-18 -- all nine figures reproduce at every
# bound from 11726 up to 11800, and drift first at 11910.
AS_OF = 11726

# LINEAGE-P9 1 and 3, published 2026-09-13. The control.
#   🚨 NOT MOVED, and the reason is visible in how the unbounded reading keeps
# moving: the first three read 123 / 90 / 109 when F764 was written and
# 128 / 95 / 114 on 2026-09-18, against a published 117 / 86 / 103. Neither is a
# correction -- both are the same figures over a bigger population, which is
# what AS_OF exists to stop happening silently. F764's rule is repair by ADDING
# what is missing (here, the bound), never by restating a number under a reader
# who will quote it.
PUBLISHED = {
    "attempt_keyed_falls": 117,
    "attempt_keyed_attempts": 86,
    "boundary_falls": 103,
    "within_phase_falls": 14,
    "within_phase_attempts": 6,
    "cut_calls": 74,
    "cut_attempts": 12,
    "falls_any_size": 23,
    "deepest_cut": 27041,
}


def timeline(db=DB, below=None):
    """Per attempt, the phases entered and the prompt_tokens of each call, in seq.

    `below` bounds the read to events under that seq -- see AS_OF. None reads the
    whole log, which is what the report wants and what `--check` must not have.
    """
    con = sqlite3.connect("file:" + db.replace("\\", "/") + "?mode=ro", uri=True)
    out = collections.defaultdict(list)
    bound = "" if below is None else f" and seq < {int(below)}"
    for _seq, kind, attempt, body in con.execute(
        "select seq, kind, attempt, body from event where kind in "
        f"('attempt_phase_entered','model_call_ended'){bound} order by seq"
    ):
        b = json.loads(body)
        # `event.attempt` is populated for these kinds; the JSON is the fallback and
        # not the other way round -- see sortieread.py's first trap.
        a = attempt if attempt is not None else b.get("attempt")
        if kind == "attempt_phase_entered":
            out[a].append(("phase", b.get("phase")))
        else:
            out[a].append(("call", b["usage"]["prompt_tokens"]))
    return out


def measure(tl, threshold=1000):
    """Both readings of the same events: attempt-keyed, and phase-segmented."""
    m = dict.fromkeys(PUBLISHED, 0)
    m["phases"] = m["calls"] = 0
    m["attempts"] = len(tl)
    keyed_attempts, within_attempts, cut_attempts = set(), set(), set()

    for a, rows in tl.items():
        # `prev_any` ignores phase boundaries -- it reproduces the published
        # instrument. The other three are per phase.
        prev_any = None
        prev = None          # the previous call OF THIS PHASE
        hi = 0               # the highest this phase has reported
        last_of_previous = None  # the last call before this phase started

        for kind, v in rows:
            if kind == "phase":
                if prev is not None:
                    last_of_previous = prev
                prev, hi = None, 0
                m["phases"] += 1
                continue

            m["calls"] += 1
            if prev_any is not None and prev_any - v > threshold:
                m["attempt_keyed_falls"] += 1
                keyed_attempts.add(a)
            if prev is None:
                # The first call of a phase: any fall from the phase before it is a
                # fresh `Body::opening` and not a cut.
                if last_of_previous is not None and last_of_previous - v > threshold:
                    m["boundary_falls"] += 1
            else:
                if prev - v > threshold:
                    m["within_phase_falls"] += 1
                    within_attempts.add(a)
                if v < prev:
                    m["falls_any_size"] += 1
            if hi and v < hi:
                m["cut_calls"] += 1
                cut_attempts.add(a)
                m["deepest_cut"] = max(m["deepest_cut"], hi - v)
            hi, prev, prev_any = max(hi, v), v, v

    m["attempt_keyed_attempts"] = len(keyed_attempts)
    m["within_phase_attempts"] = len(within_attempts)
    m["cut_attempts"] = len(cut_attempts)
    return m


def main():
    checking = "--check" in sys.argv
    # The control reads the population the figures were measured over; the report
    # reads everything there is. They are different questions on purpose.
    m = measure(timeline(below=AS_OF if checking else None))
    if checking:
        bad = 0
        for k, want in PUBLISHED.items():
            got = m[k]
            ok = "ok  " if got == want else "DRIFT"
            bad += got != want
            print(f"{ok} {k:<24} published {want:<6} measured {got}")
        print(f"\n(over events below seq {AS_OF})")
        print("CONTROL HELD" if not bad else f"{bad} FIGURE(S) DRIFTED")
        return 1 if bad else 0
    print(f"attempts {m['attempts']}  phases {m['phases']}  model calls {m['calls']}\n")
    print(f"keyed on the ATTEMPT (the wrong denominator, F748)")
    print(f"  falls > 1000 .......... {m['attempt_keyed_falls']} over {m['attempt_keyed_attempts']} attempts")
    print(f"segmented by PHASE")
    print(f"  at a boundary ......... {m['boundary_falls']}   <- fresh Body::opening, not a cut")
    print(f"  within one phase ...... {m['within_phase_falls']} over {m['within_phase_attempts']} attempts")
    print(f"against the phase HIGH WATER (the quantity that matters, F749)")
    print(f"  calls shown a cut ..... {m['cut_calls']} over {m['cut_attempts']} attempts")
    print(f"  falls, any size ....... {m['falls_any_size']}")
    print(f"  deepest cut ........... {m['deepest_cut']} tokens")
    return 0


if __name__ == "__main__":
    sys.exit(main())
