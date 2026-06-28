# 153. Find Minimum in Rotated Sorted Array

**Link:** [Find Minimum in Rotated Sorted Array](https://leetcode.com/problems/find-minimum-in-rotated-sorted-array/description/)  
**Difficulty:** Medium  
**Tags:** Array, Binary Search

## Problem Summary

A sorted array of **unique** integers is rotated at an unknown pivot (e.g. `[4, 5, 6, 7, 0, 1, 2]`). Return the **minimum** element.

The array has no duplicates. Rotation means some suffix was moved to the front without changing internal order.

---

## Approach 1: Linear Scan

If the array is still sorted (`nums[0] < nums[n-1]`), the minimum is `nums[0]`. Otherwise, walk until you find the **drop** where `nums[i] < nums[i-1]` — that index is the rotation pivot (minimum).

### Code

```javascript
/**
 * @param {number[]} nums
 * @return {number}
 */
var findMin = function (nums) {
  if (nums[0] < nums[nums.length - 1] || nums.length == 1) {
    return nums[0];
  } else {
    for (let i = 1; i < nums.length; i++) {
      if (nums[i] < nums[i - 1]) {
        return nums[i];
      }
    }
  }
};
```

### Complexity

|           |                                          |
| --------- | ---------------------------------------- |
| **Time**  | **O(n)** — worst case scans entire array |
| **Space** | **O(1)**                                 |

### Walkthrough

`nums = [4, 5, 6, 7, 0, 1, 2]`

- `nums[0] < nums[n-1]`? `4 < 2` → false (rotated)
- `i = 1..6`: first drop at `i = 4` where `0 < 1` is false... wait `nums[4]=0`, `nums[3]=7`, `0 < 7` → return `0`

### Trade-off

Simple and correct, but linear time. Binary search is the intended O(log n) solution.

---

## Approach 2: Binary Search (Best)

Compare `nums[mid]` with `nums[right]` to decide which half contains the minimum.

### Code

```javascript
/**
 * @param {number[]} nums
 * @return {number}
 */
var findMin = function (nums) {
  if (nums[0] < nums[nums.length - 1] || nums.length === 1) {
    return nums[0];
  }

  let left = 0;
  let right = nums.length - 1;

  while (left < right) {
    let middle = Math.floor((left + right) / 2);

    if (nums[middle] > nums[right]) {
      left = middle + 1;
    } else {
      right = middle;
    }
  }

  return nums[left];
};
```

### Complexity

|           |                                             |
| --------- | ------------------------------------------- |
| **Time**  | **O(log n)** — halve search space each step |
| **Space** | **O(1)**                                    |

### Why compare with `nums[right]` (not `nums[left]`)?

`nums[right]` is always in the **right half** of the current window. Comparing `mid` to `right` tells you whether the drop (minimum) lies to the right of `mid`.

| Condition                  | Meaning                                                                            | Action           |
| -------------------------- | ---------------------------------------------------------------------------------- | ---------------- |
| `nums[mid] > nums[right]`  | `mid` is in the **left (larger)** sorted segment; min is to the right              | `left = mid + 1` |
| `nums[mid] <= nums[right]` | `mid` is in the **right (smaller)** segment or at the min; min is at `mid` or left | `right = mid`    |

### Walkthrough

`nums = [4, 5, 6, 7, 0, 1, 2]`

| left | right | mid | nums[mid] | nums[right] | action             |
| ---- | ----- | --- | --------- | ----------- | ------------------ |
| 0    | 6     | 3   | 7         | 2           | 7 > 2 → left = 4   |
| 4    | 6     | 5   | 1         | 2           | 1 <= 2 → right = 5 |
| 4    | 5     | 4   | 0         | 1           | 0 <= 1 → right = 4 |

`left === right === 4` → **`nums[4] = 0`**

### Your two fixes (why they matter)

1. **`while (left < right)`** — stops when pointers converge on the minimum; `left === right` is the answer.
2. **`right = middle`** (not `middle - 1`) — `middle` might _be_ the minimum; discarding it causes wrong answers.

---

## Approach Comparison

| Approach      | Time     | Space | Notes                     |
| ------------- | -------- | ----- | ------------------------- |
| Linear scan   | O(n)     | O(1)  | Simple; good sanity check |
| Binary search | O(log n) | O(1)  | **Interview target**      |

The early `nums[0] < nums[n-1]` check is optional for binary search (the loop handles it) but avoids extra iterations on unrotated arrays.

---

## Pattern Learned

**Pattern: Binary Search on Rotated Sorted Array**

Standard binary search looks for an exact target. On a rotated array, compare `mid` with a **boundary** (`left` or `right`) to learn which half is sorted and where the pivot lives.

**Signals in the problem:**

- Sorted array, **rotated** at unknown pivot
- Find min, max, or target in O(log n)
- No duplicates (153); duplicates complicate logic (154)

**Template (find minimum — compare with right):**

```javascript
let left = 0,
  right = nums.length - 1;

while (left < right) {
  const mid = Math.floor((left + right) / 2);

  if (nums[mid] > nums[right]) {
    left = mid + 1; // min in right half
  } else {
    right = mid; // min at mid or left
  }
}

return nums[left];
```

**Alternative (compare with left)** — used more in "search target" variants:

```javascript
if (nums[mid] > nums[right]) {
  left = mid + 1;
} else if (nums[mid] < nums[left]) {
  right = mid - 1;
} else {
  // nums[mid] in sorted portion — narrow toward min
  right = mid;
}
```

For **find min**, comparing `mid` vs `right` is the cleanest form.

---

## Key Insight

In a rotated sorted array, there is exactly one **inflection point** where `nums[i] < nums[i-1]` — that value is the minimum.

Binary search finds it by asking: _"Is `mid` sitting in the larger left segment or the smaller right segment?"_  
Compare `nums[mid]` to `nums[right]` — the drop always lies in the half where values "wrap around."

---

## Follow-Up Questions

Problems using rotated-array binary search:

| Problem                                                                                                                           | Twist                                                             |
| --------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| [Search in Rotated Sorted Array](https://leetcode.com/problems/search-in-rotated-sorted-array/)                                   | Find target index — identify sorted half, then check target range |
| [Find Minimum in Rotated Sorted Array II](https://leetcode.com/problems/find-minimum-in-rotated-sorted-array-ii/)                 | **Duplicates** — `nums[mid] === nums[right]` → `right--`          |
| [Search in Rotated Sorted Array II](https://leetcode.com/problems/search-in-rotated-sorted-array-ii/)                             | Duplicates — same shrink trick                                    |
| [Find Peak Element](https://leetcode.com/problems/find-peak-element/)                                                             | Binary search on "which half has the peak"                        |
| [Find First and Last Position of Element](https://leetcode.com/problems/find-first-and-last-position-of-element-in-sorted-array/) | Classic binary search boundaries                                  |

### Interview Variants

- **Can you skip the sorted check?** — Yes; `while (left < right)` alone works for rotated arrays.
- **Why not `right = mid - 1`?** — You may discard the minimum when `mid` is the pivot.
- **Why compare to `right` not `left`?** — Both work with correct branches; `mid` vs `right` is simpler for find-min.
- **What if duplicates exist?** — When `nums[mid] === nums[right]`, shrink `right--` (can't decide which half).
- **Return the pivot index** — same algorithm; return `left` instead of `nums[left]`.

---

## Common Pitfalls

- **`while (left <= right)` with `right = mid`** — can infinite-loop; use `left < right` for find-min.
- **`right = mid - 1` when min could be `mid`** — wrong answer; use `right = mid`.
- **`left = mid + 1` when `nums[mid] > nums[right]`** — correct; min is strictly right of `mid`.
- **Comparing `mid` to `left` with wrong branches** — easy to invert; stick to `mid` vs `right` for min.
- **Duplicates (154)** — `nums[mid] === nums[right]` requires `right--`; O(n) worst case.
- **Assuming rotation always happened** — `nums[0] < nums[n-1]` means no rotation; min is `nums[0]`.
