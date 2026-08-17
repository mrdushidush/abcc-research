"""The Job record.

Times are integer seconds since the run epoch, so nothing here needs a clock.
`ended_at` is set for every terminal status, cancellation included.
"""

from . import status as st


class Job:
    def __init__(
        self,
        job_id,
        customer,
        kind,
        status,
        queued_at,
        started_at=None,
        ended_at=None,
        cpu_seconds=0,
        sla_seconds=None,
        attempts=1,
    ):
        self.job_id = job_id
        self.customer = customer
        self.kind = kind
        self.status = st.normalize(status)
        self.queued_at = queued_at
        self.started_at = started_at
        self.ended_at = ended_at
        self.cpu_seconds = cpu_seconds
        self.sla_seconds = sla_seconds
        self.attempts = attempts

    @property
    def is_terminal(self):
        return st.is_terminal(self.status)

    @property
    def duration(self):
        """Wall seconds the job occupied, or None if it never started."""
        if self.started_at is None:
            return None
        end = self.ended_at if self.ended_at is not None else self.started_at
        return max(0, end - self.started_at)

    @property
    def waited(self):
        """Seconds between being queued and starting, or None if never started."""
        if self.started_at is None:
            return None
        return max(0, self.started_at - self.queued_at)

    def __repr__(self):
        return "Job(%s, %s, %s)" % (self.job_id, self.customer, self.status)


def from_dict(raw):
    return Job(
        job_id=raw["job_id"],
        customer=raw["customer"],
        kind=raw["kind"],
        status=raw["status"],
        queued_at=raw["queued_at"],
        started_at=raw.get("started_at"),
        ended_at=raw.get("ended_at"),
        cpu_seconds=raw.get("cpu_seconds", 0),
        sla_seconds=raw.get("sla_seconds"),
        attempts=raw.get("attempts", 1),
    )


def load_all(records):
    return [from_dict(r) for r in records]
