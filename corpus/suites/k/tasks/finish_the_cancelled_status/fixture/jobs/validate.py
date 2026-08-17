"""Record validation, run before anything branches on status."""

from . import status as st


class RecordError(ValueError):
    pass


REQUIRED = ("job_id", "customer", "kind", "status", "queued_at")


def check(raw):
    if not isinstance(raw, dict):
        raise RecordError("record is %s, not dict" % type(raw).__name__)
    for field in REQUIRED:
        if field not in raw:
            raise RecordError("record missing %r" % field)

    status = st.normalize(raw["status"])
    if not st.is_known(status):
        raise RecordError("record %s has unknown status %r" % (raw["job_id"], raw["status"]))

    if st.is_terminal(status) and raw.get("ended_at") is None:
        raise RecordError("record %s is %s but has no ended_at" % (raw["job_id"], status))
    if status == st.RUNNING and raw.get("started_at") is None:
        raise RecordError("record %s is running but has no started_at" % raw["job_id"])

    if raw.get("cpu_seconds", 0) < 0:
        raise RecordError("record %s has negative cpu_seconds" % raw["job_id"])

    return True


def check_all(records):
    ok, errors = 0, []
    for raw in records:
        try:
            check(raw)
            ok += 1
        except RecordError as exc:
            errors.append(str(exc))
    return ok, errors
