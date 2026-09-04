"""The post-export audit.

Every row that went in has to come out. The check compares what the export was
ASKED for against what reached the sink -- if it compared the sink against
itself it would pass on an empty export.
"""


class RowCountMismatch(Exception):
    pass


def check(source_rows, sink):
    written = sink.rows()
    if len(written) != len(source_rows):
        raise RowCountMismatch(
            "{} rows in, {} rows out -- {} missing".format(
                len(source_rows), len(written), len(source_rows) - len(written)
            )
        )
    return len(written)
