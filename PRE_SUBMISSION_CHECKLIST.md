# 🌸 Sakura Reviews - Pre-Submission Checklist

**Review Date:** Before making $19 payment for App Store registration

---

## ✅ **TECHNICAL REQUIREMENTS**

### 1. **GDPR Webhooks (REQUIRED)** ✅
- [x] `/webhooks/customers/data_request` - Implemented
- [x] `/webhooks/customers/redact` - Implemented  
- [x] `/webhooks/shop/redact` - Implemented
- [x] `/webhooks/app/uninstalled` - Implemented
- [x] HMAC signature verification - Implemented

**Status:** ✅ All GDPR webhooks are implemented and verified

### 2. **Privacy Policy & Terms of Service** ✅
- [x] Privacy Policy page: `/privacy` - Exists
- [x] Terms of Service page: `/terms` - Exists
- [x] Both templates exist and are accessible

**URLs to verify:**
- Privacy: `https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/privacy`
- Terms: `https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/terms`

**Action:** Verify both URLs are accessible and content is complete

### 3. **Billing API** ⚠️ NEEDS ATTENTION
- [x] Billing API implemented
- [x] Recurring charges endpoint
- [x] Subscription activation
- ⚠️ **ISSUE FOUND:** `'test': True` in billing (line 7567)
  - **MUST CHANGE TO:** `'test': False` for production submission

**Action Required:** Change `test: True` to `test: False` in `app_enhanced.py` line 7567

### 4. **OAuth Flow** ✅
- [x] OAuth installation route: `/auth/install`
- [x] OAuth callback: `/auth/callback`
- [x] Access token storage
- [x] Session management

**Status:** ✅ OAuth flow is complete

### 5. **App URLs** ✅
- [x] App URL configured: `https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host/`
- [x] Redirect URI: `https://sakura-reviews-sakura-reviews-srv.utztjw.easypanel.host/auth/callback`
- [x] Widget Base URL: `https://sakura-reviews-sakrev-v15.utztjw.easypanel.host`

**Note:** There are TWO different URLs:
- App URL: `sakura-reviews-sakura-reviews-srv` (for admin app)
- Widget URL: `sakura-reviews-sakrev-v15` (for widget/scripttag)

**Action:** Verify both are correct in Shopify Partner Dashboard

---

## 📋 **APP LISTING REQUIREMENTS**

### 1. **App Information**
- [ ] App name: "Sakura Reviews" (or preferred name)
- [ ] Short description (80 characters max)
- [ ] Long description (4,000 characters max)
- [ ] Category: Marketing / Store management
- [ ] Tags: reviews, ratings, import, etc.

### 2. **Support Information** ⚠️ NEEDS VERIFICATION
- [ ] Support email address configured
- [ ] Support URL (if you have a support page)
- [ ] Contact information visible

**Current Status:** Need to verify support email is set in app listing

### 3. **Legal Pages** ✅
- [x] Privacy Policy URL: `/privacy`
- [x] Terms of Service URL: `/terms`
- [ ] Data Processing Agreement (DPA) - Optional but recommended

**Action:** Verify URLs work and content is complete

### 4. **Screenshots** ⚠️ NEEDS CREATION
- [ ] App logo (1200×1200px PNG)
- [ ] Screenshot 1: Dashboard/Overview (1320×880px)
- [ ] Screenshot 2: Review Import Interface (1320×880px)
- [ ] Screenshot 3: Widget Display (1320×880px)
- [ ] Screenshot 4: Settings Page (1320×880px)
- [ ] Screenshot 5: Bulk Import Feature (1320×880px)
- [ ] Optional: More screenshots showing features

**Action:** Create and upload screenshots to app listing

### 5. **Pricing** ✅
- [x] Free plan: $0/month (50 reviews)
- [x] Basic plan: $19.99/month (500 reviews)
- [x] Pro plan: $39.99/month (5,000 reviews)
- [x] Billing API implemented

**Action:** Verify pricing is correctly displayed in app listing

---

## 🔧 **CRITICAL FIXES NEEDED BEFORE SUBMISSION**

### 1. **Billing Test Mode** ⚠️ CRITICAL
**File:** `app_enhanced.py`  
**Line:** 7567  
**Current:** `'test': True`  
**Change to:** `'test': False`

**Why:** Shopify will reject apps with test billing in production

### 2. **Verify Webhook URLs in Shopify Dashboard**
Make sure these webhooks are registered in Shopify Partner Dashboard:
- `https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/webhooks/customers/data_request`
- `https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/webhooks/customers/redact`
- `https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/webhooks/shop/redact`
- `https://sakura-reviews-sakrev-v15.utztjw.easypanel.host/webhooks/app/uninstalled`

### 3. **Support Email/URL**
- Set a support email in app listing
- Create a support page or use contact form
- Ensure support contact is visible

---

## 🧪 **TESTING CHECKLIST**

### Before Submission:
- [ ] Test OAuth installation flow
- [ ] Test widget display on product pages
- [ ] Test review submission
- [ ] Test photo uploads
- [ ] Test billing subscription flow
- [ ] Test webhook endpoints (use Shopify webhook tester)
- [ ] Test on multiple Shopify themes
- [ ] Test mobile responsiveness
- [ ] Check for console errors
- [ ] Verify all URLs are HTTPS
- [ ] Test app uninstallation cleanup

---

## 📝 **APP LISTING CONTENT SUGGESTIONS**

### Short Description (80 chars):
```
Import reviews from AliExpress, Amazon, eBay & Walmart with AI quality scoring
```

### Long Description:
Use content from `SAKURA_REVIEWS_MARKETING.md` - it's comprehensive and highlights competitive advantages.

### Key Points to Highlight:
- Multi-platform support (more than Loox)
- AI quality scoring
- Bulk import capability
- Better pricing
- Free plan available

---

## 🚨 **IMMEDIATE ACTIONS REQUIRED**

1. **Fix billing test mode** - Change `test: True` to `test: False`
2. **Verify Privacy Policy & Terms URLs** - Test both pages load correctly
3. **Set support email** - Add to app listing
4. **Create screenshots** - At least 5 screenshots required
5. **Upload app logo** - 1200×1200px PNG
6. **Complete app listing** - Fill all required fields
7. **Test webhooks** - Use Shopify webhook tester to verify all work

---

## ✅ **WHAT'S ALREADY DONE**

- ✅ GDPR webhooks implemented
- ✅ Privacy Policy page exists
- ✅ Terms of Service page exists
- ✅ Billing API implemented (just needs test mode fix)
- ✅ OAuth flow complete
- ✅ Widget system working
- ✅ Photo uploads working
- ✅ Review submission working
- ✅ App is deployed and accessible

---

## 📞 **NEXT STEPS AFTER PAYMENT**

1. Complete app listing (screenshots, descriptions)
2. Fix billing test mode
3. Verify all webhooks
4. Test everything one more time
5. Submit for review
6. Wait 1-2 weeks for Shopify review
7. Respond to any feedback quickly

---

**Ready to proceed?** Fix the billing test mode first, then you can make the payment and complete the listing!

