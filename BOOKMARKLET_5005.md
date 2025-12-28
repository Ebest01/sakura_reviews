# Bookmarklet - Port 5005 (Database Fix Applied)

## Fresh Bookmarklet URL

```javascript
javascript:(function(){var s=document.createElement('script');s.src='http://localhost:5005/js/bookmarklet.js?v='+Date.now();document.head.appendChild(s);})();
```

**Server:** `http://localhost:5005`

---

## Database Fix Applied:

✅ **Fixed SQLAlchemy instance issue** - Now using single `models_v2.db` instance
✅ **Database integration should now work!**

---

## What to Expect:

When you import a review, you should see in server logs:

✅ **Success:**
```
DEBUG: Import request - shopify_product_id=[ID], review_id=[ID], db_integration=True
✅ Review saved to database: [review_id] - Score: [score]
```

❌ **Old Error (should be fixed now):**
```
❌ Database import error: The current Flask app is not registered...
```

---

## Test Now:

1. Update bookmarklet with port 5005
2. Import a review
3. Check server logs for "✅ Review saved to database"
4. Verify in database: `SELECT * FROM reviews WHERE shopify_product_id = '10045740417338'`

