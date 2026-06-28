# 152. Maximum Product Subarray

**Link:** [Maximum Product Subarray](https://leetcode.com/problems/maximum-product-subarray/description/)  
**Difficulty:** Medium  
**Tags:** Array, Dynamic Programming

## Problem Summary

Given an integer array `nums`, find a **contiguous subarray** with the largest product and return that product.

The subarray must be non-empty. The answer fits in a 32-bit integer.

---

## Approach 1: Brute Force (Reference)

Try every contiguous subarray `[i..j]`, multiply elements, track the maximum.

### Complexity

|           |                                                          |
| --------- | -------------------------------------------------------- |
| **Time**  | **O(n²)** — O(n²) subarrays, O(1) multiply per extension |
| **Space** | **O(1)**                                                 |

Too slow for large inputs. Included for comparison only.

---

## Approach 2: Kadane's Variant — Track Min and Max (Best)

Unlike sum, **a negative product can become the maximum** after multiplying by another negative. Track both the smallest and largest product ending at each index.

### Code

```javascript
/**
 * @param {number[]} nums
 * @return {number}
 */
var maxProduct = function (nums) {
  let np = nums[0];
  let pp = nums[0];
  let mp = nums[0];

  for (let i = 1; i < nums.length; i++) {
    let lnp = np;
    let lpp = pp;

    if (nums[i] < 0) {
      lnp = pp;
      lpp = np;
    }

    pp = Math.max(nums[i], lpp * nums[i]);
    np = Math.min(nums[i], lnp * nums[i]);

    mp = Math.max(mp, np, pp);
  }

  return mp;
};
```

**Variable names:** `pp` = max product ending here, `np` = min product ending here, `mp` = global max.

### Complexity

|           |                        |
| --------- | ---------------------- |
| **Time**  | **O(n)** — single pass |
| **Space** | **O(1)**               |

### Walkthrough

`nums = [2, 3, -2, 4]`

| i   | nums[i] | pp (max end)        | np (min end)        | mp  |
| --- | ------- | ------------------- | ------------------- | --- |
| 0   | 2       | 2                   | 2                   | 2   |
| 1   | 3       | 6                   | 6                   | 6   |
| 2   | -2      | max(-2, -12)=**-2** | min(-2, -6)=**-12** | 6   |
| 3   | 4       | max(4, -8)=**4**    | min(4, -48)=**-48** | 6   |

Answer: **6** (subarray `[2, 3]`).

`nums = [-2, 3, -4]`

| i   | nums[i] | pp     | np  | mp     |
| --- | ------- | ------ | --- | ------ |
| 0   | -2      | -2     | -2  | -2     |
| 1   | 3       | 3      | -6  | 3      |
| 2   | -4      | **24** | -12 | **24** |

Answer: **24** (full array — two negatives make a positive).

### Why swap on negative?

Multiplying by a negative **flips** min ↔ max:

```
newMax = max(nums[i], oldMax * nums[i], oldMin * nums[i])
newMin = min(nums[i], oldMax * nums[i], oldMin * nums[i])
```

When `nums[i] < 0`, swapping `lnp` and `lpp` before multiply achieves the same thing.

**Equivalent without explicit swap:**

```javascript
let tmp = pp;
pp = Math.max(nums[i], pp * nums[i], np * nums[i]);
np = Math.min(nums[i], tmp * nums[i], np * nums[i]);
mp = Math.max(mp, pp);
```

---

## Approach 3: Prefix + Suffix Product Scan

Scan from both ends simultaneously. Track running prefix product (left → right) and suffix product (right → left). Reset to `1` after hitting `0`.

### Code

```javascript
/**
 * @param {number[]} nums
 * @return {number}
 */
var maxProductPrefixSuffix = function (nums) {
  let maxProd = -Infinity;
  let prefix = 1;
  let suffix = 1;
  let n = nums.length;

  for (let i = 0; i < n; i++) {
    if (prefix === 0) prefix = 1;
    if (suffix === 0) suffix = 1;

    prefix *= nums[i];
    suffix *= nums[n - 1 - i];

    maxProd = Math.max(maxProd, prefix, suffix);
  }

  return maxProd;
};
```

### Complexity

|           |                     |
| --------- | ------------------- |
| **Time**  | **O(n)** — one pass |
| **Space** | **O(1)**            |

### Walkthrough

`nums = [-2, 3, -4]`

| i   | prefix (→) | suffix (←) | maxProd |
| --- | ---------- | ---------- | ------- |
| 0   | -2         | -4         | -2      |
| 1   | -6         | -12        | -2      |
| 2   | **24**     | **24**     | **24**  |

At `i = 2`: prefix = product `[-2, 3, -4]`; suffix = product `[3, -4]` from the right scan — both hit **24**.

### When this works

Zeros split the array into independent segments — reset to `1` skips them. The bidirectional scan captures max products that grow from either end; combined with zero-handling, it covers all optimal subarrays in one pass.

### vs Approach 2

|                                      | Min/Max Kadane                    | Prefix/Suffix          |
| ------------------------------------ | --------------------------------- | ---------------------- |
| **Direct extension of Max Subarray** | Yes                               | Less obvious           |
| **Interview clarity**                | **Preferred**                     | Clever alternative     |
| **Handles negatives**                | Explicit min/max swap             | Implicit via dual scan |
| **Handles zeros**                    | Naturally via `max(nums[i], ...)` | Explicit reset         |

---

## Approach Comparison

| Approach           | Time  | Space | Notes                         |
| ------------------ | ----- | ----- | ----------------------------- |
| Brute force        | O(n²) | O(1)  | TLE                           |
| Min/Max Kadane     | O(n)  | O(1)  | **Default interview answer**  |
| Prefix/Suffix scan | O(n)  | O(1)  | Elegant; know zero-reset rule |

---

## Pattern Learned

**Pattern: Kadane's Variant — Track Min and Max Product**

For **sum**, Kadane only needs the max ending here. For **product**, negatives flip sign — the smallest product can become the largest after one more negative.

```
maxEnd = max(nums[i], maxEnd * nums[i], minEnd * nums[i])
minEnd = min(nums[i], maxEnd * nums[i], minEnd * nums[i])
answer = max(answer, maxEnd)
```

**Signals in the problem:**

- Maximum/minimum **product** of contiguous subarray
- Array contains **negative numbers**
- Standard Kadane (max only) **fails** — need min tracking too
- Zeros create natural segment breaks

**Relation to [Maximum Subarray](./053-maximum-subarray.md):**

|                 | Sum                       | Product                          |
| --------------- | ------------------------- | -------------------------------- |
| State per index | 1 value (max ending here) | 2 values (min + max ending here) |
| Negative effect | Always hurts              | Can **flip** min into max        |
| Zero effect     | Resets sum chain          | Resets product chain to 0        |

---

## Key Insight

> **A minimum product is not useless — multiply it by a negative and it becomes a maximum.**

That's why max-only Kadane fails here. Always track **both** extremes when multiplication and negatives are involved.

---

## Follow-Up Questions

Problems extending product / Kadane thinking:

| Problem                                                                                                   | Twist                                             |
| --------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| [Maximum Subarray](./053-maximum-subarray.md)                                                             | Sum version — max only                            |
| [Maximum Product of Three Numbers](https://leetcode.com/problems/maximum-product-of-three-numbers/)       | Pick 3 elements — sort or track top 3 / bottom 2  |
| [Maximum Sum Circular Subarray](https://leetcode.com/problems/maximum-sum-circular-subarray/)             | Circular sum — Kadane + total − min               |
| [Subarray Product Less Than K](https://leetcode.com/problems/subarray-product-less-than-k/)               | Count subarrays — sliding window (positives only) |
| [Product of Array Except Self](./238-product-of-array-except-self.md)                                     | Prefix/suffix without division                    |
| [Best Time to Buy and Sell Stock III](https://leetcode.com/problems/best-time-to-buy-and-sell-stock-iii/) | DP with multiple states                           |

### Interview Variants

- **Return the subarray**, not the product — track indices when updating `mp`.
- **What if all numbers are negative?** — answer is the **single largest** element (e.g. `[-3,-1,-2]` → `-1`).
- **What about zeros?** — subarray can't include 0 if seeking max product > 0; zero forces a segment reset.
- **Why doesn't max-only Kadane work?** — `[-2, 3, -4]`: after `3`, max=3; at `-4`, max(-4, -12)=-4 — misses 24 from full array.
- **Overflow?** — use `BigInt` or log-sum in production; LeetCode usually handles 32-bit.

---

## Common Pitfalls

- **Tracking only max** — fails with two negatives (classic trap).
- **Forgetting `nums[i]` alone** — `Math.max(nums[i], ...)` handles single-element subarrays.
- **Initializing to 0** — wrong when all negatives; start from `nums[0]`.
- **Swap order bug** — when `nums[i] < 0`, use **old** min for new max and **old** max for new min (save temps before updating).
- **Confusing with sum Kadane** — product needs min **and** max state.
- **Prefix/suffix: forgetting zero reset** — `0` in array requires `prefix = 1` / `suffix = 1` before continuing.
