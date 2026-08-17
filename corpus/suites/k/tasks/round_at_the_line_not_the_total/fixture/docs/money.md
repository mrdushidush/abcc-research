# Money, precision, and where rounding goes

Notes kept because we have had this argument three times and lost a customer to
it once.

## The representation

Amounts are floats in major units. This is not what we would choose today; see
the "why not Decimal" section. Given floats, the mitigation is a single rule:

> **All rounding goes through `billing/money.py`. No other module may round.**

`money.to_cents` rounds half away from zero and returns an int.
`money.quantize` is the same thing returned in major units. `money.sum_amounts`
adds already-quantized amounts **in integer cents**, so summing does not
reintroduce the drift that rounding just removed.

## Catalogue prices carry four decimals, and must

Cable is priced per metre and print per sheet, both in fractions of a penny
(`CBL-CAT6-M` is 0.8725). Rounding a catalogue price to the cent changes what a
1,000-metre order costs by more than a pound. **A unit price is not a chargeable
amount and must not be rounded. A line total is, and must be.**

## Where the rounding has to happen — the rule people get wrong

**Round each LINE, then sum the rounded lines. Do not sum raw lines and round
once at the end.**

The two are not equivalent and the difference is not academic:

- The customer reads the **per-line amounts** on the receipt. Those are
  necessarily shown to the cent.
- If the total is computed from unrounded lines, the printed lines do not add up
  to the printed total. The customer adds them up. They are right and we are
  wrong, and the invoice has to be reissued.
- The **itemised ledger export** books one entry per line, at the printed line
  amount. The **single-entry export** books one entry at the total. If those two
  disagree, the month does not reconcile and somebody spends a day on it.

`billing/audit.py` checks both properties (`linesum_mismatch`,
`export_mismatch`). It reports; it does not correct.

> The failure is **per-invoice and data-dependent**. Rounding at the end happens
> to give the right answer whenever the discarded fractions cancel, which they
> often do — so a batch can look fine, one invoice can be off by a penny, and
> the arithmetic is wrong in every one of them. **Do not conclude from one
> corrected invoice that the batch is fixed.** Run the audit over the whole
> batch.

## Why not Decimal

It is the right answer and it is a migration, not a patch: the ledger, the
exports, the tax engine and two downstream consumers all take floats. Tracked,
not scheduled. Until then, the rule above is what keeps us correct.

## Banker's rounding

Python's built-in `round` rounds half to even, so `round(2.675, 2)` is 2.67.
Finance expects 2.68. This is why `money.to_cents` exists and why calling
`round` on an amount is a defect even when it looks like it works.
