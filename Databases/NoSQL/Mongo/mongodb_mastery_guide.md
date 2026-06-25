# MongoDB Mastery: From Fundamentals to Advanced Patterns

## Part 1: MongoDB Philosophy & Architecture

### Why MongoDB Stands Out

MongoDB is a document database designed for flexibility and developer productivity. Unlike PostgreSQL's structured tables, MongoDB stores data as flexible documents in JSON-like format (BSON).

**Key Differentiators:**

1. **Schema Flexibility**: Add new fields to documents without migrating the entire collection
2. **Nested Documents**: Store related data together (no need to JOIN)
3. **Horizontal Scalability**: Built-in sharding to spread data across multiple servers
4. **Developer-Friendly**: Documents map directly to objects in code (no O/R impedance mismatch)
5. **Rich Querying**: Powerful aggregation pipeline for complex analytics
6. **Automatic Indexing**: Flexible index strategies for different query patterns
7. **Change Streams**: Real-time subscriptions to data changes

### When to Use MongoDB vs PostgreSQL

**Use MongoDB when:**

- Schema changes frequently (social networks, content management)
- You have nested/hierarchical data that would require JOINs in SQL
- You need horizontal scaling across multiple servers
- Your data is semi-structured or varies widely
- You want rapid prototyping without schema design upfront

**Use PostgreSQL when:**

- Your schema is stable and well-defined
- You need ACID guarantees across multiple tables
- You have complex queries with many JOINs
- You need powerful full-text search
- You're storing structured, relational data

### MongoDB Terminology

| MongoDB              | PostgreSQL     | Purpose                     |
| -------------------- | -------------- | --------------------------- |
| Database             | Database       | Container for collections   |
| Collection           | Table          | Group of documents          |
| Document             | Row            | Single record (JSON object) |
| Field                | Column         | Property within a document  |
| Index                | Index          | Speed up queries            |
| Aggregation Pipeline | Complex SELECT | Transform and analyze data  |
| Replica Set          | Replication    | High availability           |
| Shard                | Partition      | Horizontal scaling          |

---

## Part 2: MongoDB Data Modeling Philosophy

### Document-Oriented Design

Unlike SQL's normalized tables, MongoDB embraces **denormalization**. You can embed related data within documents.

**Embedding vs Referencing:**

**Embedding** (good for one-to-few, tightly coupled):

```json
{
  "_id": 1,
  "name": "Alice Johnson",
  "email": "alice@example.com",
  "addresses": [
    {
      "type": "billing",
      "street": "123 Main St",
      "city": "New York"
    },
    {
      "type": "shipping",
      "street": "456 Oak Ave",
      "city": "Los Angeles"
    }
  ]
}
```

**Referencing** (good for one-to-many, when data is large or shared):

```json
{
  "_id": 1,
  "name": "Alice Johnson",
  "email": "alice@example.com",
  "address_ids": [ObjectId("..."), ObjectId("...")]
}

// Separate collection
{
  "_id": ObjectId("..."),
  "customer_id": 1,
  "type": "billing",
  "street": "123 Main St",
  "city": "New York"
}
```

**Rule of thumb:**

- Embed data if it's accessed together and grows slowly
- Reference data if it's accessed separately or grows unbounded

---

## Part 3: E-Commerce Schema Design for MongoDB

MongoDB uses **collections** instead of tables. Here's our e-commerce schema:

### Collections Overview

