"""Exercises: Data Structures

Complete each function below. Run with: python -m pytest exercises/python/test_data_structures.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# --- Exercise 1: Reverse a linked list ---

def test_reverse_linked_list():
    from skills.data_structures.linked_list import LinkedList

    ll = LinkedList()
    for v in [1, 2, 3, 4, 5]:
        ll.append(v)
    ll.reverse()
    assert ll.to_list() == [5, 4, 3, 2, 1]


# --- Exercise 2: Detect cycle in a linked list ---

def has_cycle(head):
    """Return True if the linked list has a cycle.

    Hint: Use Floyd's tortoise and hare algorithm.
    - Two pointers: slow moves 1 step, fast moves 2 steps
    - If they meet, there's a cycle
    """
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow is fast:
            return True
    return False


def test_detect_cycle():
    from skills.data_structures.linked_list import Node

    # No cycle
    a, b, c = Node(1), Node(2), Node(3)
    a.next = b
    b.next = c
    assert has_cycle(a) is False

    # With cycle
    c.next = a
    assert has_cycle(a) is True


# --- Exercise 3: BST validation ---

def is_valid_bst(node, min_val=float("-inf"), max_val=float("inf")):
    """Return True if the tree rooted at node is a valid BST.

    Each node's value must be strictly between min_val and max_val.
    """
    if node is None:
        return True
    if node.value <= min_val or node.value >= max_val:
        return False
    return (is_valid_bst(node.left, min_val, node.value) and
            is_valid_bst(node.right, node.value, max_val))


def test_valid_bst():
    from skills.data_structures.binary_tree import BinarySearchTree

    bst = BinarySearchTree()
    for v in [5, 3, 7, 1, 4, 6, 8]:
        bst.insert(v)
    assert is_valid_bst(bst.root) is True


# --- Exercise 4: Hash map usage - Two Sum ---

def two_sum(nums, target):
    """Find two indices whose values sum to target. O(n) using a hash map.

    Returns a tuple of (i, j) where nums[i] + nums[j] == target.
    """
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return (seen[complement], i)
        seen[num] = i
    return None


def test_two_sum():
    assert two_sum([2, 7, 11, 15], 9) == (0, 1)
    assert two_sum([3, 2, 4], 6) == (1, 2)
    assert two_sum([1, 2, 3, 4], 10) is None
