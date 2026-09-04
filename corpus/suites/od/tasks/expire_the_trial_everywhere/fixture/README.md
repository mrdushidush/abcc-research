# entitlement

The nightly entitlement report.

```
python run.py
```

`data/accounts.json` is a trimmed copy of a production export. `AS_OF` in
`entitlement/config.py` is pinned so the report is reproducible.

## Tests

```
python -m pytest -q
```

⚠ The suite is happy-path and it passes today. It covers active, cancelled and
suspended accounts and the arithmetic each consumer does; there is no test that
runs an account whose trial has ended through the four consumers, which is why
`docs/trials.md` is the only place the rule is written down.
