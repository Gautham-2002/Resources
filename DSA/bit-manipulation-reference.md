# Bit Manipulation — Reference Guide

Core bitwise operations, shift operators (`<<`, `>>`, `>>>`), and patterns for DSA problems. Use alongside [Sum of Two Integers](./leetcode/371-sum-of-two-integers.md) and [Number of 1 Bits](./leetcode/191-number-of-1-bits.md).

---

## What Is Bit Manipulation?

Working with integers at the **binary bit level** instead of using arithmetic operators. Each bit is an independent on/off switch.

```
13 in binary (8-bit view):  00001101
                              │││││││└─ 1 (2^0)
                              ││││││└── 0 (2^1)
                              │││││└─── 1 (2^2)
                              ││││└──── 1 (2^3)
                              └──────── higher bits...
```

---

## The Six Core Bitwise Operators

| Operator | Name                 | What it does                        | Example (8-bit)                   |
| -------- | -------------------- | ----------------------------------- | --------------------------------- |
| `&`      | AND                  | 1 only if **both** bits are 1       | `1100 & 1010` → `1000`            |
| `\|`     | OR                   | 1 if **either** bit is 1            | `1100 \| 1010` → `1110`           |
| `^`      | XOR                  | 1 if bits **differ**                | `1100 ^ 1010` → `0110`            |
| `~`      | NOT                  | Flip every bit                      | `~1100` → `0011` (in fixed width) |
| `<<`     | Left shift           | Shift bits left, fill with 0        | `0001 << 2` → `0100` (×4)         |
| `>>`     | Signed right shift   | Shift right, fill with **sign bit** | see below                         |
| `>>>`    | Unsigned right shift | Shift right, fill with **0**        | see below                         |

### AND (`&`) — mask / test / clear

```javascript
n & 1; // is last bit set?
n & mask; // keep only bits in mask
n & (n - 1); // clear lowest set bit (Brian Kernighan)
```

### OR (`|`) — set bits

```javascript
n | (1 << k); // set bit at position k
```

### XOR (`^`) — toggle / cancel pairs

```javascript
n ^ n; // 0 — same bits cancel
a ^ b; // sum without carry
n ^ (1 << k); // toggle bit at position k
```

### NOT (`~`) — flip all bits

```javascript
~n; // one's complement (two's complement in fixed width)
~0; // all 1s (useful as mask)
```

---

## Shift Operators: `<<` vs `>>` vs `>>>`

### Left shift `<<`

Moves bits **left**. Vacant right slots filled with **0**.

```
00001101  << 1  →  00011010   (13 → 26, multiply by 2)
00001101  << 2  →  00110100   (13 → 52, multiply by 4)
```

| Property      | Value                                                    |
| ------------- | -------------------------------------------------------- |
| Effect        | Multiply by `2^k` (may overflow/truncate in fixed width) |
| Fill bit      | Always **0** on the right                                |
| In JavaScript | Operates on **32-bit signed** integer for bitwise ops    |

---

### Signed right shift `>>` (arithmetic shift)

Moves bits **right**. Vacant **left** slots filled with the **sign bit** (MSB).

```
Positive (13 = 00001101):
  00001101  >> 1  →  00000110  (6)

Negative (-1 in 32-bit = 11111111...1111):
  11111111  >> 1  →  11111111  (-1 stays -1 — sign preserved)
```

| Property | Value                                                     |
| -------- | --------------------------------------------------------- |
| Effect   | Divide by `2^k`, **rounded toward negative infinity**     |
| Fill bit | **Copy of sign bit** (1 for negative, 0 for positive)     |
| Use when | You want division that preserves sign for signed integers |

---

### Unsigned right shift `>>>` (logical shift)

Moves bits **right**. Vacant **left** slots always filled with **0** — sign bit is **not** preserved.

```
Positive (13 = 00001101):
  00001101  >>> 1  →  00000110  (6) — same as >> for positives

Negative (-1 in 32-bit):
  11111111...1111  >>> 1  →  01111111...1111  (2147483647)
```

| Property | Value                                                            |
| -------- | ---------------------------------------------------------------- |
| Effect   | Treats number as **unsigned** 32-bit; top bits become 0          |
| Fill bit | Always **0** on the left                                         |
| Use when | Walking **all 32 bits** regardless of sign (e.g. Hamming weight) |

---

## Quick Comparison Table

