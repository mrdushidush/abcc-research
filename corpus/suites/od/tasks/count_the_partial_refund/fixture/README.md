# statement

Renders one customer statement four ways and reports each total.

```
python run.py
python -m pytest -q
```

⚠ Each renderer computes the total itself; they were written at different times
and the arithmetic was copied between them. The test suite covers charges and
full refunds.
