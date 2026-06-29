# Binary Search — How to Never Infinite Loop

A reusable checklist for **any** binary search problem. Read this when you feel lost in `left` / `right` / `mid` updates.

---

## The Root Cause of Infinite Loops

An infinite loop means **the search window stops shrinking** — `left` and `right` get stuck repeating the same `[left, right]` or `mid`.

That happens when you **mix rules from two different binary search templates**.

---

## Rule 1: Pick ONE Template and Commit

### Template A — "Find exact value / index"

Use when: target exists or not, return index or `-1`.

```javascript
let left = 0, right = nums.length - 1;

while (left <= right) {
  const mid = Math.floor((left + right) / 2);

  if (nums[mid] === target) return mid;

  if (/* target in left half */) {
    right = mid - 1;   // always mid - 1
  } else {
    left = mid + 1;    // always mid + 1
  }
}

return -1;
```

| Property       | Value                                         |
| -------------- | --------------------------------------------- |
| Loop           | `while (left <= right)`                       |
| On discard mid | **`mid - 1` or `mid + 1`** (never keep `mid`) |
| When loop ends | window empty → not found                      |

**Your Search in Rotated Sorted Array solution uses this template.** That is why `left = mid + 1` and `right = mid - 1` are correct here.

---

### Template B — "Find boundary / minimum / first true"

Use when: answer is a **position** (min element, first bad version, insert index).

```javascript
let left = 0, right = nums.length - 1;

while (left < right) {
  const mid = Math.floor((left + right) / 2);

  if (/* answer at mid or left of mid */) {
    right = mid;       // keep mid — it might BE the answer
  } else {
    left = mid + 1;    // discard mid and everything left
  }
}

return left; // or nums[left]
```

| Property                      | Value                               |
| ----------------------------- | ----------------------------------- |
| Loop                          | `while (left < right)`              |
| When answer might be `mid`    | **`right = mid`** (never `mid - 1`) |
| When answer is right of `mid` | **`left = mid + 1`**                |
| When loop ends                | `left === right` → converged answer |

**Find Minimum in Rotated Sorted Array uses this template.** That is why `right = mid` is correct there but would pair differently with `left <= right`.

---

## Rule 2: The Pairing Table (Memorize This)

| Loop condition  | Safe updates                        | Never combine with                           |
| --------------- | ----------------------------------- | -------------------------------------------- |
| `left <= right` | `left = mid + 1`, `right = mid - 1` | `right = mid` (can stall)                    |
| `left < right`  | `right = mid`, `left = mid + 1`     | `right = mid - 1` when `mid` might be answer |

**Golden rule:** If `mid` **might be the answer**, use Template B (`left < right`, `right = mid`).

If you **already checked** `nums[mid] === target` and returned, discarding `mid` with `mid ± 1` is safe (Template A).

---

## Rule 3: Every Branch Must Shrink the Window

Before trusting your code, ask for **each branch**:

> If `left = 2` and `right = 5`, after this update, is the new window **strictly smaller**?

| Update            | Old window size | New window | Shrinks?                               |
| ----------------- | --------------- | ---------- | -------------------------------------- |
| `right = mid - 1` | [2, 5]          | [2, mid-1] | Yes (if mid ≥ 2)                       |
| `left = mid + 1`  | [2, 5]          | [mid+1, 5] | Yes (if mid ≤ 5)                       |
| `right = mid`     | [2, 5]          | [2, mid]   | Yes **only if** mid < right            |
| `left = mid`      | [2, 5]          | [mid, 5]   | **DANGER** — can stall if mid === left |

**Never use `left = mid`** unless you have a proof it always advances (rare). Prefer `left = mid + 1`.

---

## Rule 4: The 5-Step Debug Checklist

When you hit an infinite loop or wrong answer:

1. **Which template am I using?** A (exact search) or B (boundary)?
2. **Does my loop condition match?** `<=` with `mid±1`, or `<` with `right=mid`?
3. **Trace `left === right` or `left + 1 === right`** — does one more iteration exit?
4. **Draw a 5-element array** on paper; walk 3 iterations by hand.
5. **Log `left, mid, right`** on the failing test case — if any triple repeats, you found the bug.

---

## Rule 5: Rotated Array Decision Tree

For [Search in Rotated Sorted Array](./leetcode/033-search-in-rotated-sorted-array.md):

