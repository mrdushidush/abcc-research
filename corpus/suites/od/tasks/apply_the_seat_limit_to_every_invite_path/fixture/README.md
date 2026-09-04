# invites

Replays the pending invite queue against a team.

```
python run.py
python -m pytest -q
```

⚠ Every team the test suite builds has more free seats than the test uses, so no
test in it ever crosses the limit. `limits` itself is covered directly.
