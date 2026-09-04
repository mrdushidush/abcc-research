"""The recurring-job scheduler, which stamps the next run time."""

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
