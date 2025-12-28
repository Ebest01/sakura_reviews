# 🌸 Install ReviewKing on Your Live Shopify Shop - Complete Guide

**Step-by-step guide to install and use ReviewKing on your live Shopify store**

---

## 📋 Prerequisites

Before starting, make sure you have:
- ✅ Your live Shopify store admin access
- ✅ Shopify Partner account (for app management)
- ✅ ReviewKing app deployed (already done ✅)
- ✅ Access to Easypanel dashboard (for environment variables)

---

## 🚀 PART 1: Install ReviewKing on Your Live Shop

### Step 1: Verify App Configuration

1. **Check your app is running:**
   - Visit: https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host/
   - You should see the ReviewKing homepage

2. **Verify environment variables in Easypanel:**
   - Go to your Easypanel service dashboard
   - Check these variables are set:
     ```
     SHOPIFY_API_KEY=3771d40f65cd51699b07191e8df45fe9
     SHOPIFY_API_SECRET=8c254b805fef674a9f7b390859a9d742
     SHOPIFY_APP_URL=https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host/
     SHOPIFY_REDIRECT_URI=https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host/auth/callback
     WIDGET_BASE_URL=https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host
     DATABASE_URL=postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable
     ```

   **⚠️ IMPORTANT: Understanding Variables & Access Tokens**
   
   **App-Level Variables (Same for ALL users):**
   - `SHOPIFY_API_KEY` - Your app's Client ID (same for everyone)
   - `SHOPIFY_API_SECRET` - Your app's Client Secret (same for everyone)
   - `SHOPIFY_APP_URL` - Your app's base URL (same for everyone)
   - `SHOPIFY_REDIRECT_URI` - OAuth callback URL (same for everyone)
   - `WIDGET_BASE_URL` - Widget base URL (same for everyone)
   - `DATABASE_URL` - Shared database (multi-tenant, all shops use same DB)
   
   **These are NOT test-shop-specific!** These are your app's credentials that work for:
   - ✅ Your test shop (`sakura-rev-test-store.myshopify.com`)
   - ✅ Your live shop (any shop you install on)
   - ✅ All future users (every shop that installs your app)
   
   **Per-Shop Access Tokens (Different for EACH shop):**
   - Each shop that installs your app gets its OWN unique access token
   - Generated automatically during OAuth installation
   - Stored in database: `shops.access_token` column (one per shop)
   - Used to make API calls on behalf of that specific shop
   
   **Note:** 
   - The `SHOPIFY_ACCESS_TOKEN` in `config.json` was ONLY for your test shop (`sakura-rev-test-store.myshopify.com`)
   - For your live shop and all future users, access tokens are generated automatically via OAuth
   - You don't need to change any environment variables - they work for everyone!
   
   **See `TEST_SHOP_VS_PRODUCTION.md` for complete explanation.**

### Step 2: Install via OAuth (Recommended Method)

**Option A: Direct Installation URL**

1. **Get your shop domain:**
   - Go to your Shopify admin
   - Your shop domain is: `your-shop-name.myshopify.com`

2. **Visit the installation URL:**
   ```
   https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host/auth/install?shop=your-shop-name.myshopify.com
   ```
   Replace `your-shop-name` with your actual shop name.
   
   **Example for your shop:**
   ```
   https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host/auth/install?shop=4a6f68-2.myshopify.com
   ```
   
   **⚠️ If you get 404:** The route exists in code but may need redeployment. See `DEPLOYMENT_FIX_AUTH_ROUTE.md` for fix.

3. **Authorize the app:**
   - You'll be redirected to Shopify
   - Review the permissions requested
   - Click "Install app" or "Allow"

4. **Complete installation:**
   - You'll be redirected back to ReviewKing
   - The app will automatically:
     - Save your shop to the database
     - Create a ScriptTag for automatic widget injection
     - Set up your shop settings

**Option B: Create Custom App (For Testing)**

If you want to test first with a custom app:

1. **Go to Shopify Admin:**
   - Settings → Apps and sales channels → Develop apps

2. **Create custom app:**
   - Click "Create an app"
   - Name: "ReviewKing Test"
   - Click "Create app"

3. **Configure API scopes:**
   - Go to "Configuration" tab
   - Under "Admin API integration scopes", enable:
     - ✅ `read_products`
     - ✅ `write_products`
     - ✅ `read_content`
     - ✅ `write_content`
     - ✅ `write_script_tags`

