"""The read-only guard.

`writable(project)` is the question every write path is supposed to ask before
it touches anything. It is one function so that the definition of *archived*
lives in one place — the state list has grown once already and will again.
"""

from . import model

WRITABLE_STATES = (model.STATE_ACTIVE,)


class ReadOnly(Exception):
    pass


def writable(project):
    return project.state in WRITABLE_STATES


def assert_writable(project):
    if not writable(project):
        raise ReadOnly("{} is {}".format(project.id, project.state))
