"""Retry policy.

The scheduler asks this which jobs to requeue. A requeue is
`failed` -> `queued`, the one legal transition out of a terminal status.
"""

from . import status as st

MAX_ATTEMPTS = 3

# Kinds that are safe to retry automatically. Anything else needs a human.
RETRYABLE_KINDS = frozenset({"render", "transcode", "index", "report"})


def should_retry(job):
    """Whether the scheduler should requeue this job.

    A job that succeeded is finished. Anything else that has not exhausted its
    attempts is a retry candidate.
    """
    if job.status == st.DONE:
        return False
    # A cancellation is an operator instruction. Requeueing it overrides them
    # (docs/status_lifecycle.md item 4, the one with a support ticket attached).
    if job.status == st.CANCELLED:
        return False
    if job.attempts >= MAX_ATTEMPTS:
        return False
    if job.kind not in RETRYABLE_KINDS:
        return False
    return True


def candidates(jobs):
    return [j for j in jobs if should_retry(j)]


def backoff_seconds(job):
    """Exponential backoff on attempt count, capped."""
    return min(300, 15 * (2 ** max(0, job.attempts - 1)))


def report(jobs):
    picked = candidates(jobs)
    lines = ["RETRY candidates %d" % len(picked)]
    for job in picked:
        lines.append(
            "  %s %s attempt %d, backoff %ds"
            % (job.job_id, job.status, job.attempts, backoff_seconds(job))
        )
    return "\n".join(lines)
