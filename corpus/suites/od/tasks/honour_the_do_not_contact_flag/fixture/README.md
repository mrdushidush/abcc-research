# outbound

Tonight's outbound plan.

```
python run.py
```

## Tests

```
python -m pytest -q
```

⚠ The suite covers each channel's own eligibility rule — an SMS needs a phone
number, push needs a token, win-back is lapsed contacts only — and the
suppression helper in isolation. No test builds a suppressed contact and puts it
through a channel.
