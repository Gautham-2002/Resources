# 191. Number of 1 Bits

**Link:** [Number of 1 Bits](https://leetcode.com/problems/number-of-1-bits/description/)  
**Difficulty:** Easy  
**Tags:** Divide and Conquer, Bit Manipulation

Also known as **Hamming weight** — count how many bits are `1` in the binary representation of `n`.

**Bit ops reference:** [Bit Manipulation Guide](../bit-manipulation-reference.md) — covers `<<`, `>>`, `>>>`, AND, XOR, and common tricks.

---

## Problem Summary

Given a positive integer `n`, return the number of set bits (`1`s) in its binary form.

---

## Approach 1: Check Last Bit + Unsigned Shift

Inspect the rightmost bit with `n & 1`, then shift `n` right with `>>>` to process the next bit.

### Code

```javascript
/**
 * @param {number} n
 * @return {number}
 */
var hammingWeight = function (n) {
  let count = 0;

  while (n !== 0) {
    if ((n & 1) !== 0) {
      count++;
    }
    n = n >>> 1;
  }

  return count;
};
```

### Complexity

|           |                                                                     |
| --------- | ------------------------------------------------------------------- |
| **Time**  | **O(32)** = **O(1)** — always up to 32 iterations (fixed word size) |
| **Space** | **O(1)**                                                            |

### Walkthrough

`n = 11` → binary `1011`

| step | n (binary) | n & 1 | count |
| ---- | ---------- | ----- | ----- |
| 1    | 1011       | 1     | 1     |
| 2    | 101        | 1     | 2     |
| 3    | 10         | 0     | 2     |
| 4    | 1          | 1     | 3     |
| 5    | 0          | —     | **3** |

### Why `>>>` not `>>`?

In JavaScript, **`>>>`** (unsigned right shift) fills the left with **0**, so every bit is visited.

**`>>`** (signed shift) copies the sign bit — for negative numbers (in 32-bit bitwise form), the top bits stay `1` and the loop may run many more times or behave unexpectedly.

See [Bit Manipulation Guide — Shift operators](../bit-manipulation-reference.md#shift-operators--vs--vs-).

---

## Approach 2: Brian Kernighan's Algorithm (Best when sparse)

Brian Kernighan's algorithm is one of those bitwise tricks that feels like magic until you see the math behind it. Its sole purpose is to count the number of set bits (`1`s) in an integer — the **Hamming weight**.

While a standard approach checks **every single bit** one by one (even the `0`s), Brian Kernighan's algorithm **skips all the `0`s** and jumps directly from one `1` bit to the next.

Each iteration **clears the lowest set bit** with `n & (n - 1)`. The loop runs once per `1` bit — not once per bit position.

### Code

```javascript
/**
 * @param {number} n
 * @return {number}
 */
var hammingWeight = function (n) {
  let count = 0;

  while (n !== 0) {
    n = n & (n - 1);
    count++;
  }

  return count;
};
```

### Complexity

|           |                                                            |
| --------- | ---------------------------------------------------------- |
| **Time**  | **O(k)** where **k** = number of set bits (Hamming weight) |
| **Space** | **O(1)**                                                   |

Worst case (all 32 bits set): **O(32)** = O(1). Average case is blazingly fast when `k` is small.

---

### Deep Dive: The Secret Identity `n & (n - 1)`

The core relies on a fundamental property of binary numbers:

> **Subtracting 1 from a binary number flips all bits from right to left, up to and including the first `1` bit encountered.**

Then `n & (n - 1)` keeps only bits that are `1` in **both** operands — the lowest `1` of `n` becomes `0` in `n - 1`, so it disappears from the result. All higher bits stay untouched.

#### Example 1: Clear the lowest 1 bit of 12

```
n     = 12  →  1100
n - 1 = 11  →  1011   ← lowest 1 flipped to 0; trailing 0s flipped to 1

  1100  (12)
& 1011  (11)
  ----
  1000  (8)
```

The rightmost `1` (in the 4s column) is **gone**. Bits to the left are unchanged.

#### Example 2: Full trace on 22 (three set bits → count = 3)

Binary of 22: **`10110`** — three `1` bits, so the loop should run exactly **3** times.

**Iteration 1**

```
n     = 22  →  10110
n - 1 = 21  →  10101

  10110
& 10101
  -----
  10100  (20)   ← rightmost 1 cleared

count = 1
```

**Iteration 2**

```
n     = 20  →  10100
n - 1 = 19  →  10011

  10100
& 10011
  -----
  10000  (16)   ← middle 1 cleared

count = 2
```

**Iteration 3**

```
n     = 16  →  10000
n - 1 = 15  →  01111

  10000
& 01111
  -----
  00000  (0)    ← last 1 cleared

count = 3
```

**End:** `n === 0` → loop stops → return **3**.

#### Why this beats the standard shift loop

Imagine a huge 32-bit integer like **2³⁰**:

```
2^30 in binary:  1 000000000000000000000000000000
                 ↑ one 1, thirty 0s
```

| Method                                   | Iterations                                                      |
| ---------------------------------------- | --------------------------------------------------------------- |
| **Standard shift** (`n >>> 1` + `n & 1`) | **32** — inspects every bit position, including all thirty `0`s |
| **Brian Kernighan**                      | **1** — one `n & (n-1)` wipes the single `1`, hits `0`, done    |

**Time complexity: O(k)** where **k** = number of `1` bits. Not O(32) unless the number is dense with ones.

---

### Short walkthrough (n = 11)

`n = 11` → `1011`

| step | n    | n - 1 | n & (n-1) | count |
| ---- | ---- | ----- | --------- | ----- |
| 1    | 1011 | 1010  | 1010      | 1     |
| 2    | 1010 | 1001  | 1000      | 2     |
| 3    | 1000 | 0111  | 0000      | 3     |

Answer: **3** — one iteration per set bit.

---

## Approach Comparison

| Approach        | Time             | Iterations for n = 11 (`1011`) | Best when                   |
| --------------- | ---------------- | ------------------------------ | --------------------------- |
| Mask + `>>>`    | O(32) worst case | 4 (until n = 0)                | Simple, predictable         |
| Brian Kernighan | O(k)             | **3** (one per set bit)        | **Sparse** numbers (few 1s) |

**Example:** `n = 1` (single bit set)

| Method          | Iterations |
| --------------- | ---------- |
| Mask + shift    | up to 32   |
| Brian Kernighan | **1**      |

**Example:** `n = 2^31 - 1` (all 31 bits set)

| Method          | Iterations              |
| --------------- | ----------------------- |
| Mask + shift    | ~31                     |
| Brian Kernighan | **31** (same — many 1s) |

Brian Kernighan wins when **k ≪ 32** (few set bits). Mask + shift has constant upper bound regardless of k.

---

## Pattern Learned

**Pattern: Bit Counting — Mask or Clear Lowest 1**

Two ways to peel bits off `n`:

| Method          | Operation           | Strips                    |
| --------------- | ------------------- | ------------------------- |
| Right shift     | `n >>> 1` + `n & 1` | One **position** per step |
| Brian Kernighan | `n & (n - 1)`       | One **set bit** per step  |

**Signals in the problem:**

- Count / find set bits
- "Hamming weight", "parity", "number of 1 bits"
- Power-of-two checks (`n & (n-1) === 0`)

---

## Key Insight

You don't need to convert to a binary string.

> **Either shift and test the last bit, or repeatedly delete the lowest `1` — both count in O(1) word size.**

Choose Brian Kernighan when the number is **sparse** (few 1s); choose mask + `>>>` for simplicity.

---

## Follow-Up Questions

| Problem                                                                                           | Twist                                                     |
| ------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| [191 — Number of 1 Bits](https://leetcode.com/problems/number-of-1-bits/)                         | This problem                                              |
| [338 — Counting Bits](https://leetcode.com/problems/counting-bits/)                               | Hamming weight for every 0..n — DP trick                  |
| [461 — Hamming Distance](https://leetcode.com/problems/hamming-distance/)                         | Count differing bits between two numbers — XOR then count |
| [136 — Single Number](https://leetcode.com/problems/single-number/)                               | XOR all elements                                          |
| [231 — Power of Two](https://leetcode.com/problems/power-of-two/)                                 | `n & (n-1) === 0`                                         |
| [371 — Sum of Two Integers](./371-sum-of-two-integers.md)                                         | XOR + carry                                               |
| [201 — Bitwise AND of Numbers Range](https://leetcode.com/problems/bitwise-and-of-numbers-range/) | Common prefix of bits                                     |

### Interview Variants

- **Count for all numbers 0 to n** — [338] use `dp[i] = dp[i >> 1] + (i & 1)`.
- **Hamming distance of two integers** — `countBits(a ^ b)`.
- **Why is Brian Kernighan O(k)?** — each step removes exactly one `1` bit; at most k steps.
- **Built-in** — `n.toString(2).split('0').join('').length` — valid but O(log n) string work; not what interviewers want.

---

## Common Pitfalls

- **Using `>>` instead of `>>>`** in JS — negative bitwise values can misbehave (see [shift guide](../bit-manipulation-reference.md)).
- **Forgetting `n & 1` vs `n & 1 !== 0`** — equivalent; explicit check reads clearer.
- **Thinking Brian Kernighan is always faster** — only when **k** (set bits) is small; dense numbers ≈ same as 32 steps.
- **Not handling `n = 0`** — both methods return 0 correctly (loop never runs / count stays 0).
- **Confusing `n & (n-1)` with `n & 1`** — first **clears** lowest 1; second **tests** last bit.

---

## Bit Operations Cheat Sheet (This Problem)

```javascript
n & 1; // is rightmost bit set?
n >>> 1; // move to next bit (unsigned — use in JS)
n & (n - 1); // clear lowest set bit
n & -n; // isolate lowest set bit (bonus trick)
```

Full reference: **[Bit Manipulation Guide](../bit-manipulation-reference.md)**
