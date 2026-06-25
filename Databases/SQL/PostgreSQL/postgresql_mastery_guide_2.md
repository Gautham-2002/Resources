# PostgreSQL Mastery: From Fundamentals to Advanced Patterns

## Part 1: PostgreSQL Architecture & Philosophy

### Why PostgreSQL Stands Out

PostgreSQL is the most feature-rich open-source relational database. Here's why engineers love it:

1. **ACID Compliance**: Guaranteed transaction integrity
2. **Rich Data Types**: JSON, Arrays, Range types, UUIDs, Custom types
3. **Advanced Query Features**: Window functions, CTEs, Lateral joins
4. **Extensibility**: Write custom functions in PL/pgSQL, Python, or native code
5. **Reliability**: Row-level versioning (MVCC), crash-safe, point-in-time recovery
6. **Performance**: Sophisticated query planner, parallel queries, partial indexes

### Key Concepts to Understand

**MVCC (Multi-Version Concurrency Control)**: PostgreSQL doesn't lock reads. Instead, each transaction sees a snapshot of data at transaction start time. This allows true concurrent reading and writing without contention.

**Indexes**: Speed up queries by organizing data. PostgreSQL supports B-tree (default), Hash, GiST, SP-GiST, GIN, and BRIN indexes.

**Constraints**: Enforce data integrity (NOT NULL, UNIQUE, PRIMARY KEY, FOREIGN KEY, CHECK).

**Schemas**: Organize tables into logical namespaces (like directories for database objects).

---

## Part 2: Real-World Schema: E-Commerce Platform

Let's design a schema for an e-commerce platform that covers:
- Basic CRUD operations
- JSON storage (product metadata, customer preferences)
- Arrays (product tags, order items)
- Relationships (foreign keys)
- Temporal data (timestamps, versioning)
- Numeric and text data

### Schema Overview

```sql
-- 1. CUSTOMERS TABLE: Core customer data
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    
    -- JSON column: Flexible metadata
    preferences JSONB DEFAULT '{}',
    -- Examples: {"newsletter": true, "marketing_emails": false, "theme": "dark"}
    
    -- Array column: Tags for segmentation
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- Examples: ['premium', 'high_spender', 'new_customer']
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- 2. PRODUCTS TABLE: Product catalog
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    
    -- JSON: Product attributes (flexible schema)
    metadata JSONB DEFAULT '{}',
    -- Examples: {
    --     "sku": "PROD-001",
    --     "weight_kg": 2.5,
    --     "dimensions": {"length": 10, "width": 5, "height": 3},
    --     "colors": ["red", "blue", "green"],
    --     "material": "leather"
    -- }
    
    -- Array: Product categories/tags
    categories TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- Examples: ['electronics', 'computers', 'laptops']
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. ORDERS TABLE: Customer orders
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Order items stored as JSONB array (denormalized for simplicity)
    items JSONB NOT NULL,
    -- Structure: [
    --     {"product_id": 1, "quantity": 2, "unit_price": 29.99, "total": 59.98},
    --     {"product_id": 3, "quantity": 1, "unit_price": 49.99, "total": 49.99}
    -- ]
    
    total_amount DECIMAL(10, 2) NOT NULL,
    
    -- Order status with history (JSONB array)
    status_history JSONB DEFAULT '[{"status": "pending", "timestamp": "now"}]',
    
    -- Simple column for current status
    current_status VARCHAR(50) DEFAULT 'pending',
    -- Values: pending, processing, shipped, delivered, cancelled
    
    shipping_address JSONB,
    -- Structure: {
    --     "street": "123 Main St",
    --     "city": "New York",
    --     "state": "NY",
    --     "zip": "10001",
    --     "country": "USA"
    -- }
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. REVIEWS TABLE: Product reviews
CREATE TABLE reviews (
    review_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(255),
    body TEXT,
    
    -- Review metadata as JSON
    metadata JSONB DEFAULT '{}',
    -- Examples: {"verified_purchase": true, "helpful_count": 45}
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. INVENTORY_LOGS TABLE: Inventory audit trail
CREATE TABLE inventory_logs (
    log_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    
    quantity_changed INTEGER NOT NULL,
    reason VARCHAR(100),
    -- Values: 'purchase', 'restock', 'return', 'damage', 'adjustment'
    
    previous_quantity INTEGER,
    new_quantity INTEGER,
    
    -- Context as JSON
    context JSONB DEFAULT '{}',
    -- Examples: {"order_id": 123, "user_id": 456, "notes": "Customer return"}
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. PAYMENTS TABLE: Payment transactions
CREATE TABLE payments (
    payment_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    
    amount DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(50),
    -- Values: 'credit_card', 'debit_card', 'paypal', 'bank_transfer'
    
    status VARCHAR(50) DEFAULT 'pending',
    -- Values: pending, completed, failed, refunded
    
    -- Payment gateway response (can be large JSON)
    gateway_response JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- INDEXES FOR PERFORMANCE
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_reviews_product_id ON reviews(product_id);
CREATE INDEX idx_reviews_customer_id ON reviews(customer_id);
CREATE INDEX idx_products_categories ON products USING GIN(categories);
-- GIN index for array columns speeds up @> (contains) queries

-- JSONB indexes for faster JSON queries
CREATE INDEX idx_orders_items ON orders USING GIN(items);
CREATE INDEX idx_products_metadata ON products USING GIN(metadata);
```

