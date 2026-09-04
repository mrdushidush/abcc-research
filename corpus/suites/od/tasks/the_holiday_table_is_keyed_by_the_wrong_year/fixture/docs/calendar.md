# Two calendars, and why

`worksched.holidays.TABLE` is the **holiday table**. It is what business-day
arithmetic runs on: SLA due dates, payment terms, anything that counts working
days. HR own it and it is keyed by **calendar** year.

⚠ It was keyed by *fiscal* year until 2025, and a fiscal year starts in the
previous calendar year. The re-key is done; every caller passes a calendar year.

`data/closures.json` is the **office-closure feed**, published by facilities
each November: the days the building is actually shut. `worksched.closures` is
how to read it.

**The two are supposed to agree, and checking one against the other is the only
way to find out that they do not.** That is why `sla.check` reads the closure
feed rather than asking `holidays` — a check written against the same table the
arithmetic uses would only establish that the arithmetic agrees with itself, and
would pass on any table at all.

A due date on a day the office is shut is not a due date. It is not a rounding
problem to be nudged at the point it is noticed: the same arithmetic sets
payment terms, and nothing checks those.
