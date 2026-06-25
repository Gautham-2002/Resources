# PostgreSQL SQL Query Examples: From Basic to Advanced

This document provides copy-paste ready examples for the e-commerce schema. Run these against your PostgreSQL database to see the patterns in action.

---

## SETUP: Create Tables and Sample Data

```sql
-- Create the schema (run this first)
\i postgresql_mastery_guide.md  -- includes all CREATE TABLE statements

-- Or manually paste the schema from the guide

-- Insert sample data
INSERT INTO customers (email, first_name, last_name, phone, preferences, tags)
VALUES 
    ('alice@example.com', 'Alice', 'Johnson', '555-1001', '{"newsletter": true, "theme": "dark"}'::JSONB, ARRAY['premium', 'vip']),
    ('bob@example.com', 'Bob', 'Smith', '555-1002', '{"newsletter": false, "theme": "light"}'::JSONB, ARRAY['standard']),
    ('carol@example.com', 'Carol', 'Davis', '555-1003', '{"newsletter": true, "marketing": true}'::JSONB, ARRAY['premium']),
    ('david@example.com', 'David', 'Wilson', '555-1004', '{"newsletter": false, "currency": "EUR"}'::JSONB, ARRAY['standard', 'new']);

INSERT INTO products (name, description, price, stock_quantity, metadata, categories)
VALUES 
    ('MacBook Pro 16"', 'High-performance laptop', 2499.99, 50, 
     '{"sku": "APPLE-MBP-16", "colors": ["Space Gray", "Silver"], "specs": {"ram_gb": 16, "storage_gb": 512}}'::JSONB, 
     ARRAY['electronics', 'computers', 'laptops']),
    ('USB-C Cable', 'Fast charging cable', 19.99, 200, 
     '{"sku": "CABLE-USB-C", "length_m": 2, "warranty_months": 12}'::JSONB, 
     ARRAY['accessories', 'cables']),
    ('Magic Mouse', 'Wireless mouse', 79.99, 120, 
     '{"sku": "APPLE-MOUSE", "colors": ["White", "Black"], "battery_life_hours": 30}'::JSONB, 
     ARRAY['accessories', 'input-devices']),
    ('Studio Display', '27 inch display', 1599.99, 30, 
     '{"sku": "APPLE-DISPLAY", "resolution": "5K", "brightness_nits": 500}'::JSONB, 
     ARRAY['electronics', 'displays']);

INSERT INTO orders (customer_id, items, total_amount, current_status, shipping_address)
VALUES 
    (1, '[{"product_id": 1, "product_name": "MacBook Pro 16\"", "quantity": 1, "unit_price": 2499.99, "total": 2499.99}]'::JSONB, 
     2499.99, 'pending', '{"city": "New York", "state": "NY"}'::JSONB),
    (1, '[{"product_id": 2, "product_name": "USB-C Cable", "quantity": 2, "unit_price": 19.99, "total": 39.98}]'::JSONB, 
     39.98, 'shipped', '{"city": "New York", "state": "NY"}'::JSONB),
    (2, '[{"product_id": 3, "product_name": "Magic Mouse", "quantity": 1, "unit_price": 79.99, "total": 79.99}]'::JSONB, 
     79.99, 'delivered', '{"city": "Los Angeles", "state": "CA"}'::JSONB),
    (3, '[{"product_id": 1, "product_name": "MacBook Pro 16\"", "quantity": 1, "unit_price": 2499.99, "total": 2499.99}, {"product_id": 4, "product_name": "Studio Display", "quantity": 1, "unit_price": 1599.99, "total": 1599.99}]'::JSONB, 
     4099.98, 'processing', '{"city": "San Francisco", "state": "CA"}'::JSONB);

INSERT INTO reviews (product_id, customer_id, rating, title, body, metadata)
VALUES 
    (1, 1, 5, 'Excellent laptop', 'Best laptop I have ever owned', '{"verified_purchase": true, "helpful_count": 45}'::JSONB),
    (1, 2, 4, 'Great but pricey', 'Powerful machine, very expensive', '{"verified_purchase": true, "helpful_count": 32}'::JSONB),
    (3, 1, 5, 'Perfect mouse', 'Love the Magic Mouse', '{"verified_purchase": true, "helpful_count": 28}'::JSONB),
    (2, 3, 4, 'Good quality cable', 'Works great, fast charging', '{"verified_purchase": true, "helpful_count": 15}'::JSONB);

INSERT INTO payments (order_id, amount, payment_method, status, gateway_response)
VALUES 
    (1, 2499.99, 'credit_card', 'completed', '{"transaction_id": "TXN001", "processor": "Stripe"}'::JSONB),
    (2, 39.98, 'credit_card', 'completed', '{"transaction_id": "TXN002", "processor": "Stripe"}'::JSONB),
    (3, 79.99, 'debit_card', 'completed', '{"transaction_id": "TXN003", "processor": "Stripe"}'::JSONB),
    (4, 4099.98, 'credit_card', 'pending', '{"transaction_id": "TXN004", "processor": "Stripe"}'::JSONB);
```

