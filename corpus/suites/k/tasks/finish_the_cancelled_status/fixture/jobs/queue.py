"""The transition gate.

Every status change goes through `apply`, which refuses an illegal transition
rather than recording it. This module is the one place `status.TRANSITIONS` is
enforced, and it already knows about cancellation.
"""

from . import status as st


class IllegalTransition(ValueError):
    pass


def apply(job, target, at):
    """Move `job` to `target` at time `at`, or raise."""
    target = st.normalize(target)
    if not st.is_known(target):
        raise IllegalTransition("unknown status %r" % (target,))
    if not st.can_transition(job.status, target):
        raise IllegalTransition(
            "cannot go %s -> %s for %s" % (job.status, target, job.job_id)
        )

    job.status = target
    if target == st.RUNNING:
        job.started_at = at
    elif st.is_terminal(target):
        job.ended_at = at
    elif target == st.QUEUED:
        # A requeue clears the previous run's end time and counts an attempt.
        job.ended_at = None
        job.started_at = None
        job.attempts += 1
    return job


def cancel(job, at):
    """Operator cancellation. Legal only from an active status."""
    return apply(job, st.CANCELLED, at)


def requeue(job, at):
    """Retry a failed job."""
    return apply(job, st.QUEUED, at)


def legal_targets(job):
    return sorted(st.TRANSITIONS.get(job.status, frozenset()))
