# ledgerout

Builds the ordered ledger file and pre-flights it.

```
python run.py
python -m pytest -q
```

⚠ Every batch in the test suite has fewer than ten records, so the sequence
numbers are single digits and text order and numeric order are the same thing.
