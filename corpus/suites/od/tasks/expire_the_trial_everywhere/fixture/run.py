"""Nightly entitlement report.

    python run.py

The line shapes below are consumed by the finance import and by the support
rota generator. They are a contract: do not reformat them.
"""

import sys

from entitlement import access, config, digest, model, seats, support


def main(argv):
    accounts = model.load(config.DATA)
    as_of = config.AS_OF

    print("ENTITLEMENT REPORT")
    print("as_of: {}".format(as_of))
    print("accounts: {}".format(len(accounts)))
    print("premium: {}".format(len(access.premium_accounts(accounts, as_of))))
    print("digest: {}".format(len(digest.recipients(accounts, as_of))))
    print("seats: {}".format(seats.billable_seats(accounts, as_of)))
    print("priority: {}".format(len(support.priority_accounts(accounts, as_of))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
