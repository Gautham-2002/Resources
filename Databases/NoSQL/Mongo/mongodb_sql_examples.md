# MongoDB Practical Examples: Ready-to-Run Queries

This document provides 100+ copy-paste ready MongoDB queries organized by operation type.

---

## SETUP: Sample Data Insertion

Run these commands in mongosh (MongoDB shell) to populate sample data:

```javascript
// Connect to database
use ecommerce;

// Drop existing collections (clean slate)
db.customers.drop();
db.products.drop();
db.orders.drop();
db.reviews.drop();
db.payments.drop();

// Insert customers
db.customers.insertMany([
  {
    _id: ObjectId("507f1f77bcf86cd799439001"),
    email: "alice@example.com",
    first_name: "Alice",
    last_name: "Johnson",
    phone: "555-1001",
    preferences: {
      newsletter: true,
      theme: "dark",
      currency: "USD"
    },
    tags: ["premium", "vip"],
    created_at: new Date("2024-01-10"),
    updated_at: new Date("2024-01-15"),
    is_active: true
  },
  {
    _id: ObjectId("507f1f77bcf86cd799439002"),
    email: "bob@example.com",
    first_name: "Bob",
    last_name: "Smith",
    phone: "555-1002",
    tags: ["standard"],
    created_at: new Date("2024-01-12"),
    updated_at: new Date("2024-01-12"),
    is_active: true
  },
  {
    _id: ObjectId("507f1f77bcf86cd799439003"),
    email: "carol@example.com",
    first_name: "Carol",
    last_name: "Davis",
    phone: "555-1003",
    preferences: {
      newsletter: true,
      marketing: true
    },
    tags: ["premium"],
    created_at: new Date("2024-01-05"),
    updated_at: new Date("2024-01-20"),
    is_active: true
  },
  {
    _id: ObjectId("507f1f77bcf86cd799439004"),
    email: "david@example.com",
    first_name: "David",
    last_name: "Wilson",
    tags: ["standard", "new"],
    created_at: new Date("2024-01-18"),
    updated_at: new Date("2024-01-18"),
    is_active: true
  }
]);

// Insert products
db.products.insertMany([
  {
    _id: ObjectId("507f1f77bcf86cd799440001"),
    name: "MacBook Pro 16\"",
    description: "High-performance laptop for professionals",
    price: 2499.99,
    stock_quantity: 50,
    metadata: {
      sku: "APPLE-MBP-16",
      colors: ["Space Gray", "Silver"],
      specs: {
        ram_gb: 16,
        storage_gb: 512,
        processor: "M3 Max"
      },
      warranty_months: 12
    },
    categories: ["electronics", "computers", "laptops"],
    created_at: new Date("2023-12-01"),
    updated_at: new Date("2024-01-15")
  },
  {
    _id: ObjectId("507f1f77bcf86cd799440002"),
    name: "USB-C Cable",
    description: "Fast charging cable",
    price: 19.99,
    stock_quantity: 200,
    metadata: {
      sku: "CABLE-USB-C",
      length_m: 2,
      warranty_months: 12
    },
    categories: ["accessories", "cables"],
    created_at: new Date("2023-11-01"),
    updated_at: new Date("2024-01-10")
  },
  {
    _id: ObjectId("507f1f77bcf86cd799440003"),
    name: "Magic Mouse",
    description: "Wireless mouse",
    price: 79.99,
    stock_quantity: 120,
    metadata: {
      sku: "APPLE-MOUSE",
      colors: ["White", "Black"],
      battery_life_hours: 30
    },
    categories: ["accessories", "input-devices"],
    created_at: new Date("2023-11-15"),
    updated_at: new Date("2024-01-12")
  },
  {
    _id: ObjectId("507f1f77bcf86cd799440004"),
    name: "Studio Display",
    description: "27 inch display",
    price: 1599.99,
    stock_quantity: 30,
    metadata: {
      sku: "APPLE-DISPLAY",
      resolution: "5K",
      brightness_nits: 500
    },
    categories: ["electronics", "displays"],
    created_at: new Date("2023-12-15"),
    updated_at: new Date("2024-01-18")
  }
]);

// Insert orders
db.orders.insertMany([
  {
    _id: ObjectId("507f1f77bcf86cd799441001"),
    customer_id: ObjectId("507f1f77bcf86cd799439001"),
    customer_email: "alice@example.com",
    customer_name: "Alice Johnson",
    items: [
      {
        product_id: ObjectId("507f1f77bcf86cd799440001"),
        product_name: "MacBook Pro 16\"",
        quantity: 1,
        unit_price: 2499.99,
        total: 2499.99
      }
    ],
    total_amount: 2499.99,
    current_status: "pending",
    status_history: [
      {
        status: "pending",
        timestamp: new Date("2024-01-15"),
        notes: "Order received"
      }
    ],
    shipping_address: {
      street: "123 Main St",
      city: "New York",
      state: "NY",
      zip: "10001",
      country: "USA"
    },
    created_at: new Date("2024-01-15"),
    updated_at: new Date("2024-01-15")
  },
  {
    _id: ObjectId("507f1f77bcf86cd799441002"),
    customer_id: ObjectId("507f1f77bcf86cd799439001"),
    customer_email: "alice@example.com",
    customer_name: "Alice Johnson",
    items: [
      {
        product_id: ObjectId("507f1f77bcf86cd799440002"),
        product_name: "USB-C Cable",
        quantity: 2,
        unit_price: 19.99,
        total: 39.98
      }
    ],
    total_amount: 39.98,
    current_status: "shipped",
    status_history: [
      {
        status: "pending",
        timestamp: new Date("2024-01-16"),
        notes: "Received"
      },
      {
        status: "processing",
        timestamp: new Date("2024-01-17"),
        notes: "Being packed"
      },
      {
        status: "shipped",
        timestamp: new Date("2024-01-18"),
        notes: "With FedEx"
      }
    ],
    shipping_address: {
      street: "123 Main St",
      city: "New York",
      state: "NY"
    },
    created_at: new Date("2024-01-16"),
    updated_at: new Date("2024-01-18")
  },
  {
    _id: ObjectId("507f1f77bcf86cd799441003"),
    customer_id: ObjectId("507f1f77bcf86cd799439002"),
    customer_email: "bob@example.com",
    customer_name: "Bob Smith",
    items: [
      {
        product_id: ObjectId("507f1f77bcf86cd799440003"),
        product_name: "Magic Mouse",
        quantity: 1,
        unit_price: 79.99,
        total: 79.99
      }
    ],
    total_amount: 79.99,
    current_status: "delivered",
    status_history: [
      {
        status: "pending",
        timestamp: new Date("2024-01-14"),
        notes: "Order received"
      },
      {
        status: "shipped",
        timestamp: new Date("2024-01-15"),
        notes: "Shipped"
      },
      {
        status: "delivered",
        timestamp: new Date("2024-01-17"),
        notes: "Delivered to customer"
      }
    ],
    shipping_address: {
      street: "456 Oak Ave",
      city: "Los Angeles",
      state: "CA"
    },
    created_at: new Date("2024-01-14"),
    updated_at: new Date("2024-01-17")
  },
  {
    _id: ObjectId("507f1f77bcf86cd799441004"),
    customer_id: ObjectId("507f1f77bcf86cd799439003"),
    customer_email: "carol@example.com",
    customer_name: "Carol Davis",
    items: [
      {
        product_id: ObjectId("507f1f77bcf86cd799440001"),
        product_name: "MacBook Pro 16\"",
        quantity: 1,
        unit_price: 2499.99,
        total: 2499.99
      },
      {
        product_id: ObjectId("507f1f77bcf86cd799440004"),
        product_name: "Studio Display",
        quantity: 1,
        unit_price: 1599.99,
        total: 1599.99
      }
    ],
    total_amount: 4099.98,
    current_status: "processing",
    status_history: [
      {
        status: "pending",
        timestamp: new Date("2024-01-20"),
        notes: "Order received"
      },
      {
        status: "processing",
        timestamp: new Date("2024-01-21"),
        notes: "Picking items"
      }
    ],
    shipping_address: {
      street: "789 Pine Rd",
      city: "San Francisco",
      state: "CA"
    },
    created_at: new Date("2024-01-20"),
    updated_at: new Date("2024-01-21")
  }
]);

// Insert reviews
db.reviews.insertMany([
  {
    _id: ObjectId("507f1f77bcf86cd799442001"),
    product_id: ObjectId("507f1f77bcf86cd799440001"),
    customer_id: ObjectId("507f1f77bcf86cd799439001"),
    rating: 5,
    title: "Excellent laptop",
    body: "Best laptop I have ever owned. Highly recommended!",
    metadata: {
      verified_purchase: true,
      helpful_count: 45
    },
    created_at: new Date("2024-01-16"),
    updated_at: new Date("2024-01-16")
  },
  {
    _id: ObjectId("507f1f77bcf86cd799442002"),
    product_id: ObjectId("507f1f77bcf86cd799440001"),
    customer_id: ObjectId("507f1f77bcf86cd799439002"),
    rating: 4,
    title: "Great but pricey",
    body: "Powerful machine, but very expensive.",
    metadata: {
      verified_purchase: true,
      helpful_count: 32
    },
    created_at: new Date("2024-01-18"),
    updated_at: new Date("2024-01-18")
  },
  {
    _id: ObjectId("507f1f77bcf86cd799442003"),
    product_id: ObjectId("507f1f77bcf86cd799440003"),
    customer_id: ObjectId("507f1f77bcf86cd799439001"),
    rating: 5,
    title: "Perfect mouse",
    body: "Love the Magic Mouse. Great precision.",
    metadata: {
      verified_purchase: true,
      helpful_count: 28
    },
    created_at: new Date("2024-01-17"),
    updated_at: new Date("2024-01-17")
  },
  {
    _id: ObjectId("507f1f77bcf86cd799442004"),
    product_id: ObjectId("507f1f77bcf86cd799440002"),
    customer_id: ObjectId("507f1f77bcf86cd799439003"),
    rating: 4,
    title: "Good quality cable",
    body: "Works great, fast charging.",
    metadata: {
      verified_purchase: true,
      helpful_count: 15
    },
    created_at: new Date("2024-01-19"),
    updated_at: new Date("2024-01-19")
  }
]);

// Insert payments
db.payments.insertMany([
  {
    _id: ObjectId("507f1f77bcf86cd799443001"),
    order_id: ObjectId("507f1f77bcf86cd799441001"),
    amount: 2499.99,
    payment_method: "credit_card",
    status: "completed",
    gateway_response: {
      transaction_id: "TXN001",
      processor: "Stripe",
      auth_code: "123456"
    },
    created_at: new Date("2024-01-15"),
    updated_at: new Date("2024-01-15")
  },
  {
    _id: ObjectId("507f1f77bcf86cd799443002"),
    order_id: ObjectId("507f1f77bcf86cd799441002"),
    amount: 39.98,
    payment_method: "credit_card",
    status: "completed",
    gateway_response: {
      transaction_id: "TXN002",
      processor: "Stripe"
    },
    created_at: new Date("2024-01-16"),
    updated_at: new Date("2024-01-16")
  },
  {
    _id: ObjectId("507f1f77bcf86cd799443003"),
    order_id: ObjectId("507f1f77bcf86cd799441003"),
    amount: 79.99,
    payment_method: "debit_card",
    status: "completed",
    gateway_response: {
      transaction_id: "TXN003",
      processor: "Stripe"
    },
    created_at: new Date("2024-01-14"),
    updated_at: new Date("2024-01-14")
  },
  {
    _id: ObjectId("507f1f77bcf86cd799443004"),
    order_id: ObjectId("507f1f77bcf86cd799441004"),
    amount: 4099.98,
    payment_method: "credit_card",
    status: "pending",
    gateway_response: {
      transaction_id: "TXN004",
      processor: "Stripe"
    },
    created_at: new Date("2024-01-20"),
    updated_at: new Date("2024-01-20")
  }
]);

// Create indexes
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

console.log("Sample data inserted successfully!");
```

