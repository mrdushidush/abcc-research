"""Visible tests.

⚠ Every transaction built here is a charge or a full refund, so no renderer in
this suite is ever handed a `partial_refund`. `kinds.REFUND_KINDS` is asserted
directly and it is right — nothing reads it.
"""

import json

from statement import csv_out, html_out, json_out, kinds, summary


def txn(kind, amount, ident="t"):
    return {"id": ident, "customer": "ana", "kind": kind, "amount_cents": amount,
            "date": "2026-08-01"}


BASIC = [txn("charge", 1000, "a"), txn("charge", 500, "b"), txn("refund", 500, "c")]


def test_refund_kinds_lists_both_refunds():
    assert kinds.REFUND_KINDS == ("refund", "partial_refund")


def test_csv_total_over_charges_and_a_full_refund():
    assert csv_out.total(BASIC) == 1000


def test_json_total_matches_csv():
    assert json_out.total(BASIC) == csv_out.total(BASIC)


def test_html_total_matches_csv():
    assert html_out.total(BASIC) == csv_out.total(BASIC)


def test_summary_total_matches_csv():
    assert summary.total(BASIC) == csv_out.total(BASIC)


def test_csv_renders_a_header_and_a_total_row():
    out = csv_out.render(BASIC).split("\n")
    assert out[0] == "id,date,kind,amount_cents"
    assert out[-1] == "total,,,1000"


def test_json_renders_the_total():
    assert json.loads(json_out.render(BASIC))["total_cents"] == 1000


def test_summary_counts_the_lines():
    assert summary.render(BASIC).startswith("3 transactions")
