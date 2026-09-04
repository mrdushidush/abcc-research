"""Visible tests.

⚠ Every result set built here is an exact multiple of the page size — 20 and
30 — so the partial final page never occurs and the paging is never asked the
one question it gets wrong. `audit.check` is exercised only on exports where
nothing is missing, so nothing pins what it compares against.
"""

from expo import audit, paging, writer


def rows(n):
    return [{"id": "r{}".format(i), "account": "a", "amount_cents": 100} for i in range(n)]


def test_pages_of_an_exact_multiple():
    pages = paging.pages(rows(30), 10)
    assert [len(p) for p in pages] == [10, 10, 10]


def test_pages_of_one_full_page():
    assert [len(p) for p in paging.pages(rows(20), 10)] == [10, 10]


def test_writer_collects_every_page():
    sink = writer.write_all(writer.Sink(), paging.pages(rows(20), 10))
    assert len(sink.pages) == 2
    assert len(sink.rows()) == 20


def test_audit_passes_when_the_counts_agree():
    source = rows(20)
    sink = writer.write_all(writer.Sink(), paging.pages(source, 10))
    assert audit.check(source, sink) == 20


def test_audit_returns_the_row_count_it_checked():
    source = rows(30)
    sink = writer.write_all(writer.Sink(), paging.pages(source, 10))
    assert audit.check(source, sink) == 30
