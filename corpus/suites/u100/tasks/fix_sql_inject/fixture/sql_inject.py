def get_user(db, username):
    query = f"SELECT * FROM users WHERE name = '{username}'"
    return db.execute(query)