---

## Part 3: Basic CRUD Operations

### CREATE (INSERT)

**1. Insert a single customer:**
```sql
INSERT INTO customers (email, first_name, last_name, phone, preferences, tags)
VALUES (
    'alice@example.com',
    'Alice',
    'Johnson',
    '555-1234',
    '{"newsletter": true, "marketing_emails": false, "theme": "dark", "currency": "USD"}'::JSONB,
    ARRAY['premium', 'vip']::TEXT[]
)
RETURNING customer_id, email;
-- RETURNING: Shows inserted data back (handy for getting auto-generated IDs)
```

**2. Insert a product with complex metadata:**
```sql
INSERT INTO products (name, description, price, stock_quantity, metadata, categories)
VALUES (
    'MacBook Pro 16"',
    'High-performance laptop for professionals',
    2499.99,
    50,
    '{
        "sku": "APPLE-MBP-16-2024",
        "weight_kg": 2.1,
        "dimensions": {
            "length": 35.9,
            "width": 24.8,
            "height": 1.7,
            "unit": "cm"
        },
        "colors": ["Space Gray", "Silver", "Gold"],
        "specs": {
            "processor": "M3 Max",
            "ram_gb": 36,
            "storage_gb": 512,
            "gpu_cores": 12
        },
        "warranty_months": 12,
        "in_stock": true
    }'::JSONB,
    ARRAY['electronics', 'computers', 'laptops', 'apple']::TEXT[]
)
RETURNING product_id, name;
```

**3. Insert an order with items as JSON array:**
```sql
INSERT INTO orders (customer_id, items, total_amount, shipping_address, current_status)
VALUES (
    1,
    '[
        {
            "product_id": 5,
            "product_name": "MacBook Pro 16\"",
            "quantity": 1,
            "unit_price": 2499.99,
            "total": 2499.99
        },
        {
            "product_id": 12,
            "product_name": "USB-C Cable",
            "quantity": 2,
            "unit_price": 19.99,
            "total": 39.98
        }
    ]'::JSONB,
    2539.97,
    '{
        "street": "123 Apple Lane",
        "city": "Cupertino",
        "state": "CA",
        "zip": "95014",
        "country": "USA"
    }'::JSONB,
    'pending'
)
RETURNING order_id, total_amount;
```

**4. Bulk insert multiple customers:**
```sql
INSERT INTO customers (email, first_name, last_name, tags)
VALUES
    ('bob@example.com', 'Bob', 'Smith', ARRAY['standard', 'new']),
    ('carol@example.com', 'Carol', 'Davis', ARRAY['premium']),
    ('david@example.com', 'David', 'Wilson', ARRAY['standard', 'returning'])
RETURNING customer_id, email, tags;
```

**5. Insert with generated unique ID (UUID):**
```sql
-- If you prefer UUIDs instead of SERIAL
ALTER TABLE customers ADD COLUMN customer_uuid UUID DEFAULT gen_random_uuid() UNIQUE;

-- Now insert
INSERT INTO customers (email, first_name, last_name, customer_uuid)
VALUES ('eve@example.com', 'Eve', 'Brown', gen_random_uuid())
RETURNING customer_uuid, email;
```

---

### READ (SELECT)

**1. Simple select with WHERE clause:**
```sql
-- Get all active customers
SELECT customer_id, email, first_name, last_name, created_at
FROM customers
WHERE is_active = true
ORDER BY created_at DESC;
```

**2. Extract from JSON (JSONB ->> operator):**
```sql
-- Get customers with specific preference
SELECT customer_id, email, first_name,
       preferences->>'theme' AS theme,
       preferences->>'currency' AS currency
FROM customers
WHERE preferences->>'newsletter' = 'true'
ORDER BY email;
-- ->> extracts JSON value as text
-- -> extracts JSON value as JSON
```

**3. Query with array contains:**
```sql
-- Find all premium customers
SELECT customer_id, email, tags
FROM customers
WHERE 'premium' = ANY(tags);
-- Alternative syntax: WHERE tags @> ARRAY['premium']
-- @> means "contains" for arrays and JSON
```

