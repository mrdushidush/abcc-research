"""The pre-flight the reader runs before it replays a file.

A ledger file is only replayable if its sequence numbers ascend with no gaps.
The reader cannot recover from a file that does not, because it applies each
record to the balance the previous one left.
"""

from . import ordering


class OutOfOrder(Exception):
    pass


def check(records):
    seqs = [r["seq"] for r in ordering.ordered(records)]
    for left, right in zip(seqs, seqs[1:]):
        if right != left + 1:
            raise OutOfOrder(
                "sequence {} is followed by {} -- the file is not replayable".format(
                    left, right
                )
            )
    return len(seqs)
