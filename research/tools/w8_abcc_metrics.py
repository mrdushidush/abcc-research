"""The abcc drive's metrics post-pass: one row per cell, from each cell's own abcc log.

    python research/tools/w8_abcc_metrics.py <run-dir>... [--tsv out.tsv]

The abcc drive leaves the tool- and token-level metrics as `not_applicable` in cells.jsonl and
names the cell's own abcc log in `abcc.json` (harness/crates/w8-run/src/abcc.rs). This reads that
log, read-only, and joins it to the cell's verdict. The H1 table (abcc_attempts.py) is the
template; the query shape is the same: attempt rows, then events keyed by `attempt`, never by
`task` (tool events carry a null task).

The R suite's verifier names four parts in its RESULT line (behaviour/others/fmt/clippy); they
are split into columns so "right fix, lint wrong" is readable without re-running anything.
"""
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

EDITORS = ("edit_file", "write_file", "apply_patch")
PARTS = ("behaviour", "others", "fmt", "clippy")
COLUMNS = ["suite", "task", "status", *PARTS, "abcc_ending", "attempts", "model_calls",
           "length_finishes", "tool_calls", "editing_calls", "read_file_calls", "read_bytes",
           "peak_prompt_tokens", "prompt_tokens", "completion_tokens", "wall_s", "run"]


def cell_row(run: Path, cell: dict) -> dict:
    row = {c: "" for c in COLUMNS}
    row.update(suite=cell["suite"], task=cell["task"], status=cell["status"], run=run.name)
    msg = (cell.get("verifier") or {}).get("message") or ""
    for part in PARTS:
        m = re.search(rf"\b{part}=(\w+)", msg)
        row[part] = m.group(1) if m else ""
    wall = (cell.get("metrics") or {}).get("wall_clock_s") or {}
    row["wall_s"] = f"{wall['measured']:.0f}" if "measured" in wall else ""

    side_path = run / "cells" / f"{cell['task']}__{cell['variant']}" / "abcc.json"
    if not side_path.is_file():
        row["abcc_ending"] = "no abcc.json"
        return row
    side = json.loads(side_path.read_text(encoding="utf-8"))
    log = side.get("log")
    if not log or not Path(log).is_file():
        row["abcc_ending"] = "no log"
        return row
    con = sqlite3.connect(f"file:{Path(log).as_posix()}?mode=ro", uri=True)
    task = side["task"].lstrip("t")
    attempts = con.execute("select id, outcome from attempt where task=? order by id", (task,)).fetchall()
    row["attempts"] = len(attempts)
    tools, applied = Counter(), Counter()
    read_bytes = calls = lengths = peak = prompt = completion = 0
    endings = []
    for a, outcome in attempts:
        for kind, body in con.execute("select kind, body from event where attempt=? order by seq", (a,)):
            b = json.loads(body)
            if kind == "tool_call_started":
                tools[b["tool"]] += 1
            elif kind == "tool_call_ended":
                if b["tool"] in EDITORS and not b.get("unmeasured"):
                    applied[b["tool"]] += 1
                if b["tool"] == "read_file":
                    read_bytes += len((b.get("output") or "").encode("utf-8"))
            elif kind == "model_call_ended":
                calls += 1
                usage = b.get("usage") or {}
                p = usage.get("prompt_tokens") or 0
                peak = max(peak, p)
                prompt += p
                completion += usage.get("completion_tokens") or 0
                if (b.get("finish") or {}).get("finish") == "length":
                    lengths += 1
        o = json.loads(outcome) if outcome else {"outcome": "running"}
        why = o.get("why")
        endings.append(o["outcome"] + ("/" + why["why"] if isinstance(why, dict) and "why" in why else ""))
    row.update(
        abcc_ending=" ".join(endings) or "no attempt",
        model_calls=calls,
        length_finishes=lengths,
        tool_calls=sum(tools.values()),
        editing_calls=", ".join(f"{t} {tools[t]} ({applied[t]} ok)" for t in EDITORS if tools[t]) or "0",
        read_file_calls=tools["read_file"],
        read_bytes=read_bytes,
        peak_prompt_tokens=peak,
        prompt_tokens=prompt,
        completion_tokens=completion,
    )
    return row


def main(argv: list[str]) -> None:
    tsv = None
    if "--tsv" in argv:
        i = argv.index("--tsv")
        tsv = Path(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    rows = []
    for run in map(Path, argv):
        for line in (run / "cells.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(cell_row(run, json.loads(line)))
    shown = [c for c in COLUMNS if c != "run"]
    print("| " + " | ".join(shown) + " |")
    print("|" + "---|" * len(shown))
    for r in rows:
        print("| " + " | ".join(f"{r[c]:,}" if isinstance(r[c], int) else str(r[c]) for c in shown) + " |")
    if tsv:
        with tsv.open("w", encoding="utf-8", newline="\n") as f:
            f.write("\t".join(COLUMNS) + "\n")
            for r in rows:
                f.write("\t".join(str(r[c]) for c in COLUMNS) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
