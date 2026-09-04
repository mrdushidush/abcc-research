"""The CSV the accountant imports."""

from . import kinds


def total(transactions):
    running = 0
    for txn in transactions:
        if txn["kind"] in kinds.REFUND_KINDS:
            running -= txn["amount_cents"]
        else:
            running += txn["amount_cents"]
    return running


def render(transactions):
    lines = ["id,date,kind,amount_cents"]
    for txn in transactions:
        lines.append(
            "{},{},{},{}".format(txn["id"], txn["date"], txn["kind"], txn["amount_cents"])
        )
    lines.append("total,,,{}".format(total(transactions)))
    return "\n".join(lines)
