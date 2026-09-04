# bootcfg

Boots the worker configuration and reports it.

```
python run.py
python -m pytest -q
```

⚠ The overrides in the test suite are written as literals, so they arrive as
the type they replace. Nothing in the suite passes an override through
`env.load`, which is where they arrive as strings.
