class Stack:
    def __init__(self):
        self._items = []
    def push(self, item):
        self._items.append(item)
    def pop(self):
        if not self._items:
            return None
        return self._items.pop()
    def peek(self):
        if not self._items:
            return None
        return self._items[-1]
    def size(self):
        return len(self._items)
    def is_empty(self):
        return len(self._items) == 0