---

## BASIC CRUD: READ (Find)

### 1. Find all documents
```javascript
db.customers.find();

// Pretty print
db.customers.find().pretty();
```

### 2. Find by ID
```javascript
db.customers.findOne({ _id: ObjectId("507f1f77bcf86cd799439001") });
```

### 3. Find by email
```javascript
db.customers.findOne({ email: "alice@example.com" });
```

### 4. Find with condition
```javascript
// Active customers
db.customers.find({ is_active: true });

// Premium customers
db.customers.find({ tags: "premium" });

// Customers created after date
db.customers.find({
  created_at: { $gte: new Date("2024-01-15") }
});
```

### 5. Find with multiple conditions (AND)
```javascript
db.customers.find({
  is_active: true,
  tags: "premium"
});

// Explicit AND
db.customers.find({
  $and: [
    { is_active: true },
    { created_at: { $gte: new Date("2024-01-01") } }
  ]
});
```

### 6. Find with OR
```javascript
db.customers.find({
  $or: [
    { tags: "premium" },
    { tags: "vip" }
  ]
});
```

### 7. Find with IN operator
```javascript
// Products in specific price range
db.products.find({
  price: { $in: [19.99, 79.99, 1599.99] }
});
```

### 8. Find with NOT IN
```javascript
// Orders not in these statuses
db.orders.find({
  current_status: { $nin: ["cancelled", "failed"] }
});
```