```
1. If nums[mid] === target → return mid

2. Is left half sorted?  (nums[left] <= nums[mid])
   YES → Is target in [nums[left], nums[mid]) ?
         YES → right = mid - 1
         NO  → left  = mid + 1

3. Else right half is sorted
   → Is target in (nums[mid], nums[right]] ?
         YES → left  = mid + 1
         NO  → right = mid - 1
```

Use **`<=` on left bound, `>` on right bound** for the "in sorted half" check because `mid` was already tested for equality.

---

## Rule 6: Quick Sanity Tests

Run these mentally after writing any binary search:

| Test                         | Expected                |
| ---------------------------- | ----------------------- |
| `[1]` target `1`             | found                   |
| `[1]` target `0`             | not found               |
| `[1, 3]` target `3`          | found                   |
| Two elements, target missing | returns -1, no loop     |
| Unrotated `[1,2,3,4,5]`      | standard BS still works |

### Note: Always test with array size 2 (infinite-loop detector)

> **Always test your logic with an array of size 2 — it is the fastest way to catch classic infinite-loop bugs.**

**Verdict: mostly correct, with caveats.**

| Claim                                                       | Valid?                                                 |
| ----------------------------------------------------------- | ------------------------------------------------------ |
| Size 2 catches **infinite loop** from wrong pointer updates | **Yes** — for the common bugs                          |
| Size 2 alone **guarantees** no infinite loop on all inputs  | **No** — it is a smoke test, not a proof               |
| Size 2 catches **wrong logic** that still terminates        | **No** — only catches stalling / non-shrinking windows |

**Why size 2 works so well for loops**

`n = 2` → `left = 0`, `right = 1`, `mid = 0` (always). This is the **smallest window where `mid` is not both endpoints**, so bad update rules get exposed immediately:

| Bug                                 | Trace on `[1, 3]`, target `0`           |
| ----------------------------------- | --------------------------------------- |
| `right = mid` with `left <= right`  | `[0,1]` → `[0,0]` → `[0,0]` → **stuck** |
| `left = mid` (instead of `mid + 1`) | `[0,1]` → `[0,1]` → **stuck**           |
| Correct Template A (`mid ± 1`)      | `[0,1]` → `[1,1]` → `[1,0]` → **exits** |

If your code spins forever on a 2-element input, the **loop condition / pointer update pairing** is wrong — fix that before debugging larger cases.

**What size 2 does NOT catch**

- **Wrong half chosen** in rotated search — loop may still terminate but return wrong index (test `[3,1]`, `[4,5,6,7,0,1,2]`)
- **Off-by-one on size 1** — e.g. empty-window edge cases (`[1]` only)
- **Bugs that need `mid = 1`** — rare, but size 3 (`[1,2,3]`) helps as a second pass
- **Duplicate-array shrink logic** (LeetCode 81/154) — need cases where `nums[mid] === nums[right]`

**Recommended minimum test pack**

```
n = 1   → edge case / empty-window behavior
n = 2   → infinite-loop detector  ← run this first when debugging loops
n = 3   → mid-not-at-edge sanity check
n = 5+  → logic correctness (rotated, unrotated, missing target)
```

**Practical habit:** after writing any binary search, run **size 2 with target missing** (e.g. `[1, 3]`, target `0`). If it does not return within a few iterations, you have a stall bug.

---

## Rule 7: When Duplicates Exist

Duplicates break simple `<=` / `<` logic. For rotated arrays with duplicates:

- If `nums[mid] === nums[right]` → `right--` (shrink; can't decide half)
- Worst case degrades to O(n) — acceptable on LeetCode 81/154

---

## One-Page Cheat Sheet

```
EXACT SEARCH (return index or -1):
  while (left <= right)
    discard mid → mid ± 1

BOUNDARY SEARCH (return position):
  while (left < right)
    keep mid as candidate → right = mid
    discard mid → left = mid + 1

PROGRESS TEST:
  every branch must make left ↑ or right ↓

STUCK?
  name template → match loop to updates → trace by hand
```

---

## Related Problems

| Problem                                                                                              | Template |
| ---------------------------------------------------------------------------------------------------- | -------- |
| [033 — Search in Rotated Sorted Array](./leetcode/033-search-in-rotated-sorted-array.md)             | A        |
| [153 — Find Minimum in Rotated Sorted Array](./leetcode/153-find-minimum-in-rotated-sorted-array.md) | B        |
| [704 — Binary Search](https://leetcode.com/problems/binary-search/)                                  | A        |
| [35 — Search Insert Position](https://leetcode.com/problems/search-insert-position/)                 | A or B   |
