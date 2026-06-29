# 11. Container With Most Water

**Link:** [Container With Most Water](https://leetcode.com/problems/container-with-most-water/description/)  
**Difficulty:** Medium  
**Tags:** Array, Two Pointers, Greedy

## Problem Summary

Given `n` vertical lines at `height[i]` on the x-axis, pick **two lines** that together with the x-axis form a container. Return the **maximum amount of water** the container can hold.

Water held = `min(height[i], height[j]) × (j - i)` — limited by the shorter wall, width is the distance between indices.

---

## Approach 1: Brute Force (Reference)

Try every pair `(i, j)` and compute area.

### Complexity

|           |                       |
| --------- | --------------------- |
| **Time**  | **O(n²)** — all pairs |
| **Space** | **O(1)**              |

Too slow for large `n`. Included for comparison only.

---

## Approach 2: Two Pointers — Greedy (Best)

Start with the **widest** container (`i = 0`, `j = n - 1`). Compute area, then move the pointer at the **shorter** wall inward.

### Code

```javascript
/**
 * @param {number[]} height
 * @return {number}
 */
var maxArea = function (height) {
  let res = 0;

  let i = 0,
    j = height.length - 1;

  while (i < j) {
    let area = Math.min(height[i], height[j]) * (j - i);

    res = Math.max(res, area);

    height[i] > height[j] ? j-- : i++;
  }

  return res;
};
```

### Complexity

|           |                                                 |
| --------- | ----------------------------------------------- |
| **Time**  | **O(n)** — each pointer moves at most `n` times |
| **Space** | **O(1)**                                        |

### Walkthrough

`height = [1, 8, 6, 2, 5, 4, 8, 3, 7]`

| i   | j   | min(h[i], h[j]) | width | area | move        |
| --- | --- | --------------- | ----- | ---- | ----------- |
| 0   | 8   | 1               | 8     | 8    | i++ (1 < 7) |
| 1   | 8   | 7               | 7     | 49   | j-- (8 > 7) |
| 1   | 7   | 3               | 6     | 18   | j--         |
| 1   | 6   | 4               | 5     | 20   | j--         |
| 1   | 5   | 5               | 4     | 20   | j--         |
| 1   | 4   | 4               | 3     | 12   | j--         |
| 1   | 3   | 2               | 2     | 4    | j--         |
| 1   | 2   | 6               | 1     | 6    | j--         |

Max seen: **49** at `i=1, j=8`.

### Why move the shorter wall?

Area = `min(left, right) × width`.

When moving the **taller** wall inward:

- Width **decreases**
- `min(height)` stays capped by the **shorter** wall (unchanged)
- Area can only **shrink**

So the taller wall cannot be part of a better answer — discard it by moving the shorter pointer. The shorter side might find a taller wall that offsets the width loss.

When heights are **equal**, move either pointer — your code moves `i++`.

---

## Approach Comparison

| Approach     | Time  | Space | Notes       |
| ------------ | ----- | ----- | ----------- |
| Brute force  | O(n²) | O(1)  | TLE         |
| Two pointers | O(n)  | O(1)  | **Optimal** |

---

## Pattern Learned

**Pattern: Two Pointers — Greedy (Shrink From Ends)**

Start with extremes (max width), greedily eliminate choices that cannot improve the answer, move pointers inward.

**Signals in the problem:**

- Maximize/minimize a function of **two indices** `i` and `j`
- Answer depends on **both** `height[i]` and `height[j]` and distance `j - i`
- Brute force is O(n²) pairs
- Moving one pointer inward is safe when the other side **cannot** be optimal

**General template:**

```javascript
let left = 0,
  right = n - 1;
let best = 0;

while (left < right) {
  best = Math.max(best, compute(left, right));

  if (shouldMoveLeft(height, left, right)) {
    left++;
  } else {
    right--;
  }
}
```

**Different from [3Sum](./015-three-sum.md):**

|                | 3Sum                   | Container                       |
| -------------- | ---------------------- | ------------------------------- |
| Requires sort? | Yes                    | No                              |
| Pointer move   | Based on sum vs target | Based on **greedy elimination** |
| Goal           | Find all triplets      | Maximize area                   |

---

## Key Insight

Start wide, then only move the pointer that **might** help.

> **The shorter wall is the bottleneck. Moving the taller wall inward never increases area — always advance the shorter side.**

Width only goes down as pointers converge; the only hope for a larger area is a taller minimum height.

---

## Follow-Up Questions

Problems using two pointers from both ends:

| Problem                                                                                               | Twist                                                   |
| ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| [3Sum](./015-three-sum.md)                                                                            | Sort + two pointers on sum                              |
| [Trapping Rain Water](https://leetcode.com/problems/trapping-rain-water/)                             | Water trapped between bars — two pointers or prefix max |
| [Two Sum II — Input Array Is Sorted](https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/) | Move based on sum vs target                             |
| [Valid Palindrome](https://leetcode.com/problems/valid-palindrome/)                                   | Shrink from ends while matching                         |
| [Largest Rectangle in Histogram](https://leetcode.com/problems/largest-rectangle-in-histogram/)       | Monotonic stack — harder area variant                   |

### Interview Variants

- **Prove why moving the shorter side is correct** — taller side cannot improve min height; width loss is guaranteed.
- **What if equal heights?** — move either; same reasoning.
- **Return the two indices**, not just area — track `i`, `j` when updating `res`.
- **Brute force first?** — fine to mention O(n²), then optimize to two pointers.
- **Difference from Trapping Rain Water?** — container uses **two** walls; trapping sums water **between** many walls with a different formula.

---

## Common Pitfalls

- **Moving the taller pointer** — skips valid answers is wrong reasoning; moving taller is safe but **moving shorter is the required greedy choice** (moving taller wastes the step).
- **Wrong area formula** — use `min(height[i], height[j])`, not `max` or product of both heights.
- **Off-by-one on width** — `(j - i)` is correct for indices `i` and `j`.
- **Starting pointers wrong** — must start `0` and `n-1` for max initial width.
- **Confusing with 3Sum pointer logic** — here movement is greedy on height, not sum comparison.
- **Integer overflow** — rare on LeetCode; `area` can be large (`n` up to 10⁵, heights up to 10⁴).