### 9. Find with GT/LT
```javascript
// Products more expensive than $100
db.products.find({ price: { $gt: 100 } });

// Orders less than $50
db.orders.find({ total_amount: { $lt: 50 } });

// Orders between $50 and $1000
db.orders.find({
  total_amount: { $gte: 50, $lte: 1000 }
});
```

### 10. Find with array contains
```javascript
// Customers with "premium" tag
db.customers.find({ tags: "premium" });

// Customers with ALL these tags
db.customers.find({ tags: { $all: ["premium", "vip"] } });

// Customers with any of these tags
db.customers.find({ tags: { $in: ["premium", "vip"] } });
```

### 11. Find with nested field
```javascript
// Products with specific SKU
db.products.find({ "metadata.sku": "APPLE-MBP-16" });

// Products with specific RAM
db.products.find({ "metadata.specs.ram_gb": 16 });

// Orders shipped to specific city
db.orders.find({ "shipping_address.city": "New York" });
```

### 12. Find with array size
```javascript
// Orders with exactly 2 items
db.orders.find({ items: { $size: 2 } });
```

### 13. Find with $elemMatch
```javascript
// Orders containing items over $2000
db.orders.find({
  items: {
    $elemMatch: {
      unit_price: { $gt: 2000 }
    }
  }
});

// Orders with specific product
db.orders.find({
  items: {
    $elemMatch: {
      product_name: "MacBook Pro 16\""
    }
  }
});
```

