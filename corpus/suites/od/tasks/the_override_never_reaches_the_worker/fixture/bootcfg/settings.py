"""The shipped defaults.

Deliberately timid: one worker, small batches, a short timeout. They are what a
laptop should run, and every deployed environment overrides them.
"""

DEFAULTS = {
    "concurrency": 1,
    "batch_size": 100,
    "timeout_s": 30,
}
