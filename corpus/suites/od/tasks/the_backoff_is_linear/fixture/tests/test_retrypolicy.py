"""Visible tests.

⚠ Nothing here asks for an attempt late enough that `MAX_S` would bind — the
largest delay any test looks at is the third attempt. `MAX_S` is asserted as a
constant and is right; nothing reads it.
"""

from retrypolicy import backoff, queues


def test_max_is_a_minute():
    assert backoff.MAX_S == 60
    assert backoff.BASE_S == 1


def test_first_attempt_waits_the_base():
    assert backoff.delay(1) == 1


def test_schedule_starts_at_the_base():
    assert backoff.schedule(3)[0] == 1
    assert len(backoff.schedule(3)) == 3


def test_total_wait_sums_the_schedule():
    assert backoff.total_wait(3) == sum(backoff.schedule(3))


def test_queue_ceilings():
    assert queues.ceiling("sync") == 8
    assert queues.ceiling("email") == 3
    assert queues.ceiling("unknown") == 5
