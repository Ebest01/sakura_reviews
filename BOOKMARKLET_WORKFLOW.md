# 🌸 Bookmarklet Import Workflow - Step by Step

## 📋 Prerequisites

1. ✅ Flask app running (with database integration)
2. ✅ Easypanel PostgreSQL accessible
3. ✅ Demo shop configured in database
4. ✅ Bookmarklet URL ready

## 🚀 Complete Workflow

### Step 1: Start Your App

First, make sure your app is running with database integration:

```bash
# If using app_enhanced_with_db.py:
python app_enhanced_with_db.py

# Or if you need to integrate updated endpoints:
# Make sure updated_import_endpoints.py is integrated
```

### Step 2: Get Bookmarklet URL

The bookmarklet URL should be displayed when you start the app, or get it from:

```
http://localhost:5000/js/bookmarklet.js
```

**Bookmarklet Code:**
```javascript
javascript:(function(){var s=document.createElement('script');s.src='http://localhost:5000/js/bookmarklet.js';document.head.appendChild(s);})();
```

**To use:**
1. Copy the entire code above
2. Create a new bookmark in your browser
3. Paste the code as the URL
4. Name it "🌸 Sakura Reviews"

### Step 3: Go to AliExpress

1. Open **www.aliexpress.com** in your browser
2. Search for any product (e.g., "wireless earbuds")
3. Click on a product to open its page
4. You should see the product page with reviews

### Step 4: Click the Bookmarklet

1. Click your **"🌸 Sakura Reviews"** bookmark in the browser
2. A modal should appear showing:
   - ✅ Product ID detected
   - ✅ Reviews being scraped
   - ✅ Review list with import buttons

### Step 5: Select Your Shopify Product

1. In the modal, you'll see a **"Select Product"** search box
2. Type your Shopify product name (e.g., "Snowboard")
3. Select the product from the dropdown
4. The product ID will be linked (e.g., `10045740417338`)

### Step 6: Import Reviews

**Option A: Import Single Review**
1. Find a review you like
2. Click the **"Import Review"** button on that review
3. You should see a success message: "✓ Review imported successfully!"
4. The review is now saved to Easypanel PostgreSQL database

**Option B: Import Multiple Reviews**
1. Click **"Import All Reviews"** (imports all non-skipped reviews)
2. Or click **"Import with Photos"** (only reviews with images)
3. Wait for the import to complete
4. You'll see: "✅ Imported X reviews!"

### Step 7: Verify in Database (Python)

Open a new terminal and run:

```bash
python verify_reviews_in_db.py 10045740417338
```

Replace `10045740417338` with your actual Shopify product ID.

**You should see:**
- Total reviews count
- List of imported reviews
- Reviewer names, ratings, images
- Statistics (avg rating, verified count, etc.)

### Step 8: Verify in Database (CMD/psql)

Open CMD and run:

```cmd
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -h 193.203.165.217 -p 5432 -U saksaks -d sakrev_db
```

Then run SQL:

```sql
SELECT * FROM reviews WHERE shopify_product_id = '10045740417338';
```

**Check:**
- ✅ `shopify_product_id` matches your product
- ✅ `reviewer_name` is populated
- ✅ `rating` is 1-5
- ✅ `body` has review text
- ✅ `images` contains image URLs (if review has photos)
- ✅ `status = 'published'` and `published = true`
- ✅ `imported_at` timestamp is recent

### Step 9: Test Widget Display

Once reviews are imported, test the widget:

**Option A: Using Widget Endpoint**
```bash
python widget_endpoint_simple.py
```

Then visit:
```
http://localhost:5000/widget/demo-shop/reviews/10045740417338
```

**Option B: API Endpoint**
```
http://localhost:5000/widget/demo-shop/reviews/10045740417338/api
```

**You should see:**
- ✅ Reviews displaying in HTML
- ✅ Ratings showing as stars
- ✅ Images loading (if reviews have photos)
- ✅ Reviewer names and countries
- ✅ Verified badges
- ✅ AI recommended badges (for high quality reviews)

## ✅ Success Checklist

After completing the workflow:

- [ ] Bookmarklet opens modal on AliExpress
- [ ] Reviews are scraped and displayed
- [ ] Shopify product can be searched and selected
- [ ] "Import Review" button works
- [ ] Success message appears after import
- [ ] Reviews appear in database (Python verification)
- [ ] Reviews appear in database (psql verification)
- [ ] Widget shows the imported reviews
- [ ] All review data is complete (name, rating, body, images)

## 🐛 Troubleshooting

### Issue: Bookmarklet doesn't open modal

**Fix:**
- Check if app is running: `http://localhost:5000`
- Check browser console for errors (F12)
- Verify bookmarklet URL is correct
- Try refreshing the AliExpress page and clicking bookmarklet again

### Issue: "Import Review" button does nothing

**Fix:**
- Check browser console for errors (F12)
- Verify app is running
- Check network tab to see if POST request to `/admin/reviews/import/single` is sent
- Verify database connection in app logs

### Issue: Reviews not in database after import

**Check:**
1. App logs for errors
2. Database connection: `python connect_easypanel_db.py`
3. Shop exists: `SELECT * FROM shops;`
4. Import endpoint is using database (not simulation)

### Issue: Widget shows no reviews

**Check:**
1. Product ID matches exactly (it's a STRING, not integer)
2. Reviews have `status = 'published'` and `published = true`
3. Widget endpoint is querying database correctly

## 🎯 Next Steps

Once everything works:

1. **Import reviews for multiple products**
2. **Test widget on different product pages**
3. **Integrate widget into Shopify product template**
4. **Scale up and import more reviews**

---

**Ready? Start with Step 1! 🚀**

