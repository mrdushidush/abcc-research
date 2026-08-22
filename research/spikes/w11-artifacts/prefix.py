"""W11 item 3: does ANY field in front of the verdict fix it, or only one that
carries the argument?

Standing measurement after `order.py` and `enumbias.py`: with `call` as the
first key of the object the Judge answered `pass` 11 times out of 11 against a
failed acceptance criterion, and with any of `rationale`, `assessment` or
`defects` in front of it, `fail` 17 times out of 17. Enum value order was ruled
out (reversing it changed nothing in either direction).

That leaves two different design rules, and they cost different amounts:

  weak    "never let the conclusion be the first key" — satisfied by any
          field at all, including a version tag
  strong  "the conclusion must be preceded by the evidence that justifies it"
          — which constrains the shape of every artifact that carries a
          decision, not just its key order

Two neutral prefixes separate them. Ground truth is `fail`.

  I  a constant first:  {"artifact_version": "v1"} — zero information   n=3
  J  a neutral list first: {"files_reviewed": [...]} — content, but no
     argument in it                                                     n=3
"""

import json
import pathlib

import chain  # noqa: E402
import order  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SYSTEM = chain.HEAD_JUDGE

DEFECT = order.DEFECT


def build(props_order, extra):
    props = {
        "call": {"type": "string", "enum": ["pass", "fail"]},
        "rationale": {"type": "string"},
        "defects": {"type": "array", "items": DEFECT},
    }
    props.update(extra)
    ordered = {k: props[k] for k in props_order}
    return {
        "type": "object",
        "properties": ordered,
        "required": list(props_order),
        "additionalProperties": False,
    }


def main():
    rows = []

    print('-- I: a constant first ({"artifact_version": "v1"}) --')
    si = build(
        ["artifact_version", "call", "defects", "rationale"],
        {"artifact_version": {"type": "string", "enum": ["v1"]}},
    )
    for i in range(3):
        rows.append(order.call(f"I-const-first-{i+1}", SYSTEM, si))
    print()

    print('-- J: a neutral list first ({"files_reviewed": [...]}) --')
    sj = build(
        ["files_reviewed", "call", "defects", "rationale"],
        {"files_reviewed": {"type": "array", "items": {"type": "string"}}},
    )
    for i in range(3):
        rows.append(order.call(f"J-neutral-first-{i+1}", SYSTEM, sj))
    print()

    (HERE / "prefix-results.json").write_text(json.dumps(rows, indent=2))

    print("-- tally (ground truth: fail) --")
    for arm in ("I-const-first", "J-neutral-first"):
        got = [r for r in rows if r["label"].startswith(arm)]
        ok = sum(1 for r in got if r["call"] == "fail")
        print(f"  {arm:<18} correct(fail) {ok}/{len(got)}")


if __name__ == "__main__":
    main()
