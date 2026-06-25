# MongoDB vs PostgreSQL: Comprehensive Comparison & Learning Path

## Quick Comparison Matrix

| Aspect               | MongoDB                                                               | PostgreSQL                       |
| -------------------- | --------------------------------------------------------------------- | -------------------------------- |
| **Data Model**       | Document (JSON/BSON)                                                  | Relational (Tables)              |
| **Schema**           | Flexible, schemaless                                                  | Strict, enforced                 |
| **Relationships**    | Embedded or referenced                                                | Foreign keys, JOINs              |
| **Query Language**   | Aggregation pipeline, find()                                          | SQL                              |
| **ACID**             | Multi-doc (v4.0+)                                                     | Full multi-table ACID            |
| **Scaling**          | Sharding (horizontal)                                                 | Replication (vertical)           |
| **Consistency**      | Tunable; primary reads are typically strong, replicas may be eventual | Strong transactional consistency |
| **Learning Curve**   | Developer friendly                                                    | More SQL syntax                  |
| **Use Case**         | Flexible, evolving schemas                                            | Structured, stable data          |
| **Full-text Search** | Text indexes                                                          | pg_trgm, full-text               |
| **Complex Joins**    | Via aggregation                                                       | Native JOINs                     |
| **Memory Usage**     | Generally higher                                                      | More efficient                   |
| **Transactions**     | Multi-doc (v4.0+)                                                     | Multi-table ACID                 |

---

## When to Choose MongoDB

✅ **Choose MongoDB when:**

1. **Schema evolves frequently**: Social networks, content platforms
2. **Data is naturally nested**: Embedded documents reduce JOINs
3. **You need horizontal scaling**: Built-in sharding
4. **You have semi-structured data**: Flexible schema
5. **Rapid prototyping**: No schema design upfront
6. **Document storage**: Each "object" is self-contained
7. **High write throughput**: Optimized for writes
8. **Flexible field access**: Different documents can have different fields

**Real-world examples:**

- E-commerce (products with varying specs)
- Content management (articles with different metadata)
- Mobile apps (offline-first with sync)
- Real-time analytics (event logging)
- IoT platforms (sensor data with varying fields)

---

## When to Choose PostgreSQL

✅ **Choose PostgreSQL when:**

1. **Schema is stable**: Well-defined relational data
2. **Data integrity is critical**: Financial systems, healthcare
3. **Complex queries with JOINs**: Analytical queries
4. **Strong ACID guarantees**: Multi-table transactions
5. **Strict data validation**: Constraints at DB level
6. **Complex relationships**: Many-to-many, hierarchies
7. **Full-text search**: Advanced search capabilities
8. **Vertical scaling acceptable**: Single powerful server

**Real-world examples:**

- Banking systems (transactions, accounts)
- Healthcare (patient records, prescriptions)
- Enterprise software (ERP, CRM)
- Data warehousing (analytics)
- Regulatory compliance (audit trails)

---

## Migration Path: PostgreSQL → MongoDB

If you have a PostgreSQL schema and want to move to MongoDB:

### Step 1: Analyze Your Schema

**PostgreSQL** (denormalized):

```sql
-- Separate tables
CREATE TABLE customers ( ... );
CREATE TABLE orders ( ... );
CREATE TABLE order_items ( ... );
CREATE TABLE reviews ( ... );
CREATE TABLE payments ( ... );

-- Requires JOINs for related data
SELECT * FROM customers c
JOIN orders o ON c.id = o.customer_id
JOIN order_items oi ON o.id = oi.order_id;
```

**MongoDB** (embeds related data):

```javascript
// Single document includes related data
{
  _id: ObjectId("..."),
  email: "alice@example.com",
  created_at: new Date(),
  orders: [
    {
      order_id: ObjectId("..."),
      items: [
        { product_id: "...", quantity: 1 },
        { product_id: "...", quantity: 2 }
      ],
      total: 100
    }
  ],
  reviews: [
    { product_id: "...", rating: 5 }
  ]
}
```

