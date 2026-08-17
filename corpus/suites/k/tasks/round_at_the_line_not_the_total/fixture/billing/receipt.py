"""Rendering an invoice for the customer.

The output shape is a contract — the reconciliation report and the verifier
both parse it. Adding a line is safe; changing an existing line's shape is not.
"""

from . import money


def render(inv):
    lines = []
    lines.append("INVOICE %s" % inv.number)
    lines.append("customer: %s" % inv.customer)
    lines.append("region: %s" % inv.region)

    for line, amount in zip(inv.lines, inv.line_amounts):
        lines.append(
            "  %-12s %-28s qty %4d  %s"
            % (line.sku, line.description, line.qty, money.format_amount(amount))
        )

    lines.append("TOTAL %s" % money.format_amount(inv.total))
    lines.append(
        "LINESUM %s" % money.format_amount(inv.displayed_sum)
    )
    lines.append("RECONCILES %s" % ("yes" if inv.reconciles() else "NO"))
    return "\n".join(lines)


def render_all(invoices):
    return "\n\n".join(render(inv) for inv in invoices)


def summary(invoices):
    """One line per invoice, plus a count of the ones that do not reconcile."""
    out = []
    bad = 0
    for inv in invoices:
        ok = inv.reconciles()
        if not ok:
            bad += 1
        out.append(
            "%s total=%s linesum=%s %s"
            % (
                inv.number,
                money.format_amount(inv.total),
                money.format_amount(inv.displayed_sum),
                "ok" if ok else "MISMATCH",
            )
        )
    out.append("MISMATCHES %d of %d" % (bad, len(invoices)))
    return "\n".join(out)
