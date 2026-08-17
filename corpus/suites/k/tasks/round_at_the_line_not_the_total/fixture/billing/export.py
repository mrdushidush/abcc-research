"""Exports to the finance system.

Two exports exist and they must agree, which is the constraint that makes this
module worth reading:

  - `single_entry_csv` writes ONE row per invoice, at the invoice total.
  - `itemised_csv` writes ONE row per line, at the printed line amount.

Finance imports both and reconciles them against each other. If the sum of the
itemised rows for an invoice differs from that invoice's single row, the period
does not close. `audit.CODE_EXPORT` is the check for exactly that.

Neither export rounds. Both take amounts that are already chargeable — the
single row from `Invoice.total`, the itemised rows from `Invoice.line_amounts`.
An export that had to round would be a sign the rounding happened too late.
"""

from . import money

SINGLE_HEADER = "invoice,customer,region,amount"
ITEMISED_HEADER = "invoice,sku,description,qty,amount"


def _csv_escape(text):
    text = str(text)
    if any(ch in text for ch in (",", '"', "\n")):
        return '"%s"' % text.replace('"', '""')
    return text


def single_entry_csv(invoices):
    rows = [SINGLE_HEADER]
    for inv in invoices:
        rows.append(
            "%s,%s,%s,%.2f"
            % (_csv_escape(inv.number), _csv_escape(inv.customer), inv.region, inv.total)
        )
    return "\n".join(rows)


def itemised_csv(invoices):
    rows = [ITEMISED_HEADER]
    for inv in invoices:
        for line, amount in zip(inv.lines, inv.line_amounts):
            rows.append(
                "%s,%s,%s,%d,%.2f"
                % (
                    _csv_escape(inv.number),
                    _csv_escape(line.sku),
                    _csv_escape(line.description),
                    line.qty,
                    amount,
                )
            )
    return "\n".join(rows)


def json_payload(invoices):
    """The shape the finance API accepts. Amounts are integer cents on the wire."""
    out = []
    for inv in invoices:
        out.append(
            {
                "invoice": inv.number,
                "customer": inv.customer,
                "region": inv.region,
                "total_cents": money.to_cents(inv.total),
                "lines": [
                    {
                        "sku": line.sku,
                        "qty": line.qty,
                        "amount_cents": money.to_cents(amount),
                    }
                    for line, amount in zip(inv.lines, inv.line_amounts)
                ],
            }
        )
    return out


def cross_check(invoices):
    """Return invoices where the two exports disagree, as (number, single, itemised)."""
    bad = []
    for payload in json_payload(invoices):
        itemised = sum(l["amount_cents"] for l in payload["lines"])
        if itemised != payload["total_cents"]:
            bad.append((payload["invoice"], payload["total_cents"], itemised))
    return bad
