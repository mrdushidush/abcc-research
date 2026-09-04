# Minor units

A total in this service is an integer count of the currency's smallest unit,
because that is what the payment provider settles in and what the ledger stores.
Nothing downstream of `till.money` sees a decimal string.

**The number of minor units is not two.** ISO 4217 gives:

| currency | decimals | 1 unit is |
|---|---|---|
| USD, EUR, GBP | 2 | a cent, a penny |
| JPY | **0** | a yen — there is no subdivision |
| KWD | **3** | a fils |

`till.money.MINOR_UNITS` is the table, and `minor_units(currency)` is how to ask.
A conversion that multiplies by 100 regardless is right for two thirds of the
table and a factor of a hundred out on the rest.

## Reconciliation

`till.reconcile` compares our line totals against what the provider says it
took. Both sides are in minor units of the same currency, so the comparison is
integer equality and there is nothing to tune. If they disagree, one of the two
is wrong about what the customer paid.