---

## BASIC CRUD: SELECT

### 1. Select all customers
```sql
SELECT * FROM customers;
```

### 2. Select specific columns with WHERE
```sql
SELECT customer_id, email, first_name, last_name 
FROM customers 
WHERE is_active = true 
ORDER BY first_name ASC;
```

### 3. Extract JSON field
```sql
SELECT 
    customer_id, 
    email, 
    preferences->>'theme' AS theme,
    preferences->>'newsletter' AS newsletter
FROM customers;

-- Output:
-- customer_id | email             | theme | newsletter
-- 1           | alice@example.com | dark  | true
-- 2           | bob@example.com   | light | false
```

### 4. Filter by JSON value
```sql
SELECT customer_id, email, preferences
FROM customers
WHERE preferences->>'newsletter' = 'true';
```

### 5. Extract nested JSON
```sql
SELECT 
    product_id, 
    name, 
    metadata->>'sku' AS sku,
    metadata->'specs'->>'ram_gb' AS ram_gb,
    metadata->'specs'->>'storage_gb' AS storage_gb
FROM products
WHERE name ILIKE '%macbook%';
```

### 6. Array operations - find products with 'premium' tag
```sql
SELECT customer_id, email, tags
FROM customers
WHERE 'premium' = ANY(tags);

-- Alternative syntax:
SELECT customer_id, email, tags
FROM customers
WHERE tags @> ARRAY['premium']::TEXT[];
```

### 7. Unnest JSON array into rows
```sql
SELECT 
    order_id,
    jsonb_array_elements(items)->>'product_id' AS product_id,
    jsonb_array_elements(items)->>'product_name' AS product_name,
    jsonb_array_elements(items)->>'quantity' AS qty,
    jsonb_array_elements(items)->>'unit_price' AS price
FROM orders
WHERE order_id = 1;

-- Output: One row per item in the order
```

### 8. Filter by JSON array contains
```sql
-- Find orders that contain a specific product
SELECT order_id, customer_id, total_amount
FROM orders
WHERE items @> '[{"product_id": 1}]'::JSONB;
```

### 9. Count with aggregation
```sql
SELECT 
    COUNT(*) AS total_customers,
    COUNT(DISTINCT customer_id) AS unique_customers,
    SUM(COALESCE((metadata->>'price')::NUMERIC, 0)) AS total_product_value
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id;
```

### 10. JOIN two tables
```sql
SELECT 
    c.customer_id,
    c.email,
    COUNT(o.order_id) AS order_count,
    SUM(o.total_amount) AS total_spent
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.email
ORDER BY total_spent DESC;

-- LEFT JOIN: Include customers even if they have no orders
-- INNER JOIN: Only customers with orders
```

### 11. Three-table JOIN
```sql
SELECT 
    c.customer_id,
    c.email,
    o.order_id,
    o.order_date,
    p.payment_id,
    p.amount,
    p.status
FROM customers c
INNER JOIN orders o ON c.customer_id = o.customer_id
LEFT JOIN payments p ON o.order_id = p.order_id
WHERE c.is_active = true
ORDER BY c.customer_id, o.order_date DESC;
```

---

## BASIC CRUD: INSERT

### 1. Insert single row with RETURNING
```sql
INSERT INTO customers (email, first_name, last_name, phone, preferences)
VALUES (
    'eve@example.com',
    'Eve',
    'Brown',
    '555-2000',
    '{"newsletter": true, "theme": "dark", "currency": "GBP"}'::JSONB
)
RETURNING customer_id, email;

-- Returns the inserted row(s) immediately
-- Output: customer_id=5, email=eve@example.com
```

