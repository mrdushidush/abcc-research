"""Unit tests for the job tracker.

Run with:  python3 -m unittest discover -s tests

Every module is covered in isolation, and the status vocabulary itself is
covered thoroughly — `cancelled` is in `ALL`, in `TERMINAL`, and reachable in
`TRANSITIONS`, and there are tests for all three.

What is NOT covered: no test asserts what any CONSUMER of the status does with
`cancelled`. There is no test that a cancelled job is unbilled, uncounted as a
breach, or not retried. So the vocabulary is well tested, four consumers
disagree with it, and the suite is green.
"""

import unittest

from jobs import charges, dashboard, model, notify, queue, retry, sla, status as st, validate


def job(**kw):
    base = dict(
        job_id="J-X",
        customer="acme",
        kind="render",
        status=st.DONE,
        queued_at=0,
        started_at=10,
        ended_at=100,
        cpu_seconds=50,
        sla_seconds=3600,
        attempts=1,
    )
    base.update(kw)
    return model.Job(**base)


class TestStatusVocabulary(unittest.TestCase):
    def test_cancelled_is_a_known_status(self):
        self.assertIn(st.CANCELLED, st.ALL)
        self.assertTrue(st.is_known("cancelled"))

    def test_cancelled_is_terminal(self):
        self.assertTrue(st.is_terminal(st.CANCELLED))
        self.assertFalse(st.is_active(st.CANCELLED))

    def test_cancelled_is_reachable_from_active_only(self):
        self.assertTrue(st.can_transition(st.QUEUED, st.CANCELLED))
        self.assertTrue(st.can_transition(st.RUNNING, st.CANCELLED))
        self.assertFalse(st.can_transition(st.DONE, st.CANCELLED))
        self.assertFalse(st.can_transition(st.FAILED, st.CANCELLED))

    def test_normalize(self):
        self.assertEqual(st.normalize(" CANCELLED "), "cancelled")
        self.assertEqual(st.normalize(None), "")


class TestQueue(unittest.TestCase):
    def test_cancel_sets_ended_at(self):
        j = job(status=st.RUNNING, ended_at=None)
        queue.cancel(j, 500)
        self.assertEqual(j.status, st.CANCELLED)
        self.assertEqual(j.ended_at, 500)

    def test_cannot_cancel_a_finished_job(self):
        j = job(status=st.DONE)
        with self.assertRaises(queue.IllegalTransition):
            queue.cancel(j, 500)

    def test_requeue_counts_an_attempt(self):
        j = job(status=st.FAILED, attempts=1)
        queue.requeue(j, 500)
        self.assertEqual(j.status, st.QUEUED)
        self.assertEqual(j.attempts, 2)


class TestModel(unittest.TestCase):
    def test_duration_and_waited(self):
        j = job(queued_at=0, started_at=10, ended_at=100)
        self.assertEqual(j.duration, 90)
        self.assertEqual(j.waited, 10)

    def test_never_started_has_no_duration(self):
        j = job(started_at=None, ended_at=None, status=st.QUEUED)
        self.assertIsNone(j.duration)


class TestSla(unittest.TestCase):
    def test_no_sla_cannot_breach(self):
        self.assertFalse(sla.is_breached(job(sla_seconds=None), 999_999))

    def test_late_done_job_breaches(self):
        self.assertTrue(sla.is_breached(job(ended_at=99_999, sla_seconds=60), 100_000))

    def test_running_job_measured_against_now(self):
        j = job(status=st.RUNNING, ended_at=None, sla_seconds=60)
        self.assertTrue(sla.is_breached(j, 100_000))


class TestCharges(unittest.TestCase):
    def test_failed_is_not_charged(self):
        self.assertFalse(charges.is_chargeable(job(status=st.FAILED)))

    def test_zero_cpu_is_not_charged(self):
        self.assertFalse(charges.is_chargeable(job(cpu_seconds=0)))

    def test_rate_per_kind(self):
        self.assertEqual(charges.rate_for("train"), 2.10)
        self.assertEqual(charges.rate_for("nonsense"), charges.DEFAULT_RATE)


class TestRetry(unittest.TestCase):
    def test_done_is_not_retried(self):
        self.assertFalse(retry.should_retry(job(status=st.DONE)))

    def test_attempt_cap(self):
        self.assertFalse(retry.should_retry(job(status=st.FAILED, attempts=3)))

    def test_non_retryable_kind(self):
        self.assertFalse(retry.should_retry(job(status=st.FAILED, kind="train")))

    def test_backoff_is_capped(self):
        self.assertLessEqual(retry.backoff_seconds(job(attempts=99)), 300)


class TestDashboardAndNotify(unittest.TestCase):
    def test_dashboard_knows_cancelled(self):
        self.assertEqual(dashboard.label_for(st.CANCELLED), "Cancelled")
        self.assertEqual(dashboard.colour_for(st.CANCELLED), "grey")

    def test_notify_has_a_cancellation_message(self):
        msg = notify.message_for(job(status=st.CANCELLED))
        self.assertIsNotNone(msg)
        self.assertIn("cancelled", msg)

    def test_active_statuses_are_silent(self):
        self.assertIsNone(notify.message_for(job(status=st.RUNNING)))


class TestValidate(unittest.TestCase):
    def test_terminal_needs_ended_at(self):
        with self.assertRaises(validate.RecordError):
            validate.check(
                {
                    "job_id": "J-1",
                    "customer": "a",
                    "kind": "render",
                    "status": "cancelled",
                    "queued_at": 0,
                }
            )

    def test_unknown_status_rejected(self):
        with self.assertRaises(validate.RecordError):
            validate.check(
                {
                    "job_id": "J-1",
                    "customer": "a",
                    "kind": "render",
                    "status": "exploded",
                    "queued_at": 0,
                    "ended_at": 1,
                }
            )


if __name__ == "__main__":
    unittest.main()
