# 53. Maximum Subarray

**Link:** [Maximum Subarray](https://leetcode.com/problems/maximum-subarray/description/)  
**Difficulty:** Medium  
**Tags:** Array, Divide and Conquer, Dynamic Programming

## Problem Summary

Given an integer array `nums`, find the **contiguous subarray** with the largest sum and return that sum.

A subarray is a contiguous non-empty sequence of elements within the array.

---

## Approach 1: Brute Force (TLE)

For every start index `i`, extend to every end index `j ≥ i`, accumulate the running sum, and track the maximum.

### Code

```javascript
/**
 * @param {number[]} nums
 * @return {number}
 */
var maxSubArray = function (nums) {
  let msum = -Infinity;

  for (let i = 0; i < nums.length; i++) {
    let lsum = 0;
    for (let j = i; j < nums.length; j++) {
      lsum += nums[j];

      if (lsum > msum) {
        msum = lsum;
      }
    }
  }

  return msum;
};
```

### Complexity

|           |                                                         |
| --------- | ------------------------------------------------------- |
| **Time**  | **O(n²)** — O(n) start positions × O(n) extensions each |
| **Space** | **O(1)** — only scalar variables                        |

### Why This Works / Doesn't Scale

Correct, but recomputes overlapping subarray sums. Too slow for large `n` (TLE on LeetCode).

---

## Approach 2: Kadane's Algorithm — Your Variant

Maintain a running sum `s`. When `s` is negative, carrying it forward only drags down future sums — reset or extend based on whether starting fresh at `nums[i]` is better.

### Code

```javascript
/**
 * @param {number[]} nums
 * @return {number}
 */
var maxSubArray = function (nums) {
  let s = -Infinity;
  let ms = -Infinity;

  for (let i = 0; i < nums.length; i++) {
    if (s < 0 && nums[i] > s) {
      s = nums[i];
    } else {
      s += nums[i];
    }

    if (s >= ms) {
      ms = s;
    }
  }

  return ms;
};
```

### Complexity

|           |                        |
| --------- | ---------------------- |
| **Time**  | **O(n)** — single pass |
| **Space** | **O(1)**               |

### Logic

| State                     | Action                                            |
| ------------------------- | ------------------------------------------------- |
| `s < 0` and `nums[i] > s` | Drop the negative chain; start fresh at `nums[i]` |
| Otherwise                 | Extend current subarray: `s += nums[i]`           |

`ms` tracks the best subarray sum seen at any point.

---

## Approach 3: Kadane's Algorithm — Canonical (Best)

At each index, decide: **extend** the current subarray or **start a new one** at `nums[i]`.

### Code

```javascript
/**
 * @param {number[]} nums
 * @return {number}
 */
var maxSubArray = function (nums) {
  let currentSum = nums[0];
  let maxSum = nums[0];

  for (let i = 1; i < nums.length; i++) {
    // Extend the chain, or throw it away and start fresh at nums[i]
    currentSum = Math.max(nums[i], currentSum + nums[i]);

    // Track the best subarray sum seen so far
    maxSum = Math.max(maxSum, currentSum);
  }

  return maxSum;
};
```

### Complexity

|           |          |
| --------- | -------- |
| **Time**  | **O(n)** |
| **Space** | **O(1)** |

### Walkthrough

`nums = [-2, 1, -3, 4, -1, 2, 1, -5, 4]`

| i   | nums[i] | currentSum           | maxSum |
| --- | ------- | -------------------- | ------ |
| 0   | -2      | -2                   | -2     |
| 1   | 1       | max(1, -1) = **1**   | 1      |
| 2   | -3      | max(-3, -2) = **-2** | 1      |
| 3   | 4       | max(4, 2) = **4**    | 4      |
| 4   | -1      | max(-1, 3) = **3**   | 4      |
| 5   | 2       | max(2, 5) = **5**    | 5      |
| 6   | 1       | max(1, 6) = **6**    | **6**  |
| 7   | -5      | max(-5, 1) = **1**   | 6      |
| 8   | 4       | max(4, 5) = **5**    | 6      |

Answer: **6** (subarray `[4, -1, 2, 1]`).

### vs Approach 2

Both implement Kadane's core idea. The `Math.max` form is:

- **One line** for the extend-or-reset decision
- **Easier to prove correct** — equivalent to `currentSum = max(nums[i], currentSum + nums[i])`
- **Preferred in interviews** for clarity

Your variant encodes the same reset-when-negative intuition with `if/else`.

---

## Approach Comparison

| Approach              | Time  | Space | Notes                       |
| --------------------- | ----- | ----- | --------------------------- |
| Brute force           | O(n²) | O(1)  | TLE                         |
| Kadane (your variant) | O(n)  | O(1)  | Valid; if/else style        |
| Kadane (`Math.max`)   | O(n)  | O(1)  | **Canonical — prefer this** |

**Optional:** Divide and conquer solves this in **O(n log n)** — useful to mention, rarely needed when Kadane's is O(n).

---

## Pattern Learned

**Pattern: Kadane's Algorithm — Maximum Subarray Sum**

At each position, the best subarray **ending at `i`** is either:

1. `nums[i]` alone (start fresh), or
2. `nums[i]` appended to the best subarray ending at `i - 1`

```
dp[i] = max(nums[i], dp[i-1] + nums[i])
answer = max(dp[0], dp[1], ..., dp[n-1])
```

Optimized to **O(1) space** since only `dp[i-1]` is needed.

**Signals in the problem:**

- "Maximum/minimum **contiguous** subarray"
- "Largest sum subarray"
- Brute force checks all O(n²) subarrays
- Greedy choice: negative running sum hurts future extensions — drop it

**General template:**

```javascript
let current = nums[0];
let best = nums[0];

for (let i = 1; i < nums.length; i++) {
  current = Math.max(nums[i], current + nums[i]);
  best = Math.max(best, current);
}

return best;
```

**Related idea:** Same "running best, reset when harmful" spirit as [Best Time to Buy and Sell Stock](./121-best-time-to-buy-and-sell-stock.md), but Kadane's optimizes **subarray sum** not buy/sell profit.

---

## Key Insight

You never need to know all subarrays explicitly.

For the optimal subarray ending at index `i`, there are only **two choices**: include the previous optimal ending at `i-1`, or start over at `i`. That local decision at each step gives the global answer.

> **Negative running sum is dead weight — drop the chain and start fresh.**

---

## Follow-Up Questions

Problems that extend Kadane's or contiguous-subarray thinking:

| Problem                                                                                                         | Twist                                  |
| --------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| [Maximum Product Subarray](https://leetcode.com/problems/maximum-product-subarray/)                             | Track **min and max** (negatives flip) |
| [Best Time to Buy and Sell Stock](https://leetcode.com/problems/best-time-to-buy-and-sell-stock/)               | Running min + max spread               |
| [Maximum Sum Circular Subarray](https://leetcode.com/problems/maximum-sum-circular-subarray/)                   | Kadane + total sum − min subarray      |
| [Longest Turbulent Subarray](https://leetcode.com/problems/longest-turbulent-subarray/)                         | Kadane-style on comparison pattern     |
| [Maximum Subarray Sum with One Deletion](https://leetcode.com/problems/maximum-subarray-sum-with-one-deletion/) | Kadane forward + backward              |
| [Split Array Largest Sum](https://leetcode.com/problems/split-array-largest-sum/)                               | Binary search on answer                |
| [Subarray Sum Equals K](https://leetcode.com/problems/subarray-sum-equals-k/)                                   | Prefix sum + hash map (not Kadane)     |
| [Shortest Subarray with Sum at Least K](https://leetcode.com/problems/shortest-subarray-with-sum-at-least-k/)   | Prefix sum + deque                     |

### Interview Variants

- **Return the subarray itself**, not just the sum — track start/end indices when updating `maxSum`.
- **What if all numbers are negative?** — answer is the **largest single element**; Kadane still works.
- **Divide and conquer approach?** — split at mid; max crosses left, right, or middle (O(n log n)).
- **DP vs greedy?** — Kadane is DP with O(1) space; recurrence is the proof.
- **Circular array?** — `max(kadane(nums), total - kadane(-nums))` with edge cases.

---

## Common Pitfalls

- **Initializing to `0`** — wrong when all elements are negative (e.g. `[-3,-2]` → answer `-2`, not `0`).
- **Confusing with "subsequence"** — subarray must be **contiguous**.
- **Brute force TLE** — know Kadane's for interviews.
- **Maximum Product Subarray** — Kadane's max-only fails; need min product too for negative flips.
- **Your variant's edge case** — prefer `Math.max(nums[i], currentSum + nums[i])` for clarity; equivalent and easier to verify.
