# Window Functions in PostgreSQL

## Table of Contents

1. [Introduction](#introduction)
2. [What are Window Functions?](#what-are-window-functions)
3. [The OVER() Clause](#the-over-clause)
4. [Common Window Functions](#common-window-functions)
5. [Real-World Examples](#real-world-examples)
6. [Performance Considerations](#performance-considerations)

---

## Introduction

Window functions are a powerful SQL feature that allow you to perform calculations across a set of table rows that are related to the current row. Unlike aggregate functions with `GROUP BY`, window functions don't collapse rows into groups - they return a value for each row while still being able to see other rows.

---

## What are Window Functions?

Window functions compute values based on a "window" of rows related to the current row. They are called "window" functions because they operate on a window (subset) of rows defined by the `OVER()` clause.

### Key Characteristics:

1. **Don't collapse rows** - Each input row produces one output row
2. **Operate on a window** - A subset of rows defined by `OVER()`
3. **Can access other rows** - Not just the current row
4. **Execute after WHERE but before ORDER BY** - Important for understanding execution order

### Syntax:

```sql
function_name([arguments]) OVER (
    [PARTITION BY column1, column2, ...]
    [ORDER BY column1 [ASC|DESC], ...]
    [ROWS|RANGE BETWEEN start AND end]
)
```

---

## The OVER() Clause

The `OVER()` clause defines the window (set of rows) that the function operates on.

### 1. Empty OVER() - All Rows

```sql
SELECT
    name,
    salary,
    COUNT(*) OVER() AS total_employees
FROM employees;
```

**Result:**

```
name    | salary | total_employees
--------|--------|----------------
Alice   | 5000   | 5  ← Count of ALL rows
Bob     | 6000   | 5  ← Same value for all rows
Charlie | 4500   | 5
David   | 7000   | 5
Eve     | 5500   | 5
```

### 2. PARTITION BY - Group Rows

```sql
SELECT
    name,
    department,
    salary,
    COUNT(*) OVER(PARTITION BY department) AS dept_count
FROM employees;
```

**Result:**

```
name    | department | salary | dept_count
--------|------------|--------|------------
Alice   | Sales      | 5000   | 2  ← Count within Sales partition
Bob     | Sales      | 6000   | 2
Charlie | IT         | 4500   | 3  ← Count within IT partition
David   | IT         | 7000   | 3
Eve     | IT         | 5500   | 3
```

### 3. ORDER BY - Order Within Window

```sql
SELECT
    name,
    salary,
    ROW_NUMBER() OVER(ORDER BY salary DESC) AS rank
FROM employees;
```

**Result:**

```
name    | salary | rank
--------|--------|-----
David   | 7000   | 1
Bob     | 6000   | 2
Eve     | 5500   | 3
Alice   | 4500   | 4
Charlie | 4500   | 5
```

### 4. PARTITION BY + ORDER BY

```sql
SELECT
    name,
    department,
    salary,
    ROW_NUMBER() OVER(PARTITION BY department ORDER BY salary DESC) AS dept_rank
FROM employees;
```

**Result:**

```
name    | department | salary | dept_rank
--------|------------|--------|----------
Bob     | Sales      | 6000   | 1  ← Rank 1 in Sales
Alice   | Sales      | 5000   | 2  ← Rank 2 in Sales
David   | IT         | 7000   | 1  ← Rank 1 in IT
Eve     | IT         | 5500   | 2  ← Rank 2 in IT
Charlie | IT         | 4500   | 3  ← Rank 3 in IT
```

---

## Common Window Functions

### 1. COUNT(\*) OVER()

Counts all rows in the window.

```sql
SELECT
    product_name,
    price,
    COUNT(*) OVER() AS total_products
FROM products
WHERE category = 'Electronics';
```

**Use Case:** Get total count while fetching paginated results.

```sql
-- Pagination with total count
SELECT
    id,
    name,
    COUNT(*) OVER() AS total_count
FROM users
WHERE status = 'active'
ORDER BY created_at DESC
LIMIT 10 OFFSET 20;
-- Returns 10 rows, each with total_count = total matching rows
```

---

### 2. SUM() OVER()

Calculates the sum of a column within the window.

```sql
SELECT
    date,
    sales_amount,
    SUM(sales_amount) OVER(ORDER BY date) AS running_total
FROM daily_sales;
```

**Result:**

```
date       | sales_amount | running_total
-----------|--------------|---------------
2024-01-01 | 1000         | 1000
2024-01-02 | 1500         | 2500  ← 1000 + 1500
2024-01-03 | 800          | 3300  ← 2500 + 800
2024-01-04 | 1200         | 4500  ← 3300 + 1200
```

**With PARTITION BY:**

```sql
SELECT
    employee_id,
    month,
    salary,
    SUM(salary) OVER(PARTITION BY employee_id ORDER BY month) AS cumulative_salary
FROM monthly_salaries;
```

---

### 3. AVG() OVER()

Calculates the average of a column within the window.

```sql
SELECT
    student_name,
    score,
    AVG(score) OVER() AS class_average,
    score - AVG(score) OVER() AS difference_from_avg
FROM exam_results;
```

**With PARTITION BY:**

```sql
SELECT
    student_name,
    subject,
    score,
    AVG(score) OVER(PARTITION BY subject) AS subject_average
FROM exam_results;
```

---

### 4. ROW_NUMBER() OVER()

Assigns a unique sequential number to each row.

```sql
SELECT
    name,
    score,
    ROW_NUMBER() OVER(ORDER BY score DESC) AS rank
FROM students;
```

**Result:**

```
name    | score | rank
--------|-------|-----
Alice   | 95    | 1
Bob     | 92    | 2
Charlie | 88    | 3
David   | 85    | 4
```

**Use Case:** Remove duplicates (keep first occurrence)

```sql
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER(PARTITION BY email ORDER BY created_at) AS rn
    FROM users
)
SELECT * FROM ranked WHERE rn = 1;
```

---

### 5. RANK() OVER()

Assigns rank with gaps (same values get same rank, next rank skips).

```sql
SELECT
    name,
    score,
    RANK() OVER(ORDER BY score DESC) AS rank
FROM students;
```

**Result:**

```
name    | score | rank
--------|-------|-----
Alice   | 95    | 1
Bob     | 92    | 2
Charlie | 88    | 3
David   | 88    | 3  ← Same score, same rank
Eve     | 85    | 5  ← Rank 4 is skipped
```

---

### 6. DENSE_RANK() OVER()

Assigns rank without gaps (same values get same rank, next rank doesn't skip).

```sql
SELECT
    name,
    score,
    DENSE_RANK() OVER(ORDER BY score DESC) AS rank
FROM students;
```

**Result:**

```
name    | score | rank
--------|-------|-----
Alice   | 95    | 1
Bob     | 92    | 2
Charlie | 88    | 3
David   | 88    | 3  ← Same score, same rank
Eve     | 85    | 4  ← No gap, continues to 4
```

---

### 7. LAG() OVER()

Accesses data from a previous row.

```sql
SELECT
    date,
    sales_amount,
    LAG(sales_amount) OVER(ORDER BY date) AS previous_day_sales,
    sales_amount - LAG(sales_amount) OVER(ORDER BY date) AS day_over_day_change
FROM daily_sales;
```

**Result:**

```
date       | sales_amount | previous_day_sales | day_over_day_change
-----------|--------------|-------------------|-------------------
2024-01-01 | 1000         | NULL               | NULL
2024-01-02 | 1500         | 1000               | 500
2024-01-03 | 800          | 1500               | -700
2024-01-04 | 1200         | 800                | 400
```

**With offset:**

```sql
LAG(sales_amount, 2) OVER(ORDER BY date) AS two_days_ago
```

---

### 8. LEAD() OVER()

Accesses data from a next row.

```sql
SELECT
    date,
    sales_amount,
    LEAD(sales_amount) OVER(ORDER BY date) AS next_day_sales
FROM daily_sales;
```

**Result:**

```
date       | sales_amount | next_day_sales
-----------|--------------|---------------
2024-01-01 | 1000         | 1500
2024-01-02 | 1500         | 800
2024-01-03 | 800          | 1200
2024-01-04 | 1200         | NULL
```

---

### 9. FIRST_VALUE() OVER()

Returns the first value in the window.

```sql
SELECT
    employee_id,
    month,
    salary,
    FIRST_VALUE(salary) OVER(PARTITION BY employee_id ORDER BY month) AS starting_salary
FROM monthly_salaries;
```

---

### 10. LAST_VALUE() OVER()

Returns the last value in the window.

```sql
SELECT
    employee_id,
    month,
    salary,
    LAST_VALUE(salary) OVER(
        PARTITION BY employee_id
        ORDER BY month
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS current_salary
FROM monthly_salaries;
```

**Note:** `LAST_VALUE()` requires `ROWS BETWEEN` clause to get the actual last value, otherwise it returns the last value up to the current row.

---

### 11. PERCENT_RANK() OVER()

Returns the relative rank (0 to 1) of a row.

```sql
SELECT
    name,
    score,
    PERCENT_RANK() OVER(ORDER BY score DESC) AS percentile
FROM students;
```

**Result:**

```
name    | score | percentile
--------|-------|------------
Alice   | 95    | 0.00  ← Top (0%)
Bob     | 92    | 0.25  ← 25th percentile
Charlie | 88    | 0.50  ← 50th percentile (median)
David   | 85    | 0.75  ← 75th percentile
Eve     | 80    | 1.00  ← Bottom (100%)
```

---

### 12. NTILE() OVER()

Divides rows into a specified number of groups.

```sql
SELECT
    name,
    score,
    NTILE(4) OVER(ORDER BY score DESC) AS quartile
FROM students;
```

**Result:**

```
name    | score | quartile
--------|-------|----------
Alice   | 95    | 1  ← Top quartile
Bob     | 92    | 1
Charlie | 88    | 2  ← Second quartile
David   | 85    | 3  ← Third quartile
Eve     | 80    | 4  ← Bottom quartile
```

---

## Real-World Examples

### Example 1: Pagination with Total Count

**Problem:** Get paginated results with total count in a single query.

```sql
SELECT
    id,
    name,
    email,
    COUNT(*) OVER() AS total_count
FROM users
WHERE status = 'active'
ORDER BY created_at DESC
LIMIT 10 OFFSET 20;
```

**Benefits:**

- Single database round trip
- Atomic snapshot (count and data from same moment)
- Better performance than two separate queries

---

### Example 2: Running Totals

**Problem:** Calculate cumulative sales for each day.

```sql
SELECT
    date,
    sales_amount,
    SUM(sales_amount) OVER(ORDER BY date) AS running_total,
    AVG(sales_amount) OVER(ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS seven_day_avg
FROM daily_sales
ORDER BY date;
```

---

### Example 3: Top N per Group

**Problem:** Get top 3 products by sales in each category.

```sql
WITH ranked_products AS (
    SELECT
        product_name,
        category,
        sales,
        ROW_NUMBER() OVER(PARTITION BY category ORDER BY sales DESC) AS rank
    FROM products
)
SELECT * FROM ranked_products WHERE rank <= 3;
```

---

### Example 4: Month-over-Month Growth

**Problem:** Calculate percentage change from previous month.

```sql
SELECT
    month,
    revenue,
    LAG(revenue) OVER(ORDER BY month) AS previous_month_revenue,
    ROUND(
        ((revenue - LAG(revenue) OVER(ORDER BY month)) * 100.0 /
         LAG(revenue) OVER(ORDER BY month)), 2
    ) AS growth_percentage
FROM monthly_revenue
ORDER BY month;
```

---

### Example 5: Moving Averages

**Problem:** Calculate 7-day moving average.

```sql
SELECT
    date,
    sales_amount,
    AVG(sales_amount) OVER(
        ORDER BY date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS seven_day_moving_avg
FROM daily_sales
ORDER BY date;
```

---

### Example 6: Percentile Analysis

**Problem:** Find which percentile each student's score falls into.

```sql
SELECT
    student_name,
    score,
    PERCENT_RANK() OVER(ORDER BY score) * 100 AS percentile,
    CASE
        WHEN PERCENT_RANK() OVER(ORDER BY score) >= 0.9 THEN 'Top 10%'
        WHEN PERCENT_RANK() OVER(ORDER BY score) >= 0.75 THEN 'Top 25%'
        WHEN PERCENT_RANK() OVER(ORDER BY score) >= 0.5 THEN 'Above Average'
        ELSE 'Below Average'
    END AS performance_category
FROM exam_results;
```

---

## Performance Considerations

### 1. Window Functions vs. Subqueries

**Bad (Subquery - executes for each row):**

```sql
SELECT
    id,
    name,
    (SELECT COUNT(*) FROM users WHERE status = 'active') AS total_count
FROM users
WHERE status = 'active'
LIMIT 10;
```

**Good (Window Function - executes once):**

```sql
SELECT
    id,
    name,
    COUNT(*) OVER() AS total_count
FROM users
WHERE status = 'active'
LIMIT 10;
```

### 2. Index Usage

Window functions can use indexes on columns in `ORDER BY` and `PARTITION BY`:

```sql
-- Create index for better performance
CREATE INDEX idx_users_status_created ON users(status, created_at);

-- Window function can use this index
SELECT
    id,
    name,
    ROW_NUMBER() OVER(PARTITION BY status ORDER BY created_at) AS rn
FROM users;
```

### 3. Execution Order

Window functions execute in this order:

1. FROM and JOINs
2. WHERE clause
3. **Window functions** ← Executed here
4. GROUP BY
5. HAVING
6. SELECT
7. DISTINCT
8. ORDER BY
9. LIMIT/OFFSET

This means:

- Window functions see all rows after WHERE filtering
- `COUNT(*) OVER()` counts all matching rows, not just the paginated subset
- Window functions execute before LIMIT/OFFSET

### 4. Memory Considerations

Window functions that use `ORDER BY` may require sorting, which uses memory. For large datasets:

- Use indexes on ORDER BY columns
- Consider using `ROWS BETWEEN` to limit the window size
- Monitor query execution plans

---

## Common Patterns

### Pattern 1: Pagination with Count

```sql
SELECT
    columns...,
    COUNT(*) OVER() AS total_count
FROM table
WHERE conditions...
ORDER BY sort_column
LIMIT n OFFSET m;
```

### Pattern 2: Remove Duplicates

```sql
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER(PARTITION BY unique_column ORDER BY created_at) AS rn
    FROM table
)
SELECT * FROM ranked WHERE rn = 1;
```

### Pattern 3: Compare with Previous/Next

```sql
SELECT
    *,
    LAG(value) OVER(ORDER BY date) AS previous_value,
    LEAD(value) OVER(ORDER BY date) AS next_value
FROM table;
```

### Pattern 4: Running Calculations

```sql
SELECT
    *,
    SUM(amount) OVER(ORDER BY date) AS running_total,
    AVG(amount) OVER(ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS moving_avg
FROM transactions;
```

---

## Summary

Window functions are powerful tools that allow you to:

- ✅ Perform calculations across related rows
- ✅ Get aggregate values without grouping
- ✅ Access previous/next row data
- ✅ Rank and number rows
- ✅ Optimize pagination queries

They're particularly useful for:

- Pagination APIs (get count + data in one query)
- Time-series analysis (running totals, moving averages)
- Ranking and percentile calculations
- Comparing rows with previous/next values

Remember: Window functions execute after WHERE but before LIMIT/OFFSET, making them perfect for getting total counts in paginated queries!
