"""The HTML statement we email."""

from . import kinds


def total(transactions):
    running = 0
    for txn in transactions:
        if txn["kind"] == kinds.REFUND:
            running -= txn["amount_cents"]
        else:
            running += txn["amount_cents"]
    return running


def render(transactions):
    rows = "".join(
        "<tr><td>{}</td><td>{}</td></tr>".format(txn["kind"], txn["amount_cents"])
        for txn in transactions
    )
    return "<table>{}<tfoot>{}</tfoot></table>".format(rows, total(transactions))
