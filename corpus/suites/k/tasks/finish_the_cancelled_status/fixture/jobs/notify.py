"""Customer notifications.

Which status changes generate a message, and what it says. Notifications are
rendered here and sent elsewhere; this module has no I/O.
"""

from . import status as st

TEMPLATES = {
    st.DONE: "Your %(kind)s job %(job_id)s finished.",
    st.FAILED: "Your %(kind)s job %(job_id)s failed and will be retried if eligible.",
    st.CANCELLED: "Your %(kind)s job %(job_id)s was cancelled and will not be charged.",
}

# Statuses that do not notify: reaching the queue or starting work is not news.
SILENT = frozenset({st.QUEUED, st.RUNNING})


def message_for(job):
    """The notification text for this job's current status, or None."""
    if job.status in SILENT:
        return None
    template = TEMPLATES.get(job.status)
    if template is None:
        return None
    return template % {"kind": job.kind, "job_id": job.job_id}


def pending(jobs):
    out = []
    for job in jobs:
        msg = message_for(job)
        if msg is not None:
            out.append((job.job_id, msg))
    return out


def report(jobs):
    msgs = pending(jobs)
    lines = ["NOTIFY %d message(s)" % len(msgs)]
    for job_id, msg in msgs:
        lines.append("  %s %s" % (job_id, msg))
    return "\n".join(lines)
