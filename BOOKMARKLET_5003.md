# Bookmarklet URL - Port 5003

## Latest Bookmarklet

```javascript
javascript:(function(){var s=document.createElement('script');s.src='http://localhost:5003/js/bookmarklet.js?v='+Date.now();document.head.appendChild(s);})();
```

**Server running on:** `http://localhost:5003`

---

## What to Look For in Server Logs:

When you import a review, you should see:

1. **First message:**
   ```
   DEBUG: Import request - shopify_product_id=[ID], review_id=[ID], db_integration=True
   ```

2. **Then:**
   ```
   ✅ Review saved to database: [review_id] - Score: [score]
   ```

If you see the old message:
```
Review imported: [ID] - Score: [score]
```
Then database save failed.

---

## Verify in Database:

After importing, check:
```sql
SELECT * FROM reviews WHERE shopify_product_id = '[your_shopify_product_id]'
```