### 14. Text search
```javascript
db.products.find({ $text: { $search: "laptop" } });

// Search multiple words
db.products.find({ $text: { $search: "laptop performance" } });
```

### 15. Projection - select fields
```javascript
// Get only name and price
db.products.find(
  {},
  { name: 1, price: 1, _id: 0 }
);

// Exclude a field
db.customers.find(
  {},
  { preferences: 0 }
);

// Nested projection
db.products.find(
  {},
  { name: 1, "metadata.sku": 1 }
);
```

### 16. Count
```javascript
db.customers.countDocuments();

db.customers.countDocuments({ is_active: true });

db.orders.countDocuments({ current_status: "delivered" });
```

### 17. Distinct values
```javascript
// Get all unique order statuses
db.orders.distinct("current_status");

// All unique tags
db.customers.distinct("tags");
```

### 18. Sort
```javascript
// Sort by creation date (newest first)
db.orders.find().sort({ created_at: -1 });

// Sort by price (lowest first)
db.products.find().sort({ price: 1 });

// Sort by multiple fields
db.orders.find().sort({ current_status: 1, created_at: -1 });
```

### 19. Limit and skip (pagination)
```javascript
// Get first 10
db.products.find().limit(10);

// Get page 3 (20-30)
db.products.find().skip(20).limit(10);
```

### 20. Complex query
```javascript
db.orders
  .find({
    total_amount: { $gt: 100 },
    current_status: { $in: ["shipped", "delivered"] }
  })
  .sort({ created_at: -1 })
  .limit(5)
  .pretty();
```

---

## BASIC CRUD: CREATE (Insert)

### 1. Insert one
```javascript
db.customers.insertOne({
  email: "eve@example.com",
  first_name: "Eve",
  last_name: "Brown",
  phone: "555-2000",
  preferences: {
    newsletter: true,
    theme: "light"
  },
  tags: ["new", "trial"],
  created_at: new Date(),
  updated_at: new Date(),
  is_active: true
});

// Returns: { acknowledged: true, insertedId: ObjectId("...") }
```

