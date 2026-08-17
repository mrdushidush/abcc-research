"""Audit checks run over a batch of invoices before they go out.

None of these fix anything. They report. An audit that silently corrects its
input is an audit nobody can trust.
"""

from . import ledger, money


class Finding:
    def __init__(self, invoice_number, code, detail):
        self.invoice_number = invoice_number
        self.code = code
        self.detail = detail

    def __repr__(self):
        return "Finding(%s, %s)" % (self.invoice_number, self.code)


CODE_LINESUM = "linesum_mismatch"
CODE_EXPORT = "export_mismatch"
CODE_NEGATIVE = "negative_total"
CODE_UNQUANTIZED = "unquantized_total"

CODES = (CODE_LINESUM, CODE_EXPORT, CODE_NEGATIVE, CODE_UNQUANTIZED)


def audit(invoices):
    """Run every check over `invoices` and return the findings."""
    findings = []

    for inv in invoices:
        if not inv.reconciles():
            findings.append(
                Finding(
                    inv.number,
                    CODE_LINESUM,
                    "printed lines sum to %.2f, printed total is %.2f"
                    % (inv.displayed_sum, inv.total),
                )
            )
        if inv.total < 0:
            findings.append(Finding(inv.number, CODE_NEGATIVE, "total %.2f" % inv.total))
        if not money.is_whole_cents(inv.total):
            findings.append(
                Finding(
                    inv.number,
                    CODE_UNQUANTIZED,
                    "total %.10f is not a whole number of cents" % inv.total,
                )
            )

    for number, single, itemised in ledger.check_itemised_matches_single(invoices):
        findings.append(
            Finding(
                number,
                CODE_EXPORT,
                "single-entry export books %d cents, itemised books %d" % (single, itemised),
            )
        )

    return findings


def counts(findings):
    out = {code: 0 for code in CODES}
    for f in findings:
        out[f.code] = out.get(f.code, 0) + 1
    return out


def render(findings):
    if not findings:
        return "AUDIT clean"
    lines = ["AUDIT %d finding(s)" % len(findings)]
    for f in findings:
        lines.append("  %s %s: %s" % (f.invoice_number, f.code, f.detail))
    return "\n".join(lines)
