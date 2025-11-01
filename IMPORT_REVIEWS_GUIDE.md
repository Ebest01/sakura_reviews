# 📦 Import Reviews to Specific Products - Guide

## Overview

This guide shows you how to import reviews to specific Shopify products using your Easypanel PostgreSQL database.

## ✅ What You Have

- ✅ **Connected to Easypanel PostgreSQL** (193.203.165.217)
- ✅ **Database tables created** (shops, reviews, imports, settings)
- ✅ **Demo shop configured** in database
- ✅ **Shopify API access** for your test store

## 🚀 Quick Start

### Method 1: Quick Test (Automatic)

Run the automated test script that will:
1. Fetch products from your Shopify store
2. Import 3 sample reviews to the first product
3. Show you the results

```bash
python quick_import_test.py
```

### Method 2: Interactive Menu

For more control, use the interactive menu:

```bash
python import_reviews_to_products.py
```

**Menu Options:**
1. **List Shopify products** - See all products in your store with their IDs
2. **Import sample reviews** - Import reviews to a specific product ID
3. **List reviews for product** - View all reviews imported for a product
4. **Check database stats** - See review counts and limits
5. **Exit**

## 📋 Step-by-Step Example

### Step 1: List Products

```
Option 1: List Shopify products
```

This will show you all products with their Shopify Product IDs, like:
```
1. The 3p Fulfilled Snowboard
   ID: 10045740417338
   Handle: the-3p-fulfilled-snowboard
```

### Step 2: Import Reviews

```
Option 2: Import sample reviews to a product
Enter Shopify Product ID: 10045740417338
Number of reviews to import (default 3): 3
```

This will:
- Create 3 sample reviews
- Link them to the product ID
- Save to Easypanel PostgreSQL database
- Update shop's review count

### Step 3: Verify Import

```
Option 3: List reviews for a product
Enter Shopify Product ID: 10045740417338
```

This shows all reviews for that product.

### Step 4: Check Database

Use `psql` to query directly:

```bash
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -h 193.203.165.217 -p 5432 -U saksaks -d sakrev_db -c "SELECT * FROM reviews WHERE shopify_product_id = '10045740417338';"
```

## 🔍 Database Structure

### Reviews Table

Each review is stored with:
- `shop_id` - Links to your shop
- `shopify_product_id` - The Shopify product ID (STRING)
- `reviewer_name` - Name of reviewer
- `rating` - Star rating (1-5)
- `title` - Review title
- `body` - Review text
- `images` - JSON array of image URLs
- `quality_score` - AI quality score (0-10)
- `verified_purchase` - Boolean
- `reviewer_country` - Country code
- `imported_at` - Timestamp

### Query Examples

**Get all reviews for a product:**
```sql
SELECT * FROM reviews WHERE shopify_product_id = 'YOUR_PRODUCT_ID';
```

**Get review count per product:**
```sql
SELECT shopify_product_id, COUNT(*) as review_count 
FROM reviews 
GROUP BY shopify_product_id;
```

**Get reviews with photos:**
```sql
SELECT * FROM reviews 
WHERE images IS NOT NULL 
AND images::text != '[]'::text;
```

## 🎯 Next Steps

After importing reviews:

1. **Test Widget Display:**
   ```
   http://localhost:5000/widget/demo-shop/reviews/PRODUCT_ID
   ```

2. **Integrate with app_enhanced.py:**
   - The reviews are now in the database
   - Widget endpoints can query by `shopify_product_id`
   - Reviews will display automatically

3. **Import from Real Sources:**
   - Modify `import_review_to_product()` function
   - Add your scraper data
   - Use the same function to import real reviews

## 📝 Custom Import Function

To import real reviews (not samples), modify the script:

```python
from import_reviews_to_products import import_review_to_product, get_shop_id_from_db

shop_id = get_shop_id_from_db()
product_id = "YOUR_PRODUCT_ID"

real_review_data = {
    'reviewer_name': 'Actual Customer',
    'rating': 5,
    'title': 'Real Review Title',
    'body': 'Real review text...',
    'source_platform': 'aliexpress',
    'source_product_id': 'aliexpress_product_id',
    'source_review_id': 'review_id',
    'reviewer_country': 'US',
    'verified_purchase': True,
    'images': ['url1', 'url2'],
    'quality_score': 9.0,
    'review_date': datetime.utcnow()
}

import_review_to_product(shop_id, product_id, real_review_data)
```

## ✅ Success Indicators

- ✅ Reviews appear in database queries
- ✅ Shop's `reviews_imported` count increases
- ✅ Widget shows reviews for the product
- ✅ No errors in import script

## 🐛 Troubleshooting

**Error: "No shop found in database"**
- Run `setup_database.py` first to create demo shop

**Error: "Shopify API failed"**
- Check access token in `config.json`
- Verify shop domain is correct

**Reviews not showing in widget:**
- Verify `shopify_product_id` matches exactly
- Check widget endpoint is querying database
- Ensure reviews have `status='published'` and `published=True`

---

**Ready to import! Run `python quick_import_test.py` to get started! 🚀**

