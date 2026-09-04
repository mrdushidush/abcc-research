"""Compute SLA and payment due dates for the open book.

    python run.py

The line shapes are read by the support rota and the collections queue. They
are a contract.
"""

import json
import sys

from worksched import closures as closures_mod, holidays, invoices, sla

DATA = "data/work.json"


def main(argv):
    with open(DATA, encoding="utf-8") as handle:
        work = json.load(handle)
    closures = closures_mod.load()

    ticket_due = sla.due_dates(work["tickets"])
    checked = sla.check(ticket_due, closures)
    invoice_due = invoices.due_dates(work["invoices"])

    print("CALENDAR RUN")
    print("tickets: {}".format(checked))
    print("invoices: {}".format(len(invoice_due)))
    print("holidays_2026: {}".format(len(holidays.for_year(2026))))
    print("ticket_due_closed: {}".format(
        sum(1 for _, day in ticket_due if closures.closed(day))))
    print("invoice_due_closed: {}".format(
        sum(1 for _, day in invoice_due if closures.closed(day))))
    print("first_ticket_due: {}".format(ticket_due[0][1].isoformat()))
    print("last_invoice_due: {}".format(invoice_due[-1][1].isoformat()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
