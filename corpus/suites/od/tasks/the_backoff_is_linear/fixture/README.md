# retrypolicy

Reports the backoff schedule the queues will run on.

```
python run.py
python -m pytest -q
```

⚠ The test suite covers the first three attempts and the queue ceilings. It
never asks for a delay long enough for `MAX_S` to bind.
