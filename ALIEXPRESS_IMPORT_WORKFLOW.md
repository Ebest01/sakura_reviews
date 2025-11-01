# 🌸 AliExpress Review Import - Complete Workflow

## Overview

This guide walks you through importing reviews from AliExpress and displaying them in your Shopify store.

## ✅ Prerequisites

- ✅ Easypanel PostgreSQL database connected
- ✅ Demo shop configured in database
- ✅ Shopify product IDs available
- ✅ Python environment with required packages

## 🚀 Step-by-Step Workflow

### Step 1: Import Reviews from AliExpress

Use the import script to scrape and save reviews:

```bash
python import_aliexpress_reviews.py
```

**Input Required:**
- AliExpress Product URL (e.g., `https://www.aliexpress.com/item/1234567890.html`)
- Shopify Product ID (e.g., `10045740417338`)
- Max reviews to import (default: 20)

**What it does:**
1. Extracts AliExpress product ID from URL
2. Scrapes reviews using AliExpress API
3. Calculates quality scores for each review
4. Imports reviews to Easypanel PostgreSQL database
5. Links reviews to Shopify product ID
6. Updates shop's review count

### Step 2: Verify Reviews in Database

**Option A: Using Python Script**
```bash
python verify_reviews_in_db.py 10045740417338
```

**Option B: Using psql (CMD)**
```cmd
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -h 193.203.165.217 -p 5432 -U saksaks -d sakrev_db -c "SELECT * FROM reviews WHERE shopify_product_id = '10045740417338';"
```

**What to check:**
- ✅ Reviews are saved with correct `shopify_product_id`
- ✅ All fields are populated (name, rating, body, images, etc.)
- ✅ `status = 'published'` and `published = true`
- ✅ Quality scores are calculated
- ✅ Shop's `reviews_imported` count increased

### Step 3: Test Widget Display

**Option A: Standalone Widget Server**
```bash
python widget_endpoint_simple.py
```

Then visit:
```
http://localhost:5000/widget/demo-shop/reviews/10045740417338
```

**Option B: Integrate into Main App**

Add to `backend/app.py`:
```python
from widget_endpoint_simple import create_widget_endpoint
create_widget_endpoint(app)
```

Then access:
```
http://localhost:5000/widget/demo-shop/reviews/{PRODUCT_ID}
```

### Step 4: Verify Widget Displays Correctly

**Check:**
- ✅ Reviews appear in widget
- ✅ Ratings display correctly (stars)
- ✅ Images load (if reviews have photos)
- ✅ Reviewer names, countries show
- ✅ Verified badges appear
- ✅ AI recommended badges appear (if quality_score >= 8)
- ✅ Statistics show (avg rating, verified count, etc.)

## 📋 Database Schema Reference

### Reviews Table Structure

```sql
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY,
    shop_id INTEGER NOT NULL,
    shopify_product_id VARCHAR(255),  -- KEY FIELD: Links to Shopify product
    source_platform VARCHAR(50),       -- 'aliexpress'
    source_product_id VARCHAR(255),
    source_review_id VARCHAR(255),
    reviewer_name VARCHAR(255),
    rating INTEGER NOT NULL,
    title VARCHAR(500),
    body TEXT,
    verified_purchase BOOLEAN,
    reviewer_country VARCHAR(10),
    review_date TIMESTAMP,
    images JSON,                       -- Array of image URLs
    quality_score FLOAT,
    ai_recommended BOOLEAN,
    status VARCHAR(50),                -- 'published'
    published BOOLEAN,                 -- true
    imported_at TIMESTAMP
);
```

### Key Query Examples

**Get all reviews for a product:**
```sql
SELECT * FROM reviews 
WHERE shopify_product_id = '10045740417338'
ORDER BY imported_at DESC;
```

**Count reviews per product:**
```sql
SELECT shopify_product_id, COUNT(*) as count
FROM reviews
GROUP BY shopify_product_id;
```

**Get reviews with images:**
```sql
SELECT * FROM reviews
WHERE shopify_product_id = '10045740417338'
AND images IS NOT NULL
AND images::text != '[]'::text;
```

**Check import statistics:**
```sql
SELECT 
    COUNT(*) as total,
    AVG(rating) as avg_rating,
    COUNT(CASE WHEN verified_purchase THEN 1 END) as verified,
    COUNT(CASE WHEN images IS NOT NULL AND images::text != '[]' THEN 1 END) as with_images
FROM reviews
WHERE shopify_product_id = '10045740417338';
```

## 🔍 Troubleshooting

### Issue: "No reviews found" after import

**Check:**
1. Verify shopify_product_id matches exactly (it's a STRING, not integer)
2. Check reviews table: `SELECT shopify_product_id FROM reviews;`
3. Ensure `status = 'published'` and `published = true`

**Fix:**
```sql
UPDATE reviews 
SET status = 'published', published = true
WHERE shopify_product_id = 'YOUR_PRODUCT_ID';
```

### Issue: Reviews not displaying in widget

**Check:**
1. Widget endpoint is running
2. Product ID in URL matches database
3. Reviews have `status = 'published'`

**Test:**
```bash
curl http://localhost:5000/widget/demo-shop/reviews/10045740417338/api
```

### Issue: Import script fails

**Check:**
1. Database connection (run `connect_easypanel_db.py`)
2. Shop exists in database (`SELECT * FROM shops;`)
3. AliExpress URL is valid
4. Internet connection for scraping

## ✅ Success Checklist

After completing the workflow, verify:

- [ ] Reviews imported successfully (check count)
- [ ] Reviews saved with correct shopify_product_id
- [ ] All review fields populated (name, rating, body, images)
- [ ] Widget endpoint accessible
- [ ] Reviews display in widget HTML
- [ ] Widget API returns JSON correctly
- [ ] Statistics calculate correctly
- [ ] Images load (if reviews have photos)
- [ ] Verified badges show
- [ ] AI recommended badges show (for high quality reviews)

## 🎯 Next Steps

Once import and display work:

1. **Integrate Widget into Shopify Product Pages:**
   - Add iframe to product template
   - Use widget URL: `/widget/demo-shop/reviews/{product_id}`

2. **Test with Real AliExpress Products:**
   - Try different product URLs
   - Test with various review counts
   - Verify image loading

3. **Scale to Multiple Products:**
   - Import reviews for multiple products
   - Each product has its own widget URL

## 📝 Example Workflow

```bash
# 1. Import reviews
python import_aliexpress_reviews.py
# Enter: https://www.aliexpress.com/item/1005004632823451.html
# Enter: 10045740417338
# Enter: 20

# 2. Verify in database
python verify_reviews_in_db.py 10045740417338

# 3. Start widget server
python widget_endpoint_simple.py

# 4. Open in browser
# http://localhost:5000/widget/demo-shop/reviews/10045740417338

# 5. Or verify via CMD (psql)
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -h 193.203.165.217 -p 5432 -U saksaks -d sakrev_db
# Then run: SELECT * FROM reviews WHERE shopify_product_id = '10045740417338';
```

---

**Ready to import! Start with Step 1! 🚀**