```javascript
// customers collection
db.createCollection("customers", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["email", "first_name", "last_name"],
      properties: {
        _id: { bsonType: "objectId" },
        email: { bsonType: "string" },
        first_name: { bsonType: "string" },
        last_name: { bsonType: "string" },
        phone: { bsonType: "string" },
        preferences: { bsonType: "object" },
        tags: { bsonType: "array", items: { bsonType: "string" } },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" },
        is_active: { bsonType: "bool" },
      },
    },
  },
});

// products collection
db.createCollection("products", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["name", "price"],
      properties: {
        _id: { bsonType: "objectId" },
        name: { bsonType: "string" },
        description: { bsonType: "string" },
        price: { bsonType: "decimal" },
        stock_quantity: { bsonType: "int" },
        metadata: { bsonType: "object" },
        categories: { bsonType: "array", items: { bsonType: "string" } },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" },
      },
    },
  },
});

// orders collection - DENORMALIZED (includes customer and product data)
db.createCollection("orders", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["customer_id", "items", "total_amount"],
      properties: {
        _id: { bsonType: "objectId" },
        customer_id: { bsonType: "objectId" },
        customer_email: { bsonType: "string" },
        customer_name: { bsonType: "string" },
        items: {
          bsonType: "array",
          items: {
            bsonType: "object",
            properties: {
              product_id: { bsonType: "objectId" },
              product_name: { bsonType: "string" },
              quantity: { bsonType: "int" },
              unit_price: { bsonType: "decimal" },
              total: { bsonType: "decimal" },
            },
          },
        },
        total_amount: { bsonType: "decimal" },
        current_status: { bsonType: "string" },
        status_history: { bsonType: "array" },
        shipping_address: { bsonType: "object" },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" },
      },
    },
  },
});

// reviews collection
db.createCollection("reviews");

// payments collection
db.createCollection("payments");

// inventory_logs collection
db.createCollection("inventory_logs");

// Create indexes for performance
db.customers.createIndex({ email: 1 }, { unique: true });
db.customers.createIndex({ tags: 1 });
db.customers.createIndex({ created_at: -1 });

db.products.createIndex({ name: "text", description: "text" });
db.products.createIndex({ categories: 1 });
db.products.createIndex({ price: 1 });

db.orders.createIndex({ customer_id: 1 });
db.orders.createIndex({ created_at: -1 });
db.orders.createIndex({ current_status: 1 });

db.reviews.createIndex({ product_id: 1 });
db.reviews.createIndex({ customer_id: 1 });
db.reviews.createIndex({ rating: 1 });

db.payments.createIndex({ order_id: 1 });
db.payments.createIndex({ created_at: -1 });
```

### Key Differences from PostgreSQL Schema

1. **No Foreign Keys**: MongoDB doesn't enforce referential integrity. You manage relationships in your code.
2. **Embedded Arrays**: Items in orders are embedded as an array, not stored separately.
3. **Denormalization**: Customer name stored with order (reduces lookups).
4. **ObjectId**: MongoDB's unique identifier (not auto-increment).
5. **Flexible Schema**: You can add fields anytime without migration.

---

## Part 4: Basic CRUD Operations

### INSERT Operations

#### 1. Insert a single document

```javascript
db.customers.insertOne({
  email: "alice@example.com",
  first_name: "Alice",
  last_name: "Johnson",
  phone: "555-1001",
  preferences: {
    newsletter: true,
    theme: "dark",
    currency: "USD",
  },
  tags: ["premium", "vip"],
  created_at: new Date(),
  updated_at: new Date(),
  is_active: true,
});

// Returns:
// {
//   "acknowledged": true,
//   "insertedId": ObjectId("...")
// }
```

#### 2. Insert multiple documents

```javascript
db.customers.insertMany([
  {
    email: "bob@example.com",
    first_name: "Bob",
    last_name: "Smith",
    tags: ["standard"],
    created_at: new Date(),
    updated_at: new Date(),
  },
  {
    email: "carol@example.com",
    first_name: "Carol",
    last_name: "Davis",
    tags: ["premium"],
    created_at: new Date(),
    updated_at: new Date(),
  },
  {
    email: "david@example.com",
    first_name: "David",
    last_name: "Wilson",
    tags: ["standard", "new"],
    created_at: new Date(),
    updated_at: new Date(),
  },
]);

// Returns:
// {
//   "acknowledged": true,
//   "insertedIds": [ObjectId(...), ObjectId(...), ObjectId(...)]
// }
```

#### 3. Insert with default values

```javascript
db.products.insertOne({
  name: 'MacBook Pro 16"',
  description: "High-performance laptop",
  price: 2499.99,
  stock_quantity: 50,
  metadata: {
    sku: "APPLE-MBP-16",
    colors: ["Space Gray", "Silver"],
    specs: {
      ram_gb: 16,
      storage_gb: 512,
      processor: "M3 Max",
    },
    warranty_months: 12,
  },
  categories: ["electronics", "computers", "laptops"],
  created_at: new Date(),
  updated_at: new Date(),
});
```

#### 4. Insert order with nested items

```javascript
db.orders.insertOne({
  customer_id: ObjectId("..."), // from customers collection
  customer_email: "alice@example.com",
  customer_name: "Alice Johnson",
  items: [
    {
      product_id: ObjectId("..."),
      product_name: 'MacBook Pro 16"',
      quantity: 1,
      unit_price: 2499.99,
      total: 2499.99,
    },
    {
      product_id: ObjectId("..."),
      product_name: "USB-C Cable",
      quantity: 2,
      unit_price: 19.99,
      total: 39.98,
    },
  ],
  total_amount: 2539.97,
  current_status: "pending",
  status_history: [
    {
      status: "pending",
      timestamp: new Date(),
      notes: "Order received",
    },
  ],
  shipping_address: {
    street: "123 Main St",
    city: "New York",
    state: "NY",
    zip: "10001",
    country: "USA",
  },
  created_at: new Date(),
  updated_at: new Date(),
});
```

