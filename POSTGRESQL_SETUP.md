# 🚀 PostgreSQL Setup Guide for ReviewKing

## 📋 **SETUP STEPS**

### **Step 1: Install PostgreSQL**
```bash
# Windows: Download from https://www.postgresql.org/download/windows/
# Or use Chocolatey:
choco install postgresql

# Or use Docker:
docker run --name reviewking-postgres -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres:15
```

### **Step 2: Create Database**
```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE reviewking;

# Create user (optional)
CREATE USER reviewking_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE reviewking TO reviewking_user;

# Exit
\q
```

### **Step 3: Set Environment Variables**
```bash
# Copy environment file
copy env_local.txt .env

# Edit .env file with your database credentials:
DATABASE_URL=postgresql://postgres:password@localhost:5432/reviewking
```

### **Step 4: Setup Database Schema**
```bash
# Run database setup script
python setup_database.py
```

### **Step 5: Test Database Integration**
```bash
# Run app with database
python app_enhanced_with_db.py
```

---

## 🎯 **TESTING CHECKLIST**

### **Test 1: Database Connection**
```bash
curl http://localhost:5000/health
# Should return: {"status": "healthy", "database": "healthy"}
```

### **Test 2: Product-Specific Reviews**
```bash
# Import a review
curl -X POST "http://localhost:5000/admin/reviews/import/single" \
  -H "Content-Type: application/json" \
  -d '{
    "review": {
      "author": "Test Customer",
      "rating": 5,
      "text": "Great snowboard!",
      "quality_score": 8.5
    },
    "shopify_product_id": "10045740417338"
  }'

# Get reviews for specific product
curl "http://localhost:5000/widget/demo-shop/reviews/10045740417338"
```

### **Test 3: Database Query**
```bash
# Connect to PostgreSQL and check data
psql -U postgres -d reviewking

# Check tables
\dt

# Check reviews
SELECT * FROM reviews;

# Check products
SELECT * FROM products;
```

---

## 🔧 **TROUBLESHOOTING**

### **Connection Error**
```
❌ Database connection failed: connection refused
```
**Solution:**
1. Make sure PostgreSQL is running
2. Check port 5432 is open
3. Verify credentials in .env file

### **Permission Error**
```
❌ permission denied for database reviewking
```
**Solution:**
```sql
GRANT ALL PRIVILEGES ON DATABASE reviewking TO your_user;
```

### **Table Not Found**
```
❌ relation "shops" does not exist
```
**Solution:**
```bash
python setup_database.py
```

---

## 📊 **DATABASE STRUCTURE**

### **Tables Created:**
- `shop_owners` - Shop owners (one can have multiple shops)
- `shops` - Shopify stores with sakura_shop_id
- `products` - Products linked to shops
- `reviews` - Reviews linked to specific products
- `review_media` - Media files for reviews
- `imports` - Import job tracking
- `shop_settings` - Per-shop configuration

### **Sample Data:**
```sql
-- Demo shop created
INSERT INTO shops (shop_domain, sakura_shop_id, shop_name) 
VALUES ('sakura-rev-test-store.myshopify.com', 'c2FrdXJhLXJldi10ZXN0LXN0b3JlLm15c2hvcGlmeS5jb20', 'Sakura Test Store');

-- Demo products created
INSERT INTO products (shop_id, shopify_product_id, shopify_product_title) 
VALUES (1, '10045740417338', 'The 3p Fulfilled Snowboard');
```

---

## 🎉 **SUCCESS INDICATORS**

### **✅ Database Setup Complete When:**
1. `python setup_database.py` runs without errors
2. Health check returns `"database": "healthy"`
3. Can import reviews to specific products
4. Widget shows product-specific reviews
5. Can query data in PostgreSQL client

### **🎯 Product-Specific Reviews Working When:**
1. Import review for product "10045740417338"
2. Widget `/widget/demo-shop/reviews/10045740417338` shows that review
3. Import review for product "10045740122426" 
4. Widget `/widget/demo-shop/reviews/10045740122426` shows different review
5. Each product has its own reviews!

---

## 🚀 **NEXT STEPS**

After successful setup:
1. **Test with real AliExpress products**
2. **Import reviews to different products**
3. **Verify product-specific widget display**
4. **Scale to production PostgreSQL**

**Ready to build the next Loox!** 🎉

