/**
 * JavaScript Coding Skills Exercises
 * Run with: node exercises/javascript/skills.js
 */

// === Data Structures ===

class LinkedListNode {
  constructor(value) {
    this.value = value;
    this.next = null;
  }
}

function reverseLinkedList(head) {
  let prev = null;
  let current = head;
  while (current) {
    const next = current.next;
    current.next = prev;
    prev = current;
    current = next;
  }
  return prev;
}

function hasCycle(head) {
  let slow = head;
  let fast = head;
  while (fast && fast.next) {
    slow = slow.next;
    fast = fast.next.next;
    if (slow === fast) return true;
  }
  return false;
}

// === Algorithms ===

function mergeSort(arr) {
  if (arr.length <= 1) return [...arr];
  const mid = Math.floor(arr.length / 2);
  const left = mergeSort(arr.slice(0, mid));
  const right = mergeSort(arr.slice(mid));
  const result = [];
  let i = 0, j = 0;
  while (i < left.length && j < right.length) {
    if (left[i] <= right[j]) result.push(left[i++]);
    else result.push(right[j++]);
  }
  return result.concat(left.slice(i), right.slice(j));
}

function binarySearch(arr, target) {
  let low = 0, high = arr.length - 1;
  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    if (arr[mid] === target) return mid;
    if (arr[mid] < target) low = mid + 1;
    else high = mid - 1;
  }
  return -1;
}

function twoSum(nums, target) {
  const seen = new Map();
  for (let i = 0; i < nums.length; i++) {
    const complement = target - nums[i];
    if (seen.has(complement)) return [seen.get(complement), i];
    seen.set(nums[i], i);
  }
  return null;
}

function maxSubarraySum(nums) {
  if (!nums.length) return 0;
  let maxSum = nums[0], current = nums[0];
  for (let i = 1; i < nums.length; i++) {
    current = Math.max(nums[i], current + nums[i]);
    maxSum = Math.max(maxSum, current);
  }
  return maxSum;
}

function coinChange(coins, amount) {
  const dp = new Array(amount + 1).fill(Infinity);
  dp[0] = 0;
  for (let i = 1; i <= amount; i++) {
    for (const coin of coins) {
      if (coin <= i && dp[i - coin] + 1 < dp[i]) {
        dp[i] = dp[i - coin] + 1;
      }
    }
  }
  return dp[amount] === Infinity ? -1 : dp[amount];
}

// === Tests ===

function assert(condition, message) {
  if (!condition) throw new Error(`FAIL: ${message}`);
  console.log(`  PASS: ${message}`);
}

function runTests() {
  console.log("--- Linked List ---");
  const a = new LinkedListNode(1);
  a.next = new LinkedListNode(2);
  a.next.next = new LinkedListNode(3);
  const rev = reverseLinkedList(a);
  assert(rev.value === 3 && rev.next.value === 2, "reverseLinkedList");
  assert(!hasCycle(rev), "no cycle detected");
  rev.next.next.next = rev; // create cycle
  assert(hasCycle(rev), "cycle detected");

  console.log("\n--- Sorting ---");
  const data = [38, 27, 43, 3, 9, 82, 10];
  assert(JSON.stringify(mergeSort(data)) === "[3,9,10,27,38,43,82]", "mergeSort");
  assert(JSON.stringify(mergeSort([])) === "[]", "mergeSort empty");

  console.log("\n--- Binary Search ---");
  assert(binarySearch([1, 3, 5, 7, 9], 7) === 3, "binarySearch found");
  assert(binarySearch([1, 3, 5, 7, 9], 4) === -1, "binarySearch not found");

  console.log("\n--- Two Sum ---");
  assert(JSON.stringify(twoSum([2, 7, 11, 15], 9)) === "[0,1]", "twoSum");

  console.log("\n--- Max Subarray ---");
  assert(maxSubarraySum([-2, 1, -3, 4, -1, 2, 1, -5, 4]) === 6, "maxSubarray");

  console.log("\n--- Coin Change ---");
  assert(coinChange([1, 5, 10, 25], 30) === 2, "coinChange 30");
  assert(coinChange([2], 3) === -1, "coinChange impossible");

  console.log("\nAll tests passed!");
}

runTests();
