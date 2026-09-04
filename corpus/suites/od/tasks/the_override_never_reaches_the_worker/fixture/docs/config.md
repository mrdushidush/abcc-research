# Configuration

`bootcfg.settings.DEFAULTS` is what the code ships with: one worker, small
batches, a short timeout. They are what a laptop should run. **Every deployed
environment overrides all three**, and `data/declared.json` is what ops declared
for this one.

⚠ **Every value in the environment file is a string.** It is written by the
deploy tool, which has no types, and that is not going to change. An override
that arrives as `"8"` is the number 8 — the default it replaces says which type
that is.

## The capacity floor

`bootcfg.capacity` refuses to start a worker that cannot move a thousand rows in
flight, because the failure mode is a backlog nobody notices for a day.

It checks the **running** configuration. Checking the declared one would ask
whether ops filled in a form correctly, which nothing here doubts, and would
pass on a process running any configuration at all.
