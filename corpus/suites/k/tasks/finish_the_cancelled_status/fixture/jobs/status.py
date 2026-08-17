"""The job status vocabulary.

`CANCELLED` was added in 4.2 when the console gained a cancel button. Adding the
constant and the transition was the easy half; every place that BRANCHES on
status has to agree about what it means, and the semantics are in
docs/status_lifecycle.md.
"""

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
CANCELLED = "cancelled"

ALL = (QUEUED, RUNNING, DONE, FAILED, CANCELLED)

# A job in a terminal status will not change again. Nothing should be waiting on
# it, charging for it as if it were still going, or retrying it.
TERMINAL = frozenset({DONE, FAILED, CANCELLED})

# Statuses a job can still leave.
ACTIVE = frozenset({QUEUED, RUNNING})


def is_terminal(status):
    return status in TERMINAL


def is_active(status):
    return status in ACTIVE


def is_known(status):
    return status in ALL


def normalize(status):
    """Fold a status to its canonical spelling, or return it unchanged."""
    if status is None:
        return ""
    return str(status).strip().lower()


# Legal transitions. `cancelled` is reachable from either active status and from
# nowhere else — you cannot cancel a job that has already finished.
TRANSITIONS = {
    QUEUED: frozenset({RUNNING, CANCELLED, FAILED}),
    RUNNING: frozenset({DONE, FAILED, CANCELLED}),
    DONE: frozenset(),
    FAILED: frozenset({QUEUED}),  # a failed job can be requeued
    CANCELLED: frozenset(),
}


def can_transition(current, target):
    return target in TRANSITIONS.get(current, frozenset())