### 2. Insert with default values
```sql
INSERT INTO customers (email, first_name, last_name)
VALUES ('frank@example.com', 'Frank', 'Green')
RETURNING *;

-- created_at and updated_at are auto-filled with CURRENT_TIMESTAMP
-- preferences defaults to '{}'
-- tags defaults to empty array
```

### 3. Bulk insert
```sql
INSERT INTO customers (email, first_name, last_name, tags)
VALUES 
    ('grace@example.com', 'Grace', 'Harris', ARRAY['new', 'vip']::TEXT[]),
    ('henry@example.com', 'Henry', 'Taylor', ARRAY['standard']),
    ('iris@example.com', 'Iris', 'Martin', ARRAY['premium', 'loyalty'])
RETURNING customer_id, email;
```

### 4. Insert order with complex JSON
```sql
INSERT INTO orders (customer_id, items, total_amount, current_status, shipping_address)
VALUES (
    1,
    '[
        {"product_id": 1, "product_name": "MacBook Pro 16\"", "quantity": 1, "unit_price": 2499.99, "total": 2499.99},
        {"product_id": 2, "product_name": "USB-C Cable", "quantity": 2, "unit_price": 19.99, "total": 39.98},
        {"product_id": 3, "product_name": "Magic Mouse", "quantity": 1, "unit_price": 79.99, "total": 79.99}
    ]'::JSONB,
    2619.96,
    'pending',
    '{"street": "123 Main St", "city": "New York", "state": "NY", "zip": "10001", "country": "USA"}'::JSONB
)
RETURNING order_id, total_amount;
```

### 5. Insert with SELECT (copy data)
```sql
-- Copy all premium customers into a backup table
INSERT INTO customers_backup (email, first_name, last_name, tags, created_at)
SELECT email, first_name, last_name, tags, created_at
FROM customers
WHERE 'premium' = ANY(tags)
RETURNING customer_id;
```

---

## BASIC CRUD: UPDATE

### 1. Simple update
```sql
UPDATE customers
SET first_name = 'Alexandria', 
    updated_at = CURRENT_TIMESTAMP
WHERE customer_id = 1
RETURNING customer_id, first_name, updated_at;
```

### 2. Update JSON field (merge)
```sql
UPDATE customers
SET preferences = preferences || '{"theme": "light", "language": "es"}'::JSONB,
    updated_at = CURRENT_TIMESTAMP
WHERE customer_id = 2
RETURNING customer_id, preferences;

-- || merges JSON objects
-- Output: preferences now has both old values + new values
```

### 3. Update JSON nested value
```sql
UPDATE products
SET metadata = jsonb_set(metadata, '{specs, ram_gb}', '32'::JSONB),
    updated_at = CURRENT_TIMESTAMP
WHERE product_id = 1
RETURNING product_id, metadata;

-- jsonb_set updates a nested key without losing other data
```

### 4. Add to array
```sql
UPDATE customers
SET tags = array_append(tags, 'vip'),
    updated_at = CURRENT_TIMESTAMP
WHERE customer_id = 2
RETURNING customer_id, tags;

-- Adds single element
-- Alternative: tags = tags || ARRAY['vip']::TEXT[]
```

### 5. Remove from array
```sql
UPDATE customers
SET tags = array_remove(tags, 'new'),
    updated_at = CURRENT_TIMESTAMP
WHERE customer_id = 4
RETURNING customer_id, tags;
```

### 6. Concatenate arrays
```sql
UPDATE customers
SET tags = tags || ARRAY['loyalty_member', 'referrer']::TEXT[],
    updated_at = CURRENT_TIMESTAMP
WHERE customer_id = 1
RETURNING customer_id, tags;
```

### 7. Update with CASE logic
```sql
UPDATE orders
SET current_status = CASE
        WHEN total_amount > 5000 THEN 'vip_priority'
        WHEN total_amount > 1000 THEN 'priority'
        ELSE current_status
    END,
    updated_at = CURRENT_TIMESTAMP
WHERE current_status = 'pending'
RETURNING order_id, total_amount, current_status;
```

