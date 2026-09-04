"""Visible tests.

⚠ The projects built here are active, so no write path in this suite is ever
pointed at an archived one. `guard` is covered directly and passes.
"""

import pytest

from workspace import editor, guard, importer, model, scheduler, webhook


def index(*states):
    return {
        "p{}".format(i): model.Project({"id": "p{}".format(i), "name": "n", "state": s})
        for i, s in enumerate(states)
    }


def test_writable_is_true_only_for_active():
    idx = index("active", "archived")
    assert guard.writable(idx["p0"]) is True
    assert guard.writable(idx["p1"]) is False


def test_assert_writable_raises_on_an_archived_project():
    idx = index("archived")
    with pytest.raises(guard.ReadOnly):
        guard.assert_writable(idx["p0"])


def test_editor_writes_to_an_active_project():
    idx = index("active")
    assert editor.apply(idx, [{"project": "p0", "field": "title"}])
    assert idx["p0"].revision == 1


def test_importer_writes_rows():
    idx = index("active")
    assert len(importer.apply(idx, [{"project": "p0", "field": "rows"}])) == 1


def test_scheduler_stamps_the_next_run():
    idx = index("active")
    scheduler.apply(idx, [{"project": "p0", "field": "next_run"}])
    assert idx["p0"].touched == ["next_run"]


def test_webhook_writes_status():
    idx = index("active")
    webhook.apply(idx, [{"project": "p0", "field": "status"}])
    assert idx["p0"].revision == 1
