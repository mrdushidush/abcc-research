class Node:
    def __init__(self, value):
        self.value = value
        self.next = None

class SortedList:
    def __init__(self):
        self.head = None
        self._length = 0
    def insert(self, value):
        new_node = Node(value)
        self._length += 1
        if self.head is None or value < self.head.value:
            new_node.next = self.head
            self.head = new_node
            return
        current = self.head
        while current.next and current.next.value < value:
            current = current.next
        new_node.next = current.next
        current.next = new_node
    def to_list(self):
        result = []
        current = self.head
        while current:
            result.append(current.value)
            current = current.next
        return result
    def length(self):
        return self._length
