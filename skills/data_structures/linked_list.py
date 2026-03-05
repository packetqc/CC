"""Linked List - A fundamental data structure.

A linked list stores elements in nodes, where each node points to the next.
Unlike arrays, linked lists allow O(1) insertions/deletions at known positions
but require O(n) access to arbitrary elements.

Key operations:
- append: O(1) with tail pointer
- prepend: O(1)
- search: O(n)
- delete: O(n) to find, O(1) to remove
"""


class Node:
    def __init__(self, value):
        self.value = value
        self.next = None


class LinkedList:
    def __init__(self):
        self.head = None
        self.size = 0

    def prepend(self, value):
        """Add a node at the beginning. O(1)."""
        node = Node(value)
        node.next = self.head
        self.head = node
        self.size += 1

    def append(self, value):
        """Add a node at the end. O(n) without tail pointer."""
        node = Node(value)
        if not self.head:
            self.head = node
        else:
            current = self.head
            while current.next:
                current = current.next
            current.next = node
        self.size += 1

    def delete(self, value):
        """Remove the first node with the given value. O(n)."""
        if not self.head:
            return False
        if self.head.value == value:
            self.head = self.head.next
            self.size -= 1
            return True
        current = self.head
        while current.next:
            if current.next.value == value:
                current.next = current.next.next
                self.size -= 1
                return True
            current = current.next
        return False

    def search(self, value):
        """Find the first node with the given value. O(n)."""
        current = self.head
        while current:
            if current.value == value:
                return current
            current = current.next
        return None

    def reverse(self):
        """Reverse the list in-place. O(n)."""
        prev = None
        current = self.head
        while current:
            next_node = current.next
            current.next = prev
            prev = current
            current = next_node
        self.head = prev

    def to_list(self):
        """Convert to a Python list for easy viewing."""
        result = []
        current = self.head
        while current:
            result.append(current.value)
            current = current.next
        return result

    def __len__(self):
        return self.size

    def __repr__(self):
        return " -> ".join(str(v) for v in self.to_list())