#### 5. Bulk insert with ordered/unordered

```javascript
// Ordered: stops on first error
db.customers.insertMany(documents, { ordered: true });

// Unordered: continues even if some fail
db.customers.insertMany(documents, { ordered: false });
```

---

### READ Operations (FIND)

#### 1. Find all documents

```javascript
db.customers.find();
// Returns all customer documents
```

#### 2. Find with condition (WHERE clause)

```javascript
// Find active customers
db.customers.find({ is_active: true });

// Find by email
db.customers.find({ email: "alice@example.com" });

// Find multiple conditions (AND)
db.customers.find({
  is_active: true,
  created_at: { $gte: new Date("2024-01-01") },
});
```

#### 3. Query operators

```javascript
// Comparison operators
db.products.find({ price: { $gt: 1000 } }); // greater than
db.products.find({ price: { $gte: 1000 } }); // greater or equal
db.products.find({ price: { $lt: 100 } }); // less than
db.products.find({ price: { $lte: 100 } }); // less or equal
db.products.find({ price: { $eq: 99.99 } }); // equals
db.products.find({ price: { $ne: 99.99 } }); // not equals
db.products.find({ price: { $in: [99.99, 199.99, 299.99] } }); // in array
db.products.find({ price: { $nin: [99.99, 199.99] } }); // not in array
```

#### 4. Logical operators

```javascript
// OR operator
db.customers.find({
  $or: [{ tags: "premium" }, { total_spent: { $gt: 5000 } }],
});

// AND operator (explicit, not implicit)
db.customers.find({
  $and: [{ is_active: true }, { created_at: { $gte: new Date("2024-01-01") } }],
});

// NOT operator
db.orders.find({
  current_status: { $not: { $eq: "cancelled" } },
});

// NOR operator
db.customers.find({
  $nor: [{ tags: "spammer" }, { is_active: false }],
});
```

#### 5. Array queries

```javascript
// Find customers with specific tag
db.customers.find({ tags: "premium" });

// Find customers with ALL these tags
db.customers.find({ tags: { $all: ["premium", "vip"] } });

// Find customers where array size > 1
db.customers.find({ tags: { $size: 2 } });

// Find documents where array contains at least one element matching condition
db.orders.find({
  items: {
    $elemMatch: {
      product_name: "USB-C Cable",
      quantity: { $gt: 1 },
    },
  },
});
```

#### 6. Query nested objects

```javascript
// Access nested fields with dot notation
db.products.find({ "metadata.sku": "APPLE-MBP-16" });

db.products.find({ "metadata.specs.ram_gb": { $gte: 16 } });

// Query entire object
db.orders.find({
  shipping_address: {
    city: "New York",
    state: "NY",
  },
});
```

#### 7. Projection (select specific fields)

```javascript
// Get only name and price
db.products.find(
  {},
  { name: 1, price: 1, _id: 0 }, // 1 = include, 0 = exclude
);

// Exclude a field
db.customers.find(
  {},
  { preferences: 0 }, // Don't return preferences
);

// Nested projection
db.products.find({}, { name: 1, "metadata.sku": 1 });
```

#### 8. Sorting and limiting

```javascript
// Sort by creation date (descending)
db.orders.find().sort({ created_at: -1 });

// Sort by multiple fields
db.orders.find().sort({ current_status: 1, created_at: -1 });

// Limit results
db.products.find().limit(10);

// Skip and limit (pagination)
db.products.find().skip(20).limit(10);

// Get first document
db.customers.findOne({ email: "alice@example.com" });
```

#### 9. Count documents

```javascript
// Count all
db.customers.countDocuments();

// Count with filter
db.customers.countDocuments({ is_active: true });

// Estimate count (faster, uses metadata)
db.customers.estimatedDocumentCount();
```

#### 10. Complex queries

```javascript
// Find orders with total > 1000, sort by date, get top 5
db.orders
  .find({ total_amount: { $gt: 1000 } })
  .sort({ created_at: -1 })
  .limit(5);

// Find products in specific categories
db.products.find({
  categories: { $in: ["electronics", "computers"] },
});

// Find products with price between 100 and 1000
db.products.find({
  price: { $gte: 100, $lte: 1000 },
});

// Text search
db.products.find({ $text: { $search: "laptop" } });
```

---

### UPDATE Operations

#### 1. Update a single document