### 2. Insert many
```javascript
db.customers.insertMany([
  {
    email: "frank@example.com",
    first_name: "Frank",
    last_name: "Green",
    tags: ["standard"],
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    email: "grace@example.com",
    first_name: "Grace",
    last_name: "Harris",
    tags: ["premium"],
    created_at: new Date(),
    updated_at: new Date()
  }
]);
```

### 3. Insert with defaults
```javascript
db.products.insertOne({
  name: "New Product",
  price: 99.99,
  stock_quantity: 100,
  // Other fields created automatically if missing
  created_at: new Date(),
  updated_at: new Date()
});
```

### 4. Insert nested document
```javascript
db.orders.insertOne({
  customer_id: ObjectId("507f1f77bcf86cd799439001"),
  customer_email: "alice@example.com",
  customer_name: "Alice Johnson",
  items: [
    {
      product_id: ObjectId("507f1f77bcf86cd799440001"),
      product_name: "MacBook Pro 16\"",
      quantity: 1,
      unit_price: 2499.99,
      total: 2499.99
    },
    {
      product_id: ObjectId("507f1f77bcf86cd799440003"),
      product_name: "Magic Mouse",
      quantity: 2,
      unit_price: 79.99,
      total: 159.98
    }
  ],
  total_amount: 2659.97,
  current_status: "pending",
  status_history: [
    {
      status: "pending",
      timestamp: new Date(),
      notes: "Order created"
    }
  ],
  shipping_address: {
    street: "123 Main St",
    city: "New York",
    state: "NY",
    zip: "10001"
  },
  created_at: new Date(),
  updated_at: new Date()
});
```

### 5. Ordered vs unordered insert
```javascript
// Stops on first error
db.customers.insertMany(documents, { ordered: true });

// Continues even with errors
db.customers.insertMany(documents, { ordered: false });
```

---

## BASIC CRUD: UPDATE

### 1. Update one field
```javascript
db.customers.updateOne(
  { _id: ObjectId("507f1f77bcf86cd799439001") },
  { $set: { phone: "555-9999", updated_at: new Date() } }
);
```

### 2. Update multiple documents
```javascript
db.customers.updateMany(
  { tags: "new" },
  { $set: { tags: ["standard"], updated_at: new Date() } }
);
```

### 3. Increment operator
```javascript
// Decrease stock by 5
db.products.updateOne(
  { _id: ObjectId("507f1f77bcf86cd799440001") },
  { $inc: { stock_quantity: -5 } }
);

// Increase price by 10%
db.products.updateOne(
  { _id: ObjectId("507f1f77bcf86cd799440001") },
  { $mul: { price: 1.1 } }
);
```

### 4. Push to array
```javascript
// Add tag to customer
db.customers.updateOne(
  { _id: ObjectId("507f1f77bcf86cd799439001") },
  { $push: { tags: "vip" } }
);

// Add multiple tags
db.customers.updateOne(
  { _id: ObjectId("507f1f77bcf86cd799439001") },
  { $push: { tags: { $each: ["loyalty", "referrer"] } } }
);
```

### 5. Pull from array
```javascript
// Remove tag from customer
db.customers.updateOne(
  { _id: ObjectId("507f1f77bcf86cd799439001") },
  { $pull: { tags: "new" } }
);
```

### 6. Update nested object
```javascript
// Update customer preference
db.customers.updateOne(
  { _id: ObjectId("507f1f77bcf86cd799439001") },
  { $set: { "preferences.theme": "light", updated_at: new Date() } }
);

// Add to nested object
db.customers.updateOne(
  { _id: ObjectId("507f1f77bcf86cd799439001") },
  { $set: { "preferences.language": "es" } }
);
```

### 7. Unset field
```javascript
// Remove a field
db.customers.updateOne(
  { _id: ObjectId("507f1f77bcf86cd799439001") },
  { $unset: { legacy_field: "" } }
);
```

### 8. Replace entire document
```javascript
db.customers.replaceOne(
  { _id: ObjectId("507f1f77bcf86cd799439001") },
  {
    email: "newemail@example.com",
    first_name: "Alice",
    last_name: "Smith",
    // All fields must be provided
    created_at: new Date("2024-01-10"),
    updated_at: new Date()
  }
);
```

