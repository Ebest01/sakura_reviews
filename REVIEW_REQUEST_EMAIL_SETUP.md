# 📧 Review Request Email Setup Guide

## ✅ **Current System**

Your app currently has review request emails set up to trigger when orders are **fulfilled** (shipped). This is the standard approach - asking for reviews after customers receive their products.

---

## 🔄 **How It Currently Works**

### **Webhook: `orders/fulfilled`**

1. **Customer places order** → Order is created
2. **Order is fulfilled** (shipped) → Shopify sends webhook
3. **Your app receives webhook** → Schedules review request email
4. **Email sent after delay** (default: 7 days after fulfillment)

**Webhook URL:**
```
https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/webhooks/orders/fulfilled
```

---

## ⚙️ **Setup Required in Shopify**

### **Step 1: Register the Webhook**

1. **Go to Shopify Admin:**
   - Settings → Notifications → Webhooks
   - OR: Apps → Your App → Webhooks

2. **Create New Webhook:**
   - **Event:** `Order fulfillment`
   - **Format:** JSON
   - **URL:** `https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/webhooks/orders/fulfilled`

3. **Save the webhook**

### **Step 2: Configure Email Settings**

1. **Go to your app admin:**
   - Visit: `https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/app/email-settings?shop=your-store.myshopify.com`

2. **Configure settings:**
   - ✅ Enable Review Request Emails
   - Set delay (default: 7 days after fulfillment)
   - Set send time (default: 10:00 AM)
   - Customize email subject and content
   - Add discount codes (optional)

---

## 🎯 **Alternative: Send at Checkout (Order Created)**

If you want to send review requests **immediately after checkout** (instead of after fulfillment), you can use the `orders/create` webhook.

### **Option 1: Use Order Created Webhook**

**Webhook URL:**
```
https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/webhooks/orders/create
```

**When it triggers:**
- Immediately when customer completes checkout
- Before order is fulfilled/shipped

**Pros:**
- Faster review collection
- Customer is still engaged

**Cons:**
- Customer hasn't received product yet
- May get reviews before product experience

### **Option 2: Use Order Paid Webhook**

**Webhook URL:**
```
https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/webhooks/orders/paid
```

**When it triggers:**
- When payment is confirmed
- After checkout, before fulfillment

---

## 📋 **Recommended Setup**

**Best Practice (Like Loox/Amazon):**
1. **Order Fulfilled** → Wait 7-14 days → Send review request
   - Customer has received product
   - Has time to use/test product
   - More authentic reviews

**Alternative (Faster Reviews):**
1. **Order Paid** → Wait 3-7 days → Send review request
   - Faster review collection
   - Good for digital products or fast shipping

---

## 🔧 **Current Implementation**

Your app currently supports:
- ✅ `orders/fulfilled` webhook (implemented)
- ⚠️ `orders/create` webhook (needs to be added)
- ⚠️ `orders/paid` webhook (needs to be added)

---

## 🚀 **To Add Checkout/Order Created Support**

I can add support for `orders/create` webhook if you want to send emails at checkout. Would you like me to:

1. **Add `orders/create` webhook handler** (send at checkout)
2. **Add `orders/paid` webhook handler** (send after payment)
3. **Keep current `orders/fulfilled`** (send after shipping)

Or use all three with different delays?

---

## 📝 **Email Settings Configuration**

Current settings available:
- **Delay Days:** How many days after fulfillment to send (default: 7)
- **Send Time:** What time of day to send (default: 10:00 AM)
- **Reminders:** Send follow-up if no review (default: 14 days later)
- **Discount Codes:** Optional discount for reviews
- **Photo Discount:** Extra discount for photo reviews

---

**Last Updated:** December 2025  
**Status:** `orders/fulfilled` implemented - Ready to configure

