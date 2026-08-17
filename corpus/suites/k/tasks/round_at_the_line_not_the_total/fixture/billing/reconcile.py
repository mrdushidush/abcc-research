"""Period reconciliation.

At month end, three numbers must agree:

  1. the sum of invoice totals,
  2. the sum of all itemised line amounts,
  3. what the ledger booked.

They are computed by three different paths on purpose. Agreement between three
independent paths is evidence; agreement between one path and itself is not.
"""

from . import export, ledger, money


class Period:
    def __init__(self, label, invoices):
        self.label = label
        self.invoices = invoices

    def total_of_invoices(self):
        return money.sum_amounts([inv.total for inv in self.invoices])

    def total_of_lines(self):
        amounts = []
        for inv in self.invoices:
            amounts.extend(inv.line_amounts)
        return money.sum_amounts(amounts)

    def total_of_ledger(self):
        book = ledger.Ledger()
        for inv in self.invoices:
            book.post_invoice(inv)
        return book.total()

    def agrees(self):
        a = money.to_cents(self.total_of_invoices())
        b = money.to_cents(self.total_of_lines())
        c = money.to_cents(self.total_of_ledger())
        return a == b == c

    def report(self):
        a = self.total_of_invoices()
        b = self.total_of_lines()
        c = self.total_of_ledger()
        lines = [
            "PERIOD %s" % self.label,
            "  invoices  %.2f" % a,
            "  lines     %.2f" % b,
            "  ledger    %.2f" % c,
        ]
        if self.agrees():
            lines.append("  AGREES")
        else:
            lines.append("  DISAGREES by %.2f (invoices vs lines)" % (a - b))
        return "\n".join(lines)


def close(label, invoices):
    """Attempt to close a period. Returns (Period, [problem strings])."""
    period = Period(label, invoices)
    problems = []
    if not period.agrees():
        problems.append(
            "period %s does not reconcile: invoices %.2f, lines %.2f, ledger %.2f"
            % (
                label,
                period.total_of_invoices(),
                period.total_of_lines(),
                period.total_of_ledger(),
            )
        )
    for number, single, itemised in export.cross_check(invoices):
        problems.append(
            "invoice %s: single export %d cents, itemised %d" % (number, single, itemised)
        )
    return period, problems
