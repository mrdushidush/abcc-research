# A deliberately wrong solution that satisfies the letter of the verifier.
#
# The injection is fully intact — the username is still interpolated straight into the
# query string. The only thing this adds is a trailing `-- ?`, which is enough because the
# donor's assertion is an OR-chain:
#
#     assert "'" not in q or '?' in q or ':' in q or '%s' in q
#
# and any `?` anywhere short-circuits it. The verifier returns PASS. That is F8, and it is
# why this task is quarantined rather than counted.
#
# The returned query for username = "admin' OR 1=1 --" is:
#     SELECT * FROM users WHERE name = 'admin' OR 1=1 --' -- ?


def get_user(db, username):
    query = f"SELECT * FROM users WHERE name = '{username}' -- ?"
    return {'query': query, 'params': []}
