# Archiving

Archiving a project is how a customer stops it without losing it. The contract
we make when we offer that button is one sentence:

> An archived project does not change again.

It stays readable, it stays exportable, and its revision counter stops moving.
The compliance export is built on that: a revision recorded after the archive
date is a hole in the audit trail, not a late edit.

`workspace.guard.writable(project)` is the question. It is a function and not a
comparison against `"active"` because the state list has grown once already —
`archived` was added after `active` and `draft` — and every writer that spelled
the comparison out itself had to be found again.
