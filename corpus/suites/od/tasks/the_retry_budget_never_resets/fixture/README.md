# retryd

Replays a day of failures through the retry scheduler.

```
python run.py
python -m pytest -q
```

⚠ Every failure the test suite builds falls inside a single hour, so no test
asks the budget what happens when the clock moves into the next window.
