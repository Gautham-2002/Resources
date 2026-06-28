# 1. Two Sum

**Link:** [Two Sum](https://leetcode.com/problems/two-sum/description/)  
**Difficulty:** Easy  
**Tags:** Array, Hash Table

## Problem Summary

Given an array of integers `nums` and an integer `target`, return the **indices** of two distinct elements that add up to `target`. Exactly one solution exists, and you may not use the same element twice.

---

## Approach 1: Brute Force

Check every pair of indices `(i, j)` where `i < j` and see if their values sum to `target`.

### Code

```javascript
/**
 * @param {number[]} nums
 * @param {number} target
 * @return {number[]}
 */
var twoSum = function (nums, target) {
  let pair = [];

  for (let i = 0; i < nums.length - 1; i++) {
    for (let j = i + 1; j < nums.length; j++) {
      if (nums[i] + nums[j] == target) {
        pair.push(i, j);
        break;
      }
    }
  }

  return pair;
};
```

### Complexity

|           |                                                                                          |
| --------- | ---------------------------------------------------------------------------------------- |
| **Time**  | **O(n²)** — nested loops visit up to n(n−1)/2 pairs                                      |
| **Space** | **O(1)** — only a fixed-size result array (output is not counted toward auxiliary space) |

### Why This Works / Doesn't Scale

Correct and simple, but redundant work: for each `nums[i]`, you re-scan the rest of the array instead of remembering what you've already seen.

---

## Approach 2: Hash Map (One Pass)

For each element, ask: **"Have I already seen the complement `target - nums[i]`?"**  
Store each value's index in a map keyed by the complement you still need.

### Code

```javascript
/**
 * @param {number[]} nums
 * @param {number} target
 * @return {number[]}
 */
var twoSum = function (nums, target) {
  let map = {};

  for (let i = 0; i < nums.length; i++) {
    if (nums[i] in map) {
      return [map[nums[i]], i];
    }

    map[target - nums[i]] = i;
  }

  return [];
};
```

### Complexity

|           |                                                           |
| --------- | --------------------------------------------------------- |
| **Time**  | **O(n)** — single pass; map lookup/insert is O(1) average |
| **Space** | **O(n)** — map stores up to n entries in the worst case   |

### Walkthrough

`nums = [2, 7, 11, 15]`, `target = 9`

| i   | nums[i] | complement needed | map (before) | action                       |
| --- | ------- | ----------------- | ------------ | ---------------------------- |
| 0   | 2       | 7                 | `{}`         | map `{7: 0}`                 |
| 1   | 7       | 2                 | `{7: 0}`     | `7 in map` → return `[0, 1]` |

**How the map works:** at index `i`, you store `map[target - nums[i]] = i`.  
So when you later see `nums[j]`, checking `nums[j] in map` means: _"Was `nums[j]` the complement someone earlier was waiting for?"_

---

## Pattern Learned

**Pattern: Hash Map — Complement Lookup**

Use a hash map when you need **O(1) lookups** for a value you've seen before (or a value derived from the current element).

**Signals in the problem:**

- "Find two elements that satisfy X" (sum, difference, product)
- "Have we seen this before?"
- Brute force is O(n²) from nested scanning

**General template:**

```javascript
const seen = new Map(); // or {}

for (let i = 0; i < nums.length; i++) {
  const complement = target - nums[i]; // derive what you need

  if (seen.has(nums[i])) {
    return [seen.get(nums[i]), i];
  }

  seen.set(complement, i);
}
```

**Core trade-off:** spend O(n) extra space to avoid O(n) repeated scanning → total time drops from O(n²) to O(n).

---

## Key Insight

Don't search forward for a partner every time. **Remember past elements** so each new number can be matched instantly:

> For each `nums[i]`, the partner is `target - nums[i]`.  
> Store complements as you go; match on sight.

---

## Follow-Up Questions

Problems that reuse or extend this pattern:

| Problem                                                                                                 | Twist                                                           |
| ------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| [Two Sum II — Input Array Is Sorted](https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/)   | Sorted array → **two pointers** instead of hash map; O(1) space |
| [Two Sum III — Data Structure Design](https://leetcode.com/problems/two-sum-iii-data-structure-design/) | Design `add()` / `find()` with hash set of values               |
| [Two Sum IV — Input Is a BST](https://leetcode.com/problems/two-sum-iv-input-is-a-bst/)                 | Tree traversal + hash set                                       |
| [3Sum](https://leetcode.com/problems/3sum/)                                                             | Fix one element, then two-sum on the rest (sort + two pointers) |
| [4Sum](https://leetcode.com/problems/4sum/)                                                             | Same idea, one more outer loop                                  |
| [Subarray Sum Equals K](https://leetcode.com/problems/subarray-sum-equals-k/)                           | Prefix sum + hash map (count complements)                       |
| [Valid Anagram](https://leetcode.com/problems/valid-anagram/)                                           | Frequency hash map                                              |
| [Contains Duplicate II](https://leetcode.com/problems/contains-duplicate-ii/)                           | Hash map with index/window constraint                           |
| [Group Anagrams](https://leetcode.com/problems/group-anagrams/)                                         | Hash map keyed by sorted string or frequency signature          |

### Interview Variants

- **Return the values instead of indices** — same logic, return `[nums[i], nums[j]]`.
- **What if there are multiple pairs?** — collect all pairs; watch for duplicate index usage.
- **What if the array is sorted?** — two pointers; no extra space.
- **What if inputs don't fit in memory?** — external sort, or hash the smaller of two files/streams.
- **Can you do it in one pass?** — yes, the hash map approach above.
- **Why `map[target - nums[i]] = i` instead of `map[nums[i]] = i`?** — both work; this version checks whether the _current_ value was previously needed as a complement.

---

## Common Pitfalls

- **Using the same element twice** — indices must be distinct (`i !== j`).
- **Storing value instead of index** — problem asks for indices; map must store index.
- **Off-by-one in brute force** — inner loop starts at `i + 1`, not `i`.
- **Forgetting average vs worst case** — hash map is O(1) average; O(n) worst case with collisions (rare in interviews).
- **Brute force `break` only exits inner loop** — outer loop still runs; harmless when exactly one solution exists, but inefficient.
