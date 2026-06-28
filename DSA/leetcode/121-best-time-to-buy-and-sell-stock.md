# 121. Best Time to Buy and Sell Stock

**Link:** [Best Time to Buy and Sell Stock](https://leetcode.com/problems/best-time-to-buy-and-sell-stock/description/)  
**Difficulty:** Easy  
**Tags:** Array, Dynamic Programming, Greedy

## Problem Summary

Given an array `prices` where `prices[i]` is the stock price on day `i`, pick **one buy day** and **one sell day after it** to maximize profit. Return the maximum profit, or `0` if no profit is possible.

---

## Approach 1: Brute Force

Try every valid buy/sell pair `(i, j)` where `i < j` and track the maximum `prices[j] - prices[i]`.

### Code

```javascript
/**
 * @param {number[]} prices
 * @return {number}
 */
var maxProfit = function (prices) {
  let profit = 0;

  for (let i = 0; i < prices.length - 1; i++) {
    for (let j = i + 1; j < prices.length; j++) {
      let lp = prices[j] - prices[i];

      profit = lp > profit ? lp : profit;
    }
  }

  return profit;
};
```

### Complexity

|           |                                                               |
| --------- | ------------------------------------------------------------- |
| **Time**  | **O(n²)** — every buy day is paired with every later sell day |
| **Space** | **O(1)** — only a few scalar variables                        |

### Why This Works / Doesn't Scale

Correct, but recomputes the same information repeatedly. For each buy day `i`, you scan all future days instead of tracking the best buy price seen so far.

---

## Approach 2: Single Pass (Running Minimum)

As you scan left to right, maintain the **lowest price seen so far** (best buy opportunity). At each day, the best profit if you sell today is `prices[i] - minPrice`.

### Code

```javascript
/**
 * @param {number[]} prices
 * @return {number}
 */
var maxProfit = function (prices) {
  let maxProfit = 0;
  let minPrize = Infinity;

  for (let i = 0; i < prices.length; i++) {
    let lp = prices[i] - minPrize;
    if (lp < 0) {
      minPrize = prices[i];
    } else {
      maxProfit = lp > maxProfit ? lp : maxProfit;
    }
  }

  return maxProfit;
};
```

> **Note:** `minPrize` is a typo for `minPrice` — logic is unchanged.

**Equivalent one-liner form** (same idea, often easier to read):

```javascript
var maxProfit = function (prices) {
  let maxProfit = 0;
  let minPrice = Infinity;

  for (let i = 0; i < prices.length; i++) {
    minPrice = Math.min(minPrice, prices[i]);
    maxProfit = Math.max(maxProfit, prices[i] - minPrice);
  }

  return maxProfit;
};
```

### Complexity

|           |                                            |
| --------- | ------------------------------------------ |
| **Time**  | **O(n)** — one pass through the array      |
| **Space** | **O(1)** — only `minPrice` and `maxProfit` |

### Walkthrough

`prices = [7, 1, 5, 3, 6, 4]`

| i   | prices[i] | minPrice | profit if sell today | maxProfit |
| --- | --------- | -------- | -------------------- | --------- |
| 0   | 7         | 7        | 0                    | 0         |
| 1   | 1         | 1        | 0                    | 0         |
| 2   | 5         | 1        | 4                    | 4         |
| 3   | 3         | 1        | 2                    | 4         |
| 4   | 6         | 1        | 5                    | 5         |
| 5   | 4         | 1        | 3                    | 5         |

Answer: **5** (buy at 1, sell at 6).

**Your `if/else` logic:** when `lp < 0`, today's price is a new low — update `minPrize`. Otherwise, selling today beats the running minimum, so update `maxProfit`.

---

## Pattern Learned

**Pattern: Single Pass with Running State (Greedy / Kadane-style)**

Track the best state seen so far while scanning the array once. Here the state is the **minimum buy price**; the answer is the **maximum spread** from that minimum.

**Signals in the problem:**

- "Best" outcome from a subarray or pair of indices with ordering constraint (`buy before sell`)
- Profit/difference depends on **current value minus best past value**
- Brute force is O(n²) from checking all pairs

**General template:**

```javascript
let bestState = initial; // e.g., Infinity for min, -Infinity for max
let answer = 0;

for (const value of arr) {
  bestState = Math.min(bestState, value); // update running min
  answer = Math.max(answer, value - bestState); // best outcome so far
}
```

**Core idea:** you don't need to know _when_ you bought — only the **cheapest price before today**. Each day asks: _"If I sell today, what's the best profit given all prior days?"_

---

## Key Insight

The maximum profit ending at day `j` is:

```
maxProfit[j] = prices[j] - min(prices[0..j-1])
```

You don't need nested loops. One running minimum gives you the best buy price for every sell day in a single scan.

---

## Follow-Up Questions

Problems that extend the stock series:

| Problem                                                                                                                                     | Twist                                                         |
| ------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| [Best Time to Buy and Sell Stock II](https://leetcode.com/problems/best-time-to-buy-and-sell-stock-ii/)                                     | Unlimited transactions — greedy: sum all upward moves         |
| [Best Time to Buy and Sell Stock III](https://leetcode.com/problems/best-time-to-buy-and-sell-stock-iii/)                                   | At most **2** transactions — DP with states                   |
| [Best Time to Buy and Sell Stock IV](https://leetcode.com/problems/best-time-to-buy-and-sell-stock-iv/)                                     | At most **k** transactions — DP; special case when k is large |
| [Best Time to Buy and Sell Stock with Cooldown](https://leetcode.com/problems/best-time-to-buy-and-sell-stock-with-cooldown/)               | Must wait 1 day after selling — state machine DP              |
| [Best Time to Buy and Sell Stock with Transaction Fee](https://leetcode.com/problems/best-time-to-buy-and-sell-stock-with-transaction-fee/) | Fee per transaction — DP or greedy with fee adjustment        |
| [Maximum Subarray](https://leetcode.com/problems/maximum-subarray/)                                                                         | Same "running best" spirit as Kadane's algorithm              |
| [Maximum Profit in Job Scheduling](https://leetcode.com/problems/maximum-profit-in-job-scheduling/)                                         | DP on sorted intervals (harder variant of optimal scheduling) |

### Interview Variants

- **Return the buy and sell days**, not just profit — track indices when updating `maxProfit`.
- **What if you must hold for at least k days?** — sliding window or DP with delay.
- **What if prices stream in?** — same O(1) space algorithm works online.
- **Why is greedy enough here but not for III/IV?** — only one transaction allowed; no conflicting overlapping trades.
- **DP formulation** — `dp[i] = max(dp[i-1], prices[i] - minSoFar)`; optimized to O(1) space.

---

## Common Pitfalls

- **Selling before buying** — sell day must be strictly after buy day; single left-to-right pass enforces this.
- **Returning negative profit** — if prices only fall, answer is `0` (no transaction), not a negative number.
- **Initializing `minPrice`** — use `Infinity`, not `0` or `prices[0]`, so the first element is handled correctly.
- **Off-by-one in brute force** — inner loop starts at `i + 1`.
- **Confusing this with Stock II** — unlimited trades changes the strategy entirely (capture every rise).
