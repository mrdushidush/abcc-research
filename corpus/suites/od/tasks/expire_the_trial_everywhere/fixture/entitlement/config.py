"""Run configuration.

`AS_OF` is pinned rather than read from the clock so the nightly report is
reproducible and so a failing report can be re-run tomorrow and still fail.
"""

AS_OF = "2026-09-01"

DATA = "data/accounts.json"
