def process_user(data):
    age = int(data['age'])
    name = data['name']
    return {'name': name, 'age': age}
