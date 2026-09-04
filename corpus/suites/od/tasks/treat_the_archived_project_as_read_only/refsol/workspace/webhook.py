"""Inbound webhooks from the build system."""

from . import guard


def apply(index, ops):
    written = []
    for op in ops:
        project = index[op["project"]]
        if not guard.writable(project):
            continue
        project.write(op["field"])
        written.append(op)
    return written
