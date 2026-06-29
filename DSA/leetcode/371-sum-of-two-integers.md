# 371. Sum of Two Integers

**Link:** [Sum of Two Integers](https://leetcode.com/problems/sum-of-two-integers/description/)  
**Difficulty:** Medium  
**Tags:** Math, Bit Manipulation

## Problem Summary

Given two integers `a` and `b`, return their **sum** without using the operators `+` and `-`.

---

## Approach 1: Built-in (Not Allowed)

```javascript
return a + b;
```

Fails the problem constraint — included only to state the obvious baseline.

---

## Approach 2: Bit Manipulation — XOR + Carry (Best)

Simulate hardware addition: XOR gives **sum without carry**; AND + shift gives **carry bits** to add next round. Repeat until carry is zero.

### Code

```javascript
/**
 * @param {number} a
 * @param {number} b
 * @return {number}
 */
var getSum = function (a, b) {
  while (b !== 0) {
    let carry = (a & b) << 1;

    a = a ^ b;

    b = carry;
  }

  return a;
};
```

### Complexity

|           |                                                                               |
| --------- | ----------------------------------------------------------------------------- |
| **Time**  | **O(1)** — at most ~32 iterations (word size); constant for fixed 32-bit ints |
| **Space** | **O(1)**                                                                      |

### How binary addition works

Adding bit-by-bit:

| Bit op         | Role                                                           |
| -------------- | -------------------------------------------------------------- |
| `a ^ b`        | Sum **without** carries (each bit: 0+0→0, 1+0→1, 0+1→1, 1+1→0) |
| `a & b`        | Positions where **both** bits are 1 → need a carry             |
| `(a & b) << 1` | Shift carry left to the next higher bit                        |

Repeat: add the carry (`b`) into the partial sum (`a`) until no carry remains.

### Walkthrough

`a = 5` (`101`), `b = 3` (`011`)

| Round | a       | b        | carry = (a&b)<<1 | new a = a^b | new b    |
| ----- | ------- | -------- | ---------------- | ----------- | -------- |
| 1     | 101 (5) | 011 (3)  | 010 (2)          | 110 (6)     | 010 (2)  |
| 2     | 110 (6) | 010 (2)  | 100 (4)          | 100 (4)     | 100 (4)  |
| 3     | 100 (4) | 100 (4)  | 1000 (8)         | 000 (0)     | 1000 (8) |
| 4     | 000 (0) | 1000 (8) | 0                | 1000 (8)    | 0        |

`b === 0` → return **8**

---

## Approach Comparison

| Approach         | Time   | Space | Allowed? |
| ---------------- | ------ | ----- | -------- |
| `a + b`          | O(1)   | O(1)  | No       |
| XOR + carry loop | O(1)\* | O(1)  | Yes      |

\*32 iterations max for 32-bit integers.

---

## Pattern Learned

**Pattern: Bit Manipulation — Add / Subtract with XOR and Carry**

Decompose arithmetic into bitwise ops that mirror digital adders.

**Signals in the problem:**

- Forbidden to use `+` / `-`
- Integer math at bit level
- "Without arithmetic operators"

**See also:** [Bit Manipulation Guide](../bit-manipulation-reference.md) for `<<`, `>>`, `>>>`, and core operators.

**General templates:**

```javascript
// Add a + b
while (b !== 0) {
  const carry = (a & b) << 1;
  a = a ^ b;
  b = carry;
}

// Subtract a - b  (a + (-b), where -b = ~b + 1)
b = ~b + 1; // or use XOR/sub pattern in loop
```

**Subtract variant (same loop, different carry setup):**

```javascript
while (b !== 0) {
  const borrow = (~a & b) << 1;
  a = a ^ b;
  b = borrow;
}
```

---

## Key Insight

Addition is two independent jobs:

1. **Combine bits** → XOR
2. **Propagate carries** → AND, then shift left

Loop until carries are exhausted. This is exactly how a hardware full adder chain works.

---

## Follow-Up Questions

Problems using bitwise arithmetic:

| Problem                                                                                           | Twist                             |
| ------------------------------------------------------------------------------------------------- | --------------------------------- |
| [67 — Add Binary](https://leetcode.com/problems/add-binary/)                                      | String bits; same carry logic     |
| [371 — Sum of Two Integers](https://leetcode.com/problems/sum-of-two-integers/)                   | This problem                      |
| [201 — Bitwise AND of Numbers Range](https://leetcode.com/problems/bitwise-and-of-numbers-range/) | Find common prefix of bits        |
| [136 — Single Number](https://leetcode.com/problems/single-number/)                               | XOR cancels pairs                 |
| [191 — Number of 1 Bits](https://leetcode.com/problems/number-of-1-bits/)                         | `n & (n-1)` clears lowest set bit |
| [231 — Power of Two](https://leetcode.com/problems/power-of-two/)                                 | `n & (n-1) === 0`                 |
| [260 — Single Number III](https://leetcode.com/problems/single-number-iii/)                       | XOR split into groups             |

### Interview Variants

- **Implement subtract** without `-` — two's complement: `a + (~b + 1)`.
- **Add three numbers** — loop pairwise, or extend carry logic.
- **Why does XOR give sum without carry?** — 1+1=2 writes 0 in bit, carry handled separately by AND.
- **How many iterations?** — at most number of bits (32 for 32-bit ints).

---

## Common Pitfalls

- **Using `+` or `-`** — violates constraint (even for `~b + 1` in strict interviews — use bitwise NOT and carry loop instead).
- **JavaScript 32-bit signed bitwise ops** — `&`, `^`, `<<` coerce to **signed 32-bit** integers. Large or negative numbers can behave unexpectedly in JS vs Python/Java. LeetCode test cases usually fit 32-bit range; for edge cases:

```javascript
// JS-safe 32-bit wrap (if needed)
const MASK = 0xffffffff;
const MAX = 0x7fffffff;
// normalize after each op...
```

- **Infinite loop if carry never shrinks** — should not happen with correct `(a & b) << 1`; carry always moves left and eventually clears in fixed-width arithmetic.
- **Forgetting `<< 1` on carry** — carry belongs in the **next** bit position.
- **Confusing XOR with OR** — OR does not cancel; XOR is required for addition without double-counting.
