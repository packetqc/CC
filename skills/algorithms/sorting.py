"""Sorting Algorithms - Essential algorithms every developer should know.

Comparison of common sorting algorithms:
| Algorithm      | Best    | Average | Worst   | Space | Stable |
|---------------|---------|---------|---------|-------|--------|
| Bubble Sort   | O(n)    | O(n^2)  | O(n^2)  | O(1)  | Yes    |
| Selection Sort| O(n^2)  | O(n^2)  | O(n^2)  | O(1)  | No     |
| Insertion Sort| O(n)    | O(n^2)  | O(n^2)  | O(1)  | Yes    |
| Merge Sort    | O(nlogn)| O(nlogn)| O(nlogn)| O(n)  | Yes    |
| Quick Sort    | O(nlogn)| O(nlogn)| O(n^2)  | O(logn)| No    |
"""


def bubble_sort(arr):
    """Simple but slow. Good for learning, not for production."""
    arr = arr.copy()
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr


def insertion_sort(arr):
    """Efficient for small or nearly-sorted arrays."""
    arr = arr.copy()
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr


def merge_sort(arr):
    """Divide and conquer. Guaranteed O(n log n) but uses O(n) space."""
    if len(arr) <= 1:
        return arr.copy()
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return _merge(left, right)


def _merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result


def quick_sort(arr):
    """Fast in practice. O(n log n) average, O(n^2) worst case."""
    if len(arr) <= 1:
        return arr.copy()
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)


def binary_search(arr, target):
    """Search a sorted array in O(log n). Returns index or -1."""
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
