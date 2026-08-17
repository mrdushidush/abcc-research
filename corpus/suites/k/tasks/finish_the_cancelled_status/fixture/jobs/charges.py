"""Billing for compute.

Charged per CPU-second, per job kind. A job that produced no usable result is
not charged, because charging for it generates a credit request and we lose the
staff time twice.
"""

from . import status as st

# pence per CPU-second, by kind
RATES = {
    "render": 0.85,
    "transcode": 0.40,
    "index": 0.25,
    "report": 0.15,
    "train": 2.10,
}

DEFAULT_RATE = 0.30


def rate_for(kind):
    return RATES.get(kind, DEFAULT_RATE)


def is_chargeable(job):
    """Whether this job's compute is billable.

    A failed job is not charged — the customer got nothing.
    """
    if job.status == st.FAILED:
        return False
    return job.cpu_seconds > 0


def charge_pence(job):
    if not is_chargeable(job):
        return 0.0
    return job.cpu_seconds * rate_for(job.kind)


def total_pence(jobs):
    return sum(charge_pence(j) for j in jobs)


def chargeable_jobs(jobs):
    return [j for j in jobs if is_chargeable(j)]


def by_customer(jobs):
    out = {}
    for job in jobs:
        out[job.customer] = out.get(job.customer, 0.0) + charge_pence(job)
    return out


def report(jobs):
    lines = ["CHARGES total %.2fp across %d job(s)" % (total_pence(jobs), len(chargeable_jobs(jobs)))]
    for customer in sorted(by_customer(jobs)):
        lines.append("  %s %.2fp" % (customer, by_customer(jobs)[customer]))
    return "\n".join(lines)
