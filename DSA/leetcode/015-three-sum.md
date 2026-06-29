# 15. 3Sum

**Link:** [3Sum](https://leetcode.com/problems/3sum/description/)  
**Difficulty:** Medium  
**Tags:** Array, Two Pointers, Sorting

## Problem Summary

Given an integer array `nums`, return all **unique triplets** `[nums[i], nums[j], nums[k]]` such that:

- `i != j`, `i != k`, `j != k`
- `nums[i] + nums[j] + nums[k] == 0`

The solution set must not contain duplicate triplets.

---

## Approach 1: Brute Force (Reference)

Check every triple `(i, j, k)` with `i < j < k`. Use a set or sort results to deduplicate.

### Complexity

|           |                               |
| --------- | ----------------------------- |
| **Time**  | **O(n³)** — all triplets      |
| **Space** | **O(k)** — output + dedup set |

Too slow for large inputs. Included for comparison only.

---

## Approach 2: Sort + Fix One + Two Pointers (Best)

Sort the array. Fix the first element at index `i`, then run **two pointers** on the remaining subarray to find pairs that sum to `-nums[i]` — a classic reduction from 3Sum to [Two Sum](./001-two-sum.md).

### Code

```javascript
/**
 * @param {number[]} nums
 * @return {number[][]}
 */
var threeSum = function (nums) {
  nums.sort((a, b) => a - b);

  let res = [];

  for (let i = 0; i < nums.length - 2; i++) {
    if (nums[i] > 0) break;

    if (i > 0 && nums[i] == nums[i - 1]) continue;

    let j = i + 1,
      k = nums.length - 1;
    while (j < k) {
      if (nums[i] + nums[j] + nums[k] == 0) {
        res.push([nums[i], nums[j], nums[k]]);
        while (j < k && nums[j] == nums[j + 1]) {
          j++;
        }

        while (j < k && nums[k] == nums[k - 1]) {
          k--;
        }

        j++;
        k--;
      } else if (nums[i] + nums[j] + nums[k] < 0) {
        j++;
      } else {
        k--;
      }
    }
  }

  return res;
};
```

### Complexity

|           |                                                                          |
| --------- | ------------------------------------------------------------------------ |
| **Time**  | **O(n²)** — O(n log n) sort + O(n) outer loop × O(n) two pointers        |
| **Space** | **O(1)** extra — excluding output and sort stack (sort may use O(log n)) |

### Walkthrough

`nums = [-1, 0, 1, 2, -1, -4]` → sorted: `[-4, -1, -1, 0, 1, 2]`

**i = 0** (`nums[i] = -4`): need sum `4`
| j | k | sum | action |
| --- | --- | --- | --- |
| 1 | 5 | 3 | j++ |
| 2 | 5 | 4 | j++ |
| 3 | 5 | 5 | j++ |
| 4 | 5 | 7 | k-- |
| ... | | | no triplet |

**i = 1** (`nums[i] = -1`): need sum `1`
| j | k | sum | action |
| --- | --- | --- | --- |
| 2 | 5 | 2 | k-- |
| 2 | 4 | **0** | push `[-1,-1,2]`, skip dupes, j++, k-- |
| 3 | 3 | — | j < k fails |

**i = 2**: skip — `nums[2] == nums[1]` (duplicate `i`)

**i = 3** (`nums[i] = 0`): need sum `0`
| j | k | sum | action |
| --- | --- | --- | --- |
| 4 | 5 | 1 | k-- |
| 4 | 4 | — | stop |

Result: `[[-1, -1, 2], [-1, 0, 1]]`

### Three optimizations in your code

| Optimization                                  | Why                                                          |
| --------------------------------------------- | ------------------------------------------------------------ |
| `if (nums[i] > 0) break`                      | Array sorted — remaining values are positive; sum can't be 0 |
| `if (i > 0 && nums[i] == nums[i-1]) continue` | Skip duplicate first elements                                |
| Skip dupes on `j` and `k` after a match       | Avoid duplicate triplets in result                           |

---

## Approach Comparison

| Approach                | Time  | Space              | Dedup                  |
| ----------------------- | ----- | ------------------ | ---------------------- |
| Brute force             | O(n³) | O(k)               | Set or sort output     |
| Sort + two pointers     | O(n²) | O(1) extra         | Skip duplicates inline |
| Sort + hash map per `i` | O(n²) | O(n) per iteration | Harder dedup           |

---

## Pattern Learned

**Pattern: Sort + Two Pointers (K-Sum Reduction)**

Fix `k-2` elements with an outer loop, then solve the remaining **2Sum** with two pointers on the sorted subarray.

```
3Sum → fix i, two-pointer 2Sum on [i+1 .. n-1] targeting -nums[i]
4Sum → fix i, fix j, two-pointer 2Sum on [j+1 .. n-1]
```

**Signals in the problem:**

- Find **all unique triplets/quads** with a sum condition
- Duplicates must be avoided in output
- Brute force is O(n³) or O(n⁴)
- Sorting enables two-pointer movement

**Two-pointer rules (sorted array, target sum = `T`):**

```javascript
while (left < right) {
  const sum = nums[left] + nums[right];
  if (sum === T) {
    // record, skip duplicates, move both
    left++;
    right--;
  } else if (sum < T) {
    left++; // need larger sum
  } else {
    right--; // need smaller sum
  }
}
```

**Relation to [Two Sum](./001-two-sum.md):**

|            | Two Sum                                  | 3Sum                          |
| ---------- | ---------------------------------------- | ----------------------------- |
| Target     | `target`                                 | `0` (via `-nums[i]`)          |
| Method     | Hash map **or** two pointers (if sorted) | Sort + fix one + two pointers |
| Duplicates | Usually one answer                       | Must skip at `i`, `j`, `k`    |

---

## Key Insight

Sorting turns the problem from "check all triplets" into "for each first value, find two others with a two-pointer scan."

Duplicates are handled **during** the search by skipping repeated values at each level — not after collecting results.

> **Fix one element → reduce to 2Sum → move pointers based on whether sum is too small or too large.**

---

## Follow-Up Questions

Problems extending k-sum / two-pointer patterns:

| Problem                                                                                               | Twist                                  |
| ----------------------------------------------------------------------------------------------------- | -------------------------------------- |
| [Two Sum](./001-two-sum.md)                                                                           | Base case — hash map or two pointers   |
| [Two Sum II — Input Array Is Sorted](https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/) | Two pointers only; return indices      |
| [3Sum Closest](https://leetcode.com/problems/3sum-closest/)                                           | Track closest sum to target, not exact |
| [4Sum](https://leetcode.com/problems/4sum/)                                                           | Fix `i` and `j`, two pointers for rest |
| [4Sum II](https://leetcode.com/problems/4sum-ii/)                                                     | Four separate arrays — hash map on two |
| [Container With Most Water](https://leetcode.com/problems/container-with-most-water/)                 | Two pointers on heights                |
| [Trapping Rain Water](https://leetcode.com/problems/trapping-rain-water/)                             | Two pointers / prefix max              |
| [Valid Triangle Number](https://leetcode.com/problems/valid-triangle-number/)                         | Sort + two pointers count              |

### Interview Variants

- **Return count instead of triplets** — same logic, increment counter instead of push.
- **3Sum with target `T` (not 0)** — two-pointer target becomes `T - nums[i]`.
- **Can you use a hash map for 3Sum?** — yes O(n²), but dedup is messier than sort + pointers.
- **Why sort first?** — enables duplicate skipping and two-pointer O(n) scan per fixed `i`.
- **Why `break` when `nums[i] > 0`?** — sorted array; all later `i` values are positive too.

---

## Common Pitfalls

- **Forgetting to sort** — two pointers require sorted order.
- **Duplicate triplets** — skip `i`, `j`, `k` duplicates; don't only dedup at the end.
- **Using `continue` on `i` without `i > 0` guard** — skips `i = 0` incorrectly if you check `nums[i] == nums[i-1]` when `i === 0`.
- **Not moving both pointers after a match** — infinite loop on same triplet.
- **Wrong pointer movement** — sum too small → `j++`; too large → `k--`.
- **Off-by-one on outer loop** — stop at `i < nums.length - 2` (need room for `j` and `k`).
- **Confusing with Two Sum hash map** — 3Sum dedup is easier with sort + skip.
