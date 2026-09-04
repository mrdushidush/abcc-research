# baro

Ingests a batch of barometer readings, calibrates them and alerts.

```
python run.py
python -m pytest -q
```

⚠ The test suite covers `units.to_ckpa` and the alert predicates directly, with
values written in the unit each function expects. Nothing in it runs the ingest
and the calibration back to back.