```javascript
db.customers.updateOne(
  { _id: ObjectId("...") },
  {
    $set: {
      first_name: "Alexandra",
      updated_at: new Date(),
    },
  },
);

// Returns:
// {
//   "acknowledged": true,
//   "modifiedCount": 1,
//   "upsertedId": null
// }
```

#### 2. Update multiple documents

```javascript
db.customers.updateMany(
  { tags: "new" },
  {
    $set: {
      tags: ["standard"],
      updated_at: new Date(),
    },
  },
);
```

#### 3. Update operators

```javascript
// $set: set field value
db.customers.updateOne(
  { _id: ObjectId("...") },
  { $set: { phone: "555-2000" } },
);

// $unset: remove field
db.customers.updateOne(
  { _id: ObjectId("...") },
  { $unset: { legacy_field: "" } },
);

// $inc: increment numeric value
db.products.updateOne(
  { _id: ObjectId("...") },
  { $inc: { stock_quantity: -5 } }, // decrease stock by 5
);

// $mul: multiply value
db.products.updateOne(
  { _id: ObjectId("...") },
  { $mul: { price: 1.1 } }, // increase price by 10%
);

// $push: add element to array
db.customers.updateOne({ _id: ObjectId("...") }, { $push: { tags: "vip" } });

// $push with multiple
db.customers.updateOne(
  { _id: ObjectId("...") },
  { $push: { tags: { $each: ["loyalty", "referrer"] } } },
);

// $pull: remove element from array
db.customers.updateOne({ _id: ObjectId("...") }, { $pull: { tags: "new" } });

// $pop: remove first/last element
db.customers.updateOne(
  { _id: ObjectId("...") },
  { $pop: { tags: 1 } }, // remove last element (or -1 for first)
);
```

#### 4. Update nested objects

```javascript
// Update nested field
db.customers.updateOne(
  { _id: ObjectId("...") },
  { $set: { "preferences.theme": "light" } },
);

// Update multiple nested fields
db.products.updateOne(
  { _id: ObjectId("...") },
  {
    $set: {
      "metadata.sku": "NEW-SKU",
      "metadata.specs.ram_gb": 32,
    },
  },
);
```

#### 5. Replace entire document

```javascript
db.customers.replaceOne(
  { _id: ObjectId("...") },
  {
    email: "newemail@example.com",
    first_name: "New",
    last_name: "Person",
    // Must provide all required fields
    created_at: new Date(),
    updated_at: new Date(),
  },
);
```

#### 6. Upsert (update or insert)

```javascript
// If document exists, update. Otherwise, insert.
db.customers.updateOne(
  { email: "frank@example.com" },
  {
    $set: {
      first_name: "Frank",
      last_name: "Green",
      created_at: new Date(),
      updated_at: new Date(),
    },
  },
  { upsert: true }, // upsert flag
);
```

#### 7. Update with conditions (CASE logic)

```javascript
// Use aggregation pipeline in updates (MongoDB 4.2+)
db.orders.updateMany({ current_status: "pending" }, [
  {
    $set: {
      current_status: {
        $cond: [
          { $gt: ["$total_amount", 5000] },
          "vip_priority",
          { $cond: [{ $gt: ["$total_amount", 1000] }, "priority", "standard"] },
        ],
      },
      updated_at: new Date(),
    },
  },
]);
```

#### 8. Update with array modification

```javascript
// Add to order status history
db.orders.updateOne(
  { _id: ObjectId("...") },
  {
    $push: {
      status_history: {
        status: "shipped",
        timestamp: new Date(),
        carrier: "FedEx",
      },
    },
    $set: {
      current_status: "shipped",
      updated_at: new Date(),
    },
  },
);
```

---

### DELETE Operations

#### 1. Delete a single document

```javascript
db.customers.deleteOne({ _id: ObjectId("...") });

// Returns:
// {
//   "acknowledged": true,
//   "deletedCount": 1
// }
```

#### 2. Delete multiple documents

```javascript
db.orders.deleteMany({
  current_status: "cancelled",
  created_at: { $lt: new Date("2023-01-01") },
});
```

#### 3. Delete with condition

```javascript
// Delete all inactive customers
db.customers.deleteMany({ is_active: false });

// Delete one from query result
db.customers.deleteOne({ email: "spammer@example.com" });
```

#### 4. Soft delete (preferred)

```javascript
// Mark as deleted instead of removing
db.customers.updateOne(
  { _id: ObjectId("...") },
  { $set: { deleted_at: new Date() } },
);

// Now always filter deleted records
db.customers.find({ deleted_at: { $exists: false } });
```

