# Logging

`observe/` holds every place this process writes to something outside itself:
the console an operator watches, the structured log file, the error tracker and
the metrics socket.

**A live API key must not leave the process.** Not to a file we own, not to a
vendor, not in a metric tag. There is no sink where it is acceptable and no
severity that makes it acceptable — a key in a debug line is a key.

`observe.redact.scrub()` and `scrub_mapping()` are the way to satisfy that.
`observe.audit.leaks()` counts what got through and is deliberately written
against its own pattern, so that a rendered payload is checked rather than the
scrubber being asked whether it agrees with itself.

Keys arrive in message text, in `authorization` context values and in anything
else a caller decided to attach. That is why the scrubber takes text and takes
a mapping: both are places they have actually turned up.
