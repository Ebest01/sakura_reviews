# 📧 Email Settings Page - User Flow & Explanation

## 👥 **Who Accesses This Page?**

**Shopify Store Owners/Admins** - The merchants who have installed your Sakura Reviews app on their Shopify store.

---

## 🚀 **How Do They Access This Page?**

### **Method 1: Through Shopify Admin (Embedded App)**

1. **Store owner logs into Shopify Admin:**
   - Goes to: `https://their-store.myshopify.com/admin`

2. **Opens the Sakura Reviews app:**
   - Navigates to: **Apps** → **Sakura Reviews**
   - OR clicks on the app from the Shopify admin sidebar

3. **Shopify redirects to your app:**
   - URL: `https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/app/email-settings?shop=their-store.myshopify.com`
   - The `?shop=` parameter is automatically added by Shopify

4. **Your app verifies the shop:**
   - Checks if the shop exists in your database
   - Loads email settings for that shop
   - Displays the email settings page

### **Method 2: Direct URL (For Testing/Development)**

- Direct access: `https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/app/email-settings?shop=their-store.myshopify.com`
- Must include the `?shop=` parameter

---

## 🔄 **Complete Flow Diagram**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Store Owner in Shopify Admin                              │
│    - Opens "Apps" → "Sakura Reviews"                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Shopify Redirects                                        │
│    URL: /app/email-settings?shop=store.myshopify.com       │
│    (Shopify automatically adds ?shop= parameter)              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Your App (app_enhanced.py)                               │
│    - Receives request with shop parameter                   │
│    - Queries database: Shop.query.filter_by(shop_domain=...)│
│    - Gets or creates EmailSettings for that shop            │
│    - Loads email stats (sent, pending, conversion rate)     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Renders Email Settings Page                               │
│    Template: templates/app-email-settings.html                │
│    Shows:                                                     │
│    - Email stats (sent, pending, reviews received)           │
│    - Enable/disable toggle                                   │
│    - Timing settings (delay days, send time)                  │
│    - Reminder settings                                       │
│    - Discount/incentive settings                              │
│    - Email content (subject, from name)                       │
│    - Test email form                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Store Owner Configures Settings                           │
│    - Toggles email on/off                                    │
│    - Sets delay days (e.g., 7 days after order)              │
│    - Sets send time (e.g., 10:00 AM)                         │
│    - Configures discounts                                    │
│    - Customizes email subject                                │
│    - Clicks "Save Settings"                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Settings Saved to Database                                │
│    Table: email_settings                                     │
│    Columns: enabled, delay_days, send_time, etc.             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Store Owner Tests Email                                   │
│    - Enters their email address                              │
│    - Clicks "Send Test"                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. Test Email Endpoint (/app/email-test)                     │
│    - Gets shop from form parameter                           │
│    - Gets a sample product from database                     │
│    - Uses product.image_url (NOT shopify_product_image)      │
│    - Renders email template                                  │
│    - Sends via SMTP                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🖼️ **Where Does `product_image` Come From?**

### **The Error Explained:**

The error `'Product' object has no attribute 'shopify_product_image'` happened because:

1. **Wrong attribute name:** The code tried to access `product.shopify_product_image`
2. **Correct attribute:** The Product model uses `image_url` (not `shopify_product_image`)

### **Product Model Structure:**

```python
class Product(db.Model):
    # ... other fields ...
    shopify_product_id = db.Column(db.String(255))
    shopify_product_title = db.Column(db.String(500))
    image_url = db.Column(db.Text)  # ← This is the correct field!
    # ... other fields ...
```

### **Where `image_url` Comes From:**

1. **When products are imported from Shopify:**
   - Your app fetches products via Shopify API
   - Gets the product's featured image URL
   - Stores it in `Product.image_url`

2. **When products are imported from other platforms:**
   - AliExpress, Amazon, eBay, etc.
   - Image URL from the source platform
   - Stored in `Product.image_url`

3. **For test emails:**
   - If no product exists: Uses placeholder image (`https://via.placeholder.com/100`)
   - If product exists: Uses `product.image_url` or falls back to placeholder

---

## 📧 **Email Sending Flow (After Configuration)**

```
┌─────────────────────────────────────────────────────────────┐
│ Customer Places Order                                       │
│ → Order created in Shopify                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Order Fulfilled (Shipped)                                   │
│ → Shopify sends webhook to your app                         │
│   URL: /webhooks/orders/fulfilled                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Your App Receives Webhook                                   │
│ - Checks if email settings are enabled                       │
│ - Checks if customer is unsubscribed                         │
│ - Creates ReviewRequest record in database                   │
│ - Schedules email based on delay_days setting                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Scheduled Email Sent                                        │
│ - After delay_days (e.g., 7 days)                           │
│ - At send_time (e.g., 10:00 AM)                             │
│ - Uses product.image_url for product image in email          │
│ - Includes discount code if enabled                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 **Fixed Issues:**

1. ✅ **Fixed `shopify_product_image` error:**
   - Changed to use `product.image_url` (correct field name)
   - Added fallback to placeholder if no image exists

2. ✅ **Added error message display:**
   - Template now shows red error messages if email sending fails
   - Better error handling for SMTP issues

3. ✅ **Added shop parameter to test form:**
   - Hidden input field ensures shop is passed correctly

---

## 📝 **Key Points:**

- **Who:** Shopify store owners/admins
- **How:** Through Shopify Admin → Apps → Sakura Reviews
- **Product Image:** Comes from `Product.image_url` field in database
- **Image Source:** Set when products are imported from Shopify or other platforms
- **Test Email:** Uses real product data if available, otherwise placeholder

---

**Last Updated:** December 31, 2025

