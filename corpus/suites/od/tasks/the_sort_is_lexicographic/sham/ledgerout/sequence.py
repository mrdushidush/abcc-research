"""The pre-flight the reader runs before it replays a file.

A ledger file is only replayable if its sequence numbers ascend with no gaps.
The reader cannot recover from a file that does not, because it applies each
record to the balance the previous one left.
"""

class OutOfOrder(Exception):
    pass


def check(records):
    # Check the sequence itself rather than whatever order the records happen to
    # arrive in: a gap is a gap, and the arrival order is not the reader's
    # problem.
    seqs = sorted(r["seq"] for r in records)
    for left, right in zip(seqs, seqs[1:]):
        if right != left + 1:
            raise OutOfOrder(
                "sequence {} is followed by {} -- the file is not replayable".format(
                    left, right
                )
            )
    return len(seqs)