### Step 2: Denormalization Strategy

**Embed if:**

- Data is accessed together
- Embedded data grows slowly (< 16MB doc limit)
- One-to-few relationships

**Reference if:**

- Data accessed separately
- Embedded data could grow unbounded
- One-to-many relationships
- Data is shared across documents

### Step 3: Handle Relationships

**PostgreSQL foreign keys** become MongoDB references:

```javascript
// Option 1: Embed (simple)
{
  customer_id: 1,
  name: "Alice",
  shipping_address: {
    street: "123 Main",
    city: "NYC"
  }
}

// Option 2: Reference (complex)
{
  customer_id: 1,
  name: "Alice",
  address_id: ObjectId("...")
}
```

### Step 4: Handle JOINs

```javascript
// PostgreSQL (SQL JOIN)
SELECT o.*, c.name, p.name
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN products p ON o.product_id = p.id;

// MongoDB (aggregation $lookup)
db.orders.aggregate([
  {
    $lookup: {
      from: "customers",
      localField: "customer_id",
      foreignField: "_id",
      as: "customer"
    }
  },
  {
    $lookup: {
      from: "products",
      localField: "product_id",
      foreignField: "_id",
      as: "product"
    }
  }
]);
```

---

## Migration Path: MongoDB → PostgreSQL

If you have MongoDB data and want structured SQL:

### Step 1: Flatten Embedded Documents

```javascript
// MongoDB nested
{
  customer_id: 1,
  name: "Alice",
  orders: [
    {
      order_id: 100,
      items: [
        { product_id: 1, qty: 1 }
      ]
    }
  ]
}

// PostgreSQL normalized
CREATE TABLE customers (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100)
);

CREATE TABLE orders (
  id SERIAL PRIMARY KEY,
  customer_id INT REFERENCES customers(id),
  order_date TIMESTAMP
);

CREATE TABLE order_items (
  id SERIAL PRIMARY KEY,
  order_id INT REFERENCES orders(id),
  product_id INT REFERENCES products(id),
  quantity INT
);
```

### Step 2: Design Proper Schema

```sql
-- Identify entities and relationships
-- Create normalized schema
-- Define constraints (NOT NULL, UNIQUE, FOREIGN KEY)
-- Create indexes for query performance
```

### Step 3: Handle Array Fields

```javascript
// MongoDB array
{ tags: ["premium", "vip", "loyal"] }

// PostgreSQL: Option 1 (array type)
{ tags: TEXT[] ARRAY['premium', 'vip', 'loyal'] }

// PostgreSQL: Option 2 (separate table)
CREATE TABLE customer_tags (
  customer_id INT REFERENCES customers(id),
  tag VARCHAR(50),
  PRIMARY KEY (customer_id, tag)
);
```

---

## Detailed Feature Comparison

### 1. Query Performance

**Simple lookups:**

```javascript
// MongoDB: O(1) with index
db.customers.findOne({ email: "alice@example.com" })

// PostgreSQL: O(log n) with index
SELECT * FROM customers WHERE email = 'alice@example.com';
```

**Winner: Tie** (both O(log n) with proper indexes)

**Complex aggregation:**

```javascript
// MongoDB: Single aggregation pipeline
db.orders.aggregate([...])

// PostgreSQL: Multiple JOINs + GROUP BY
SELECT c.id, SUM(o.total)
FROM customers c
JOIN orders o ON c.id = o.customer_id
GROUP BY c.id;
```

**Winner: Depends on data structure** (MongoDB faster for embedded, PostgreSQL for normalized)

**Full-text search:**

```javascript
// MongoDB: Text index
db.products.find({ $text: { $search: "laptop" } })

// PostgreSQL: Better tokenization
SELECT * FROM products
WHERE to_tsvector('english', name || ' ' || description)
      @@ plainto_tsquery('english', 'laptop');
```

