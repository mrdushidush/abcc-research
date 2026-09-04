# observe

Replays a captured event batch through every sink and reports what leaked.

```
python run.py
python -m pytest -q
```

⚠ The test suite renders events whose message and context hold no secret, plus
a direct test of the scrubber and of the canary. No test renders a
secret-bearing event through a sink and audits the result.