**4. Complex JSON extraction:**
```sql
-- Get product specs
SELECT 
    product_id,
    name,
    price,
    metadata->>'sku' AS sku,
    metadata->'specs'->>'processor' AS processor,
    metadata->'specs'->>'ram_gb' AS ram_gb,
    metadata->'dimensions'->>'height' AS height_cm
FROM products
WHERE name ILIKE '%macbook%';
-- ILIKE: case-insensitive LIKE
```

**5. Unnest array to rows:**
```sql
-- Expand product colors into separate rows
SELECT 
    product_id,
    name,
    jsonb_array_elements(metadata->'specs'->'colors') AS color
FROM products
WHERE metadata ? 'specs';
-- ? operator checks if JSON has a key
```

**6. Filter by JSON object properties:**
```sql
-- Find all products with warranty > 12 months
SELECT product_id, name, price
FROM products
WHERE (metadata->>'warranty_months')::INTEGER > 12;
-- :: is the cast operator (convert type)
```

**7. Select order items (unnest JSON array):**
```sql
-- Expand order items into separate rows
SELECT 
    order_id,
    customer_id,
    order_date,
    jsonb_array_elements(items)->>'product_id' AS product_id,
    jsonb_array_elements(items)->>'quantity' AS quantity,
    jsonb_array_elements(items)->>'unit_price' AS unit_price
FROM orders
WHERE order_id = 1;
```

**8. Complex filtering on nested JSON:**
```sql
-- Find orders with items that have specific product_id
SELECT order_id, customer_id, total_amount
FROM orders
WHERE items @> '[{"product_id": 5}]'::JSONB;
```

**9. Count and aggregate:**
```sql
-- Count orders per customer
SELECT 
    customer_id,
    COUNT(*) AS total_orders,
    SUM(total_amount) AS total_spent,
    AVG(total_amount) AS avg_order_value,
    MAX(order_date) AS last_order_date
FROM orders
WHERE current_status != 'cancelled'
GROUP BY customer_id
HAVING COUNT(*) > 1
ORDER BY total_spent DESC;
```

**10. Join multiple tables:**
```sql
-- Get customer with their recent orders and total spending
SELECT 
    c.customer_id,
    c.email,
    c.first_name,
    o.order_id,
    o.order_date,
    o.total_amount,
    o.current_status
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE c.is_active = true
ORDER BY c.customer_id, o.order_date DESC;
```

---

### UPDATE

**1. Simple update:**
```sql
-- Update customer information
UPDATE customers
SET first_name = 'Alexandra',
    updated_at = CURRENT_TIMESTAMP
WHERE customer_id = 1
RETURNING customer_id, first_name, updated_at;
```

**2. Update JSON field:**
```sql
-- Update customer preference
UPDATE customers
SET preferences = preferences || '{"theme": "light", "language": "es"}'::JSONB,
    updated_at = CURRENT_TIMESTAMP
WHERE customer_id = 1
RETURNING customer_id, preferences;
-- || merges JSON objects
```

**3. Update array field:**
```sql
-- Add a tag to customer
UPDATE customers
SET tags = array_append(tags, 'loyal_customer'),
    updated_at = CURRENT_TIMESTAMP
WHERE customer_id = 1
RETURNING customer_id, tags;

-- Add multiple tags
UPDATE customers
SET tags = tags || ARRAY['loyalty_program', 'referrer']::TEXT[],
    updated_at = CURRENT_TIMESTAMP
WHERE customer_id = 1;

-- Remove a tag
UPDATE customers
SET tags = array_remove(tags, 'new_customer'),
    updated_at = CURRENT_TIMESTAMP
WHERE customer_id = 1;
```

**4. Update based on condition (CASE):**
```sql
-- Update order status
UPDATE orders
SET current_status = CASE
        WHEN CURRENT_TIMESTAMP > created_at + INTERVAL '3 days' AND current_status = 'pending'
        THEN 'abandoned'
        WHEN total_amount > 1000 THEN 'priority'
        ELSE current_status
    END,
    updated_at = CURRENT_TIMESTAMP
WHERE customer_id = 1;
```

**5. Update with JSON array append (for status history):**
```sql
-- Add status to order history
UPDATE orders
SET status_history = status_history || 
    jsonb_build_array(
        jsonb_build_object(
            'status', 'shipped',
            'timestamp', CURRENT_TIMESTAMP,
            'notes', 'Shipped via FedEx'
        )
    ),
    current_status = 'shipped',
    updated_at = CURRENT_TIMESTAMP
WHERE order_id = 1
RETURNING order_id, current_status, status_history;
```

