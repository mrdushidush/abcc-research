# worksched

Computes SLA and payment due dates for the open book.

```
python run.py
python -m pytest -q
```

⚠ The test suite covers weekend skipping and the shape of the holiday table.
`add_business_days` is exercised on ranges that contain no holiday.
