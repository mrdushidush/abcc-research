# billing

Prices a batch of orders into invoices, prints receipts, books the ledger, and
audits the result.

```
python3 run.py data/orders.json
```

## Stages

| Stage | Module | In → Out |
|---|---|---|
| validate | `billing/validate.py` | orders → orders (or `OrderError`) |
| catalogue | `billing/catalog.py` | SKU → `Entry` (unit prices, 4 dp) |
| discounts | `billing/discounts.py` | customer/category/qty → rate |
| tax | `billing/tax.py` | region → rate |
| pricing | `billing/pricing.py` | items + catalogue + tax → `[Line]` |
| invoice | `billing/invoice.py` | `[Line]` → `Invoice` (lines + total) |
| receipt | `billing/receipt.py` | `Invoice` → text the customer reads |
| ledger | `billing/ledger.py` | `Invoice` → integer-cent entries |
| export | `billing/export.py` | `[Invoice]` → CSV/JSON for finance |
| audit | `billing/audit.py` | `[Invoice]` → findings, no corrections |

`money` and `currency` are not stages. **`money` is the only module permitted to
round** — see `docs/money.md`, which is the important document in this repo.
`currency` converts for display only and its output is never booked.

## The invariant everything else exists to protect

> The per-line amounts a customer reads must add up to the total they are
> charged, and the itemised ledger export must sum to the single-entry export.

`Invoice.reconciles()` is that property. `audit.py` checks it
(`linesum_mismatch`, `export_mismatch`) and `reconcile.py` checks it again at
period close, from three independently computed paths. Nothing corrects it —
these are reports, because an audit that silently fixes its input is an audit
nobody can trust.

## Known issues

- Amounts are floats. `docs/money.md` has the argument and the mitigation;
  moving to `Decimal` is a migration, not a patch, and is tracked but unscheduled.
- `reconcile.close` has never been run against a full month of real volume.
- The unit tests cover each module in isolation. Nothing prices a whole batch
  end to end and asserts the invariant above over real data.
