# 217. Contains Duplicate

**Link:** [Contains Duplicate](https://leetcode.com/problems/contains-duplicate/description/)  
**Difficulty:** Easy  
**Tags:** Array, Hash Table, Sorting

## Problem Summary

Given an integer array `nums`, return `true` if any value appears **at least twice**, and `false` if every element is distinct.

---

## Approach 1: Brute Force

Compare every pair of elements `(i, j)` where `i < j`. Return `true` on the first match.

### Code

```javascript
/**
 * @param {number[]} nums
 * @return {boolean}
 */
var containsDuplicate = function (nums) {
  for (let i = 0; i < nums.length - 1; i++) {
    for (let j = i + 1; j < nums.length; j++) {
      if (nums[i] == nums[j]) {
        return true;
      }
    }
  }

  return false;
};
```

### Complexity

|           |                                |
| --------- | ------------------------------ |
| **Time**  | **O(n²)** — all pairs checked  |
| **Space** | **O(1)** — no extra structures |

### Why This Works / Doesn't Scale

Correct and needs no extra memory, but repeats comparisons. For large `n`, quadratic time is too slow.

---

## Approach 2: Sort and Scan Adjacent

Sort the array so duplicates become neighbors. One pass comparing `nums[j]` with `nums[j - 1]` is enough.

### Code

```javascript
/**
 * @param {number[]} nums
 * @return {boolean}
 */
var containsDuplicate = function (nums) {
  nums.sort((a, b) => a - b);

  for (let j = 1; j < nums.length; j++) {
    if (nums[j - 1] == nums[j]) {
      return true;
    }
  }

  return false;
};
```

### Complexity

|           |                                                                         |
| --------- | ----------------------------------------------------------------------- |
| **Time**  | **O(n log n)** — dominated by sorting                                   |
| **Space** | **O(1)** or **O(n)** — depends on sort implementation (in-place vs not) |

### Walkthrough

`nums = [1, 2, 3, 1]` → after sort: `[1, 1, 2, 3]`

| j   | nums[j-1] | nums[j] | match?              |
| --- | --------- | ------- | ------------------- |
| 1   | 1         | 1       | yes → return `true` |

### Trade-off

Faster than brute force, uses little extra space (if sort is in-place), but **mutates the input** and still slower than a hash set.

---

## Approach 3: Hash Set — Iterative (Early Exit)

Track seen values. If the current number is already in the set, a duplicate exists. Can return immediately on first duplicate.

### Code

```javascript
/**
 * @param {number[]} nums
 * @return {boolean}
 */
var containsDuplicate = function (nums) {
  let s = new Set();

  for (let i = 0; i < nums.length; i++) {
    if (s.has(nums[i])) {
      return true;
    }

    s.add(nums[i]);
  }

  return false;
};
```

### Complexity

|           |                                                         |
| --------- | ------------------------------------------------------- |
| **Time**  | **O(n)** — single pass; set operations are O(1) average |
| **Space** | **O(n)** — set stores up to n unique values             |

### Walkthrough

`nums = [1, 2, 3, 1]`

| i   | nums[i] | set before  | action                   |
| --- | ------- | ----------- | ------------------------ |
| 0   | 1       | `{}`        | add 1                    |
| 1   | 2       | `{1}`       | add 2                    |
| 2   | 3       | `{1, 2}`    | add 3                    |
| 3   | 1       | `{1, 2, 3}` | `1` seen → return `true` |

---

## Approach 4: Hash Set — Size Check (One-Liner)

A `Set` only keeps **unique** values. If any duplicate exists, unique count is less than array length.

### Code

```javascript
/**
 * @param {number[]} nums
 * @return {boolean}
 */
var containsDuplicate = function (nums) {
  return new Set(nums).size != nums.length;
};
```

### Complexity

|           |                                                    |
| --------- | -------------------------------------------------- |
| **Time**  | **O(n)** — `Set` constructor iterates all elements |
| **Space** | **O(n)** — set holds up to n unique values         |

### Walkthrough

`nums = [1, 2, 3, 1]`

- `new Set(nums)` → `{1, 2, 3}` (size **3**)
- `nums.length` → **4**
- `3 != 4` → **`true`**

`nums = [1, 2, 3, 4]`

- Set size **4**, length **4** → **`false`**

### vs Approach 3

|                 | Iterative set                    | Size one-liner                          |
| --------------- | -------------------------------- | --------------------------------------- |
| **Early exit**  | Yes — stops on first duplicate   | No — always builds full set             |
| **Readability** | More verbose                     | Idiomatic, shortest                     |
| **Best when**   | Duplicates likely early in array | Code clarity matters; full scan is fine |

Both are O(n) and valid interview answers.

---

## Approach Comparison

| Approach         | Time       | Space  | Mutates input? | Early exit? |
| ---------------- | ---------- | ------ | -------------- | ----------- |
| Brute force      | O(n²)      | O(1)   | No             | Yes         |
| Sort + scan      | O(n log n) | O(1)\* | Yes            | Yes         |
| Set — iterative  | O(n)       | O(n)   | No             | Yes         |
| Set — size check | O(n)       | O(n)   | No             | No          |

\*Space depends on in-place sort.

**When to pick which:**

- **Shortest / cleanest:** size one-liner — `new Set(nums).size != nums.length`
- **Early exit matters:** iterative set loop
- **Memory constrained, can mutate:** sort

---

## Pattern Learned

**Pattern: Hash Set — Membership / Duplicate Detection**

Use a set when you need **O(1) "have I seen this before?"** checks while scanning.

**Signals in the problem:**

- "Contains duplicate", "unique", "distinct"
- "Have we seen this element/value before?"
- Brute force compares all pairs → O(n²)

**General templates:**

```javascript
// Iterative — early exit
const seen = new Set();
for (const x of nums) {
  if (seen.has(x)) return true;
  seen.add(x);
}
return false;

// One-liner — unique count vs length
return new Set(nums).size !== nums.length;
```

**Related pattern: Sort + Scan Adjacent**

When duplicates must end up next to each other, sorting groups equal values together. Useful when you cannot use extra space but can sort.

---

## Key Insight

Duplicate detection is a **membership problem**, not a pairing problem.

A set stores only unique values — so `set.size < nums.length` means something appeared twice. You can check that in one line, or loop and exit early when you see a repeat.

---

## Follow-Up Questions

Problems that build on duplicate detection:

| Problem                                                                                           | Twist                                                                   |
| ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| [Contains Duplicate II](https://leetcode.com/problems/contains-duplicate-ii/)                     | Duplicate indices must be at most `k` apart — set + sliding window      |
| [Contains Duplicate III](https://leetcode.com/problems/contains-duplicate-iii/)                   | Indices within `k` and values within `t` — sorted set / bucket / window |
| [Valid Anagram](https://leetcode.com/problems/valid-anagram/)                                     | Two strings — frequency map or sort                                     |
| [Group Anagrams](https://leetcode.com/problems/group-anagrams/)                                   | Group by sorted string or frequency signature                           |
| [Find All Duplicates in an Array](https://leetcode.com/problems/find-all-duplicates-in-an-array/) | O(1) extra space — mark visited using index negation                    |
| [Single Number](https://leetcode.com/problems/single-number/)                                     | Every element appears twice except one — XOR                            |
| [Intersection of Two Arrays](https://leetcode.com/problems/intersection-of-two-arrays/)           | Common elements — set intersection                                      |
| [Happy Number](https://leetcode.com/problems/happy-number/)                                       | Cycle detection — set of seen sums                                      |

### Interview Variants

- **Return the duplicate value(s)** — collect in a set or array instead of returning boolean.
- **Count duplicates** — use a `Map` for frequencies.
- **What if array is sorted?** — single O(n) scan, no set needed.
- **What if you cannot use extra space and cannot mutate?** — harder; may need sorting copy or bit tricks for bounded ranges.
- **Sort vs set — which do you prefer?** — set for time; sort when space is tight and mutation is OK.

---

## Common Pitfalls

- **Mutating input with sort** — breaks code that relies on original order elsewhere.
- **Using `==` vs `===`** — fine for integers; be careful with objects/NaN edge cases.
- **Forgetting early return** — set approach can exit as soon as duplicate is found (efficient).
- **One-liner `Set` size trick** — must scan entire array; no early exit (still O(n)).
- **Confusing with Contains Duplicate II** — that problem adds a **distance constraint**; a plain set is not enough.