### 8. Update with subquery
```sql
UPDATE products
SET stock_quantity = stock_quantity - 5
WHERE product_id IN (
    SELECT DISTINCT (jsonb_array_elements(items)->>'product_id')::INTEGER
    FROM orders
    WHERE order_id = 1
)
RETURNING product_id, stock_quantity;
```

### 9. Batch update multiple rows
```sql
UPDATE orders
SET current_status = 'shipped',
    updated_at = CURRENT_TIMESTAMP
WHERE order_id IN (1, 2, 3)
RETURNING order_id, current_status;
```

### 10. Update with JSON array append (append to status history)
```sql
UPDATE orders
SET status_history = status_history || jsonb_build_array(
        jsonb_build_object(
            'status', 'shipped',
            'timestamp', CURRENT_TIMESTAMP::TEXT,
            'carrier', 'FedEx'
        )
    ),
    current_status = 'shipped',
    updated_at = CURRENT_TIMESTAMP
WHERE order_id = 1
RETURNING order_id, status_history;
```

---

## BASIC CRUD: DELETE

### 1. Delete single row
```sql
DELETE FROM customers
WHERE customer_id = 10
RETURNING customer_id, email;
```

### 2. Delete with condition
```sql
DELETE FROM orders
WHERE current_status = 'cancelled' 
  AND created_at < CURRENT_TIMESTAMP - INTERVAL '6 months'
RETURNING order_id, total_amount;
```

### 3. Delete with subquery
```sql
DELETE FROM orders
WHERE customer_id IN (
    SELECT customer_id FROM customers WHERE is_active = false
)
RETURNING order_id, customer_id;
```

### 4. Soft delete pattern (preferred)
```sql
-- Add deleted_at column if not exists
ALTER TABLE customers ADD COLUMN deleted_at TIMESTAMP;

-- Mark as deleted instead of removing
UPDATE customers
SET deleted_at = CURRENT_TIMESTAMP
WHERE customer_id = 10
RETURNING customer_id, deleted_at;

-- Always filter deleted records in SELECT
SELECT * FROM customers 
WHERE deleted_at IS NULL 
ORDER BY created_at DESC;
```

### 5. Delete all (be careful!)
```sql
DELETE FROM customers WHERE true RETURNING COUNT(*);
-- Much faster than DELETE without WHERE, but dangerous!
```

---

## ADVANCED: Window Functions

### 1. Row numbering and ranking
```sql
-- Rank customers by spending
SELECT 
    c.customer_id,
    c.email,
    COALESCE(SUM(o.total_amount), 0) AS total_spent,
    RANK() OVER (ORDER BY COALESCE(SUM(o.total_amount), 0) DESC) AS spending_rank,
    DENSE_RANK() OVER (ORDER BY COALESCE(SUM(o.total_amount), 0) DESC) AS dense_rank,
    ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(o.total_amount), 0) DESC) AS row_num,
    NTILE(4) OVER (ORDER BY COALESCE(SUM(o.total_amount), 0) DESC) AS quartile
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.email
ORDER BY spending_rank;

-- Output example:
-- customer_id | email            | total_spent | spending_rank | dense_rank | row_num | quartile
-- 3           | carol@example.com | 4099.98    | 1             | 1          | 1       | 1
-- 1           | alice@example.com | 2539.97    | 2             | 2          | 2       | 1
-- 2           | bob@example.com   | 79.99      | 3             | 3          | 3       | 2
```

### 2. Running totals (cumulative sum)
```sql
-- Running total of spending over time
SELECT 
    o.order_id,
    o.customer_id,
    o.order_date,
    o.total_amount,
    SUM(o.total_amount) OVER (
        PARTITION BY o.customer_id 
        ORDER BY o.order_date
    ) AS running_total,
    SUM(o.total_amount) OVER (
        PARTITION BY o.customer_id 
        ORDER BY o.order_date 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_sum
FROM orders o
WHERE o.customer_id = 1
ORDER BY o.order_date;

-- Output:
-- order_id | customer_id | order_date | total_amount | running_total | cumulative_sum
-- 1        | 1           | 2024-01-15 | 2499.99     | 2499.99      | 2499.99
-- 2        | 1           | 2024-01-20 | 39.98       | 2539.97      | 2539.97
```

