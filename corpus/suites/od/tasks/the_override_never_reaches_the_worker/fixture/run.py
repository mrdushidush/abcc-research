"""Boot the worker configuration and report it.

    python run.py

The line shapes are read by the deploy check. They are a contract.
"""

import sys

from bootcfg import capacity, env, overrides, settings


def main(argv):
    config = overrides.apply(settings.DEFAULTS, env.load())
    value = capacity.check(config)

    print("BOOT RUN")
    print("concurrency: {}".format(config["concurrency"]))
    print("batch_size: {}".format(config["batch_size"]))
    print("timeout_s: {}".format(config["timeout_s"]))
    print("throughput: {}".format(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