4. **Install the app:**
   - Click "Install app"
   - Copy the access token (you'll need this for testing)

5. **Test the connection:**
   - Use the access token to test API calls
   - Or use the OAuth flow for full integration

### Step 3: Verify Installation

1. **Check database:**
   - Your shop should be saved in the `shops` table
   - Access token stored securely

2. **Check ScriptTag:**
   - Go to: Settings → Apps and sales channels → Installed apps
   - Find "Sakura Reviews" or "ReviewKing"
   - The ScriptTag should be automatically created

3. **Test widget:**
   - Visit any product page on your store
   - The review widget should appear automatically
   - If not, check browser console for errors

---

## 📥 PART 2: Import Your First Reviews

### Step 1: Get the Bookmarklet

1. **Copy this bookmarklet code:**
   ```javascript
   javascript:(function(){var s=document.createElement('script');s.src='https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host/js/bookmarklet.js';document.head.appendChild(s);})();
   ```

2. **Add to browser bookmarks:**
   - Create a new bookmark
   - Name: "ReviewKing Import"
   - URL: Paste the code above
   - Save

### Step 2: Import Reviews from AliExpress

1. **Go to AliExpress:**
   - Find a product you sell (or similar)
   - Open the product page
   - Example: `https://www.aliexpress.com/item/1005005914201208.html`

2. **Click the bookmarklet:**
   - Click your "ReviewKing Import" bookmark
   - The ReviewKing overlay will appear

3. **Select reviews:**
   - Use filters (Stars, Photos, Country, AI Recommended)
   - Click "Import" on reviews you want
   - Or use "Bulk Import" for multiple reviews

4. **Link to Shopify product:**
   - A product search will appear
   - Search for your Shopify product
   - Select the product to link reviews

5. **Verify import:**
   - Reviews are saved to database
   - Widget will show reviews on product page

### Step 3: View Reviews on Your Store

1. **Check product page:**
   - Visit the product page where you imported reviews
   - The review widget should display automatically

2. **Widget URL format:**
   ```
   https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host/widget/{shop_id}/reviews/{product_id}
   ```

3. **Verify in database:**
   - Reviews are stored in `reviews` table
   - Images in `review_media` table
   - Products in `products` table

---

## 🔄 PART 3: Replace Loox with ReviewKing

### Step 1: Backup Current Loox Data (Optional)

If you want to keep your existing Loox reviews:

1. **Export Loox reviews:**
   - Go to Loox dashboard
   - Export reviews if possible
   - Save product-review mappings

2. **Note your current setup:**
   - Which products have Loox reviews
   - Review counts per product
   - Any custom configurations

### Step 2: Remove Loox ScriptTag

1. **Go to Shopify Admin:**
   - Settings → Apps and sales channels → Installed apps
   - Find "Loox"
   - Click "Uninstall" or "Remove"

2. **Or manually remove ScriptTag:**
   - Settings → Online Store → Themes
   - Click "Actions" → "Edit code"
   - Look for Loox script in `theme.liquid`
   - Remove Loox JavaScript code

3. **Check ScriptTags via API:**
   ```bash
   # List all ScriptTags
   curl -X GET "https://your-shop.myshopify.com/admin/api/2025-10/script_tags.json" \
     -H "X-Shopify-Access-Token: YOUR_ACCESS_TOKEN"
   ```

### Step 3: Install ReviewKing ScriptTag

**Automatic (Recommended):**
- ReviewKing automatically creates ScriptTag on installation
- No manual work needed!

**Manual (If needed):**
1. **Create ScriptTag via API:**
   ```bash
   curl -X POST "https://your-shop.myshopify.com/admin/api/2025-10/script_tags.json" \
     -H "X-Shopify-Access-Token: YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "script_tag": {
         "event": "onload",
         "src": "https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host/js/sakura-reviews.js"
       }
     }'
   ```

2. **Or use ReviewKing endpoint:**
   ```bash
   curl -X POST "https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host/shopify/scripttag/create" \
     -H "Content-Type: application/json" \
     -d '{
       "shop_domain": "your-shop.myshopify.com",
       "access_token": "YOUR_ACCESS_TOKEN"
     }'
   ```

### Step 4: Import Reviews to Match Loox Products

1. **For each product with Loox reviews:**
   - Find the source product on AliExpress
   - Use bookmarklet to import reviews
   - Link to your Shopify product
   - Import same or better reviews

2. **Bulk import option:**
   - Use "Bulk Import" feature
   - Select multiple reviews at once
   - Faster than Loox's one-by-one

3. **Verify widget appears:**
   - Check product pages
   - ReviewKing widget should show
   - Loox widget should be gone

### Step 5: Update Theme (If Needed)

**If widget doesn't appear automatically:**

1. **Check theme compatibility:**
   - ReviewKing works with most themes
   - ScriptTag auto-injects on product pages

2. **Manual theme integration (if needed):**
   - Go to: Settings → Online Store → Themes
   - Click "Actions" → "Edit code"
   - Open `product.liquid` or `product-template.liquid`
   - Add widget iframe:
     ```liquid
     <div id="sakura-reviews-widget">
       <iframe 
         src="https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host/widget/{{ shop.id }}/reviews/{{ product.id }}"
         width="100%" 
         height="600"
         frameborder="0"
         style="border: none;">
       </iframe>
     </div>
     ```

### Step 6: Test Everything

1. **Test on multiple products:**
   - Check products with reviews
   - Verify widget displays correctly
   - Check mobile responsiveness

2. **Test review import:**
   - Import new reviews
   - Verify they appear on product page
   - Check images load correctly

3. **Test filters:**
   - Star ratings
   - Photo reviews
   - Country filters
   - AI recommendations

---

## ✅ PART 4: Verification Checklist

### Installation Verification
- [ ] App installed via OAuth
- [ ] Shop saved in database
- [ ] ScriptTag created automatically
- [ ] Access token stored securely

### Review Import Verification
- [ ] Bookmarklet works on AliExpress
- [ ] Reviews import successfully
- [ ] Reviews linked to correct products
- [ ] Images imported correctly

### Widget Display Verification
- [ ] Widget appears on product pages
- [ ] Reviews display correctly
- [ ] Images show in grid
- [ ] Mobile responsive
- [ ] No console errors

### Loox Replacement Verification
- [ ] Loox uninstalled/removed
- [ ] Loox ScriptTag removed
- [ ] ReviewKing widget shows
- [ ] All products have reviews
- [ ] No conflicts between apps

---

## 🐛 Troubleshooting

### Widget Not Appearing

**Problem:** Widget doesn't show on product pages

**Solutions:**
1. Check ScriptTag is created:
   ```bash
   # List ScriptTags
   curl -X GET "https://your-shop.myshopify.com/admin/api/2025-10/script_tags.json" \
     -H "X-Shopify-Access-Token: YOUR_TOKEN"
   ```

2. Check browser console for errors (F12)

3. Verify widget URL is accessible:
   ```
   https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host/widget/{shop_id}/reviews/{product_id}
   ```

4. Check database has reviews for that product

### OAuth Installation Fails

**Problem:** Can't install app via OAuth

**Solutions:**
1. Verify app URLs in Shopify Partner Dashboard match Easypanel URL
2. Check redirect URI is correct
3. Ensure scopes are properly configured
4. Check app is not already installed

### Reviews Not Importing

**Problem:** Reviews don't save to database

**Solutions:**
1. Check database connection:
   ```bash
   # Test connection
   python connect_easypanel_db.py
   ```

2. Verify shop exists in database
3. Check product mapping is correct
4. Review server logs for errors

### Images Not Displaying

**Problem:** Review images don't show

**Solutions:**
1. Check `review_media` table has images
2. Verify image URLs are accessible
3. Check CORS settings
4. Verify image URLs are HTTPS

---

## 📞 Support

If you encounter issues:

1. **Check logs:**
   - Easypanel service logs
   - Browser console (F12)
   - Database connection logs

2. **Verify configuration:**
   - Environment variables
   - Shopify app settings
   - Database connection

3. **Test endpoints:**
   - Health check: `/health`
   - Widget test: `/widget-test`
   - Routes: `/debug/routes`

---

## 🎉 Success!

Once everything is working:

✅ **ReviewKing is installed**  
✅ **Reviews are importing**  
✅ **Widget is displaying**  
✅ **Loox is replaced**  

**Your store now has superior review functionality with:**
- Multi-platform support (not just AliExpress)
- AI quality scoring
- Bulk import capabilities
- Better pricing
- Modern UI

---

**Next Steps:**
- Import reviews for all your products
- Customize widget appearance (if needed)
- Set up subscription plans
- Prepare for Shopify App Store submission

---

*For App Store submission guide, see: `SHOPIFY_APP_STORE_GUIDE.md`*