**Winner: PostgreSQL** (more sophisticated)

### 2. Data Integrity

**MongoDB:**

```javascript
// Optional validation
db.createCollection("orders", {
  validator: {
    $jsonSchema: {
      required: ["customer_id", "items"],
      properties: {
        items: { minItems: 1 },
      },
    },
  },
});

// But app must enforce
if (order.items.length === 0) throw error;
```

**PostgreSQL:**

```sql
-- Constraints enforced at DB level
ALTER TABLE orders ADD CONSTRAINT check_items_count
CHECK (array_length(items, 1) > 0);

-- Foreign keys enforced
ALTER TABLE orders
ADD CONSTRAINT fk_customer
FOREIGN KEY (customer_id) REFERENCES customers(id);
```

**Winner: PostgreSQL** (enforces integrity)

### 3. Scaling

**MongoDB:**

```javascript
// Sharding: automatic horizontal scaling
// Configure shard key
sh.shardCollection("ecommerce.orders", { customer_id: 1 });
// Data automatically distributed across servers
```

**PostgreSQL:**

```sql
-- Manual sharding (application level)
-- Or use replication for read scaling
-- Write scaling requires application-level partitioning
```

**Winner: MongoDB** (simpler scaling)

### 4. Transactions

**MongoDB (multi-document):**

```javascript
session.startTransaction();
db.orders.insertOne({ ... }, { session });
db.products.updateMany({ ... }, { ... }, { session });
session.commitTransaction();
// Automatic rollback on error
```

**PostgreSQL (full ACID):**

```sql
BEGIN;
INSERT INTO orders ...;
UPDATE products SET stock = stock - 1 WHERE ...;
COMMIT;
-- Automatic rollback on error
```

**Winner: PostgreSQL** (stricter guarantees)

---

## Schema Design Patterns

### Pattern 1: One-to-Many (Orders → Items)

**MongoDB (Embed):**

```javascript
{
  _id: ObjectId("..."),
  customer_id: ObjectId("..."),
  items: [
    { product_id: ObjectId("..."), qty: 2 },
    { product_id: ObjectId("..."), qty: 1 }
  ]
}
```

**PostgreSQL (Reference):**

```sql
CREATE TABLE orders (id, customer_id, ...);
CREATE TABLE order_items (id, order_id, product_id, quantity);
```

### Pattern 2: Many-to-Many (Customers → Tags)

**MongoDB (Array):**

```javascript
{
  _id: ObjectId("..."),
  name: "Alice",
  tags: ["premium", "vip", "loyal"]
}
```

**PostgreSQL (Junction Table):**

```sql
CREATE TABLE customer_tags (
  customer_id INT,
  tag VARCHAR(50),
  PRIMARY KEY (customer_id, tag)
);
```

### Pattern 3: Versioning/History

**MongoDB (Array of documents):**

```javascript
{
  _id: ObjectId("..."),
  name: "Alice",
  status_history: [
    { status: "pending", timestamp: new Date(), notes: "..." },
    { status: "processing", timestamp: new Date(), notes: "..." },
    { status: "completed", timestamp: new Date(), notes: "..." }
  ]
}
```

**PostgreSQL (Separate table + trigger):**

```sql
CREATE TABLE order_history (
  id SERIAL PRIMARY KEY,
  order_id INT REFERENCES orders(id),
  status VARCHAR(50),
  timestamp TIMESTAMP,
  notes TEXT
);

CREATE TRIGGER order_status_history
AFTER UPDATE ON orders
FOR EACH ROW
INSERT INTO order_history (order_id, status, timestamp)
VALUES (NEW.id, NEW.status, NOW());
```

---

## Real-World Scenario: E-Commerce Platform

### MongoDB Approach

**Advantages:**

