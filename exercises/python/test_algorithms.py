"""Exercises: Algorithms

Complete each function below. Run with: python -m pytest exercises/python/test_algorithms.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from skills.algorithms.sorting import merge_sort, quick_sort, binary_search
from skills.algorithms.dynamic_programming import (
    fibonacci_tabulation, longest_common_subsequence, coin_change
)


# --- Exercise 1: Verify sorting algorithms ---

def test_sorting():
    data = [38, 27, 43, 3, 9, 82, 10]
    expected = [3, 9, 10, 27, 38, 43, 82]
    assert merge_sort(data) == expected
    assert quick_sort(data) == expected
    # Original should be unchanged (non-destructive)
    assert data == [38, 27, 43, 3, 9, 82, 10]


def test_sorting_edge_cases():
    assert merge_sort([]) == []
    assert merge_sort([1]) == [1]
    assert quick_sort([5, 5, 5]) == [5, 5, 5]
    assert merge_sort([3, 2, 1]) == [1, 2, 3]


# --- Exercise 2: Binary search ---

def test_binary_search():
    arr = [1, 3, 5, 7, 9, 11, 13]
    assert binary_search(arr, 7) == 3
    assert binary_search(arr, 1) == 0
    assert binary_search(arr, 13) == 6
    assert binary_search(arr, 4) == -1


# --- Exercise 3: Fibonacci ---

def test_fibonacci():
    assert fibonacci_tabulation(0) == 0
    assert fibonacci_tabulation(1) == 1
    assert fibonacci_tabulation(10) == 55
    assert fibonacci_tabulation(20) == 6765


# --- Exercise 4: Longest Common Subsequence ---

def test_lcs():
    assert longest_common_subsequence("abcde", "ace") == 3
    assert longest_common_subsequence("abc", "abc") == 3
    assert longest_common_subsequence("abc", "def") == 0


# --- Exercise 5: Coin Change ---

def test_coin_change():
    assert coin_change([1, 5, 10, 25], 30) == 2  # 25 + 5
    assert coin_change([2], 3) == -1  # impossible
    assert coin_change([1, 2, 5], 11) == 3  # 5 + 5 + 1


# --- Exercise 6: Implement max subarray (Kadane's algorithm) ---

def max_subarray_sum(nums):
    """Find the contiguous subarray with the largest sum. O(n).

    Kadane's algorithm: track current sum, reset when it goes negative.
    """
    if not nums:
        return 0
    max_sum = current = nums[0]
    for num in nums[1:]:
        current = max(num, current + num)
        max_sum = max(max_sum, current)
    return max_sum


def test_max_subarray():
    assert max_subarray_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6
    assert max_subarray_sum([1]) == 1
    assert max_subarray_sum([-1, -2, -3]) == -1
