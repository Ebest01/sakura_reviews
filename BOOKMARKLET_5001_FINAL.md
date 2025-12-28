# 🌸 Bookmarklet URL - Port 5001 (Final)

## Latest Bookmarklet (with cache-busting)

**Copy this:**
```javascript
javascript:(function(){var s=document.createElement('script');s.src='http://localhost:5001/js/bookmarklet.js?v='+Date.now();document.head.appendChild(s);})();
```

---

## Start App

**Run the main app:**
```bash
python app_enhanced.py
```

The app will:
- ✅ Run on port **5001** (to avoid cache issues)
- ✅ Display the bookmarklet URL when it starts
- ✅ Support `/js/bookmarklet.js` endpoint
- ✅ Include cache-busting (`?v='+Date.now()`)

---

## Add to Browser

1. **Copy the bookmarklet code above**
2. **Right-click bookmarks bar** → "Add page"
3. **Name:** `🌸 Sakura Reviews`
4. **URL:** Paste the code
5. **Save**

---

## Usage

1. **Start app:** `python app_enhanced.py`
2. **Go to AliExpress:** www.aliexpress.com
3. **Open product page**
4. **Click bookmarklet:** 🌸 Sakura Reviews
5. **Select Shopify product** → **Import reviews!**

---

**✅ This bookmarklet uses cache-busting, so it always loads fresh code!**