- Products with varying attributes (specs differ per product type)
- Order details denormalized for fast checkout page
- Customer preferences stored flexibly
- Scalable to millions of customers

**Challenges:**

- Need to denormalize product info in orders (must update on price changes)
- Text search requires index management
- Transactions across collections more complex

**Schema:**

```javascript
db.customers.insertOne({
  email: "alice@example.com",
  name: "Alice",
  preferences: { theme: "dark", currency: "USD" },
  tags: ["premium"],
});

db.products.insertOne({
  name: "Laptop",
  price: 999,
  specs: { ram_gb: 16, storage_gb: 512 },
});

db.orders.insertOne({
  customer_id: ObjectId("..."),
  items: [
    {
      product_id: ObjectId("..."),
      product_name: "Laptop",
      unit_price: 999,
      quantity: 1,
    },
  ],
  total: 999,
  status: "pending",
});
```

### PostgreSQL Approach

**Advantages:**

- Normalized schema prevents data duplication
- Price changes automatically reflected in reports
- Strong consistency guarantees
- Complex queries (e.g., customers who bought product X also bought Y)

**Challenges:**

- JOINs required for every complex query
- Schema changes require migrations
- Less flexible for varying product attributes

**Schema:**

```sql
CREATE TABLE customers (
  id SERIAL PRIMARY KEY,
  email VARCHAR UNIQUE,
  name VARCHAR,
  preferences JSONB,
  tags TEXT[]
);

CREATE TABLE products (
  id SERIAL PRIMARY KEY,
  name VARCHAR,
  price DECIMAL,
  specs JSONB
);

CREATE TABLE orders (
  id SERIAL PRIMARY KEY,
  customer_id INT REFERENCES customers(id),
  total DECIMAL,
  status VARCHAR
);

CREATE TABLE order_items (
  id SERIAL PRIMARY KEY,
  order_id INT REFERENCES orders(id),
  product_id INT REFERENCES products(id),
  quantity INT,
  unit_price DECIMAL
);
```

---

## Learning Path: MongoDB

### Week 1: Fundamentals

- [ ] Understand JSON/BSON format
- [ ] Learn document structure vs relational
- [ ] Practice basic CRUD operations
- [ ] Create indexes
- [ ] Use find() with various queries

**Time:** 2-3 hours/day

### Week 2: Aggregation Pipeline

- [ ] Master $match, $project, $group
- [ ] Practice $lookup for joining collections
- [ ] Learn $unwind for array expansion
- [ ] Study $facet for multiple analyses
- [ ] Build complex aggregations

**Time:** 3-4 hours/day

### Week 3: Advanced Patterns

- [ ] Transactions and consistency
- [ ] Schema design (embed vs reference)
- [ ] Text search and full-text indexing
- [ ] Performance optimization
- [ ] Connection pooling

**Time:** 3-4 hours/day

### Week 4: Project

- [ ] Build mini e-commerce project
- [ ] Implement search functionality
- [ ] Create analytics dashboard
- [ ] Optimize queries with indexes
- [ ] Handle real-world scenarios

**Time:** 5-6 hours/day

---

## Learning Path: PostgreSQL

### Week 1: SQL Fundamentals

- [ ] SELECT, WHERE, ORDER BY, LIMIT
- [ ] JOIN operations (INNER, LEFT, RIGHT)
- [ ] GROUP BY and HAVING
- [ ] Aggregation functions (SUM, AVG, COUNT)
- [ ] WHERE clause operators

**Time:** 2-3 hours/day

### Week 2: Advanced Queries

- [ ] Subqueries and derived tables
- [ ] Window functions (RANK, ROW_NUMBER, SUM OVER)
- [ ] CTEs (WITH clause)
- [ ] UNION and set operations
- [ ] Complex JOINs

**Time:** 3-4 hours/day

### Week 3: Schema Design & Optimization

