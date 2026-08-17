"""Job tracking.

`status.py` holds the vocabulary. Everything else either moves a job between
statuses (`queue`) or branches on the one it is in:

    sla         is this job late?
    charges     is this job billable?
    summary     which bucket does it count in?
    retry       should the scheduler requeue it?
    notify      does the customer hear about it?
    dashboard   what label and colour does it get?

Semantics for each status are in docs/status_lifecycle.md, which is the document
to read before changing any of the above.
"""

__all__ = [
    "charges",
    "dashboard",
    "model",
    "notify",
    "queue",
    "retry",
    "sla",
    "status",
    "summary",
    "validate",
]

VERSION = "4.2.1"
