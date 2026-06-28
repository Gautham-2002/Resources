# 238. Product of Array Except Self

**Link:** [Product of Array Except Self](https://leetcode.com/problems/product-of-array-except-self/description/)  
**Difficulty:** Medium  
**Tags:** Array, Prefix Sum

## Problem Summary

Given an integer array `nums`, return an array `answer` where `answer[i]` is the product of all elements of `nums` **except** `nums[i]`.

Constraints (typical interview follow-ups):

- Solve in **O(n)** time.
- **Without using division.**
- **O(1)** extra space (the output array does not count).

---

## Approach 1: Total Product + Division (Zero Handling)

Compute the product of all non-zero elements, count zeros, then derive each answer with division and case logic.

### Code

```javascript
/**
 * @param {number[]} nums
 * @return {number[]}
 */
var productExceptSelf = function (nums) {
  let nZeros = 0;
  let fp = nums
    .filter((i) => {
      if (i == 0) nZeros++;
      return i != 0;
    })
    .reduce((i, p) => i * p, 1);

  return nums.map((i) =>
    nZeros > 1 ? 0 : nZeros == 1 ? (i == 0 ? fp : 0) : fp / i,
  );
};
```

### Complexity

|           |                                                                    |
| --------- | ------------------------------------------------------------------ |
| **Time**  | **O(n)** — filter, reduce, and map each scan once                  |
| **Space** | **O(n)** — output array; filter may allocate an intermediate array |

### Zero cases

| Zeros  | Result                                                            |
| ------ | ----------------------------------------------------------------- |
| **0**  | `answer[i] = totalProduct / nums[i]`                              |
| **1**  | Only the zero index gets product of non-zeros; all others are `0` |
| **2+** | Every answer is `0`                                               |

### Trade-off

Clever and fast, but **uses division** — fails the explicit follow-up constraint. Still worth knowing for variants where division is allowed.

---

## Approach 2: Prefix + Suffix Arrays (`unshift`)

Build `lpa` (product of all elements to the left) and `rpa` (product of all elements to the right), then multiply position-wise.

### Code

```javascript
/**
 * @param {number[]} nums
 * @return {number[]}
 */
var productExceptSelf = function (nums) {
  let lp = 1;
  let lpa = nums.reduce((a, i) => {
    a.push(lp);
    lp *= i;
    return a;
  }, []);

  let rp = 1;
  let rpa = nums.reduceRight((a, i) => {
    a.unshift(rp);
    rp *= i;
    return a;
  }, []);

  return nums.map((_, i) => lpa[i] * rpa[i]);
};
```

### Complexity

|           |                                                            |
| --------- | ---------------------------------------------------------- |
| **Time**  | **O(n)** — three linear passes                             |
| **Space** | **O(n)** — two auxiliary arrays (`lpa`, `rpa`) plus output |

### Walkthrough

`nums = [1, 2, 3, 4]`

| i   | lpa[i] (left of i) | rpa[i] (right of i) | answer |
| --- | ------------------ | ------------------- | ------ |
| 0   | 1                  | 24                  | 24     |
| 1   | 1                  | 12                  | 12     |
| 2   | 2                  | 4                   | 8      |
| 3   | 6                  | 1                   | 6      |

**Note:** `unshift` on each step is **O(n)** per call → **O(n²)** total in the worst case. Use Approach 3 or 4 instead for true O(n).

---

## Approach 3: Prefix + Suffix Arrays (`push` + `reverse`)

Same logic as Approach 2, but build the suffix array with `push` (O(1) amortized) then `reverse` once.

### Code

```javascript
/**
 * @param {number[]} nums
 * @return {number[]}
 */
var productExceptSelf = function (nums) {
  let lp = 1;
  let lpa = nums.reduce((a, i) => {
    a.push(lp);
    lp *= i;
    return a;
  }, []);

  let rp = 1;
  let rpa = nums.reduceRight((a, i) => {
    a.push(rp);
    rp *= i;
    return a;
  }, []);

  rpa.reverse();

  return nums.map((_, i) => lpa[i] * rpa[i]);
};
```

### Complexity

|           |                                             |
| --------- | ------------------------------------------- |
| **Time**  | **O(n)** — `unshift` avoided                |
| **Space** | **O(n)** — two auxiliary arrays plus output |

### Why `push` + `reverse`?

`reduceRight` with `push` fills `rpa` in reverse index order. One `reverse()` aligns indices with `lpa`. Same idea, proper O(n) time.

---

## Approach 4: Single Output Array — O(1) Extra Space (Best)

Store prefix products in `res` in a forward pass. Multiply by a running suffix in a backward pass — no extra arrays.

### Code

```javascript
/**
 * @param {number[]} nums
 * @return {number[]}
 */
var productExceptSelf = function (nums) {
  let n = nums.length;
  let res = new Array(n);

  // Forward: res[i] = product of all elements left of i
  let prefix = 1;
  for (let i = 0; i < n; i++) {
    res[i] = prefix;
    prefix *= nums[i];
  }

  // Backward: multiply res[i] by product of all elements right of i
  let suffix = 1;
  for (let i = n - 1; i >= 0; i--) {
    res[i] *= suffix;
    suffix *= nums[i];
  }

  return res;
};
```

### Complexity

|           |                                                                                    |
| --------- | ---------------------------------------------------------------------------------- |
| **Time**  | **O(n)** — two linear passes                                                       |
| **Space** | **O(1)** extra — only `prefix`, `suffix`, and output (output excluded per problem) |

### Walkthrough

`nums = [1, 2, 3, 4]`

**After forward pass** (`res[i]` = left product):

| i   | res[i] |
| --- | ------ |
| 0   | 1      |
| 1   | 1      |
| 2   | 2      |
| 3   | 6      |

**Backward pass** (multiply by running suffix):

| i   | suffix before | res[i] after × suffix |
| --- | ------------- | --------------------- |
| 3   | 1             | 6 × 1 = 6             |
| 2   | 4             | 2 × 4 = 8             |
| 1   | 12            | 1 × 12 = 12           |
| 0   | 24            | 1 × 24 = 24           |

---

## Approach Comparison

| Approach                         | Time    | Extra space | Division? | Meets constraints?     |
| -------------------------------- | ------- | ----------- | --------- | ---------------------- |
| Product + division               | O(n)    | O(n)        | Yes       | No                     |
| Prefix/suffix (`unshift`)        | O(n²)\* | O(n)        | No        | No                     |
| Prefix/suffix (`push` + reverse) | O(n)    | O(n)        | No        | Partial (extra arrays) |
| Single array, two passes         | O(n)    | O(1)        | No        | **Yes**                |

\*`unshift` in a loop degrades time.

---

## Pattern Learned

**Pattern: Prefix / Suffix Decomposition**

When each answer depends on **all values except one at index `i`**, split the contribution into:

```
answer[i] = (product of nums[0..i-1]) × (product of nums[i+1..n-1])
            \_________ prefix ________/   \_________ suffix ________/
```

**Signals in the problem:**

- "Except self", "all others", "left and right of index"
- Naive approach is O(n²) — re-multiply for every index
- Often solvable with two passes and O(1) rolling state

**General template:**

```javascript
const res = new Array(n);

let prefix = 1;
for (let i = 0; i < n; i++) {
  res[i] = prefix;
  prefix *= nums[i];
}

let suffix = 1;
for (let i = n - 1; i >= 0; i--) {
  res[i] *= suffix;
  suffix *= nums[i];
}
```

Same pattern works for **prefix/suffix sums**, **max**, or **min** when combining left + right contributions.

---

## Key Insight

You don't need to recompute the full product for every index.

`answer[i]` only needs everything **before** `i` and everything **after** `i`. Two running products — one forward, one backward — give both halves in linear time.

---

## Follow-Up Questions

Problems using prefix/suffix thinking:

| Problem                                                                                     | Twist                                                           |
| ------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| [Trapping Rain Water](https://leetcode.com/problems/trapping-rain-water/)                   | Prefix max + suffix max at each index                           |
| [Maximum Product Subarray](https://leetcode.com/problems/maximum-product-subarray/)         | Track running max/min (negatives flip sign)                     |
| [Subarray Product Less Than K](https://leetcode.com/problems/subarray-product-less-than-k/) | Sliding window on product                                       |
| [Find Pivot Index](https://leetcode.com/problems/find-pivot-index/)                         | Prefix sum left equals suffix sum right                         |
| [Range Sum Query - Immutable](https://leetcode.com/problems/range-sum-query-immutable/)     | Precomputed prefix sums                                         |
| [Candy](https://leetcode.com/problems/candy/)                                               | Two-pass greedy with left/right constraints                     |
| [Daily Temperatures](https://leetcode.com/problems/daily-temperatures/)                     | Monotonic stack (different tool, same "look left/right" spirit) |

### Interview Variants

- **Can you use division?** — Approach 1; handle zero count carefully.
- **What if there are zeros?** — prefix/suffix handles naturally; division needs special cases.
- **What if array has negative numbers?** — prefix/suffix still works; watch overflow in languages with fixed-width ints.
- **Return indices, not products** — different problem; same decomposition may apply.
- **Multiple queries on static array** — precompute prefix products once, answer each query in O(1).

---

## Common Pitfalls

- **Using division when disallowed** — confirm constraints before Approach 1.
- **`unshift` in a loop** — O(n²); prefer `push` + `reverse` or the single-array method.
- **Initializing prefix/suffix to 0** — must start at **1** (empty product is 1, not 0).
- **Off-by-one on boundaries** — index `0` has no left neighbors (prefix = 1); last index has no right neighbors (suffix = 1).
- **Integer overflow** — LeetCode often allows it; in production, consider `BigInt` or log-sum tricks.
- **Mutating input** — these solutions don't require it; avoid unless space-critical.
