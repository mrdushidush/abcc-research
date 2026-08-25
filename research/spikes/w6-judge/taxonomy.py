#!/usr/bin/env python3
"""W6 item 7 — OQ-W6-13: the hand classification of the 29, with its quotes checked.

The question F321 left open is what the 29 clean-arm failures *are*. K's taxonomy
(F302: nothing done / part of it done / symptom removed) does not transfer,
because these are one-file tasks where the file was always written and the visible
suite is always green.

The axis that turned out to matter is **what decides the failing case**, because
that, and not the language, is what sets whether a reviewer with no tools could
possibly have caught it:

  stated     the ticket's own words fix the expected value. A reader needs
             nothing outside the ticket.
  signalled  the ticket contains a generality clause pointing at edges — "for
             whatever titles people throw at it" — which says edges exist and
             does not say what the answer is.
  implied    the ticket does not mention the case at all; the domain decides it
             (a divisor of zero, an empty input, a duplicate registration).
  undecided  neither the ticket nor the domain decides it, and the hidden test
             picks a convention. There is one of these and the agent argued the
             other side in a test it wrote itself.
  mechanical not a reasoning failure at all: the artifact was mangled by the
             mechanism that wrote it, or the code does not terminate.

Every `stated` and `signalled` row carries the clause verbatim, and `main()`
asserts the clause is a substring of the ticket — a classification whose evidence
is a quotation is only worth having if the quotation is checked.

    python taxonomy.py
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

import common as C

HERE = pathlib.Path(__file__).resolve().parent

# key: the content sha of the tree the agent left (see common.population)
ROWS = {
    "2f026af92584428f": dict(
        task="Q01", cls="signalled",
        fails="already_a_slug_is_stable",
        case='slugify("already-a-slug")',
        expected='"already-a-slug"', actual='"alreadyaslug"',
        quote="Make sure it produces clean slugs for whatever titles people throw at it.",
        note="'-' is not alphanumeric and is not a space, so the agent's match arm "
             "drops it; feeding a slug back in is not stable. The ticket's example "
             "makes '-' the separator but never says a hyphen survives.",
    ),
    "e45a172aa82aea9c": dict(
        task="Q03", cls="stated",
        fails="remainder_sums_exact_2 (and zero_people_no_panic)",
        case="split_bill(10, 4)",
        expected="[3, 3, 2, 2]", actual="[4, 2, 2, 2]",
        quote="while keeping the split as even as possible",
        note="the whole remainder goes to shares[0]. Also panics at people == 0, "
             "which is the `implied` half of the same tree.",
    ),
    "7d272eecc3197b4b": dict(
        task="Q03", cls="implied",
        fails="zero_people_no_panic",
        case="split_bill(7, 0)",
        expected="[]", actual="panics (divide by zero)",
        quote=None,
        note="the remainder distribution is correct. The ticket names no zero case.",
    ),
    "e82fc26978b60565": dict(
        task="Q03", cls="implied",
        fails="zero_people_no_panic",
        case="split_bill(7, 0)",
        expected="[]", actual="panics (divide by zero)",
        quote=None,
        note="same shape as 7d272e, written differently.",
    ),
    "341857425332f6b8": dict(
        task="Q05", cls="signalled",
        fails="blank_lines_skipped",
        case='parse_kv("a=1\\n\\n   \\nb=2")',
        expected='Ok({"a": "1", "b": "2"})', actual='Err("line 2: missing \'=\'")',
        quote="Callers pass whole config files, so make sure it handles them gracefully.",
        note="a blank line in a config file is the canonical case, and the clause "
             "points at it without deciding it.",
    ),
    "a7b711ff7041ac0a": dict(
        task="Q05", cls="signalled",
        fails="blank_lines_skipped",
        case='parse_kv("a=1\\n\\n   \\nb=2")',
        expected='Ok({"a": "1", "b": "2"})', actual='Err("line 2: missing \'=\'")',
        quote="Callers pass whole config files, so make sure it handles them gracefully.",
        note="same as 341857 with a different binding style.",
    ),
    "c87bafa532f5fc73": dict(
        task="Q07", cls="stated",
        fails="ties_broken_alphabetically",
        case='word_frequencies("cherry banana apple")',
        expected='[("apple",1), ("banana",1), ("cherry",1)]',
        actual='[("cherry",1), ("banana",1), ("apple",1)]',
        quote="breaking ties alphabetically",
        note="sorts ascending by (count, word) and then calls .reverse(), which "
             "reverses the tie order too. Decidable from the ticket alone.",
    ),
    "4e4cfe591d9296f4": dict(
        task="Q25", cls="implied",
        fails="test_integer_dollar_string",
        case='total_cents(["5"])',
        expected="500", actual="ValueError: not enough values to unpack",
        quote=None,
        note='p.split(".") on a price with no decimal point. The ticket only ever '
             'shows prices with a point.',
    ),
    "c0852d9ec290c1a1": dict(
        task="Q40", cls="implied",
        fails="same listener added twice fires twice",
        case='e.on("e", bump); e.on("e", bump); e.emit("e")',
        expected="bump called twice", actual="bump called once",
        quote=None,
        note="listeners are held in a Set, which silently dedupes. The ticket says "
             "'every listener registered ... in the order they were added' and does "
             "not settle whether registration is a set or a list, so the ticket does "
             "not decide the multiplicity.",
    ),
    "89a76d26debbc8ca": dict(
        task="Q45", cls="mechanical",
        fails="the whole script",
        case="bash solution.sh < input.txt",
        expected="the non-comment, non-blank lines",
        actual="nothing at all",
        quote=None,
        note="the file is ONE line: `#!/usr/bin/env bash`n# Strip ...`ngrep ...`n` — "
             "PowerShell's backtick-n escape written literally into a bash script. "
             "As bash the whole line is a comment, so the script produces no output. "
             "`bash -n` is green on it (it is valid), and so is the structural check "
             "(the file was modified).",
    ),
    "b952a1e351b4a00f": dict(
        task="Q46", cls="stated",
        fails="range 8..100",
        case="printf 'l1..l10' | bash solution.sh 8 100",
        expected="lines 8, 9, 10", actual="lines 1..10",
        quote="if END is past the end of input, print through the last line",
        note="`head -n 100 | tail -n 93` on 10 lines is the whole file. The ticket "
             "names this edge and fixes its answer.",
    ),
    "826b4b7126b5167d": dict(
        task="Q46", cls="implied",
        fails="range 5..3",
        case="printf 'l1..l10' | bash solution.sh 5 3",
        expected="nothing", actual="line 5",
        quote=None,
        note='`sed -n "5,3p"` prints the single line at the start address. The '
             "ticket names START past the end of INPUT, not START past END; the "
             "reference solution guards it with a comment saying exactly that.",
    ),
    "666fdcaa71b4080d": dict(
        task="Q49", cls="mechanical",
        fails="the whole script (does not terminate)",
        case="printf '  hi  \\n' | bash solution.sh",
        expected="hi", actual="never returns",
        quote=None,
        note="`s=\"${s#[[:space]]}\"` — the character class is misspelled "
             "(`[[:space]]`, not `[[:space:]]`), so the parameter expansion strips "
             "nothing while the `[[ =~ ]]` guard keeps matching. Measured: the "
             "regex matches a leading space and the expansion returns the string "
             "unchanged, so the while loop is infinite.",
    ),
    "79abd449e5eaa69c": dict(
        task="Q49", cls="implied",
        fails="output line structure",
        case="printf '  hi  \\n' | bash solution.sh",
        expected="hi\\n", actual="hi (no trailing newline)",
        quote=None,
        note="`printf '%s'` replaces `echo`, dropping the newline `normalize` used "
             "to emit; the sed also carries a literal \\xEF\\xBB\\xBF that sed does "
             "not interpret. The ticket asks about whitespace, not line structure.",
    ),
    "968ea7fde157d0df": dict(
        task="Q51", cls="signalled",
        fails="test_whitespace_tolerated",
        case='parse_duration("1h 30m")',
        expected="5400", actual="ValueError: invalid duration",
        quote="Make it robust for the kinds of strings people actually type.",
        note=r"the validating regex is `(\d+\s*[hms])+`: the `\s*` sits between the "
             "number and the unit, so a space BETWEEN tokens is rejected. The agent "
             "thought about whitespace and put it in the wrong place.",
    ),
    "ba11c73639fe9d4d": dict(
        task="Q51", cls="signalled",
        fails="test_whitespace_tolerated",
        case='parse_duration("1h 30m")',
        expected="5400", actual="ValueError: invalid duration string",
        quote="Make it robust for the kinds of strings people actually type.",
        note=r"same defect via `^\s*(?:(\d+)\s*([hms]))+$`.",
    ),
    "fc24feae1327d477": dict(
        task="Q51", cls="signalled",
        fails="test_whitespace_tolerated",
        case='parse_duration("1h 30m")',
        expected="5400", actual="ValueError: Invalid duration string",
        quote="Make it robust for the kinds of strings people actually type.",
        note=r"same defect via `re.fullmatch(r'(?:(\d+)\s*([hms]))+', s)`.",
    ),
    "04b8a23c59c50fb2": dict(
        task="Q52", cls="stated",
        fails="capacity_zero_never_panics",
        case="RingBuffer::new(0); r.push(1)",
        expected="len 0, to_vec []", actual="panics (% by zero)",
        quote="and for any capacity",
        note="`% self.capacity` with capacity 0.",
    ),
    "27cd7053d844146c": dict(
        task="Q52", cls="stated",
        fails="capacity_zero_never_panics",
        case="RingBuffer::new(0); r.push(1)",
        expected="len 0, to_vec []", actual="panics (% by zero)",
        quote="and for any capacity",
        note="the agent also wrote ELEVEN tests of its own, all green, covering "
             "capacity 1, multiple wraps and overwrite order — and none of them "
             "capacity 0.",
    ),
    "28345f8d03bfa560": dict(
        task="Q52", cls="stated",
        fails="capacity_zero_never_panics",
        case="RingBuffer::new(0); r.push(1)",
        expected="len 0, to_vec []", actual="panics (remove(0) on an empty Vec)",
        quote="and for any capacity",
        note="a different mechanism for the same case: len()==capacity==0 takes "
             "the overwrite branch.",
    ),
    "c49cab1db5cbc2a7": dict(
        task="Q52", cls="stated",
        fails="capacity_zero_never_panics",
        case="RingBuffer::new(0); r.push(1)",
        expected="len 0, to_vec []", actual="panics (% by zero)",
        quote="and for any capacity",
        note="same as 27cd70's mechanism.",
    ),
    "75f09792c29b38b2": dict(
        task="Q53", cls="undecided",
        fails="empty input",
        case='parseCsv("")',
        expected="[]", actual='[[""]]',
        quote=None,
        note="the ticket says a trailing newline must not produce an extra empty "
             "row and says nothing about empty input. The agent wrote its own probe "
             "file `_quick_test.mjs` containing the line `// Empty input -> one "
             "empty row (standard CSV behavior)` — it saw the ambiguity, decided it, "
             "and decided against the hidden test.",
    ),
    "9d3a55a1fc3dba31": dict(
        task="Q56", cls="stated",
        fails="shorter_is_zero_padded",
        case='compare_versions("1.2.0", "1.2")',
        expected="Equal", actual="Greater",
        quote="Versions with different numbers of components compare as if the "
              "shorter one is padded with trailing zeros",
        note="`(Some(_), None) => return Ordering::Greater` — the padding rule is "
             "stated in the ticket and in the doc comment above the function.",
    ),
}

ORDER = ["stated", "signalled", "implied", "undecided", "mechanical"]


def main():
    pop = {a["content_sha"]: a for a in C.population() if a["truth"] == "FAIL"}
    missing = set(pop) - set(ROWS)
    extra = set(ROWS) - set(pop)
    assert not missing, f"unclassified trees: {sorted(missing)}"
    assert not extra, f"rows for trees that are not in the population: {sorted(extra)}"

    # A classification whose evidence is a quotation is worth nothing until the
    # quotation is checked against the ticket the agent was actually given.
    for sha, row in ROWS.items():
        assert row["task"] == pop[sha]["task"], sha
        if row["quote"]:
            t = C.ticket(row["task"])
            assert row["quote"] in t, f"{sha} {row['task']}: quote not in ticket"
        else:
            assert row["cls"] in ("implied", "undecided", "mechanical"), sha

    trees = collections.Counter(r["cls"] for r in ROWS.values())
    cells = collections.Counter()
    langs = collections.defaultdict(collections.Counter)
    for sha, row in ROWS.items():
        cells[row["cls"]] += pop[sha]["n_cells"]
        langs[row["cls"]][pop[sha]["lang"]] += pop[sha]["n_cells"]

    print(f"{'class':<11} {'trees':>6} {'cells':>6}   languages")
    for c in ORDER:
        langstr = ", ".join(f"{k} {v}" for k, v in sorted(langs[c].items()))
        print(f"{c:<11} {trees[c]:>6} {cells[c]:>6}   {langstr}")
    print(f"{'TOTAL':<11} {sum(trees.values()):>6} {sum(cells.values()):>6}")

    out = []
    for sha, row in sorted(ROWS.items(), key=lambda kv: (kv[1]["task"], kv[0])):
        out.append(dict(row, sha=sha, lang=pop[sha]["lang"],
                        n_cells=pop[sha]["n_cells"], uids=pop[sha]["uids"]))
    (HERE / "taxonomy-results.json").write_text(
        json.dumps({"rows": out,
                    "trees": dict(trees), "cells": dict(cells)}, indent=1),
        encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
