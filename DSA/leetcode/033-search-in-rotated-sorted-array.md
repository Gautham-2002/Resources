# 33. Search in Rotated Sorted Array

**Link:** [Search in Rotated Sorted Array](https://leetcode.com/problems/search-in-rotated-sorted-array/description/)  
**Difficulty:** Medium  
**Tags:** Array, Binary Search

## Problem Summary

A sorted array of **unique** integers is rotated at an unknown pivot. Given `target`, return its index or `-1` if not present. Must run in **O(log n)** time.

---

## Approach: Modified Binary Search (Template A)

At each step, one half `[left..mid]` or `[mid..right]` is **always sorted**. Check whether `target` lies in the sorted half; if yes, search there, else search the other half.

### Code

```javascript
/**
 * @param {number[]} nums
 * @param {number} target
 * @return {number}
 */
var search = function (nums, target) {
  let left = 0;
  let right = nums.length - 1;

  while (left <= right) {
    let middle = Math.floor((left + right) / 2);

    if (nums[middle] == target) return middle;

    if (nums[left] <= nums[middle]) {
      // Left half [left..mid] is sorted
      if (nums[middle] > target && target >= nums[left]) {
        right = middle - 1;
      } else {
        left = middle + 1;
      }
    } else if (nums[middle] <= nums[right]) {
      // Right half [mid..right] is sorted
      if (nums[middle] < target && target <= nums[right]) {
        left = middle + 1;
      } else {
        right = middle - 1;
      }
    } else {
      break;
    }
  }

  return -1;
};
```

### Complexity

|           |                                             |
| --------- | ------------------------------------------- |
| **Time**  | **O(log n)** — halve search space each step |
| **Space** | **O(1)**                                    |

---

## Decision Tree (Memorize This)

```
nums[mid] === target  →  return mid

nums[left] <= nums[mid]   (left half sorted)
  target in [nums[left], nums[mid])  →  search left:  right = mid - 1
  else                               →  search right: left  = mid + 1

else                      (right half sorted)
  target in (nums[mid], nums[right]]  →  search right: left  = mid + 1
  else                                →  search left:  right = mid - 1
```

**Why `nums[mid] > target` on the left (not `>=`)?**  
You already returned when `nums[mid] === target`. The sorted left range is `[left, mid)`, excluding `mid`.

**Why `nums[middle] < target` on the right?**  
Sorted right range is `(mid, right]`, excluding `mid`.

---

## Walkthrough

`nums = [4, 5, 6, 7, 0, 1, 2]`, `target = 0`

| left | right | mid | nums[mid] | sorted half | target in half? | move         |
| ---- | ----- | --- | --------- | ----------- | --------------- | ------------ |
| 0    | 6     | 3   | 7         | left [4,7]  | 0 in [4,7)? no  | left = 4     |
| 4    | 6     | 5   | 1         | left [0,1]  | 0 in [0,1)? yes | right = 4    |
| 4    | 4     | 4   | **0**     | —           | found           | return **4** |

`nums = [4, 5, 6, 7, 0, 1, 2]`, `target = 3` → returns **-1**

---

## Why Your Code Does NOT Infinite Loop

You use **Template A** consistently:

| Piece       | Your code               | Safe?                       |
| ----------- | ----------------------- | --------------------------- |
| Loop        | `while (left <= right)` | Yes for exact search        |
| Discard mid | always `mid ± 1`        | Yes — window always shrinks |
| Keep mid    | never `right = mid`     | Correct for Template A      |

Every iteration either returns or moves `left` to `mid + 1` or `right` to `mid - 1`. The window `[left, right]` gets strictly smaller until empty.

**The `else break` branch** is dead code on valid rotated unique arrays — if both `nums[left] <= nums[mid]` and `nums[middle] <= nums[right]` fail, the subarray is strictly decreasing (impossible here). Safe to remove.

---

## Avoiding Infinite Loops (Read This When Confused)

Full guide: **[Binary Search Safety Guide](../binary-search-safety-guide.md)**

### The mistake that causes loops

Mixing two templates:

| Wrong combo                                | What happens                               |
| ------------------------------------------ | ------------------------------------------ |
| `while (left <= right)` + `right = mid`    | `left` and `right` can stall on same `mid` |
| `while (left < right)` + `right = mid - 1` | may skip the answer                        |
| `left = mid` without proof                 | infinite loop when `mid === left`          |

### This problem vs [Find Minimum (153)](./153-find-minimum-in-rotated-sorted-array.md)

|                 | Search (33)     | Find Min (153)                    |
| --------------- | --------------- | --------------------------------- |
| **Goal**        | exact index     | minimum value                     |
| **Template**    | A               | B                                 |
| **Loop**        | `left <= right` | `left < right`                    |
| **Discard mid** | `mid ± 1`       | `left = mid + 1` or `right = mid` |

**Same rotated array, different templates — that is why the updates feel different.**

### 30-second checklist before submitting

1. Am I finding an **exact** target? → Template A → `<=` + `mid±1`
2. Am I finding a **boundary/min**? → Template B → `<` + `right=mid`
3. Does every branch shrink `[left, right]`?
4. **Size-2 smoke test:** run `[1, 3]` target `0` — if it loops, pointer pairing is wrong (see [Binary Search Safety Guide](../binary-search-safety-guide.md))
5. Trace a 5-element rotated case by hand for logic correctness

---

## Pattern Learned

**Pattern: Binary Search on Rotated Sorted Array — Identify Sorted Half**

One half is always normally sorted. Use that half to decide whether `target` can live there.

**Signals:**

- Sorted data, rotated pivot, O(log n) required
- Not plain binary search — need to detect which side is sorted
- Unique elements (33); duplicates need extra handling (81)

**Template A code skeleton:**

```javascript
while (left <= right) {
  const mid = Math.floor((left + right) / 2);
  if (nums[mid] === target) return mid;

  if (nums[left] <= nums[mid]) {
    if (target >= nums[left] && target < nums[mid]) right = mid - 1;
    else left = mid + 1;
  } else {
    if (target > nums[mid] && target <= nums[right]) left = mid + 1;
    else right = mid - 1;
  }
}
return -1;
```

---

## Key Insight

You don't need to find the pivot first.

At any `mid`, **at least one half is sorted**. That sorted half gives you a normal binary-search range check — narrow to the half that _could_ contain `target`.

---

## Follow-Up Questions

| Problem                                                                                                    | Twist                                                   |
| ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| [153 — Find Minimum in Rotated Sorted Array](./153-find-minimum-in-rotated-sorted-array.md)                | Template B — compare `mid` vs `right`                   |
| [81 — Search in Rotated Sorted Array II](https://leetcode.com/problems/search-in-rotated-sorted-array-ii/) | Duplicates → `right--` when `nums[mid] === nums[right]` |
| [154 — Find Minimum II](https://leetcode.com/problems/find-minimum-in-rotated-sorted-array-ii/)            | Same duplicate shrink                                   |
| [704 — Binary Search](https://leetcode.com/problems/binary-search/)                                        | Plain Template A baseline                               |

### Interview Variants

- **Find pivot index first, then two binary searches** — valid O(log n), more code.
- **Why `nums[left] <= nums[mid]` not `<`?** — when `left === mid`, `<=` correctly marks one-element half as sorted.
- **What if array not rotated?** — one half always fully sorted; still works.

---

## Common Pitfalls

- **Infinite loop** — mixing Template A loop with Template B updates (see safety guide).
- **Wrong sorted-half check** — inverted `<` / `<=` on target range.
- **Including `mid` in range after equality check** — use `[left, mid)` and `(mid, right]`.
- **Using find-min logic here** — `right = mid` is wrong for exact search with `left <= right`.
- **Forgetting unrotated case** — `[1,2,3,4,5]` must still work.
