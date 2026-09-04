"""Visible tests.

⚠ Every batch here has fewer than ten records, so every sequence number is a
single digit and its text order is its numeric order. That is the one condition
under which the ordering is right.
"""

from ledgerout import ordering, sequence, writer


def records(*seqs):
    return [{"seq": s, "id": "seq-{}".format(s), "amount_cents": 100 * s} for s in seqs]


def test_ordered_sorts_a_shuffled_batch():
    assert [r["seq"] for r in ordering.ordered(records(3, 1, 2))] == [1, 2, 3]


def test_emit_returns_ids_in_order():
    assert writer.emit(records(2, 1, 3)) == ["seq-1", "seq-2", "seq-3"]


def test_running_balance_follows_the_written_order():
    assert writer.running_balance(records(2, 1, 3)) == [100, 300, 600]


def test_check_accepts_a_contiguous_batch():
    assert sequence.check(records(4, 2, 3, 1, 5)) == 5


def test_check_refuses_a_gap():
    try:
        sequence.check(records(1, 2, 4))
    except sequence.OutOfOrder as exc:
        assert "followed by 4" in str(exc)
    else:
        raise AssertionError("expected OutOfOrder")