#### 5. Delete all (dangerous!)

```javascript
db.customers.deleteMany({}); // Delete everything!

// Use with caution or better yet, don't use at all
```

---

## Part 5: Aggregation Pipeline (Advanced Queries)

The aggregation pipeline is MongoDB's powerful query language. It transforms documents through stages.

### Basic Aggregation Stages

#### 1. $match - Filter documents (like WHERE)

```javascript
// Find active customers created in 2024
db.customers.aggregate([
  {
    $match: {
      is_active: true,
      created_at: { $gte: new Date("2024-01-01") },
    },
  },
]);
```

#### 2. $project - Select/transform fields (like SELECT)

```javascript
// Get only name and email, add full_name
db.customers.aggregate([
  {
    $project: {
      _id: 1,
      email: 1,
      full_name: { $concat: ["$first_name", " ", "$last_name"] },
      email_domain: { $arrayElemAt: [{ $split: ["$email", "@"] }, 1] },
    },
  },
]);

// Output:
// {
//   "_id": ObjectId("..."),
//   "email": "alice@example.com",
//   "full_name": "Alice Johnson",
//   "email_domain": "example.com"
// }
```

#### 3. $group - Group by field and aggregate

```javascript
// Count customers by tag
db.customers.aggregate([
  {
    $unwind: "$tags", // Expand array to multiple documents
  },
  {
    $group: {
      _id: "$tags", // Group by tag
      count: { $sum: 1 }, // Count documents
      emails: { $push: "$email" }, // Collect emails
    },
  },
  {
    $sort: { count: -1 },
  },
]);

// Output:
// {
//   "_id": "premium",
//   "count": 2,
//   "emails": ["alice@example.com", "carol@example.com"]
// }
// {
//   "_id": "standard",
//   "count": 2,
//   "emails": ["bob@example.com", "david@example.com"]
// }
```

#### 4. $sort - Sort documents

```javascript
db.orders.aggregate([
  {
    $match: { current_status: "completed" },
  },
  {
    $sort: { created_at: -1 }, // -1 = descending, 1 = ascending
  },
]);
```

#### 5. $limit and $skip - Pagination

```javascript
db.products.aggregate([{ $skip: 20 }, { $limit: 10 }]);
```

#### 6. $lookup - Join with another collection

```javascript
// Get customer with their orders
db.customers.aggregate([
  {
    $match: { _id: ObjectId("...") },
  },
  {
    $lookup: {
      from: "orders", // Collection to join
      localField: "_id", // Field in customers
      foreignField: "customer_id", // Field in orders
      as: "orders", // Output array name
    },
  },
]);

// Output:
// {
//   "_id": ObjectId("..."),
//   "email": "alice@example.com",
//   "orders": [
//     { _id: ..., customer_id: ..., total_amount: 2539.97, ... },
//     { _id: ..., customer_id: ..., total_amount: 39.98, ... }
//   ]
// }
```

#### 7. $unwind - Expand arrays

```javascript
// Expand order items into separate documents
db.orders.aggregate([
  {
    $unwind: "$items",
  },
  {
    $project: {
      customer_id: 1,
      product_name: "$items.product_name",
      quantity: "$items.quantity",
      unit_price: "$items.unit_price",
    },
  },
]);

// Output: One document per item
// {
//   "customer_id": ObjectId("..."),
//   "product_name": "MacBook Pro 16\"",
//   "quantity": 1,
//   "unit_price": 2499.99
// }
```

#### 8. $group with multiple statistics

```javascript
// Customer lifetime value calculation
db.orders.aggregate([
  {
    $match: { current_status: { $ne: "cancelled" } },
  },
  {
    $group: {
      _id: "$customer_id",
      total_orders: { $sum: 1 },
      total_spent: { $sum: "$total_amount" },
      avg_order: { $avg: "$total_amount" },
      max_order: { $max: "$total_amount" },
      min_order: { $min: "$total_amount" },
      first_order: { $min: "$created_at" },
      last_order: { $max: "$created_at" },
    },
  },
  {
    $sort: { total_spent: -1 },
  },
]);

// Output:
// {
//   "_id": ObjectId("..."),
//   "total_orders": 2,
//   "total_spent": 2539.97,
//   "avg_order": 1269.985,
//   "max_order": 2499.99,
//   "min_order": 39.98,
//   "first_order": ISODate("2024-01-15T00:00:00Z"),
//   "last_order": ISODate("2024-01-20T00:00:00Z")
// }
```

#### 9. $facet - Multiple aggregations in one pass

