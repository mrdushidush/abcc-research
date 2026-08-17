"""Presentation helpers for the console.

Nothing here decides anything; it only chooses labels and colours. Included
because it is a status consumer and a reader tracing "who branches on status"
should find it — and then notice that it is NOT one of the ones that matters.
"""

from . import status as st

LABELS = {
    st.QUEUED: "Queued",
    st.RUNNING: "Running",
    st.DONE: "Done",
    st.FAILED: "Failed",
    st.CANCELLED: "Cancelled",
}

COLOURS = {
    st.QUEUED: "slate",
    st.RUNNING: "amber",
    st.DONE: "green",
    st.FAILED: "red",
    st.CANCELLED: "grey",
}

GLYPHS = {
    st.QUEUED: "·",
    st.RUNNING: ">",
    st.DONE: "+",
    st.FAILED: "x",
    st.CANCELLED: "-",
}


def label_for(status):
    return LABELS.get(st.normalize(status), "Unknown")


def colour_for(status):
    return COLOURS.get(st.normalize(status), "grey")


def glyph_for(status):
    return GLYPHS.get(st.normalize(status), "?")


def badge(job):
    return "%s %s" % (glyph_for(job.status), label_for(job.status))


def legend():
    return "  ".join("%s %s" % (GLYPHS[s], LABELS[s]) for s in st.ALL)