**6. Update stock based on order (inventory management):**
```sql
-- Decrease stock when order is placed
UPDATE products
SET stock_quantity = stock_quantity - (
    SELECT COALESCE(SUM((item->>'quantity')::INTEGER), 0)
    FROM orders, jsonb_array_elements(orders.items) AS item
    WHERE orders.order_id = 1 AND (item->>'product_id')::INTEGER = products.product_id
),
updated_at = CURRENT_TIMESTAMP
WHERE product_id IN (
    SELECT DISTINCT (jsonb_array_elements(items)->>'product_id')::INTEGER
    FROM orders
    WHERE order_id = 1
);
```

---

### DELETE

**1. Simple delete:**
```sql
-- Delete a customer (be careful!)
DELETE FROM customers
WHERE customer_id = 10
RETURNING customer_id, email;
```

**2. Delete with condition:**
```sql
-- Delete inactive orders from 1 year ago
DELETE FROM orders
WHERE current_status = 'cancelled'
  AND created_at < CURRENT_TIMESTAMP - INTERVAL '1 year'
RETURNING order_id, customer_id, total_amount;
```

**3. Delete with constraint handling:**
```sql
-- If you have foreign key constraints, you might get errors
-- Option 1: Delete child records first
DELETE FROM reviews WHERE customer_id = 10;
DELETE FROM orders WHERE customer_id = 10;
DELETE FROM customers WHERE customer_id = 10;

-- Option 2: Use ON DELETE CASCADE on the foreign key (set when creating table)
-- ALTER TABLE orders DROP CONSTRAINT orders_customer_id_fkey;
-- ALTER TABLE orders ADD CONSTRAINT orders_customer_id_fkey
--     FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE;
```

**4. Archive instead of delete (soft delete pattern):**
```sql
-- Better practice: mark as deleted instead of removing
ALTER TABLE customers ADD COLUMN deleted_at TIMESTAMP;

UPDATE customers
SET deleted_at = CURRENT_TIMESTAMP
WHERE customer_id = 10
RETURNING customer_id, email, deleted_at;

-- Now always filter deleted records in SELECT
SELECT * FROM customers WHERE deleted_at IS NULL;
```

---

## Part 4: Advanced SQL Patterns

### Window Functions (Analytic Functions)

Window functions perform calculations across rows without collapsing them.

**1. Row numbering and ranking:**
```sql
-- Rank customers by total spending
SELECT 
    c.customer_id,
    c.email,
    SUM(o.total_amount) AS total_spent,
    RANK() OVER (ORDER BY SUM(o.total_amount) DESC) AS spending_rank,
    DENSE_RANK() OVER (ORDER BY SUM(o.total_amount) DESC) AS dense_rank,
    ROW_NUMBER() OVER (ORDER BY SUM(o.total_amount) DESC) AS row_num
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE o.current_status != 'cancelled'
GROUP BY c.customer_id, c.email
ORDER BY spending_rank;

-- RANK: 1, 2, 2, 4 (skips numbers after tie)
-- DENSE_RANK: 1, 2, 2, 3 (no gaps)
-- ROW_NUMBER: 1, 2, 3, 4 (always sequential)
```

**2. Running totals (cumulative sum):**
```sql
-- Running total of order amounts
SELECT 
    order_id,
    customer_id,
    order_date,
    total_amount,
    SUM(total_amount) OVER (
        PARTITION BY customer_id 
        ORDER BY order_date
    ) AS running_total,
    SUM(total_amount) OVER (
        PARTITION BY customer_id 
        ORDER BY order_date 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_sum
FROM orders
WHERE customer_id = 1
ORDER BY order_date;
```

**3. Compare to previous row (LAG) and next row (LEAD):**
```sql
-- Compare each order to previous order
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
WHERE current_status != 'cancelled'
ORDER BY customer_id, order_date;
```

**4. Percentile ranking:**
```sql
-- Bucket customers into quartiles by spending
SELECT 
    c.customer_id,
    c.email,
    COALESCE(SUM(o.total_amount), 0) AS total_spent,
    NTILE(4) OVER (ORDER BY COALESCE(SUM(o.total_amount), 0) DESC) AS spending_quartile,
    -- 1 = top quartile, 4 = bottom
    PERCENT_RANK() OVER (ORDER BY COALESCE(SUM(o.total_amount), 0) DESC) AS percentile
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.email
ORDER BY spending_quartile, percentile;
```

**5. First and last in partition:**
```sql
-- Get first and last order for each customer
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
    DATEDIFF(day, 
        FIRST_VALUE(order_date) OVER (PARTITION BY customer_id ORDER BY order_date),
        CURRENT_DATE
    ) AS days_as_customer
FROM orders
ORDER BY customer_id, order_date;
```

**6. Moving average (smoothing data):**
```sql
-- 7-day moving average of orders
SELECT 
    DATE(order_date) AS order_day,
    COUNT(*) AS orders_count,
    ROUND(
        AVG(COUNT(*)) OVER (
            ORDER BY DATE(order_date)
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ), 2
    ) AS moving_avg_7day
FROM orders
GROUP BY DATE(order_date)
ORDER BY order_day DESC;
```