```javascript
// Get multiple insights in one query
db.orders.aggregate([
  {
    $facet: {
      by_status: [{ $group: { _id: "$current_status", count: { $sum: 1 } } }],
      by_customer: [
        { $group: { _id: "$customer_id", total: { $sum: "$total_amount" } } },
        { $sort: { total: -1 } },
        { $limit: 5 },
      ],
      summary: [
        {
          $group: {
            _id: null,
            total_revenue: { $sum: "$total_amount" },
            avg_order: { $avg: "$total_amount" },
            count: { $sum: 1 },
          },
        },
      ],
    },
  },
]);

// Output: Object with three arrays
// {
//   "by_status": [...],
//   "by_customer": [...],
//   "summary": [...]
// }
```

#### 10. $facet with filtering

```javascript
// Get multiple analyses in one query
db.products.aggregate([
  {
    $facet: {
      // Top products by price
      expensive: [
        { $sort: { price: -1 } },
        { $limit: 5 },
        { $project: { name: 1, price: 1 } },
      ],
      // Products in specific categories
      by_category: [{ $group: { _id: "$categories", count: { $sum: 1 } } }],
      // Count stats
      stats: [
        {
          $group: {
            _id: null,
            avg_price: { $avg: "$price" },
            max_price: { $max: "$price" },
            min_price: { $min: "$price" },
          },
        },
      ],
    },
  },
]);
```

---

## Part 6: Advanced Patterns

### Pattern 1: Text Search

```javascript
// Create text index
db.products.createIndex({ name: "text", description: "text" });

// Search
db.products.find({
  $text: { $search: "laptop performance" },
});

// With score
db.products.aggregate([
  {
    $match: { $text: { $search: "laptop" } },
  },
  {
    $project: {
      name: 1,
      description: 1,
      score: { $meta: "textScore" },
    },
  },
  {
    $sort: { score: -1 },
  },
]);
```

### Pattern 2: Range Queries with $gte and $lte

```javascript
// Products priced between $100 and $1000
db.products.find({
  price: { $gte: 100, $lte: 1000 },
});

// Orders from last 30 days
db.orders.find({
  created_at: {
    $gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
    $lt: new Date(),
  },
});
```

### Pattern 3: Conditional Logic in Aggregation

```javascript
// Segment customers by spending
db.customers.aggregate([
  {
    $lookup: {
      from: "orders",
      localField: "_id",
      foreignField: "customer_id",
      as: "orders",
    },
  },
  {
    $project: {
      email: 1,
      first_name: 1,
      total_spent: { $sum: "$orders.total_amount" },
      segment: {
        $cond: [
          { $gte: [{ $sum: "$orders.total_amount" }, 5000] },
          "VIP",
          {
            $cond: [
              { $gte: [{ $sum: "$orders.total_amount" }, 1000] },
              "Premium",
              "Standard",
            ],
          },
        ],
      },
    },
  },
]);
```

### Pattern 4: Percentile Ranking

```javascript
// Rank customers by spending
db.customers.aggregate([
  {
    $lookup: {
      from: "orders",
      localField: "_id",
      foreignField: "customer_id",
      as: "orders",
    },
  },
  {
    $project: {
      email: 1,
      total_spent: { $sum: "$orders.total_amount" },
    },
  },
  {
    $bucketAuto: {
      groupBy: "$total_spent",
      buckets: 4,
    },
  },
]);
```

### Pattern 5: Time-based Aggregation

```javascript
// Revenue by day for last 30 days
db.orders.aggregate([
  {
    $match: {
      created_at: {
        $gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
      },
    },
  },
  {
    $group: {
      _id: {
        $dateToString: {
          format: "%Y-%m-%d",
          date: "$created_at",
        },
      },
      total_revenue: { $sum: "$total_amount" },
      order_count: { $sum: 1 },
    },
  },
  {
    $sort: { _id: 1 },
  },
]);
```

### Pattern 6: Complex Filtering with $cond

```javascript
// Find orders that need action
db.orders.aggregate([
  {
    $addFields: {
      needs_action: {
        $cond: [
          {
            $or: [
              { $eq: ["$current_status", "pending"] },
              {
                $and: [
                  { $eq: ["$current_status", "processing"] },
                  {
                    $lt: [
                      "$created_at",
                      new Date(Date.now() - 24 * 60 * 60 * 1000),
                    ],
                  },
                ],
              },
            ],
          },
          true,
          false,
        ],
      },
    },
  },
  {
    $match: { needs_action: true },
  },
]);
```

---

## Part 7: Transactions (Multi-Document ACID)

MongoDB 4.0+ supports multi-document ACID transactions:

