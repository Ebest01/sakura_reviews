# Bookmarklet - Port 5004 (FRESH)

## Latest Bookmarklet URL

```javascript
javascript:(function(){var s=document.createElement('script');s.src='http://localhost:5004/js/bookmarklet.js?v='+Date.now();document.head.appendChild(s);})();
```

**Server:** `http://localhost:5004`

---

## What Should Work Now:

✅ **`/item/` pages** - Should detect product from:
- URL pattern (`/item/123456.html`)
- window.runParams
- Meta tags

✅ **`/ssr/` pages** - Should:
- Detect SSR page
- Set up product click listener
- Add "Get Reviews" button when product clicked

---

## Test Steps:

1. **Hard refresh browser** (Ctrl+Shift+R)
2. **Update bookmarklet** with new URL above
3. **Test on `/item/` page** - Should detect product
4. **Test on `/ssr/` page** - Click product, button should appear

---

**Server is running on port 5004 with all fixes!**

