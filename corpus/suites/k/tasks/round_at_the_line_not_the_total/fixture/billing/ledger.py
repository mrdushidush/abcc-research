"""The ledger: what we actually book, in whole cents.

The ledger is integer-only by design. Every amount entering it goes through
`money.to_cents`, so a float that was never reduced to a chargeable amount is
silently truncated to whatever cent it happens to land in. That is the point at
which a precision mistake upstream stops being visible and starts being
accounting.
"""

from . import money


class Entry:
    def __init__(self, invoice_number, description, cents):
        self.invoice_number = invoice_number
        self.description = description
        self.cents = cents

    @property
    def amount(self):
        return money.from_cents(self.cents)

    def __repr__(self):
        return "Entry(%s, %d)" % (self.invoice_number, self.cents)


class Ledger:
    def __init__(self):
        self.entries = []

    def post_invoice(self, inv):
        """Book one invoice as a single entry at its total."""
        self.entries.append(
            Entry(inv.number, "invoice %s" % inv.number, money.to_cents(inv.total))
        )

    def post_lines(self, inv):
        """Book one invoice as one entry per line.

        Used by the itemised export. The sum of these entries MUST equal the
        single entry `post_invoice` books for the same invoice, or the two
        exports disagree and someone spends a morning on it.
        """
        for line, amount in zip(inv.lines, inv.line_amounts):
            self.entries.append(
                Entry(inv.number, "%s %s" % (inv.number, line.sku), money.to_cents(amount))
            )

    def total_cents(self):
        return sum(e.cents for e in self.entries)

    def total(self):
        return money.from_cents(self.total_cents())

    def for_invoice(self, number):
        return [e for e in self.entries if e.invoice_number == number]

    def __len__(self):
        return len(self.entries)


def check_itemised_matches_single(invoices):
    """Book each invoice both ways and report any invoice where they disagree.

    Returns a list of (invoice_number, single_cents, itemised_cents).
    """
    bad = []
    for inv in invoices:
        single = Ledger()
        single.post_invoice(inv)
        itemised = Ledger()
        itemised.post_lines(inv)
        if single.total_cents() != itemised.total_cents():
            bad.append((inv.number, single.total_cents(), itemised.total_cents()))
    return bad
