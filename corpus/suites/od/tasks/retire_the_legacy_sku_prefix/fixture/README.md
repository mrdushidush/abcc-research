# catalog

Nightly reconciliation of yesterday's traffic against the product index.

```
python run.py
python -m pytest -q
```

⚠ The test suite uses canonical SKUs throughout — the ones the index is keyed
on — so every lookup in it succeeds without any folding. `normalize` is tested,
thoroughly, in isolation.
