import sys
sys.path.insert(0, sys.argv[1])
try:
    from sql_inject import get_user
    r = get_user(None, "admin' OR 1=1 --")
    assert isinstance(r, dict)
    q = r.get('query', '')
    assert "'" not in q or '?' in q or ':' in q or '%s' in q
    print("RESULT: PASS donor assertions held")
except Exception as e:
    print(f"RESULT: FAIL {type(e).__name__}: {e}")