### 9. Upsert (update or insert)
```javascript
db.customers.updateOne(
  { email: "henry@example.com" },
  {
    $set: {
      first_name: "Henry",
      last_name: "Taylor",
      created_at: new Date(),
      updated_at: new Date()
    }
  },
  { upsert: true }
);
```

### 10. Add to status history
```javascript
db.orders.updateOne(
  { _id: ObjectId("507f1f77bcf86cd799441001") },
  {
    $push: {
      status_history: {
        status: "shipped",
        timestamp: new Date(),
        carrier: "FedEx",
        tracking: "123456789"
      }
    },
    $set: {
      current_status: "shipped",
      updated_at: new Date()
    }
  }
);
```

---

## BASIC CRUD: DELETE

### 1. Delete one
```javascript
db.customers.deleteOne({ _id: ObjectId("507f1f77bcf86cd799439001") });
```

### 2. Delete many
```javascript
db.orders.deleteMany({
  current_status: "cancelled",
  created_at: { $lt: new Date("2023-01-01") }
});
```

### 3. Delete by condition
```javascript
// Delete inactive customers
db.customers.deleteMany({ is_active: false });

// Delete low-value products
db.products.deleteMany({ stock_quantity: 0, price: { $lt: 10 } });
```

### 4. Soft delete (preferred)
```javascript
// Mark as deleted instead of removing
db.customers.updateOne(
  { _id: ObjectId("507f1f77bcf86cd799439001") },
  { $set: { deleted_at: new Date() } }
);

// Always filter soft-deleted
db.customers.find({ deleted_at: { $exists: false } });
```

### 5. Delete all
```javascript
db.customers.deleteMany({});  // Dangerous!
```

---

## AGGREGATION PIPELINE: Basic Stages

### 1. $match - Filter
```javascript
db.customers.aggregate([
  {
    $match: {
      is_active: true,
      created_at: { $gte: new Date("2024-01-01") }
    }
  }
]);
```

### 2. $project - Select and transform fields
```javascript
db.customers.aggregate([
  {
    $project: {
      _id: 1,
      email: 1,
      full_name: { $concat: ["$first_name", " ", "$last_name"] },
      is_premium: { $in: ["premium", "$tags"] }
    }
  }
]);
```

### 3. $group - Group and aggregate
```javascript
db.customers.aggregate([
  {
    $unwind: "$tags"
  },
  {
    $group: {
      _id: "$tags",
      count: { $sum: 1 },
      emails: { $push: "$email" }
    }
  }
]);
```

### 4. $sort
```javascript
db.orders.aggregate([
  { $sort: { created_at: -1 } }
]);
```

### 5. $limit and $skip
```javascript
db.products.aggregate([
  { $skip: 20 },
  { $limit: 10 }
]);
```

---

## AGGREGATION PIPELINE: Complex Examples

### 1. Customer lifetime value
```javascript
db.orders.aggregate([
  {
    $match: { current_status: { $ne: "cancelled" } }
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
      last_order: { $max: "$created_at" }
    }
  },
  {
    $sort: { total_spent: -1 }
  }
]);
```

### 2. $lookup - Join collections
```javascript
db.customers.aggregate([
  {
    $match: { _id: ObjectId("507f1f77bcf86cd799439001") }
  },
  {
    $lookup: {
      from: "orders",
      localField: "_id",
      foreignField: "customer_id",
      as: "orders"
    }
  },
  {
    $project: {
      email: 1,
      first_name: 1,
      order_count: { $size: "$orders" },
      total_spent: { $sum: "$orders.total_amount" }
    }
  }
]);
```

### 3. $unwind - Expand arrays
```javascript
db.orders.aggregate([
  {
    $unwind: "$items"
  },
  {
    $project: {
      customer_id: 1,
      product_name: "$items.product_name",
      quantity: "$items.quantity",
      unit_price: "$items.unit_price"
    }
  }
]);
```

### 4. Revenue by day
```javascript
db.orders.aggregate([
  {
    $match: {
      created_at: {
        $gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
      }
    }
  },
  {
    $group: {
      _id: {
        $dateToString: {
          format: "%Y-%m-%d",
          date: "$created_at"
        }
      },
      total_revenue: { $sum: "$total_amount" },
      order_count: { $sum: 1 }
    }
  },
  {
    $sort: { _id: 1 }
  }
]);
```