---

### Common Table Expressions (CTEs)

CTEs make complex queries readable by breaking them into named steps.

**1. Simple CTE:**
```sql
-- Calculate customer metrics in steps
WITH customer_orders AS (
    SELECT 
        customer_id,
        COUNT(*) AS order_count,
        SUM(total_amount) AS total_spent,
        AVG(total_amount) AS avg_order
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
    ROUND(co.avg_order * 1.1, 2) AS projected_next_order
FROM customers c
JOIN customer_orders co ON c.customer_id = co.customer_id
WHERE co.total_spent > 1000
ORDER BY co.total_spent DESC;
```

**2. Multiple CTEs (chained):**
```sql
WITH customer_metrics AS (
    -- First CTE: Calculate customer order metrics
    SELECT 
        customer_id,
        COUNT(*) AS total_orders,
        SUM(total_amount) AS lifetime_value,
        MAX(order_date) AS last_order_date,
        AVG(total_amount) AS avg_order_value
    FROM orders
    WHERE current_status != 'cancelled'
    GROUP BY customer_id
),
customer_recency AS (
    -- Second CTE: Calculate how recently customer ordered
    SELECT 
        customer_id,
        (CURRENT_TIMESTAMP - last_order_date)::INTEGER / 86400 AS days_since_order,
        CASE 
            WHEN (CURRENT_TIMESTAMP - last_order_date)::INTEGER / 86400 <= 30 THEN 'Active'
            WHEN (CURRENT_TIMESTAMP - last_order_date)::INTEGER / 86400 <= 90 THEN 'At Risk'
            WHEN (CURRENT_TIMESTAMP - last_order_date)::INTEGER / 86400 <= 365 THEN 'Inactive'
            ELSE 'Dormant'
        END AS customer_status
    FROM customer_metrics
)
SELECT 
    c.customer_id,
    c.email,
    cm.lifetime_value,
    cm.total_orders,
    cr.customer_status,
    cr.days_since_order
FROM customers c
JOIN customer_metrics cm ON c.customer_id = cm.customer_id
JOIN customer_recency cr ON c.customer_id = cr.customer_id
WHERE cm.lifetime_value > 500
ORDER BY cm.lifetime_value DESC;
```

**3. Recursive CTE (for hierarchical data):**
```sql
-- Example: Category hierarchy (if you had nested categories)
WITH RECURSIVE category_tree AS (
    -- Base case: top-level categories
    SELECT 1 AS category_id, NULL::INTEGER AS parent_id, 'Electronics'::VARCHAR AS name, 0 AS depth
    UNION ALL
    SELECT 2, 1, 'Laptops', 1
    UNION ALL
    SELECT 3, 1, 'Phones', 1
    UNION ALL
    SELECT 4, 2, 'Gaming Laptops', 2
    UNION ALL
    SELECT 5, 2, 'Business Laptops', 2
)
SELECT 
    category_id,
    parent_id,
    REPEAT('  ', depth) || name AS category_path,
    depth
FROM category_tree
ORDER BY category_id;
```

**4. CTE with window functions:**
```sql
-- Find top 3 products in each category
WITH product_sales AS (
    SELECT 
        p.product_id,
        p.name,
        p.categories[1] AS category,
        COUNT(DISTINCT o.order_id) AS sales_count,
        SUM((jsonb_array_elements(o.items)->>'quantity')::INTEGER) AS total_quantity_sold,
        ROW_NUMBER() OVER (
            PARTITION BY p.categories[1] 
            ORDER BY COUNT(DISTINCT o.order_id) DESC
        ) AS rank_in_category
    FROM products p
    LEFT JOIN orders o ON o.items @> jsonb_build_array(
        jsonb_build_object('product_id', p.product_id)
    )
    GROUP BY p.product_id, p.name, p.categories[1]
)
SELECT 
    category,
    product_id,
    name,
    sales_count,
    total_quantity_sold,
    rank_in_category
FROM product_sales
WHERE rank_in_category <= 3
ORDER BY category, rank_in_category;
```

---

### JSON Aggregation (Building JSON from rows)

**1. Aggregate rows into JSON object:**
```sql
-- Build customer summary with their recent orders
SELECT 
    c.customer_id,
    c.email,
    c.first_name,
    json_build_object(
        'email', c.email,
        'full_name', c.first_name || ' ' || c.last_name,
        'total_orders', COUNT(DISTINCT o.order_id),
        'lifetime_value', COALESCE(SUM(o.total_amount), 0),
        'last_order', MAX(o.order_date),
        'is_vip', 'premium' = ANY(c.tags)
    ) AS customer_summary
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.email, c.first_name, c.last_name;
```

