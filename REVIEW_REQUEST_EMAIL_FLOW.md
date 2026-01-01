# 📧 Review Request Email Flow - Complete Explanation

## 🔄 **How It Works**

### **The Problem You Identified:**

You're absolutely right! Email providers (Gmail, Outlook, Yahoo, etc.) **CANNOT** run JavaScript or complex forms directly in emails. They only support:
- ✅ HTML links
- ✅ Basic HTML/CSS styling
- ✅ Images
- ❌ JavaScript
- ❌ Forms
- ❌ Interactive wizards

### **The Solution:**

**Email → Link → Standalone Review Page → Database**

1. **Customer receives email** (in Gmail/Outlook/Yahoo)
2. **Clicks "Write a Review" button** in email
3. **Redirects to standalone review page** on your server:
   ```
   https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/review/submit?shop_id=1&product_id=123&order_id=456&email=customer@example.com
   ```
4. **Review wizard loads** (full 5-step wizard: rating → photos → text → user info → confirmation)
5. **Customer completes wizard** and submits
6. **Review saved to database** via `/widget/{shop_id}/reviews/{product_id}/submit` endpoint
7. **Success page shown** with discount code (if enabled)

---

## 📋 **Complete Flow Diagram**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Customer Places Order                                     │
│    → Order created in Shopify                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Order Fulfilled (Shipped)                                │
│    → Shopify sends webhook to your app                       │
│    URL: /webhooks/orders/fulfilled                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Your App Receives Webhook                                 │
│    - Checks if email settings enabled                        │
│    - Checks if customer unsubscribed                         │
│    - Creates ReviewRequest record in database                │
│    - Schedules email (default: 7 days after fulfillment)    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Email Sent (After Delay)                                  │
│    - Uses SMTP to send email                                 │
│    - Email contains:                                          │
│      • Product image                                          │
│      • Product name                                           │
│      • "Write a Review" button (link)                        │
│      • Link format:                                           │
│        /review/submit?shop_id=X&product_id=Y&order_id=Z&email=E│
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Customer Opens Email (Gmail/Outlook/Yahoo)                │
│    - Email is plain HTML (no JavaScript)                      │
│    - Customer sees product info and "Write a Review" button   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Customer Clicks "Write a Review" Button                   │
│    - Opens browser                                           │
│    - Navigates to:                                           │
│      https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/│
│      review/submit?shop_id=1&product_id=123&order_id=456&    │
│      email=customer@example.com                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Standalone Review Submission Page Loads                  │
│    Route: /review/submit                                      │
│    Template: templates/review-submit.html                     │
│    Shows:                                                     │
│    - Product info (image, name, order date)                   │
│    - 5-step wizard:                                          │
│      1. Rating (stars)                                        │
│      2. Photos (optional)                                    │
│      3. Review text (optional)                               │
│      4. User info (name, email)                               │
│      5. Success confirmation                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. Customer Completes Wizard                                 │
│    - Selects rating                                          │
│    - Uploads photos (optional)                                │
│    - Writes review text (optional)                           │
│    - Enters name and email                                   │
│    - Clicks "Submit Review"                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. Review Submitted to Server                                │
│    Endpoint: POST /widget/{shop_id}/reviews/{product_id}/submit│
│    - Validates data                                          │
│    - Saves review to database                                │
│    - Saves photos to uploads/reviews/{review_id}/           │
│    - Creates ReviewMedia records                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 10. Success Page Shown                                       │
│     - Shows confirmation message                             │
│     - Displays discount code (if enabled)                    │
│     - Customer can close page                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 11. Review Appears in Widget                                 │
│     - Review is now visible on product page                  │
│     - Shows in widget with rating, photos, text              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 **Technical Implementation**

### **1. Email Template (`templates/email-review-request.html`)**

The email contains:
- **HTML only** (no JavaScript)
- **"Write a Review" button** that's actually a link:
  ```html
  <a href="{{ review_url }}" class="cta-button">Write a Review →</a>
  ```
- **Star rating links** (also just links):
  ```html
  <a href="{{ review_url }}?rating=1" class="star-link">★</a>
  ```

### **2. Review URL Format**

The `review_url` in emails is:
```
https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/review/submit?shop_id={shop_id}&product_id={product_id}&order_id={order_id}&email={customer_email}
```

**Parameters:**
- `shop_id`: Shop's ID in your database
- `product_id`: Shopify product ID
- `order_id`: Order ID (for tracking)
- `email`: Customer email (pre-fills form)

### **3. Standalone Review Page (`/review/submit`)**

- **Route:** `@app.route('/review/submit')`
- **Template:** `templates/review-submit.html`
- **Features:**
  - Full 5-step wizard (rating, photos, text, user info, success)
  - Product info display
  - Photo upload with preview
  - Form validation
  - Submits to existing `/widget/{shop_id}/reviews/{product_id}/submit` endpoint

### **4. Review Submission Endpoint**

- **Route:** `POST /widget/{shop_id}/reviews/{product_id}/submit`
- **Already exists and works!**
- **Handles:**
  - Rating validation
  - Photo uploads
  - Review text
  - User info
  - Saves to database
  - Sends acknowledgment email

---

## ✅ **What's Already Working**

1. ✅ **Review submission endpoint** - Fully functional
2. ✅ **Photo uploads** - Working
. ✅ **Database saving** - Reviews are stored
3. ✅ **Acknowledgment emails** - Sent after review submission

---

## 🔨 **What Needs to Be Done**

### **1. Create Function to Send Review Request Emails**

Currently, webhooks create `ReviewRequest` records but don't actually send emails. We need:

```python
def send_review_request_email(review_request):
    """
    Send review request email to customer
    Called when scheduled_at time is reached
    """
    # Build review URL
    review_url = f"https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/review/submit?shop_id={review_request.shop_id}&product_id={review_request.product_id}&order_id={review_request.order_id}&email={review_request.customer_email}"
    
    # Render email template
    # Send via SMTP
    # Update ReviewRequest status to 'sent'
```

### **2. Create Scheduled Task/Endpoint**

Need a way to process pending `ReviewRequest` records and send emails:

- **Option A:** Cron job / scheduled task
- **Option B:** Background worker (Celery, etc.)
- **Option C:** Endpoint that can be called periodically

### **3. Update Webhook Handlers**

Update `webhook_order_fulfilled` and `webhook_order_create` to:
- Store the correct review URL format in `ReviewRequest` records
- Or generate it when sending the email

---

## 📝 **Current Status**

- ✅ **Standalone review page created** (`/review/submit`)
- ✅ **Review wizard fully functional** (5 steps)
- ✅ **Review submission endpoint works**
- ✅ **Test email uses correct URL format**
- ⚠️ **Email sending function needs to be created**
- ⚠️ **Scheduled email processing needs to be implemented**

---

## 🚀 **Next Steps**

1. Create `send_review_request_email()` function
2. Create scheduled task/endpoint to process pending emails
3. Update webhook handlers to use correct URL format
4. Test end-to-end flow

---

**Last Updated:** December 31, 2025

