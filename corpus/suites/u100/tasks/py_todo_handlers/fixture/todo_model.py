class TodoStore:
    def __init__(self):
        self._todos = {}
        self._next_id = 1

    def create(self, title):
        todo = {'id': self._next_id, 'title': title, 'done': False}
        self._todos[self._next_id] = todo
        self._next_id += 1
        return todo

    def get(self, todo_id):
        return self._todos.get(todo_id)

    def list_all(self):
        return list(self._todos.values())

    def delete(self, todo_id):
        if todo_id in self._todos:
            del self._todos[todo_id]
            return True
        return False

    def update(self, todo_id, title=None, done=None):
        todo = self._todos.get(todo_id)
        if not todo:
            return None
        if title is not None:
            todo['title'] = title
        if done is not None:
            todo['done'] = done
        return todo
