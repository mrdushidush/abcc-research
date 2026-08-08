#!/usr/bin/env python3
"""Extract the 90 stable ABCC suite tasks with their verifiers, from the donor source.

Reads scripts/ultimate-100-task-test.js at d5528ea. Emits tasks.json.

Why not a regex over the whole file: `validation` is a template literal that spans
lines for the go/ts tasks and contains backticks-adjacent code, so the field has to be
scanned with a real string walker, not matched.

Usage: python extract_tasks.py <path-to-abcc-repo> > /dev/null
"""
import json
import re
import sys
from pathlib import Path

FIELD = re.compile(r"\b(name|section|complexity|category|validationLang|dir|files):\s*")

# JS escape sequences, as a template literal / quoted string resolves them. The walkers
# below capture `\x` pairs verbatim so the closing delimiter is not misread; the value
# still has to be unescaped afterwards or it carries one backslash too many. Getting this
# wrong is silent and one-directional: `py_csv_transform`'s `\\n` reaches python3 -c as a
# literal backslash-n instead of a newline, the CSV parses as one row, and the verifier
# FAILs for a reason that has nothing to do with the artifact.
JS_ESC = {
    "\\": "\\", "`": "`", "$": "$", "'": "'", '"': '"',
    "n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0",
}


def js_unescape(s):
    """Resolve JS string escapes to the value the donor actually passes to the runner."""
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c != "\\" or i + 1 >= len(s):
            out.append(c)
            i += 1
            continue
        nxt = s[i + 1]
        if nxt == "u" and i + 5 < len(s) + 1:
            hexs = s[i + 2 : i + 6]
            if len(hexs) == 4 and all(h in "0123456789abcdefABCDEF" for h in hexs):
                out.append(chr(int(hexs, 16)))
                i += 6
                continue
        if nxt == "x":
            hexs = s[i + 2 : i + 4]
            if len(hexs) == 2 and all(h in "0123456789abcdefABCDEF" for h in hexs):
                out.append(chr(int(hexs, 16)))
                i += 4
                continue
        # Unknown escapes resolve to the escaped character itself, as JS does.
        out.append(JS_ESC.get(nxt, nxt))
        i += 2
    return "".join(out)


def read_template_literal(src, i):
    """src[i] == '`'. Return (value, index_after_closing_backtick)."""
    assert src[i] == "`", src[i - 20 : i + 20]
    i += 1
    out = []
    while i < len(src):
        c = src[i]
        if c == "\\":
            out.append(src[i : i + 2])
            i += 2
            continue
        if c == "`":
            return "".join(out), i + 1
        out.append(c)
        i += 1
    raise ValueError("unterminated template literal")


def read_quoted(src, i):
    q = src[i]
    i += 1
    out = []
    while i < len(src):
        c = src[i]
        if c == "\\":
            out.append(src[i : i + 2])
            i += 2
            continue
        if c == q:
            return "".join(out), i + 1
        out.append(c)
        i += 1
    raise ValueError("unterminated string")


def read_value(src, i):
    """Read a JS value starting at i. Handles strings, template literals, numbers."""
    while src[i] in " \t\n":
        i += 1
    if src[i] == "`":
        val, j = read_template_literal(src, i)
        return js_unescape(val), j
    if src[i] in "\"'":
        val, j = read_quoted(src, i)
        return js_unescape(val), j
    j = i
    while j < len(src) and src[j] not in ",\n}":
        j += 1
    return src[i:j].strip(), j


def extract(js_path):
    src = Path(js_path).read_text(encoding="utf-8")
    tasks = []
    # Task objects are the ones carrying `name:` together with `validation:`.
    for m in re.finditer(r"\bname:\s*'([^']+)'", src):
        name = m.group(1)
        # Scan forward to the next `name:` — that bounds this object.
        nxt = src.find("name:", m.end())
        block = src[m.end() : nxt if nxt != -1 else len(src)]
        vi = block.find("validation:")
        if vi == -1:
            continue
        val, _ = read_value(block, vi + len("validation:"))
        rec = {"name": name, "validation": val}
        for f in ("section", "complexity", "category", "validationLang", "dir", "files"):
            fm = re.search(r"\b" + f + r":\s*", block)
            if fm:
                v, _ = read_value(block, fm.end())
                rec[f] = v
        # The prompt/description is the other field worth carrying.
        dm = re.search(r"\bdescription:\s*", block)
        if dm:
            rec["description"], _ = read_value(block, dm.end())
        tasks.append(rec)
    return tasks


if __name__ == "__main__":
    repo = sys.argv[1] if len(sys.argv) > 1 else r"D:\dev\agent-battle-command-center"
    tasks = extract(Path(repo) / "scripts" / "ultimate-100-task-test.js")
    Path("tasks.json").write_text(json.dumps(tasks, indent=1), encoding="utf-8")
    print(f"extracted {len(tasks)} tasks -> tasks.json", file=sys.stderr)
    import collections

    print(collections.Counter(t.get("category") for t in tasks), file=sys.stderr)
