"""Write a measured `[gate]` block into a task.toml, between its markers.

Called by `gate-task.sh WRITE=1`. It replaces everything between the lines
`# GATE BEGIN` and `# GATE END` and refuses a file that does not carry both, so
it can never append a second `[gate]` table or scribble over a hand-written one.

ENCODE FIRST, THEN OPEN — the replacement is built and checked in full before
the file is opened for writing, because `open(path, "w")` truncates before it
writes and that is how a file reaches 0 bytes.
"""

import os
import sys

BEGIN = "# GATE BEGIN"
END = "# GATE END"


def block():
    suite = os.environ["GATE_SUITE"]
    ident = os.environ["GATE_ID"]
    date = os.environ["GATE_DATE"]
    run = "corpus/suites/{}/tasks/{}/verify.sh, host, {}".format(suite, ident, date)
    has_sham = os.environ.get("GATE_HAS_SHAM") == "1"

    def evidence(point, tier, verdict, detail):
        return (
            "\n[[gate.evidence]]\n"
            'point    = {}\n'
            'tier     = "{}"\n'
            'verdict  = "{}"\n'
            'detail   = "{}"\n'
            'verifier = "rewritten"\n'
            'run      = "{}"\n'
        ).format(point, tier, verdict, detail, run)

    out = [
        BEGIN,
        "[gate]",
        'point1 = "sound"',
        'point2 = "sound"',
        'point3 = "{}"'.format("sound" if has_sham else "not_run"),
        "",
        evidence(1, "donor_fixture", "FAIL", os.environ["GATE_P1"]).strip("\n"),
        "",
        evidence(2, "refsol", "PASS", os.environ["GATE_P2"]).strip("\n"),
    ]
    if has_sham:
        out += ["", evidence(3, "sham", "FAIL", os.environ["GATE_P3"]).strip("\n")]
    out.append(END)
    return "\n".join(out) + "\n"


def main(argv):
    path = argv[1]
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    if BEGIN not in text or END not in text:
        sys.stderr.write("{} carries no GATE BEGIN/END markers\n".format(path))
        return 1
    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    new = head + block() + tail.lstrip("\n")
    if new.count(BEGIN) != 1 or new.count(END) != 1:
        sys.stderr.write("refusing: the result would carry the markers twice\n")
        return 1
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(new)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
