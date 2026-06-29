# DSA Solutions — Master Index

Structured notes for LeetCode and interview problems: solutions, complexity, patterns, and follow-up questions.

## How Each Problem Is Documented

Every problem file follows this structure:

| Section                 | Purpose                                    |
| ----------------------- | ------------------------------------------ |
| **Problem**             | Link, difficulty, one-line summary         |
| **Brute Force**         | Naive solution + time/space complexity     |
| **Optimized**           | Better approach + time/space complexity    |
| **Pattern**             | Reusable technique and when to apply it    |
| **Key Insight**         | The mental model that unlocks the solution |
| **Follow-Up Questions** | Related problems and interview variants    |
| **Common Pitfalls**     | Mistakes to avoid                          |

## Patterns Index

| Pattern                              | Problems                                                                                                                                                               |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hash Map — Complement Lookup         | [001 — Two Sum](./leetcode/001-two-sum.md)                                                                                                                             |
| Single Pass — Running State (Greedy) | [121 — Best Time to Buy and Sell Stock](./leetcode/121-best-time-to-buy-and-sell-stock.md)                                                                             |
| Hash Set — Membership / Duplicates   | [217 — Contains Duplicate](./leetcode/217-contains-duplicate.md)                                                                                                       |
| Prefix / Suffix Decomposition        | [238 — Product of Array Except Self](./leetcode/238-product-of-array-except-self.md)                                                                                   |
| Kadane's Algorithm — Max Subarray    | [053 — Maximum Subarray](./leetcode/053-maximum-subarray.md)                                                                                                           |
| Kadane's Variant — Min/Max Product   | [152 — Maximum Product Subarray](./leetcode/152-maximum-product-subarray.md)                                                                                           |
| Binary Search — Rotated Sorted Array | [033 — Search in Rotated Sorted Array](./leetcode/033-search-in-rotated-sorted-array.md), [153 — Find Minimum](./leetcode/153-find-minimum-in-rotated-sorted-array.md) |
| Sort + Two Pointers (K-Sum)          | [015 — 3Sum](./leetcode/015-three-sum.md)                                                                                                                              |
| Two Pointers — Greedy (Shrink Ends)  | [011 — Container With Most Water](./leetcode/011-container-with-most-water.md)                                                                                         |
| Bit Manipulation — XOR + Carry       | [371 — Sum of Two Integers](./leetcode/371-sum-of-two-integers.md)                                                                                                     |
| Bit Manipulation — Count Set Bits    | [191 — Number of 1 Bits](./leetcode/191-number-of-1-bits.md)                                                                                                           |

## Problems by Number

| #   | Problem                                                                                        | Difficulty | Pattern                              |
| --- | ---------------------------------------------------------------------------------------------- | ---------- | ------------------------------------ |
| 1   | [Two Sum](./leetcode/001-two-sum.md)                                                           | Easy       | Hash Map — Complement Lookup         |
| 121 | [Best Time to Buy and Sell Stock](./leetcode/121-best-time-to-buy-and-sell-stock.md)           | Easy       | Single Pass — Running State (Greedy) |
| 217 | [Contains Duplicate](./leetcode/217-contains-duplicate.md)                                     | Easy       | Hash Set — Membership / Duplicates   |
| 238 | [Product of Array Except Self](./leetcode/238-product-of-array-except-self.md)                 | Medium     | Prefix / Suffix Decomposition        |
| 53  | [Maximum Subarray](./leetcode/053-maximum-subarray.md)                                         | Medium     | Kadane's Algorithm — Max Subarray    |
| 152 | [Maximum Product Subarray](./leetcode/152-maximum-product-subarray.md)                         | Medium     | Kadane's Variant — Min/Max Product   |
| 11  | [Container With Most Water](./leetcode/011-container-with-most-water.md)                       | Medium     | Two Pointers — Greedy (Shrink Ends)  |
| 15  | [3Sum](./leetcode/015-three-sum.md)                                                            | Medium     | Sort + Two Pointers (K-Sum)          |
| 153 | [Find Minimum in Rotated Sorted Array](./leetcode/153-find-minimum-in-rotated-sorted-array.md) | Medium     | Binary Search — Rotated Sorted Array |
| 33  | [Search in Rotated Sorted Array](./leetcode/033-search-in-rotated-sorted-array.md)             | Medium     | Binary Search — Rotated Sorted Array |
| 371 | [Sum of Two Integers](./leetcode/371-sum-of-two-integers.md)                                   | Medium     | Bit Manipulation — XOR + Carry       |
| 191 | [Number of 1 Bits](./leetcode/191-number-of-1-bits.md)                                         | Easy       | Bit Manipulation — Count Set Bits    |

## Template for New Problems

Copy `leetcode/_template.md` when adding a new solution.

## Binary Search Reference

Stuck on infinite loops or `left`/`right` updates? Read **[Binary Search Safety Guide](./binary-search-safety-guide.md)** first.

## Bit Manipulation Reference

Shifts, AND/XOR/OR, and bit tricks: **[Bit Manipulation Guide](./bit-manipulation-reference.md)**.
