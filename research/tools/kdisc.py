"""Derive each K task's root/sham file sets from the refsol and sham OVERLAYS.

`refsol/` and `sham/` are PARTIAL overlays -- they contain only the files they
change, laid over `fixture/`. So the edited set is simply what is present in them;
walking the fixture and calling a missing file "different" inverts the meaning and
was the first bug in this tool.

A hand-typed discriminator path that never matches reports a clean 'no-root' that is
indistinguishable from a genuine miss -- which is what a typo produced on
`finish_the_cancelled_status` (jobs/summary.py, typed as summary.py).
"""
import os

TASKS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "corpus", "suites", "k", "tasks")

NOISE = ("__pycache__", ".pytest_cache", ".pyc", ".git")

# Where the file alone cannot decide, the content does. Each entry is
#   task -> (file, needle-that-only-the-CORRECT-answer contains, what it means)
# derived by reading refsol against sham, not from prose.
CONTENT_TELL = {
    # The tell must be BEHAVIOURAL, not lexical. An earlier version looked for the
    # helper name `sum_amounts` and scored champion b2 r3 as wrong -- it had written
    #   total_cents += money.to_cents(money.quantize(line.total))
    # which is refsol's behaviour with different identifiers. A content check keyed to
    # one implementation's names marks a correct alternative implementation as a sham.
    #
    # What actually separates the three:
    #   fixture (broken): money.quantize(running)          <- quantized ONCE, at the end
    #   refsol  (right) : money.quantize(line.total) ...   <- quantized PER LINE
    #   sham    (wrong) : math.ceil(running * CENTS - EPS) <- ceils the running total
    # So: is `quantize` applied to a per-line value?
    "round_at_the_line_not_the_total": (
        "billing/pricing.py", "quantize(line",
        "quantizes PER LINE (refsol); fixture quantizes the running total once, "
        "the sham ceils it"),
}

# The F308 format trap: the `finish` verifier requires `other=0` to still be PRINTED,
# and a subject that replaces `other` with `cancelled` in summary.BUCKETS fails on
# format while having fixed the behaviour correctly at all four sites. Detect it from
# the verifier's own message -- a substring search of summary.py is too weak, because
# the word `other` survives elsewhere in the file after BUCKETS has been rewritten.
FORMAT_TELL = {}
FORMAT_FAIL_MARKER = {
    "finish_the_cancelled_status": (
        "other=0",
        "F308 shape: FORMAT failure, not a behavioural one -- check the four root sites"),
}


def noisy(rel):
    return any(n in rel for n in NOISE)


def overlay_files(task, kind):
    """Files present in refsol/ or sham/ -- i.e. the files that answer edits."""
    base = os.path.join(TASKS, task, kind)
    out = set()
    if not os.path.isdir(base):
        return out
    for dirpath, dirs, names in os.walk(base):
        dirs[:] = [d for d in dirs if not noisy(d)]
        for n in names:
            rel = os.path.relpath(os.path.join(dirpath, n), base).replace(os.sep, "/")
            if not noisy(rel):
                out.add(rel)
    return out


def sets_for(task):
    return overlay_files(task, "refsol"), overlay_files(task, "sham")


def all_sets():
    return {t: sets_for(t) for t in sorted(os.listdir(TASKS))
            if os.path.isdir(os.path.join(TASKS, t))}


if __name__ == "__main__":
    for task, (root, sham) in all_sets().items():
        print("=== %s" % task)
        print("  root  (refsol edits) : %s" % ", ".join(sorted(root)))
        print("  sham  (sham edits)   : %s" % ", ".join(sorted(sham)))
        so = sham - root
        print("  sham-ONLY file tell  : %s" % (", ".join(sorted(so)) or
                                               "(none -- same file; content decides)"))
        if task in CONTENT_TELL:
            f, needle, why = CONTENT_TELL[task]
            print("  content tell         : %s must contain %r -- %s" % (f, needle, why))
        if task in FORMAT_TELL:
            f, needle, why = FORMAT_TELL[task]
            print("  format tell          : %s should keep %r -- %s" % (f, needle, why))
