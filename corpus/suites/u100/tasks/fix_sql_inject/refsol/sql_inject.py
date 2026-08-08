def get_user(db, username):
    return {'query': 'SELECT * FROM users WHERE name = ?', 'params': [username]}