```javascript
const session = db.getMongo().startSession();

try {
  session.startTransaction();

  // Insert order
  const orderResult = db.orders.insertOne({
    customer_id: ObjectId("..."),
    items: [...],
    total_amount: 2539.97,
    current_status: "pending",
    created_at: new Date()
  }, { session });

  // Decrease stock
  db.products.updateMany(
    { _id: { $in: [...] } },
    { $inc: { stock_quantity: -5 } },
    { session }
  );

  // Create payment
  db.payments.insertOne({
    order_id: orderResult.insertedId,
    amount: 2539.97,
    status: "pending"
  }, { session });

  session.commitTransaction();
} catch (error) {
  session.abortTransaction();
  throw error;
} finally {
  session.endSession();
}
```

---

## Part 8: Indexing Strategies

### Types of Indexes

```javascript
// Single field index
db.customers.createIndex({ email: 1 });

// Compound index (for queries using both fields)
db.orders.createIndex({ customer_id: 1, created_at: -1 });

// Text index (for full-text search)
db.products.createIndex({ name: "text", description: "text" });

// Wildcard index (for flexible field access)
db.products.createIndex({ "metadata.$**": 1 });

// Unique index
db.customers.createIndex({ email: 1 }, { unique: true });

// Sparse index (only index documents with the field)
db.customers.createIndex({ phone: 1 }, { sparse: true });

// TTL index (auto-delete documents after time)
db.sessions.createIndex(
  { created_at: 1 },
  { expireAfterSeconds: 3600 }, // Delete after 1 hour
);

// List indexes
db.customers.getIndexes();

// Drop index
db.customers.dropIndex("email_1");

// Check query plan
db.customers.find({ email: "alice@example.com" }).explain("executionStats");
```

---

## Part 9: Performance Tips

### 1. Use covered queries

```javascript
// Good: Index covers entire query
db.customers.createIndex({ email: 1, first_name: 1 });
db.customers.find(
  { email: "alice@example.com" },
  { email: 1, first_name: 1, _id: 0 },
);
// MongoDB returns data directly from index, no disk access
```

### 2. Projection to reduce data transfer

```javascript
// Bad: Get entire document
db.orders.find({ customer_id: ObjectId("...") });

// Good: Get only needed fields
db.orders.find(
  { customer_id: ObjectId("...") },
  { items: 1, total_amount: 1, created_at: 1 },
);
```

### 3. Batch processing

```javascript
// Process in batches instead of loading everything
db.orders
  .aggregate([
    { $match: { current_status: "pending" } },
    { $limit: 1000 }, // Process 1000 at a time
    { $project: { _id: 1 } },
  ])
  .forEach((doc) => {
    // Process doc
  });
```

### 4. Use aggregation for complex operations

```javascript
// Bad: Get data, manipulate in app
const orders = db.orders.find().toArray();
let total = 0;
orders.forEach((o) => (total += o.total_amount));

// Good: Let database do the work
const result = db.orders.aggregate([
  { $group: { _id: null, total: { $sum: "$total_amount" } } },
]);
```

---

## Part 10: Common Patterns & Real-World Queries

### Pattern 1: Customer Segmentation

```javascript
db.customers.aggregate([
  {
    $lookup: {
      from: "orders",
      localField: "_id",
      foreignField: "customer_id",
      as: "orders",
    },
  },
  {
    $project: {
      email: 1,
      total_orders: { $size: "$orders" },
      lifetime_value: { $sum: "$orders.total_amount" },
      last_order: { $max: "$orders.created_at" },
      segment: {
        $cond: [
          { $gte: [{ $sum: "$orders.total_amount" }, 5000] },
          "VIP",
          {
            $cond: [
              { $gte: [{ $sum: "$orders.total_amount" }, 1000] },
              "Premium",
              "Standard",
            ],
          },
        ],
      },
    },
  },
  {
    $sort: { lifetime_value: -1 },
  },
]);
```

### Pattern 2: Product Popularity with Reviews

```javascript
db.products.aggregate([
  {
    $lookup: {
      from: "reviews",
      localField: "_id",
      foreignField: "product_id",
      as: "reviews",
    },
  },
  {
    $lookup: {
      from: "orders",
      let: { product_id: "$_id" },
      pipeline: [
        { $unwind: "$items" },
        { $match: { $expr: { $eq: ["$items.product_id", "$$product_id"] } } },
        { $group: { _id: null, count: { $sum: 1 } } },
      ],
      as: "order_data",
    },
  },
  {
    $project: {
      name: 1,
      price: 1,
      review_count: { $size: "$reviews" },
      avg_rating: { $avg: "$reviews.rating" },
      times_ordered: { $arrayElemAt: ["$order_data.count", 0] },
      popularity: {
        $add: [
          { $size: "$reviews" },
          { $ifNull: [{ $arrayElemAt: ["$order_data.count", 0] }, 0] },
        ],
      },
    },
  },
  {
    $sort: { popularity: -1 },
  },
]);
```

