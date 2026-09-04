"""The CSV importer."""


def apply(index, ops):
    written = []
    for op in ops:
        project = index[op["project"]]
        project.write(op["field"])
        written.append(op)
    return written