### 3. LAG and LEAD (compare to previous/next)
```sql
-- Compare each order amount to previous order
SELECT 
    customer_id,
    order_id,
    order_date,
    total_amount,
    LAG(total_amount) OVER (
        PARTITION BY customer_id 
        ORDER BY order_date
    ) AS previous_order_amount,
    LEAD(total_amount) OVER (
        PARTITION BY customer_id 
        ORDER BY order_date
    ) AS next_order_amount,
    total_amount - LAG(total_amount) OVER (
        PARTITION BY customer_id 
        ORDER BY order_date
    ) AS amount_change,
    ROUND(
        100.0 * (total_amount - LAG(total_amount) OVER (
            PARTITION BY customer_id 
            ORDER BY order_date
        )) / LAG(total_amount) OVER (
            PARTITION BY customer_id 
            ORDER BY order_date
        ), 2
    ) AS percent_change
FROM orders
ORDER BY customer_id, order_date;

-- Output:
-- customer_id | order_id | order_date | total_amount | previous_order_amount | amount_change | percent_change
-- 1           | 1        | 2024-01-15 | 2499.99     | NULL                  | NULL          | NULL
-- 1           | 2        | 2024-01-20 | 39.98       | 2499.99               | -2460.01      | -98.40
```

### 4. First and last value in partition
```sql
-- Find first and last order for each customer
SELECT 
    customer_id,
    order_id,
    order_date,
    total_amount,
    FIRST_VALUE(order_date) OVER (
        PARTITION BY customer_id 
        ORDER BY order_date
    ) AS first_order_date,
    LAST_VALUE(order_date) OVER (
        PARTITION BY customer_id 
        ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
    ) AS last_order_date,
    EXTRACT(DAY FROM CURRENT_DATE - FIRST_VALUE(order_date) OVER (
        PARTITION BY customer_id 
        ORDER BY order_date
    )::DATE) AS days_as_customer
FROM orders
ORDER BY customer_id, order_date;
```

### 5. Percentile ranking
```sql
-- Bucket customers into quartiles by spending
SELECT 
    c.customer_id,
    c.email,
    COALESCE(SUM(o.total_amount), 0) AS total_spent,
    PERCENT_RANK() OVER (ORDER BY COALESCE(SUM(o.total_amount), 0) DESC) AS percentile,
    NTILE(4) OVER (ORDER BY COALESCE(SUM(o.total_amount), 0) DESC) AS quartile
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.email
ORDER BY percentile;

-- Output:
-- customer_id | email            | total_spent | percentile | quartile
-- 3           | carol@example.com | 4099.98    | 0.0        | 1
-- 1           | alice@example.com | 2539.97    | 0.33       | 1
```

---

## ADVANCED: Common Table Expressions (CTEs)

### 1. Simple CTE
```sql
-- Calculate customer metrics in steps
WITH customer_orders AS (
    SELECT 
        customer_id,
        COUNT(*) AS order_count,
        SUM(total_amount) AS total_spent,
        AVG(total_amount) AS avg_order,
        MAX(order_date) AS last_order
    FROM orders
    WHERE current_status != 'cancelled'
    GROUP BY customer_id
)
SELECT 
    c.customer_id,
    c.email,
    co.order_count,
    co.total_spent,
    co.avg_order,
    co.last_order
FROM customers c
JOIN customer_orders co ON c.customer_id = co.customer_id
WHERE co.total_spent > 100
ORDER BY co.total_spent DESC;

-- Output:
-- customer_id | email            | order_count | total_spent | avg_order | last_order
-- 3           | carol@example.com | 1           | 4099.98    | 4099.98  | 2024-01-25
-- 1           | alice@example.com | 2           | 2539.97    | 1269.99  | 2024-01-20
```

