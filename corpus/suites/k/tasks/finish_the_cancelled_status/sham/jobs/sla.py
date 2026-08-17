"""SLA evaluation.

A job breaches its SLA when the time from queueing to finishing exceeds
`sla_seconds`. A job with no `sla_seconds` has no SLA and cannot breach.
"""

from . import status as st

# Jobs still in flight are measured against `now` rather than an end time.
DEFAULT_SLA_SECONDS = 3600


def deadline(job):
    """The absolute time by which this job must have finished, or None."""
    limit = job.sla_seconds if job.sla_seconds is not None else DEFAULT_SLA_SECONDS
    return job.queued_at + limit


def finished_at(job, now):
    """The time to measure the SLA against.

    A job that has finished is measured at its end time; a job still in flight
    is measured against the current time, because an unfinished job keeps
    accruing.
    """
    # Every TERMINAL status is measured at its end time, cancellation included:
    # the clock stops when the operator stops the job (docs/status_lifecycle.md).
    if st.is_terminal(job.status):
        return job.ended_at if job.ended_at is not None else now
    return now


def is_breached(job, now):
    """True when this job has missed its deadline."""
    if job.sla_seconds is None:
        return False
    return finished_at(job, now) > deadline(job)


def breaches(jobs, now):
    return [j for j in jobs if is_breached(j, now)]


def margin(job, now):
    """Seconds of headroom left, negative when breached."""
    return deadline(job) - finished_at(job, now)


def report(jobs, now):
    bad = breaches(jobs, now)
    lines = ["SLA breaches %d" % len(bad)]
    for job in bad:
        lines.append("  %s %s over by %ds" % (job.job_id, job.customer, -margin(job, now)))
    return "\n".join(lines)
