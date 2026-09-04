"""Report the backoff schedule the queues will run on.

    python run.py

The line shapes are read by the on-call runbook generator. They are a contract.
"""

import json
import sys

from retrypolicy import backoff, queues

DATA = "data/jobs.json"


def main(argv):
    with open(DATA, encoding="utf-8") as handle:
        jobs = json.load(handle)

    print("BACKOFF RUN")
    print("jobs: {}".format(len(jobs)))
    print("schedule_8: {}".format(",".join(str(s) for s in backoff.schedule(8))))
    print("attempt5_s: {}".format(backoff.delay(5)))
    print("attempt8_s: {}".format(backoff.delay(8)))
    print("longest_wait_s: {}".format(max(backoff.schedule(8))))
    print("total_wait_s: {}".format(sum(backoff.total_wait(j["attempts"]) for j in jobs)))
    print("sync_ceiling_wait_s: {}".format(backoff.total_wait(queues.ceiling("sync"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
