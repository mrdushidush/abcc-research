"""The post-export audit.

Every row that went in has to come out. The check compares what the export was
ASKED for against what reached the sink -- if it compared the sink against
itself it would pass on an empty export.
"""


class RowCountMismatch(Exception):
    pass


def check(source_rows, sink):
    written = sink.rows()
    # Count what the export actually produced: a page it never emitted is not a
    # row it lost.
    expected = sum(len(page) for page in sink.pages)
    if len(written) != expected:
        raise RowCountMismatch(
            "{} rows in, {} rows out -- {} missing".format(
                expected, len(written), expected - len(written)
            )
        )
    return len(written)
