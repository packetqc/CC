"""Binary Search Tree - Ordered data with O(log n) average operations.

A BST maintains the invariant: left < node < right for all nodes.
This enables efficient search, insertion, and deletion.

Key operations (average / worst case):
- search: O(log n) / O(n)
- insert: O(log n) / O(n)
- delete: O(log n) / O(n)

Worst case occurs with unbalanced trees (essentially linked lists).
Balanced variants (AVL, Red-Black) guarantee O(log n).
"""


class TreeNode:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None


class BinarySearchTree:
    def __init__(self):
        self.root = None

    def insert(self, value):
        """Insert a value into the BST."""
        if not self.root:
            self.root = TreeNode(value)
        else:
            self._insert(self.root, value)

    def _insert(self, node, value):
        if value < node.value:
            if node.left is None:
                node.left = TreeNode(value)
            else:
                self._insert(node.left, value)
        elif value > node.value:
            if node.right is None:
                node.right = TreeNode(value)
            else:
                self._insert(node.right, value)

    def search(self, value):
        """Search for a value. Returns the node or None."""
        return self._search(self.root, value)

    def _search(self, node, value):
        if node is None or node.value == value:
            return node
        if value < node.value:
            return self._search(node.left, value)
        return self._search(node.right, value)

    def inorder(self):
        """Return values in sorted order (in-order traversal)."""
        result = []
        self._inorder(self.root, result)
        return result

    def _inorder(self, node, result):
        if node:
            self._inorder(node.left, result)
            result.append(node.value)
            self._inorder(node.right, result)

    def preorder(self):
        """Return values in pre-order (root, left, right)."""
        result = []
        self._preorder(self.root, result)
        return result

    def _preorder(self, node, result):
        if node:
            result.append(node.value)
            self._preorder(node.left, result)
            self._preorder(node.right, result)

    def min_value(self):
        """Find the minimum value in the tree."""
        if not self.root:
            return None
        current = self.root
        while current.left:
            current = current.left
        return current.value

    def max_value(self):
        """Find the maximum value in the tree."""
        if not self.root:
            return None
        current = self.root
        while current.right:
            current = current.right
        return current.value

    def height(self):
        """Calculate the height of the tree."""
        return self._height(self.root)

    def _height(self, node):
        if not node:
            return -1
        return 1 + max(self._height(node.left), self._height(node.right))