### 5. Product popularity
```javascript
db.products.aggregate([
  {
    $lookup: {
      from: "reviews",
      localField: "_id",
      foreignField: "product_id",
      as: "reviews"
    }
  },
  {
    $lookup: {
      from: "orders",
      let: { product_id: "$_id" },
      pipeline: [
        { $unwind: "$items" },
        { $match: { $expr: { $eq: ["$items.product_id", "$$product_id"] } } },
        { $group: { _id: null, count: { $sum: 1 } } }
      ],
      as: "order_data"
    }
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
          { $ifNull: [{ $arrayElemAt: ["$order_data.count", 0] }, 0] }
        ]
      }
    }
  },
  {
    $sort: { popularity: -1 }
  }
]);
```

### 6. Customer segmentation
```javascript
db.customers.aggregate([
  {
    $lookup: {
      from: "orders",
      localField: "_id",
      foreignField: "customer_id",
      as: "orders"
    }
  },
  {
    $project: {
      email: 1,
      total_orders: { $size: "$orders" },
      lifetime_value: { $sum: "$orders.total_amount" },
      segment: {
        $cond: [
          { $gte: [{ $sum: "$orders.total_amount" }, 5000] },
          "VIP",
          {
            $cond: [
              { $gte: [{ $sum: "$orders.total_amount" }, 1000] },
              "Premium",
              "Standard"
            ]
          }
        ]
      }
    }
  },
  {
    $sort: { lifetime_value: -1 }
  }
]);
```

### 7. Orders with customer details
```javascript
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
    $unwind: "$customer"
  },
  {
    $project: {
      _id: 1,
      customer_email: "$customer.email",
      customer_name: { $concat: ["$customer.first_name", " ", "$customer.last_name"] },
      total_amount: 1,
      status: "$current_status",
      items_count: { $size: "$items" },
      created_at: 1
    }
  },
  {
    $sort: { created_at: -1 }
  }
]);
```

### 8. Churn analysis
```javascript
db.customers.aggregate([
  {
    $lookup: {
      from: "orders",
      localField: "_id",
      foreignField: "customer_id",
      as: "orders"
    }
  },
  {
    $project: {
      email: 1,
      last_order_date: { $max: "$orders.created_at" },
      days_inactive: {
        $divide: [
          { $subtract: [new Date(), { $max: "$orders.created_at" }] },
          86400000
        ]
      }
    }
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
                  "Dormant"
                ]
              }
            ]
          }
        ]
      }
    }
  },
  {
    $match: { churn_status: { $in: ["At Risk", "Inactive", "Dormant"] } }
  },
  {
    $sort: { days_inactive: -1 }
  }
]);
```

---

## ADVANCED PATTERNS

### 1. Text search with score
```javascript
db.products.aggregate([
  {
    $match: { $text: { $search: "laptop" } }
  },
  {
    $project: {
      name: 1,
      description: 1,
      score: { $meta: "textScore" }
    }
  },
  {
    $sort: { score: -1 }
  }
]);
```

### 2. Faceted search
```javascript
db.products.aggregate([
  {
    $facet: {
      expensive: [
        { $sort: { price: -1 } },
        { $limit: 5 },
        { $project: { name: 1, price: 1 } }
      ],
      by_category: [
        { $group: { _id: "$categories", count: { $sum: 1 } } }
      ],
      stats: [
        {
          $group: {
            _id: null,
            avg_price: { $avg: "$price" },
            max_price: { $max: "$price" }
          }
        }
      ]
    }
  }
]);
```

### 3. $facet with multiple analyses
```javascript
db.orders.aggregate([
  {
    $facet: {
      by_status: [
        { $group: { _id: "$current_status", count: { $sum: 1 } } }
      ],
      top_customers: [
        { $group: { _id: "$customer_id", total: { $sum: "$total_amount" } } },
        { $sort: { total: -1 } },
        { $limit: 5 }
      ],
      summary: [
        {
          $group: {
            _id: null,
            total_revenue: { $sum: "$total_amount" },
            avg_order: { $avg: "$total_amount" },
            order_count: { $sum: 1 }
          }
        }
      ]
    }
  }
]);
```