**2. Aggregate rows into JSON array:**
```sql
-- Build customer with array of their orders
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
```

**3. Nested JSON aggregation (detailed order with items):**
```sql
-- Build each order with all its items and product details
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
            ) ORDER BY item->>'product_id'
        )
    ) AS order_details
FROM orders o,
     jsonb_array_elements(o.items) AS item
GROUP BY o.order_id
LIMIT 5;
```

---

### Subqueries and Derived Tables

**1. Subquery in WHERE clause:**
```sql
-- Find customers who spent more than average
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

**2. Derived table (FROM subquery):**
```sql
-- Find top performing months
SELECT 
    month,
    total_orders,
    total_revenue,
    avg_order_value,
    ROUND(100.0 * total_revenue / SUM(total_revenue) OVER (), 2) AS percent_of_total_revenue
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

**3. IN subquery:**
```sql
-- Find products ordered by premium customers
SELECT DISTINCT p.product_id, p.name
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

### Advanced CASE and Conditional Logic

**1. Segmentation logic:**
```sql
-- Segment customers by RFM (Recency, Frequency, Monetary)
SELECT 
    c.customer_id,
    c.email,
    COUNT(DISTINCT o.order_id) AS frequency,
    COALESCE(SUM(o.total_amount), 0) AS monetary,
    EXTRACT(DAY FROM CURRENT_TIMESTAMP - MAX(o.order_date))::INTEGER AS recency_days,
    CASE 
        WHEN COUNT(DISTINCT o.order_id) >= 10 AND COALESCE(SUM(o.total_amount), 0) >= 5000 
             AND EXTRACT(DAY FROM CURRENT_TIMESTAMP - MAX(o.order_date)) <= 30
        THEN 'Champions'
        WHEN COUNT(DISTINCT o.order_id) >= 5 AND COALESCE(SUM(o.total_amount), 0) >= 1000
        THEN 'Loyal Customers'
        WHEN COUNT(DISTINCT o.order_id) = 1 AND COALESCE(SUM(o.total_amount), 0) >= 500
        THEN 'High Value At Risk'
        WHEN COALESCE(SUM(o.total_amount), 0) < 100
        THEN 'Low Value'
        ELSE 'Standard'
    END AS customer_segment
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.email
ORDER BY customer_segment, monetary DESC;
```

**2. Complex business logic:**
```sql
-- Calculate order fulfillment time and SLA status
SELECT 
    o.order_id,
    o.customer_id,
    o.order_date,
    CASE 
        WHEN o.current_status = 'delivered' 
        THEN EXTRACT(DAY FROM MAX(
            CASE WHEN status->>'status' = 'delivered' 
            THEN (status->>'timestamp')::TIMESTAMP
            END
        ) - o.order_date)
        ELSE NULL
    END AS delivery_days,
    CASE 
        WHEN o.current_status = 'delivered'
             AND EXTRACT(DAY FROM MAX(
                    CASE WHEN status->>'status' = 'delivered' 
                    THEN (status->>'timestamp')::TIMESTAMP
                    END
                ) - o.order_date) <= 5
        THEN 'SLA Met'
        WHEN o.current_status = 'delivered'
        THEN 'SLA Missed'
        WHEN o.current_status IN ('pending', 'processing')
        THEN 'In Progress'
        WHEN o.current_status = 'cancelled'
        THEN 'Cancelled'
        ELSE 'Unknown'
    END AS sla_status
FROM orders o,
     jsonb_array_elements(o.status_history) AS status
GROUP BY o.order_id, o.customer_id, o.order_date, o.current_status
ORDER BY o.order_date DESC
LIMIT 10;
```

---

### UNION and Set Operations

**1. UNION (combine results, remove duplicates):**
```sql
-- Combine customers who have orders and those who don't
SELECT customer_id, email, 'Has Orders' AS customer_type
FROM customers
WHERE customer_id IN (SELECT DISTINCT customer_id FROM orders)
UNION
SELECT customer_id, email, 'No Orders' AS customer_type
FROM customers
WHERE customer_id NOT IN (SELECT DISTINCT customer_id FROM orders)
ORDER BY customer_id;
```

**2. UNION ALL (combine, keep duplicates):**
```sql
-- All price changes (increase and decrease)
SELECT product_id, name, price AS amount, 'Current Price' AS type
FROM products
UNION ALL
SELECT product_id, name, (metadata->>'previous_price')::NUMERIC, 'Previous Price'
FROM products
WHERE metadata ? 'previous_price'
ORDER BY product_id;
```

---

### HAVING Clause for Aggregates

**1. Filter aggregated results:**
```sql
-- Find products with more than 10 reviews and average rating > 4
SELECT 
    p.product_id,
    p.name,
    COUNT(r.review_id) AS review_count,
    ROUND(AVG(r.rating), 2) AS avg_rating,
    json_agg(json_build_object(
        'rating', r.rating,
        'title', r.title
    )) AS recent_reviews
