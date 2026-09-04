# crm

Imports the partner feed and reports the state of the store.

```
python run.py
python -m pytest -q
```

⚠ The test suite feeds already-folded email addresses through the importer, so
nothing in it exercises the spelling the partner actually sends. `fold_email` is
covered directly, and `link.check` is covered on stores that are already clean —
nothing tests the branch that raises.