### 2. Multiple CTEs (chained)
```sql
WITH customer_metrics AS (
    -- First CTE: Calculate customer metrics
    SELECT 
        customer_id,
        COUNT(DISTINCT order_id) AS total_orders,
        SUM(total_amount) AS lifetime_value,
        MAX(order_date) AS last_order_date,
        AVG(total_amount) AS avg_order_value
    FROM orders
    WHERE current_status != 'cancelled'
    GROUP BY customer_id
),
customer_recency AS (
    -- Second CTE: Calculate recency
    SELECT 
        customer_id,
        lifetime_value,
        total_orders,
        EXTRACT(DAY FROM CURRENT_TIMESTAMP - last_order_date)::INTEGER AS days_since_order,
        CASE 
            WHEN EXTRACT(DAY FROM CURRENT_TIMESTAMP - last_order_date)::INTEGER <= 30 THEN 'Active'
            WHEN EXTRACT(DAY FROM CURRENT_TIMESTAMP - last_order_date)::INTEGER <= 90 THEN 'At Risk'
            WHEN EXTRACT(DAY FROM CURRENT_TIMESTAMP - last_order_date)::INTEGER <= 365 THEN 'Inactive'
            ELSE 'Dormant'
        END AS customer_status
    FROM customer_metrics
)
SELECT 
    c.customer_id,
    c.email,
    cr.lifetime_value,
    cr.total_orders,
    cr.days_since_order,
    cr.customer_status
FROM customers c
JOIN customer_recency cr ON c.customer_id = cr.customer_id
WHERE cr.lifetime_value > 50
ORDER BY cr.lifetime_value DESC;

-- Output:
-- customer_id | email            | lifetime_value | total_orders | days_since_order | customer_status
-- 3           | carol@example.com | 4099.98       | 1            | 2                | Active
-- 1           | alice@example.com | 2539.97       | 2            | 7                | Active
```

### 3. CTE with window functions (RFM Segmentation)
```sql
WITH order_metrics AS (
    SELECT 
        customer_id,
        COUNT(DISTINCT order_id) AS frequency,
        SUM(total_amount) AS monetary,
        EXTRACT(DAY FROM CURRENT_TIMESTAMP - MAX(order_date))::INTEGER AS recency_days
    FROM orders
    WHERE current_status != 'cancelled'
    GROUP BY customer_id
),
rfm_scores AS (
    SELECT 
        customer_id,
        frequency,
        monetary,
        recency_days,
        NTILE(5) OVER (ORDER BY recency_days) AS r_score,
        NTILE(5) OVER (ORDER BY frequency DESC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary DESC) AS m_score
    FROM order_metrics
),
segments AS (
    SELECT 
        customer_id,
        frequency,
        monetary,
        recency_days,
        r_score,
        f_score,
        m_score,
        (r_score + f_score + m_score) / 3 AS rfm_avg,
        CASE 
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Loyal'
            WHEN r_score >= 4 THEN 'At Risk'
            WHEN f_score < 3 AND m_score < 3 THEN 'Lost'
            ELSE 'Potential'
        END AS segment
    FROM rfm_scores
)
SELECT 
    c.customer_id,
    c.email,
    s.frequency,
    s.monetary,
    s.recency_days,
    s.segment
FROM customers c
JOIN segments s ON c.customer_id = s.customer_id
ORDER BY s.rfm_avg DESC;
```

---

## ADVANCED: JSON Aggregation

### 1. Build JSON object from aggregated rows
```sql
-- Create customer summary
SELECT 
    c.customer_id,
    json_build_object(
        'email', c.email,
        'full_name', c.first_name || ' ' || c.last_name,
        'total_orders', COUNT(DISTINCT o.order_id),
        'lifetime_value', COALESCE(SUM(o.total_amount), 0),
        'last_order', MAX(o.order_date),
        'is_premium', 'premium' = ANY(c.tags)
    ) AS customer_summary
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.email, c.first_name, c.last_name;

-- Output:
-- customer_id | customer_summary
-- 1           | {"email": "alice@example.com", "full_name": "Alice Johnson", "total_orders": 2, "lifetime_value": 2539.97, "last_order": "2024-01-20", "is_premium": true}
```

### 2. Build JSON array from aggregated rows
```sql
-- Build customer with array of all their orders
SELECT 
    c.customer_id,
    c.email,
    json_build_object(
        'customer', json_build_object(
            'id', c.customer_id,
            'email', c.email,
            'name', c.first_name || ' ' || c.last_name
        ),
        'orders', json_agg(
            json_build_object(
                'order_id', o.order_id,
                'date', o.order_date,
                'amount', o.total_amount,
                'status', o.current_status
            ) ORDER BY o.order_date DESC
        ) FILTER (WHERE o.order_id IS NOT NULL)
    ) AS customer_data
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.email, c.first_name, c.last_name
LIMIT 5;

-- Output: Single JSON object with nested arrays
```

