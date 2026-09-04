# workspace

Replays a batch of write operations and reports what was written.

```
python run.py
python -m pytest -q
```

⚠ Every project the test suite builds is active, except in the two tests that
exercise `guard` itself. No test drives a write path against an archived
project.