FROM products p
LEFT JOIN reviews r ON p.product_id = r.product_id
GROUP BY p.product_id, p.name
HAVING COUNT(r.review_id) >= 10
   AND AVG(r.rating) > 4
ORDER BY avg_rating DESC;
```

---

## Part 5: Complex Patterns & Real-World Scenarios

### Pattern 1: Event Sourcing with JSON History

```sql
-- Track all order status changes
SELECT 
    o.order_id,
    o.customer_id,
    jsonb_array_elements(o.status_history) AS event,
    (jsonb_array_elements(o.status_history)->>'timestamp')::TIMESTAMP AS event_time,
    jsonb_array_elements(o.status_history)->>'status' AS status
FROM orders o
ORDER BY o.order_id, event_time;
```

### Pattern 2: Full-Text Search

```sql
-- Search products and reviews
SELECT 
    p.product_id,
    p.name,
    r.review_id,
    r.title,
    r.body,
    ts_rank(
        to_tsvector('english', COALESCE(p.name, '') || ' ' || COALESCE(p.description, '') || ' ' || COALESCE(r.body, '')),
        plainto_tsquery('english', 'reliable wireless')
    ) AS search_rank
FROM products p
LEFT JOIN reviews r ON p.product_id = r.product_id
WHERE to_tsvector('english', COALESCE(p.name, '') || ' ' || COALESCE(p.description, '')) 
      @@ plainto_tsquery('english', 'reliable wireless')
   OR to_tsvector('english', COALESCE(r.body, '')) 
      @@ plainto_tsquery('english', 'reliable wireless')
ORDER BY search_rank DESC
LIMIT 20;
```

### Pattern 3: Hierarchical Data (Self-referencing)

```sql
-- If you added parent_category_id to products
-- Find all parent categories and their products
WITH RECURSIVE category_path AS (
    SELECT product_id, name, ARRAY[name] AS path
    FROM products
    WHERE categories[1] IS NOT NULL
    
    UNION ALL
    
    SELECT p.product_id, cp.name, cp.path || p.name
    FROM products p
    JOIN category_path cp ON p.product_id = cp.product_id
)
SELECT * FROM category_path;
```

### Pattern 4: Batch Updates with Returning

```sql
-- Mark multiple orders as shipped and get summary
UPDATE orders
SET current_status = 'shipped',
    status_history = status_history || jsonb_build_array(
        jsonb_build_object(
            'status', 'shipped',
            'timestamp', CURRENT_TIMESTAMP
        )
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE order_id IN (SELECT order_id FROM orders WHERE current_status = 'processing' LIMIT 10)
RETURNING order_id, customer_id, total_amount, current_status;
```

### Pattern 5: Temporal Queries (Time-based Analysis)

```sql
-- Orders by hour of day
SELECT 
    EXTRACT(HOUR FROM order_date) AS hour_of_day,
    COUNT(*) AS order_count,
    ROUND(AVG(total_amount), 2) AS avg_order_amount,
    SUM(total_amount) AS total_revenue
FROM orders
WHERE CURRENT_DATE - INTERVAL '30 days' <= order_date::DATE
GROUP BY EXTRACT(HOUR FROM order_date)
ORDER BY hour_of_day;
```

### Pattern 6: Array Operations

```sql
-- Find products in multiple categories
SELECT product_id, name, categories
FROM products
WHERE categories && ARRAY['electronics', 'computing']::TEXT[]
-- && means "overlap" (have any elements in common)
ORDER BY name;

-- Check if product has specific category
SELECT product_id, name, categories
FROM products
WHERE categories @> ARRAY['premium']::TEXT[]
-- @> means "contains"
ORDER BY name;

-- Array length
SELECT product_id, name, array_length(categories, 1) AS category_count
FROM products
WHERE array_length(categories, 1) > 1
ORDER BY category_count DESC;
```

### Pattern 7: Distinct Aggregation

```sql
-- Count distinct customers per product
SELECT 
    p.product_id,
    p.name,
    COUNT(DISTINCT o.customer_id) AS unique_customers,
    COUNT(DISTINCT o.order_id) AS total_times_ordered
FROM products p
LEFT JOIN orders o ON o.items @> jsonb_build_array(
    jsonb_build_object('product_id', p.product_id)
)
GROUP BY p.product_id, p.name
ORDER BY unique_customers DESC;
```

---

## Part 6: Performance Optimization Tips

### 1. Create Appropriate Indexes

```sql
-- Single column index
CREATE INDEX idx_orders_status ON orders(current_status);

-- Composite index (for queries filtering both columns)
CREATE INDEX idx_orders_customer_status ON orders(customer_id, current_status);

-- Partial index (only index rows matching condition)
CREATE INDEX idx_active_orders ON orders(customer_id) 
WHERE current_status != 'cancelled';

-- JSONB index for JSON queries
CREATE INDEX idx_products_metadata_sku ON products USING GIN(metadata);

-- Array index
CREATE INDEX idx_customers_tags ON customers USING GIN(tags);

-- Expression index
CREATE INDEX idx_customer_email_lower ON customers(LOWER(email));
```

### 2. EXPLAIN and ANALYZE

```sql
-- See the query execution plan
EXPLAIN SELECT * FROM orders WHERE customer_id = 1 AND current_status = 'shipped';

-- Get actual execution stats
EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 1 AND current_status = 'shipped';

-- See detailed output
EXPLAIN (ANALYZE, BUFFERS, VERBOSE) SELECT * FROM orders WHERE customer_id = 1;
```

### 3. Query Optimization Techniques

```sql
-- Use LIMIT when you only need a subset
SELECT * FROM orders ORDER BY order_date DESC LIMIT 100;

-- Avoid SELECT * if you only need certain columns
SELECT order_id, customer_id, total_amount FROM orders;

-- Use EXISTS for existence checks instead of COUNT
SELECT * FROM customers c
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id);

