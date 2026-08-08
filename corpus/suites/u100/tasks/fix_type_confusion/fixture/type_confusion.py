def is_admin(user):
    return user.get('role') == True or user.get('role') == 'admin'
