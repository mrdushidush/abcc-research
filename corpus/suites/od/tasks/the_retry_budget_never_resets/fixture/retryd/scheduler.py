"""Deciding which failures get retried."""


def run(budget, failures):
    retried, dropped = [], []
    for failure in sorted(failures, key=lambda f: f["ts"]):
        if not budget.has_room(failure["ts"]):
            dropped.append(failure["id"])
            continue
        budget.spend(failure["ts"])
        retried.append(failure["id"])
    return retried, dropped