- [ ] Normalization (1NF, 2NF, 3NF)
- [ ] Index strategies
- [ ] Query optimization with EXPLAIN
- [ ] Constraints and data integrity
- [ ] Views and materialized views

**Time:** 3-4 hours/day

### Week 4: Project

- [ ] Design normalized schema
- [ ] Build complex queries
- [ ] Optimize with indexes
- [ ] Create reporting queries
- [ ] Handle edge cases

**Time:** 5-6 hours/day

---

## Quick Reference: Syntax Translation

| Task      | MongoDB                            | PostgreSQL                              |
| --------- | ---------------------------------- | --------------------------------------- |
| Find one  | `db.col.findOne({...})`            | `SELECT * FROM table WHERE ... LIMIT 1` |
| Find many | `db.col.find({...})`               | `SELECT * FROM table WHERE ...`         |
| Count     | `db.col.countDocuments({...})`     | `SELECT COUNT(*) FROM table WHERE ...`  |
| Insert    | `db.col.insertOne({...})`          | `INSERT INTO table VALUES (...)`        |
| Update    | `db.col.updateOne({}, {$set: {}})` | `UPDATE table SET ... WHERE ...`        |
| Delete    | `db.col.deleteOne({...})`          | `DELETE FROM table WHERE ...`           |
| Group     | `$group: { _id: "$field" }`        | `GROUP BY field`                        |
| Sort      | `sort({ field: 1 })`               | `ORDER BY field ASC`                    |
| Join      | `$lookup`                          | `JOIN ... ON ...`                       |
| Filter    | `$match`                           | `WHERE`                                 |

---

## Common Mistakes to Avoid

### MongoDB Mistakes

❌ **Forgetting indexes on frequently queried fields**

```javascript
// Bad: Query will scan all documents
db.orders.find({ customer_id: 123 });

// Good: Create index first
db.orders.createIndex({ customer_id: 1 });
db.orders.find({ customer_id: 123 }); // Now fast
```

❌ **Embedding unbounded arrays**

```javascript
// Bad: Array grows without limit (16MB doc limit)
{
  customer_id: 1,
  reviews: [ { ... }, { ... }, ... ] // could be millions
}

// Good: Reference instead
db.reviews.find({ customer_id: 1 })
```

❌ **Denormalizing without update strategy**

```javascript
// Bad: Customer name in orders, but updates in customers don't propagate
{ order_id: 1, customer_name: "Alice" }  // Stale after name change!

// Good: Store only what you need, use $lookup for current data
```

### PostgreSQL Mistakes

❌ **Insufficient normalization**

```sql
-- Bad: Customer name duplicated in every order
CREATE TABLE orders (
  id INT,
  customer_id INT,
  customer_name VARCHAR  -- WRONG! Should only store ID
);

-- Good: Reference the customer
CREATE TABLE orders (
  id INT,
  customer_id INT REFERENCES customers(id)
);
```

❌ **Missing indexes**

```sql
-- Bad: Frequent WHERE on unindexed column
SELECT * FROM orders WHERE customer_id = 123;  -- Table scan!

-- Good: Create index
CREATE INDEX idx_orders_customer ON orders(customer_id);
```

❌ **SELECT \* in production**

```sql
-- Bad: Fetches all columns
SELECT * FROM orders;

-- Good: Only needed columns
SELECT order_id, customer_id, total FROM orders;
```

---

## Conclusion

**Choose MongoDB if:**

- You value developer velocity and flexibility
- Your data model evolves frequently
- You need horizontal scaling out-of-the-box
- You have semi-structured or nested data

**Choose PostgreSQL if:**

- You need strict data integrity
- Your schema is stable and well-defined
- You have complex relational queries
- You need powerful analytical capabilities

**Best practice:** Use both!

- MongoDB for flexible, rapidly-evolving collections
- PostgreSQL for structured, relational data

Many successful companies use both databases for different purposes. The important thing is to understand the trade-offs and choose the right tool for each job.

Happy database engineering!
