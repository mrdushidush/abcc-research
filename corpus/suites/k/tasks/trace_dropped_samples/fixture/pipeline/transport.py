"""Reading sample files.

Kept separate from `run.py` so a future streaming source can be dropped in
without touching the pipeline stages.
"""

import json


def read_jsonl(path):
    """Yield one dict per non-blank line. Malformed lines are yielded as the
    sentinel `{"__malformed__": line}` rather than skipped, so that ingest can
    count them against `DROP_MALFORMED` instead of losing them silently."""
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                yield {"__malformed__": line}


def read_all(path):
    return list(read_jsonl(path))


def write_jsonl(path, records):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for rec in records:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
