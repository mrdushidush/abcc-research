# Trials

A trial is fourteen days. `accounts.trial_ends_on` holds the last day it runs,
inclusive — an account whose `trial_ends_on` is today is still on trial today.

**A trial that has ended is not an entitled account.** It keeps its data and it
can be converted at any time, but until it converts it is treated exactly like a
cancelled account by everything that asks whether an account is entitled:
features, the digest, the seat count and the support rota.

`entitlement.calendar.lapsed(ends_on, as_of)` is the comparison. It exists so
that nobody writes the `<` by hand and gets the inclusive last day wrong.

## Why `ENTITLED_STATUSES` is not enough

`model.ENTITLED_STATUSES` was written when `trial` was a status you were in or
were not, before `trial_ends_on` existed. It answers *what kind of account is
this*, which is not the same question as *is this account entitled today*, and
a caller that only asks the first one cannot see an expiry.
