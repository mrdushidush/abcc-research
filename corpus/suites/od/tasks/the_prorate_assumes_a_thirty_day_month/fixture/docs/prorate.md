# Prorated refunds

A customer who cancels part-way through a month gets back the part they did not
use, of the month they already paid for.

**The denominator is the real length of that real month.** Twenty-eight days in
February 2026, twenty-nine in February 2028, thirty-one in July. A customer paid
for a month, not for thirty days, and the difference is money in both directions:
a thirty-day denominator under-refunds every 31-day month and over-refunds every
February.

`calendar.monthrange(year, month)[1]` is the answer and it is in the standard
library. `subs.prorate.days_in` takes the year as well as the month for exactly
one reason — February is not always the same length.
