"""W11 item 3: is it the field order, or the order of the enum's own values?

`order.py` measured call-first 0/5 correct and rationale-first 10/10 correct.
Before that becomes a design rule it has to survive the obvious confound: in
every failing arm the enum was `["pass","fail"]` and the wrong answer was
`pass` — the *first* value. The enforcement control is worse: its enum was
`["affirmative","negative"]`, its prose argued for the negative, and it emitted
`affirmative`. Two for two on "whatever was listed first".

So the field-order finding and a first-alternative bias are, so far,
indistinguishable. Four arms separate them. Ground truth is `fail` throughout.

  E  call first,      enum ["fail","pass"]   n=5   value order reversed
  F  rationale first, enum ["fail","pass"]   n=3   both reversed
  G  call first,      enum ["fail","pass"], and the ONE field before it is
                      `defects`, which carries no argument                n=3
  H  call first,      enum ["pass","fail"], `defects` before it           n=3

E vs. order.py's A isolates value order. G vs. H isolates value order with a
non-arguing field in front. If E comes back correct, "put the reasoning first"
is not the rule — "do not let the grammar's first alternative be the answer you
would rather not get" is, and that is a much larger constraint on every enum in
every artifact.
"""

import json
import pathlib
import time
import urllib.request

BASE = "http://localhost:1234"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"
HERE = pathlib.Path(__file__).resolve().parent

import chain  # noqa: E402
import order  # noqa: E402

SYSTEM = chain.HEAD_JUDGE
USER = chain.USER_JUDGE


def main():
    rows = []
    plan = [
        ("E-call-first-failfirst", ["call", "defects", "rationale"], ["fail", "pass"], 5),
        ("F-rat-first-failfirst", ["rationale", "defects", "call"], ["fail", "pass"], 3),
        ("G-defects-then-call-failfirst", ["defects", "call", "rationale"], ["fail", "pass"], 3),
        ("H-defects-then-call-passfirst", ["defects", "call", "rationale"], ["pass", "fail"], 3),
    ]
    for name, keys, enum, n in plan:
        print(f"-- {name}: keys={keys} enum={enum} --")
        sch = order.schema(keys, call_enum=enum)
        for i in range(n):
            rows.append(order.call(f"{name}-{i+1}", SYSTEM, sch))
        print()

    (HERE / "enumbias-results.json").write_text(json.dumps(rows, indent=2))

    print("-- tally (ground truth: fail) --")
    for name, keys, enum, _ in plan:
        got = [r for r in rows if r["label"].startswith(name)]
        ok = sum(1 for r in got if r["call"] == "fail")
        print(f"  {name:<32} first_enum={enum[0]:<4} correct(fail) {ok}/{len(got)}")


if __name__ == "__main__":
    main()