|              | `<<`                    | `>>`                     | `>>>`                     |
| ------------ | ----------------------- | ------------------------ | ------------------------- |
| Direction    | Left                    | Right                    | Right                     |
| Fill from    | Right side (0)          | Left side (**sign bit**) | Left side (**always 0**)  |
| Positive `n` | × 2^k                   | ÷ 2^k (floor)            | ÷ 2^k (floor)             |
| Negative `n` | (32-bit wrap)           | Keeps negative           | Becomes large positive    |
| Typical use  | Build masks, carry left | Signed divide            | Count bits, unsigned scan |

### When to use which right shift?

```javascript
// Counting / checking every bit position — use >>>
while (n !== 0) {
  if (n & 1) count++;
  n = n >>> 1; // ✅ walks all 32 bits even if n was negative
}

// Signed arithmetic divide by 2 — use >>
n = n >> 1; // ✅ -8 >> 1 === -4
```

**Rule of thumb:** For LeetCode bit-counting on JavaScript, prefer **`>>>`** when shifting `n` right in a loop so negative inputs don't stall or behave oddly.

---

## JavaScript-Specific: 32-Bit Bitwise Conversion

In JavaScript, `&`, `|`, `^`, `~`, `<<`, `>>`, `>>>` all convert operands to **32-bit signed integers** first.

```javascript
(1 << 31)(
  // -2147483648 (sign bit set — overflow in signed 32-bit)
  1 << 31,
) >>> 0; // 2147483648 if treated unsigned — watch overflow
```

For LeetCode problems with large unsigned inputs, you may need masking — most problems stay within safe range.

---

## Essential Bit Tricks (Memorize These)

| Trick             | Code                             | Use                                          |
| ----------------- | -------------------------------- | -------------------------------------------- |
| Check bit `k`     | `(n >> k) & 1` or `n & (1 << k)` | Test if set                                  |
| Set bit `k`       | `n \| (1 << k)`                  | Turn on                                      |
| Clear bit `k`     | `n & ~(1 << k)`                  | Turn off                                     |
| Toggle bit `k`    | `n ^ (1 << k)`                   | Flip                                         |
| Clear lowest 1    | `n & (n - 1)`                    | Brian Kernighan                              |
| Isolate lowest 1  | `n & -n`                         | Get lowest set bit only                      |
| Check power of 2  | `n > 0 && (n & (n - 1)) === 0`   | Only one bit set                             |
| Swap without temp | `a ^= b; b ^= a; a ^= b`         | XOR swap                                     |
| Add without +     | XOR + carry loop                 | [371](./leetcode/371-sum-of-two-integers.md) |

### Why `n & (n - 1)` clears the lowest 1 bit

```
n     = ...1101000   (lowest 1 marked)
n - 1 = ...1100111   (trailing 0s flip, that 1 flips to 0)
n & (n-1) = ...1100000   (lowest 1 gone)
```

**Full deep dive** (n=12, n=22 step-by-step, 2³⁰ vs shift loop): [191 — Brian Kernighan](./leetcode/191-number-of-1-bits.md#deep-dive-the-secret-identity-n--n---1)

---

## Common Patterns in DSA

| Pattern                | Example problems                                                                                  |
| ---------------------- | ------------------------------------------------------------------------------------------------- |
| Count set bits         | [191 — Number of 1 Bits](./leetcode/191-number-of-1-bits.md)                                      |
| Add/sub without +/-    | [371 — Sum of Two Integers](./leetcode/371-sum-of-two-integers.md)                                |
| XOR cancels duplicates | [136 — Single Number](https://leetcode.com/problems/single-number/)                               |
| Power of two check     | [231 — Power of Two](https://leetcode.com/problems/power-of-two/)                                 |
| Bit DP / subsets       | [78 — Subsets](https://leetcode.com/problems/subsets/) with bitmask                               |
| Range AND              | [201 — Bitwise AND of Numbers Range](https://leetcode.com/problems/bitwise-and-of-numbers-range/) |

---

## Debugging Tips

1. **Print in binary:** `n.toString(2).padStart(32, '0')` (32-bit view)
2. **Positive vs negative shift:** if loop never ends on negative `n`, switch `>>` to `>>>`
3. **Mask width:** `1 << k` for bit `k`; `((1 << n) - 1)` for lower `n` bits all 1s
4. **Off-by-one on bit index:** bit 0 is the **rightmost** (least significant)

---

## Related References

| Resource                                                           | Topic                                 |
| ------------------------------------------------------------------ | ------------------------------------- |
| [191 — Number of 1 Bits](./leetcode/191-number-of-1-bits.md)       | Hamming weight, both counting methods |
| [371 — Sum of Two Integers](./leetcode/371-sum-of-two-integers.md) | XOR + carry addition                  |
| [Binary Search Safety Guide](./binary-search-safety-guide.md)      | Different topic — pointer loops       |
