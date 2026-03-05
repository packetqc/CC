"""Dynamic Programming - Solve complex problems by breaking them into subproblems.

DP works when a problem has:
1. Optimal substructure: optimal solution uses optimal solutions of subproblems
2. Overlapping subproblems: same subproblems are solved multiple times

Two approaches:
- Top-down (memoization): recursive with caching
- Bottom-up (tabulation): iterative, building up from base cases
"""


def fibonacci_naive(n):
    """Naive recursive Fibonacci. O(2^n) - DON'T use this."""
    if n <= 1:
        return n
    return fibonacci_naive(n - 1) + fibonacci_naive(n - 2)


def fibonacci_memo(n, memo=None):
    """Memoized Fibonacci. O(n) time, O(n) space."""
    if memo is None:
        memo = {}
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = fibonacci_memo(n - 1, memo) + fibonacci_memo(n - 2, memo)
    return memo[n]


def fibonacci_tabulation(n):
    """Bottom-up Fibonacci. O(n) time, O(1) space."""
    if n <= 1:
        return n
    prev, curr = 0, 1
    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr
    return curr


def longest_common_subsequence(s1, s2):
    """Find the length of the longest common subsequence. O(m*n)."""
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]


def knapsack_01(weights, values, capacity):
    """0/1 Knapsack: maximize value within weight capacity. O(n*W)."""
    n = len(weights)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(capacity + 1):
            dp[i][w] = dp[i - 1][w]
            if weights[i - 1] <= w:
                dp[i][w] = max(dp[i][w], dp[i - 1][w - weights[i - 1]] + values[i - 1])
    return dp[n][capacity]


def coin_change(coins, amount):
    """Minimum coins needed to make amount. O(n*amount)."""
    dp = [float("inf")] * (amount + 1)
    dp[0] = 0
    for i in range(1, amount + 1):
        for coin in coins:
            if coin <= i and dp[i - coin] + 1 < dp[i]:
                dp[i] = dp[i - coin] + 1
    return dp[amount] if dp[amount] != float("inf") else -1
