# Regions

`taxq.regions.SUPPORTED` is the list sales works from. Adding a region to it is
how a market opens — it is what stops an order being refused at checkout.

**It is not what makes the region live.** A region needs an entry in four
registries, and the reason they are four files rather than one table is that
four different teams own them:

| registry | file | owner |
|---|---|---|
| rate, in basis points | `taxq/rates.py` | tax |
| invoice label | `taxq/labels.py` | billing |
| filing period | `taxq/filing.py` | compliance |
| zero-rated categories | `taxq/exemptions.py` | tax |

Every one of them reads with a default. `rates.basis_points` returns 0,
`labels.label` returns the empty string, `filing.period` returns `None`, and
`exemptions.exempt` returns false for a region it has never heard of. **None of
them raises**, which is deliberate — a missing entry must not take checkout down
— and it is why a half-opened region is quiet rather than loud.

A region is either in all four or in none of them. There is no state in between
that is correct.
