# Job status lifecycle

## The statuses

| Status | Terminal? | Meaning |
|---|---|---|
| `queued` | no | accepted, not started |
| `running` | no | a worker holds it |
| `done` | yes | finished successfully |
| `failed` | yes | finished unsuccessfully |
| `cancelled` | **yes** | an operator stopped it before it finished |

## `cancelled`, added in 4.2

The console gained a cancel button and `cancelled` came with it. It is reachable
from `queued` or `running` and from nowhere else: a job that has already reached
`done` or `failed` cannot be cancelled.

**Its semantics, stated once, here, because every module that branches on status
has to agree about them:**

1. **It is TERMINAL.** Nothing is waiting on a cancelled job and nothing should
   treat it as still in flight.
2. **It is NOT an SLA breach.** The clock stops at the moment of cancellation.
   A job the operator deliberately stopped has not missed its deadline — the
   deadline no longer applies to it.
3. **It is NOT chargeable.** We do not bill for work the customer told us to
   stop. Partial compute is absorbed; that was the commercial decision when the
   button shipped.
4. **It MUST NOT be retried.** A cancellation is an instruction, and requeueing
   a cancelled job overrides an operator. This is the one in the list with a
   support ticket attached.
5. **It gets its OWN bucket in every count.** Folding it into `failed` overstates
   the failure rate, and folding it into `other` hides it. The rollout was
   justified on cancellation volume, so that number has to be visible.

## The thing to check when touching this

> `cancelled` was added to `status.py` and to `TRANSITIONS`. **The constant
> existing does not mean every consumer handles it.** Grep for the other
> statuses — anywhere that names `DONE` or `FAILED` in a condition is a place
> that may have been written when there were only four statuses, and a default
> branch will swallow the fifth without raising anything.

## Requeueing

`failed` → `queued` is legal and is how a retry works. That is the only
transition out of a terminal status, and it exists because a failure can be
transient. A cancellation cannot be transient.
