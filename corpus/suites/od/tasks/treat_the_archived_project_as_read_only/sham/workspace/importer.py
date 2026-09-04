"""The CSV importer."""


def apply(index, ops):
    written = []
    for op in ops:
        project = index[op["project"]]
        # An archived project must not be imported into.
        if project.state == "archived":
            continue
        project.write(op["field"])
        written.append(op)
    return written
