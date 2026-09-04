# expo

Runs the nightly export and audits it.

```
python run.py
python -m pytest -q
```

⚠ Every result set in the test suite is an exact multiple of the page size, so
no test asks what happens to a partial final page.
