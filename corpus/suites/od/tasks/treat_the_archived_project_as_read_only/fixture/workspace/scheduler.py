"""The recurring-job scheduler, which stamps the next run time."""


def apply(index, ops):
    written = []
    for op in ops:
        project = index[op["project"]]
        project.write(op["field"])
        written.append(op)
    return written