### 3. Nested JSON aggregation with details
```sql
-- Build each order with its items and payment status
SELECT 
    o.order_id,
    json_build_object(
        'order_id', o.order_id,
        'customer_id', o.customer_id,
        'total_amount', o.total_amount,
        'status', o.current_status,
        'order_date', o.order_date,
        'shipping', o.shipping_address,
        'items', json_agg(
            json_build_object(
                'product_id', (item->>'product_id')::INTEGER,
                'product_name', item->>'product_name',
                'quantity', (item->>'quantity')::INTEGER,
                'unit_price', (item->>'unit_price')::NUMERIC,
                'total', (item->>'total')::NUMERIC
            ) ORDER BY (item->>'product_id')::INTEGER
        ),
        'payment_status', (SELECT p.status FROM payments p WHERE p.order_id = o.order_id LIMIT 1)
    ) AS order_details
FROM orders o,
     jsonb_array_elements(o.items) AS item
GROUP BY o.order_id
LIMIT 3;

-- Output: Complete order details with items
```

---

## ADVANCED: Subqueries and Derived Tables

### 1. Subquery in WHERE clause
```sql
-- Find customers who spent more than the average
SELECT 
    c.customer_id,
    c.email,
    SUM(o.total_amount) AS total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.email
HAVING SUM(o.total_amount) > (
    SELECT AVG(total_amount) FROM orders WHERE current_status != 'cancelled'
)
ORDER BY total_spent DESC;
```

### 2. Derived table (FROM subquery)
```sql
-- Find top performing months
SELECT 
    month,
    total_orders,
    total_revenue,
    avg_order_value,
    ROUND(100.0 * total_revenue / SUM(total_revenue) OVER (), 2) AS pct_of_total
FROM (
    SELECT 
        DATE_TRUNC('month', order_date)::DATE AS month,
        COUNT(*) AS total_orders,
        SUM(total_amount) AS total_revenue,
        ROUND(AVG(total_amount), 2) AS avg_order_value
    FROM orders
    WHERE current_status != 'cancelled'
    GROUP BY DATE_TRUNC('month', order_date)
) monthly_stats
ORDER BY month DESC;
```

### 3. IN subquery
```sql
-- Find products ordered by VIP customers
SELECT DISTINCT p.product_id, p.name, p.price
FROM products p
WHERE p.product_id IN (
    SELECT DISTINCT (jsonb_array_elements(o.items)->>'product_id')::INTEGER
    FROM orders o
    WHERE o.customer_id IN (
        SELECT customer_id FROM customers WHERE 'premium' = ANY(tags)
    )
)
ORDER BY p.name;
```

---

## ADVANCED: Full Text Search

### 1. Simple text search
```sql
-- Search for products
SELECT 
    product_id,
    name,
    description,
    ts_rank(
        to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(description, '')),
        plainto_tsquery('english', 'laptop')
    ) AS relevance
FROM products
WHERE to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(description, '')) 
      @@ plainto_tsquery('english', 'laptop')
ORDER BY relevance DESC;
```

### 2. Search reviews
```sql
-- Search reviews for specific words
SELECT 
    r.review_id,
    r.product_id,
    r.rating,
    r.title,
    r.body,
    ts_rank(
        to_tsvector('english', COALESCE(r.body, '')),
        plainto_tsquery('english', 'excellent quality')
    ) AS relevance
FROM reviews r
WHERE to_tsvector('english', COALESCE(r.body, '')) 
      @@ plainto_tsquery('english', 'excellent quality')
ORDER BY relevance DESC;
```

---

## PERFORMANCE PATTERNS

### 1. Check query performance
```sql
-- See execution plan
EXPLAIN SELECT * FROM orders WHERE customer_id = 1 AND current_status = 'shipped';

-- Get actual execution stats
EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 1;
```

### 2. Create indexes
```sql
-- Single column
CREATE INDEX idx_orders_customer_status ON orders(customer_id, current_status);

-- Partial index (only index certain rows)
CREATE INDEX idx_active_orders ON orders(customer_id) 
WHERE current_status != 'cancelled';

-- JSONB index
CREATE INDEX idx_products_metadata ON products USING GIN(metadata);

-- Array index
CREATE INDEX idx_customers_tags ON customers USING GIN(tags);

-- Expression index
CREATE INDEX idx_customer_email_lower ON customers(LOWER(email));
```

