"""Replay the captured sign-up candidates through the password policy.

    python run.py

The line shapes are read by the security review. They are a contract.
"""

import sys

from pwpolicy import candidates, policy

DATA = "data/candidates.json"


def main(argv):
    rows = candidates.load(DATA)
    verdicts = {row["id"]: policy.accepts(row["password"]) for row in rows}

    print("PASSWORD RUN")
    print("candidates: {}".format(len(rows)))
    print("accepted: {}".format(sum(1 for v in verdicts.values() if v)))
    for ident in ("c1", "c2", "c5", "c7", "c8"):
        print("{}_accepted: {}".format(ident, "yes" if verdicts[ident] else "no"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
