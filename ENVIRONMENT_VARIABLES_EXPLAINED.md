# 🔐 Environment Variables & Access Tokens Explained

**Complete guide to understanding ReviewKing's configuration**

---

## 📋 Two Types of Variables

### 1. **App-Level Variables** (Same for ALL Users)
These are your app's credentials and URLs - **the same for every shop that installs your app**.

### 2. **Per-Shop Access Tokens** (Different for EACH Shop)
Each shop gets its own unique access token after OAuth installation.

---

## 🌐 App-Level Variables (Set Once in Easypanel)

These variables are **the same for all users** and should be set in your Easypanel environment:

```bash
# Your App's Credentials (Same for Everyone)
SHOPIFY_API_KEY=3771d40f65cd51699b07191e8df45fe9
SHOPIFY_API_SECRET=8c254b805fef674a9f7b390859a9d742

# Your App's URLs (Same for Everyone)
SHOPIFY_APP_URL=https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host/
SHOPIFY_REDIRECT_URI=https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host/auth/callback
WIDGET_BASE_URL=https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host

# Shared Database (Multi-Tenant - All Shops Use Same DB)
DATABASE_URL=postgresql://saksaks:11!!!!.Magics4321@193.203.165.217:5432/sakrev_db?sslmode=disable
```

### What Each Variable Does:

| Variable | Purpose | Who Uses It |
|----------|---------|-------------|
| `SHOPIFY_API_KEY` | Your app's Client ID (from Shopify Partner Dashboard) | All shops (for OAuth) |
| `SHOPIFY_API_SECRET` | Your app's Client Secret (from Shopify Partner Dashboard) | All shops (for OAuth) |
| `SHOPIFY_APP_URL` | Your app's base URL | All shops (for OAuth redirect) |
| `SHOPIFY_REDIRECT_URI` | OAuth callback URL | All shops (for OAuth) |
| `WIDGET_BASE_URL` | Base URL for widget JavaScript | All shops (for ScriptTag) |
| `DATABASE_URL` | PostgreSQL connection string | All shops (shared database) |

**✅ These NEVER change** - Set them once in Easypanel and they work for all users.

---

## 🔑 Per-Shop Access Tokens (Generated Per Shop)

### How It Works:

1. **Shop installs your app** via OAuth
2. **Shopify generates unique access token** for that shop
3. **Token is stored in database** (`shops.access_token` column)
4. **Token is used** to make API calls for that specific shop

### Example:

```
Shop 1 (mystore.myshopify.com):
  → Gets token: shpat_abc123xyz789...
  → Stored in: shops table, access_token column
  → Used for: API calls to mystore.myshopify.com

Shop 2 (anotherstore.myshopify.com):
  → Gets token: shpat_def456uvw012...
  → Stored in: shops table, access_token column
  → Used for: API calls to anotherstore.myshopify.com
```

### Where Tokens Are Stored:

**Database Table: `shops`**
```sql
CREATE TABLE shops (
    id SERIAL PRIMARY KEY,
    shop_domain VARCHAR(255) UNIQUE,
    access_token TEXT,  -- ← Each shop has its own token here
    shop_name VARCHAR(255),
    plan VARCHAR(50),
    ...
);
```

### How Tokens Are Generated:

**During OAuth Installation:**
1. User visits: `/auth/install?shop=mystore.myshopify.com`
2. Redirected to Shopify OAuth page
3. User authorizes app
4. Shopify redirects to: `/auth/callback?code=...&shop=...`
5. App exchanges `code` for `access_token`
6. Token saved to database via `database_integration.py`

**Code Flow:**
```python
# In app_enhanced.py - /auth/callback route
access_token = token_response.get('access_token')  # From Shopify

# Save to database
db_integration.get_or_create_shop(
    shop_domain=shop,
    access_token=access_token  # ← Saved per shop
)
```

---

## ❓ Common Questions

### Q: Do I need different variables for each new user?

**A: NO!** The app-level variables are the same for everyone. Only the access tokens are different per shop.

### Q: What about `SHOPIFY_ACCESS_TOKEN` in config?

**A:** That's ONLY for testing/development with one test store. For public app:
- Each shop gets its own token via OAuth
- Tokens are stored in database automatically
- You don't need to set `SHOPIFY_ACCESS_TOKEN` in environment

### Q: How many access tokens will I have?

**A:** One per shop that installs your app:
- Shop 1 installs → Token 1 stored in database
- Shop 2 installs → Token 2 stored in database
- Shop 3 installs → Token 3 stored in database
- etc.

### Q: What if a shop uninstalls?

**A:** The `app/uninstalled` webhook fires:
- Token is removed from database (`access_token = None`)
- Shop marked as `status = 'uninstalled'`
- Shop data can be deleted (GDPR compliance)

### Q: Can shops share the same token?

**A: NO!** Each shop must have its own token:
- Tokens are shop-specific
- Tokens have shop-specific permissions
- Sharing tokens would be a security risk

---

## 🔒 Security Notes

### App-Level Variables:
- ✅ Safe to share (they're public in OAuth flow anyway)
- ✅ Same for all users (by design)
- ✅ Stored in Easypanel environment variables

### Per-Shop Access Tokens:
- 🔒 **NEVER expose** in environment variables
- 🔒 **Stored securely** in database
- 🔒 **One per shop** (never shared)
- 🔒 **Removed** when shop uninstalls

---

## 📊 Database Structure

### `shops` Table:
```sql
id | shop_domain              | access_token                    | plan  | ...
---|--------------------------|----------------------------------|-------|----
1  | mystore.myshopify.com    | shpat_abc123xyz789...           | free  | ...
2  | another.myshopify.com    | shpat_def456uvw012...           | basic | ...
3  | third.myshopify.com      | shpat_ghi789rst345...           | pro   | ...
```

**Each row = One shop with its own access token**

---

## ✅ Setup Checklist

### For Your Live Shop (First User):
- [x] App-level variables set in Easypanel
- [x] Database connected
- [x] OAuth flow working
- [ ] Shop installs app → Gets its own token automatically

### For Public App (All Users):
- [x] App-level variables set in Easypanel (same for everyone)
- [x] OAuth flow working (generates tokens automatically)
- [x] Database stores tokens per shop
- [x] No additional setup needed per user!

---

## 🎯 Summary

**App-Level Variables:**
- ✅ Set ONCE in Easypanel
- ✅ Same for ALL users
- ✅ Never change

**Per-Shop Access Tokens:**
- ✅ Generated automatically via OAuth
- ✅ Stored in database per shop
- ✅ Different for each shop
- ✅ No manual setup needed

**For Public App:**
- ✅ Use the SAME environment variables
- ✅ Each shop gets its own token automatically
- ✅ No additional configuration needed!

---

**You're all set!** The same environment variables work for your live shop AND all future users. 🌸

