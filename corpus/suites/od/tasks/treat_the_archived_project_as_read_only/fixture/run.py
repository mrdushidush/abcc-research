"""Replay a batch of write operations against the workspace.

    python run.py

The line shapes are read by the compliance export. They are a contract.
"""

import sys

from workspace import editor, importer, model, scheduler, webhook

DATA = "data/projects.json"

PATHS = (
    ("editor", editor.apply),
    ("importer", importer.apply),
    ("scheduler", scheduler.apply),
    ("webhook", webhook.apply),
)


def main(argv):
    raw = model.load(DATA)
    index = model.index(raw["projects"])

    print("WRITE AUDIT")
    print("projects: {}".format(len(index)))
    for name, apply in PATHS:
        print("{}_writes: {}".format(name, len(apply(index, raw[name]))))

    archived = sum(
        project.revision
        for project in index.values()
        if project.state == model.STATE_ARCHIVED
    )
    print("archived_touched: {}".format(archived))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