### Pattern 3: Orders with Customer Details

```javascript
db.orders.aggregate([
  {
    $lookup: {
      from: "customers",
      localField: "customer_id",
      foreignField: "_id",
      as: "customer",
    },
  },
  {
    $unwind: "$customer",
  },
  {
    $project: {
      _id: 1,
      customer_email: "$customer.email",
      customer_name: {
        $concat: ["$customer.first_name", " ", "$customer.last_name"],
      },
      items: 1,
      total_amount: 1,
      status: "$current_status",
      created_at: 1,
    },
  },
  {
    $sort: { created_at: -1 },
  },
]);
```

### Pattern 4: Revenue by Category

```javascript
db.products.aggregate([
  {
    $unwind: "$categories",
  },
  {
    $lookup: {
      from: "orders",
      let: { product_id: "$_id" },
      pipeline: [
        { $unwind: "$items" },
        { $match: { $expr: { $eq: ["$items.product_id", "$$product_id"] } } },
      ],
      as: "orders",
    },
  },
  {
    $unwind: "$orders",
  },
  {
    $group: {
      _id: "$categories",
      revenue: { $sum: "$orders.total_amount" },
      order_count: { $sum: 1 },
      avg_order_value: { $avg: "$orders.total_amount" },
    },
  },
  {
    $sort: { revenue: -1 },
  },
]);
```

### Pattern 5: Churn Analysis

```javascript
db.customers.aggregate([
  {
    $lookup: {
      from: "orders",
      localField: "_id",
      foreignField: "customer_id",
      as: "orders",
    },
  },
  {
    $project: {
      email: 1,
      last_order_date: { $max: "$orders.created_at" },
      days_inactive: {
        $divide: [
          { $subtract: [new Date(), { $max: "$orders.created_at" }] },
          86400000, // milliseconds per day
        ],
      },
    },
  },
  {
    $addFields: {
      churn_status: {
        $cond: [
          { $lte: ["$days_inactive", 30] },
          "Active",
          {
            $cond: [
              { $lte: ["$days_inactive", 90] },
              "At Risk",
              {
                $cond: [
                  { $lte: ["$days_inactive", 180] },
                  "Inactive",
                  "Dormant",
                ],
              },
            ],
          },
        ],
      },
    },
  },
  {
    $match: { churn_status: { $in: ["At Risk", "Inactive", "Dormant"] } },
  },
  {
    $sort: { days_inactive: -1 },
  },
]);
```

---

## Comparison: MongoDB vs PostgreSQL

| Aspect                   | MongoDB                | PostgreSQL                       |
| ------------------------ | ---------------------- | -------------------------------- |
| **Schema**               | Flexible, denormalized | Strict, normalized               |
| **Joins**                | $lookup, embedded docs | Complex JOINs                    |
| **ACID**                 | Multi-doc (v4.0+)      | Full ACID across multiple tables |
| **Scaling**              | Sharding (horizontal)  | Replication (vertical)           |
| **Queries**              | Aggregation pipeline   | SQL                              |
| **Data types**           | Flexible               | Strongly typed                   |
| **Full-text search**     | Text indexes           | pg_trgm                          |
| **Learning curve**       | Easier for devs        | More complex SQL                 |
| **Production readiness** | Excellent              | Excellent                        |

---

## Key Takeaways

1. **Embrace denormalization**: Store related data together
2. **Use aggregation pipeline**: It's powerful and flexible
3. **Index strategically**: Match your query patterns
4. **Think in documents**: Not tables and rows
5. **Leverage flexibility**: Schema-less design is a feature
6. **Use transactions**: When you need consistency
7. **Monitor performance**: Use explain() to check queries
8. **Plan for scaling**: Sharding is built-in

MongoDB is excellent for applications with evolving requirements, nested data, and need for horizontal scaling. Use it when flexibility and developer velocity matter more than strict schema enforcement.

---

## Next Steps

1. Install MongoDB locally or use MongoDB Atlas (cloud)
2. Run all examples from the practical section
3. Design your own schema for a familiar domain
4. Build a small project with CRUD operations
5. Learn aggregation pipeline deeply
6. Explore transactions for consistency requirements
7. Study sharding strategies for large-scale apps

Happy document querying!
