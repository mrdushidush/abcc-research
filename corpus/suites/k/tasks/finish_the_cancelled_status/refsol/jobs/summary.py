"""Counts and rates over a set of jobs.

The dashboard and the weekly report both read this. Every status the system can
produce needs its own bucket — a status that lands in `other` is a status nobody
looks at.
"""

from . import status as st

BUCKETS = ("queued", "running", "done", "failed", "cancelled", "other")


def counts(jobs):
    """Count jobs per bucket."""
    out = {b: 0 for b in BUCKETS}
    for job in jobs:
        if job.status == st.QUEUED:
            out["queued"] += 1
        elif job.status == st.RUNNING:
            out["running"] += 1
        elif job.status == st.DONE:
            out["done"] += 1
        elif job.status == st.FAILED:
            out["failed"] += 1
        elif job.status == st.CANCELLED:
            out["cancelled"] += 1
        else:
            out["other"] += 1
    return out


def failure_rate(jobs):
    """Failed jobs as a fraction of jobs that reached a terminal status."""
    c = counts(jobs)
    finished = c["done"] + c["failed"]
    if finished == 0:
        return 0.0
    return c["failed"] / finished


def completion_rate(jobs):
    c = counts(jobs)
    finished = c["done"] + c["failed"]
    if finished == 0:
        return 0.0
    return c["done"] / finished


def report(jobs):
    c = counts(jobs)
    parts = ["%s=%d" % (b, c[b]) for b in BUCKETS]
    lines = ["COUNTS " + " ".join(parts)]
    lines.append("RATES failure=%.3f completion=%.3f" % (failure_rate(jobs), completion_rate(jobs)))
    return "\n".join(lines)