-- Use EXCEPT/INTERSECT for set operations instead of joins
SELECT DISTINCT customer_id FROM customers
EXCEPT
SELECT DISTINCT customer_id FROM orders;
```

---

## Part 7: Common Pitfalls & Solutions

### Pitfall 1: NULL Handling

```sql
-- Wrong: comparisons with NULL always return NULL/false
SELECT * FROM orders WHERE current_status = NULL;  -- Returns nothing!

-- Right: use IS NULL
SELECT * FROM orders WHERE current_status IS NULL;

-- Avoid NULLs in aggregates
SELECT COUNT(*) FROM orders;  -- Never NULL
SELECT SUM(total_amount) FROM orders WHERE id > 1000000;  -- Could be NULL if no rows
SELECT COALESCE(SUM(total_amount), 0) FROM orders;  -- Always a number
```

### Pitfall 2: Type Casting Mistakes

```sql
-- Wrong: implicit cast might fail
SELECT * FROM products WHERE stock_quantity = '50';  -- Works but inefficient

-- Right: explicit cast
SELECT * FROM products WHERE stock_quantity = 50;
SELECT * FROM products WHERE (metadata->>'stock')::INTEGER > 100;
```

### Pitfall 3: JSON Key Existence

```sql
-- Wrong: ->> returns NULL for missing keys
SELECT metadata->>'non_existent_key' FROM products;  -- Returns NULL

-- Right: check key exists first
SELECT metadata FROM products WHERE metadata ? 'sku';

-- Or use COALESCE for defaults
SELECT COALESCE(metadata->>'warranty_months', '12')::INTEGER FROM products;
```

### Pitfall 4: Array Element Comparison

```sql
-- Wrong: comparing array to single value
SELECT * FROM customers WHERE tags = 'premium';  -- Doesn't work!

-- Right: use ANY() or @>
SELECT * FROM customers WHERE 'premium' = ANY(tags);
SELECT * FROM customers WHERE tags @> ARRAY['premium'];
```

### Pitfall 5: Undefined ORDER in Aggregates

```sql
-- Wrong: unclear which review gets returned
SELECT product_id, title FROM reviews GROUP BY product_id;

-- Right: specify which review you want
SELECT DISTINCT ON (product_id) product_id, title
FROM reviews
ORDER BY product_id, created_at DESC;

-- Or use aggregation function
SELECT product_id, MAX(title) FROM reviews GROUP BY product_id;
```

---

## Summary: SQL Query Checklist

When writing queries, verify:
- [ ] Indexes exist for WHERE and JOIN conditions
- [ ] Using IS NULL, not = NULL
- [ ] Type casting is explicit
- [ ] JSON/array operations are correct (@>, ?, ->>)
- [ ] Window functions have correct PARTITION BY and ORDER BY
- [ ] CTEs are named descriptively
- [ ] HAVING clauses work with aggregates only
- [ ] NULL values are handled (COALESCE, NULLIF, etc.)
- [ ] Query plan is efficient (use EXPLAIN ANALYZE)
- [ ] Foreign key constraints exist for data integrity

---

## Next Steps

1. Practice each pattern with your own data
2. Understand EXPLAIN ANALYZE output
3. Master indexing strategies
4. Learn about transactions and locks
5. Explore full-text search and trigram similarity
6. Study query optimization
7. Master connection pooling and tuning

Happy querying!