### 3. Optimize with proper SELECT
```sql
-- Good: Only fetch needed columns
SELECT customer_id, email, first_name FROM customers;

-- Bad: Fetch everything even if you need 2 columns
SELECT * FROM customers;

-- Good: Use EXISTS for existence checks
SELECT * FROM customers c
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id);

-- Bad: Use COUNT (counts all rows)
SELECT * FROM customers c
WHERE (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.customer_id) > 0;
```

---

## COMMON PATTERNS

### 1. Get latest order per customer
```sql
WITH ranked_orders AS (
    SELECT 
        o.*,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn
    FROM orders o
)
SELECT * FROM ranked_orders WHERE rn = 1;
```

### 2. Customer lifetime value (CLV)
```sql
SELECT 
    c.customer_id,
    c.email,
    COUNT(DISTINCT o.order_id) AS lifetime_orders,
    SUM(o.total_amount) AS lifetime_revenue,
    AVG(o.total_amount) AS avg_order_value,
    MIN(o.order_date) AS first_order_date,
    MAX(o.order_date) AS most_recent_order,
    EXTRACT(DAY FROM MAX(o.order_date) - MIN(o.order_date)) AS customer_lifespan_days
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE o.current_status != 'cancelled'
GROUP BY c.customer_id, c.email
ORDER BY lifetime_revenue DESC;
```

### 3. Churn analysis (inactive customers)
```sql
WITH last_order AS (
    SELECT 
        customer_id,
        MAX(order_date) AS most_recent_order
    FROM orders
    GROUP BY customer_id
)
SELECT 
    c.customer_id,
    c.email,
    lo.most_recent_order,
    EXTRACT(DAY FROM CURRENT_TIMESTAMP - lo.most_recent_order)::INTEGER AS days_inactive,
    CASE 
        WHEN EXTRACT(DAY FROM CURRENT_TIMESTAMP - lo.most_recent_order)::INTEGER <= 30 THEN 'Active'
        WHEN EXTRACT(DAY FROM CURRENT_TIMESTAMP - lo.most_recent_order)::INTEGER <= 90 THEN 'At Risk'
        WHEN EXTRACT(DAY FROM CURRENT_TIMESTAMP - lo.most_recent_order)::INTEGER <= 180 THEN 'Inactive'
        ELSE 'Dormant'
    END AS churn_status
FROM customers c
LEFT JOIN last_order lo ON c.customer_id = lo.customer_id
WHERE lo.most_recent_order IS NOT NULL
ORDER BY days_inactive DESC;
```

### 4. Product popularity
```sql
SELECT 
    p.product_id,
    p.name,
    COUNT(DISTINCT o.order_id) AS times_ordered,
    SUM((jsonb_array_elements(o.items)->>'quantity')::INTEGER) AS total_quantity_sold,
    ROUND(AVG(r.rating), 2) AS avg_rating,
    COUNT(DISTINCT r.review_id) AS review_count
FROM products p
LEFT JOIN orders o ON o.items @> jsonb_build_array(
    jsonb_build_object('product_id', p.product_id)
)
LEFT JOIN reviews r ON p.product_id = r.product_id
GROUP BY p.product_id, p.name
HAVING COUNT(DISTINCT o.order_id) > 0
ORDER BY total_quantity_sold DESC;
```

### 5. Sales by category
```sql
SELECT 
    UNNEST(p.categories) AS category,
    COUNT(DISTINCT o.order_id) AS order_count,
    SUM(o.total_amount) AS category_revenue,
    COUNT(DISTINCT p.product_id) AS product_count
FROM products p
LEFT JOIN orders o ON o.items @> jsonb_build_array(
    jsonb_build_object('product_id', p.product_id)
)
GROUP BY category
ORDER BY category_revenue DESC;
```

---

## Tips & Tricks

1. **Always use COALESCE for aggregates**: `COALESCE(SUM(amount), 0)`
2. **Use FILTER for conditional aggregation**: `COUNT(*) FILTER (WHERE status = 'active')`
3. **Use DISTINCT ON for getting one row per group**: `SELECT DISTINCT ON (customer_id) * FROM orders ORDER BY customer_id, created_at DESC`
4. **JSON vs JSONB**: Always use JSONB (with index support)
5. **Test your indexes**: Use EXPLAIN ANALYZE to verify they're being used
6. **Use RETURNING to confirm changes**: Helps catch logic errors immediately

Happy querying!
