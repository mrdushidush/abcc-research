# till

Totals yesterday's orders and reconciles them against the payment provider.

```
python run.py
python -m pytest -q
```

⚠ Every amount in the test suite is a two-decimal currency. `MINOR_UNITS` is
asserted as a table and `minor_units()` is asserted directly; nothing joins them
to a conversion.
