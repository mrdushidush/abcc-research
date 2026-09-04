"""Visible tests.

⚠ The events built here carry no secret, so no sink in this suite is ever asked
what it does with one. `redact` and `audit` are both covered directly, which is
what makes the package look safe.
"""

import json

from observe import audit, console, errors, logfile, metrics, redact


def event(level="info", message="sync started", context=None):
    return {
        "ts": "2026-09-01T00:00:00Z",
        "level": level,
        "message": message,
        "context": context if context is not None else {"tenant": "acme"},
    }


def test_scrub_replaces_a_key():
    assert redact.scrub("key sk_live_ABC123 here") == "key [redacted] here"


def test_scrub_mapping_covers_values():
    out = redact.scrub_mapping({"authorization": "Bearer sk_live_ABC123"})
    assert out == {"authorization": "Bearer [redacted]"}


def test_audit_counts_live_keys():
    assert audit.leaks("sk_live_AAA and sk_live_BBB") == 2
    assert audit.leaks("nothing here") == 0


def test_console_renders_level_and_message():
    line = console.render(event())
    assert "INFO" in line and "sync started" in line


def test_logfile_renders_one_json_object():
    parsed = json.loads(logfile.render(event()))
    assert parsed["msg"] == "sync started"
    assert parsed["ctx"] == {"tenant": "acme"}


def test_errors_skips_anything_that_is_not_an_error():
    assert errors.render(event(level="info")) is None
    assert errors.render(event(level="error")).startswith("title: ")


def test_metrics_tags_the_level():
    assert "level:info" in metrics.render(event())