### 4. Conditional aggregation
```javascript
db.orders.aggregate([
  {
    $addFields: {
      needs_attention: {
        $cond: [
          {
            $or: [
              { $eq: ["$current_status", "pending"] },
              { $and: [
                { $eq: ["$current_status", "processing"] },
                {
                  $lt: [
                    "$created_at",
                    new Date(Date.now() - 24 * 60 * 60 * 1000)
                  ]
                }
              ]}
            ]
          },
          true,
          false
        ]
      }
    }
  },
  {
    $match: { needs_attention: true }
  }
]);
```

---

## INDEXING & PERFORMANCE

### Create indexes
```javascript
// Single field
db.customers.createIndex({ email: 1 });

// Compound
db.orders.createIndex({ customer_id: 1, created_at: -1 });

// Text index
db.products.createIndex({ name: "text", description: "text" });

// Unique
db.customers.createIndex({ email: 1 }, { unique: true });

// Sparse
db.customers.createIndex({ phone: 1 }, { sparse: true });

// TTL
db.sessions.createIndex(
  { created_at: 1 },
  { expireAfterSeconds: 3600 }
);
```

### List indexes
```javascript
db.customers.getIndexes();
```

### Drop index
```javascript
db.customers.dropIndex("email_1");
```

### Analyze query performance
```javascript
db.customers.find({ email: "alice@example.com" }).explain("executionStats");
```

---

## TIPS & TRICKS

### 1. Count distinct values
```javascript
db.orders.distinct("current_status");
db.customers.distinct("tags");
```

### 2. Get one random document
```javascript
db.customers.aggregate([
  { $sample: { size: 1 } }
]);
```

### 3. Pagination cursor
```javascript
// Get next 10 after a specific ID
db.orders
  .find({ _id: { $gt: last_id } })
  .sort({ _id: 1 })
  .limit(10);
```

### 4. Bulk operations
```javascript
const bulk = db.customers.initializeUnorderedBulkOp();
bulk.find({ is_active: false }).update({ $set: { deleted: true } });
bulk.find({ tags: "new" }).update({ $pull: { tags: "new" } });
bulk.execute();
```

### 5. Transactions
```javascript
const session = db.getMongo().startSession();

try {
  session.startTransaction();
  
  db.orders.insertOne({ ... }, { session });
  db.products.updateMany({ ... }, { ... }, { session });
  
  session.commitTransaction();
} catch (error) {
  session.abortTransaction();
  throw error;
} finally {
  session.endSession();
}
```

---

## Common Business Queries

### 1. Total revenue last 30 days
```javascript
db.orders.aggregate([
  {
    $match: {
      created_at: {
        $gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
      },
      current_status: { $ne: "cancelled" }
    }
  },
  {
    $group: {
      _id: null,
      total_revenue: { $sum: "$total_amount" }
    }
  }
]);
```

### 2. Top 10 customers by revenue
```javascript
db.orders.aggregate([
  { $match: { current_status: { $ne: "cancelled" } } },
  { $group: {
      _id: "$customer_id",
      total: { $sum: "$total_amount" },
      orders: { $sum: 1 }
    }
  },
  { $sort: { total: -1 } },
  { $limit: 10 },
  {
    $lookup: {
      from: "customers",
      localField: "_id",
      foreignField: "_id",
      as: "customer"
    }
  },
  { $unwind: "$customer" },
  {
    $project: {
      email: "$customer.email",
      total: 1,
      orders: 1
    }
  }
]);
```

### 3. Orders pending shipment
```javascript
db.orders.find({
  current_status: "processing"
}).sort({ created_at: 1 });
```

### 4. Low stock products
```javascript
db.products.find({
  stock_quantity: { $lt: 10 }
}).sort({ stock_quantity: 1 });
```

### 5. Best rated products
```javascript
db.reviews.aggregate([
  { $group: {
      _id: "$product_id",
      avg_rating: { $avg: "$rating" },
      review_count: { $sum: 1 }
    }
  },
  { $match: { review_count: { $gte: 5 } } },
  { $sort: { avg_rating: -1 } },
  { $limit: 10 },
  {
    $lookup: {
      from: "products",
      localField: "_id",
      foreignField: "_id",
      as: "product"
    }
  },
  { $unwind: "$product" },
  {
    $project: {
      name: "$product.name",
      avg_rating: 1,
      review_count: 1
    }
  }
]);
```

Happy querying with MongoDB!
