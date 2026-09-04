# The ledger file

The downstream reader replays this file top to bottom and applies each record to
the balance the previous one left. **The file's order is the ledger's order.**
There is no sequence column in the output format and no way for the reader to
re-order what it is given.

`ledgerout.ordering.sort_key` decides that order. `seq` is a number and it has
to sort as one: as text, `"10"` comes before `"9"`, which puts the tenth record
second and the ninth last.

## The pre-flight

`ledgerout.sequence.check` is what the reader runs before it will accept a file.
It walks the records **in the order they will be written** and refuses a file
whose sequence numbers do not ascend by one. It is not a validation of the
source data — the source is fine, the source system sends the records in
whatever order it likes — it is a validation of what we are about to hand over.
