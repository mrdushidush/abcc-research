"""Tonight's outbound plan.

    python run.py

The line shapes are read by the send scheduler. They are a contract.
"""

import sys

from outbound import model, newsletter, promo_sms, push, winback

DATA = "data/contacts.json"


def main(argv):
    contacts = model.load(DATA)
    print("OUTBOUND PLAN")
    print("contacts: {}".format(len(contacts)))
    print("newsletter: {}".format(len(newsletter.audience(contacts))))
    print("winback: {}".format(len(winback.audience(contacts))))
    print("promo_sms: {}".format(len(promo_sms.audience(contacts))))
    print("push: {}".format(len(push.audience(contacts))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
