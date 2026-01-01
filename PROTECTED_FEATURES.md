# 🛡️ PROTECTED FEATURES REGISTRY

## ⚠️ CRITICAL: DO NOT REMOVE OR SIMPLIFY THESE FEATURES ⚠️

This document lists ALL features that were developed with significant effort and MUST be preserved. **Any changes to these features require explicit approval from the project owner.**

---

## 📋 BOOKMARKLET IMPORT FEATURES

### 1. Bulk Import Section Layout
**Status:** ✅ PROTECTED  
**Location:** `app_enhanced.py` - `/js/bookmarklet.js` route (lines ~4215-4250)  
**Last Verified:** 2025-01-XX  
**Why Protected:** User spent hours perfecting this layout. It's a core differentiator.

**Required Elements:**
- ✅ "Bulk Imports:" section label (`font-size: 16px; font-weight: 600; color: #9ca3af;`)
- ✅ 6 bulk import buttons in 2 rows (3 buttons each):
  - Row 1: All Reviews (count), With Photos (count), No Photos (count)
  - Row 2: AI Recommended (count), 4-5 ★ (count), 3 ★ (count)
- ✅ Warning message box about negative reviews
- ✅ Progress loader system (`rk-import-loader` with spinner)
- ✅ All buttons must show dynamic counts: `(${{this.allReviews.length}})`

**DO NOT:**
- ❌ Remove the "Bulk Imports:" label
- ❌ Reduce buttons from 6 to 3
- ❌ Remove the warning message
- ❌ Simplify the progress loader
- ❌ Remove count displays from buttons

---

### 2. Import Methods (JavaScript Functions)
**Status:** ✅ PROTECTED  
**Location:** `app_enhanced.py` - `ReviewKingClient` class (lines ~4465-4900)  
**Last Verified:** 2025-01-XX

**Required Methods:**
- ✅ `importAllReviews()` - Imports all reviews with warning for negative reviews
- ✅ `importWithPhotos()` - Imports only reviews with photos
- ✅ `importWithoutPhotos()` - Imports only reviews without photos
- ✅ `importAIRecommended()` - Imports AI recommended reviews
- ✅ `import45Star()` - Imports 4-5 star reviews
- ✅ `import3Star()` - Imports 3 star reviews

**Helper Methods (REQUIRED):**
- ✅ `showImportLoader(statusText, totalReviews)` - Shows progress loader
- ✅ `hideImportLoader(success, message, details)` - Hides loader with results
- ✅ `updateImportProgress(current, total)` - Updates progress bar
- ✅ `setBulkImportButtonsEnabled(enabled)` - Enables/disables buttons during import

**DO NOT:**
- ❌ Remove any of these 6 import methods
- ❌ Remove helper methods
- ❌ Simplify progress tracking
- ❌ Remove duplicate detection logic

---

### 3. Product Thumbnail in Import Overlay
**Status:** ✅ PROTECTED  
**Location:** `app_enhanced.py` - `selectProduct()` method (lines ~3800-3900)  
**Last Verified:** 2025-01-XX  
**Why Protected:** User specifically requested this feature and it matches v12 design.

**Required Elements:**
- ✅ 50x50px product thumbnail image next to "Target Product Selected"
- ✅ Placeholder icon (📦) if image not available
- ✅ Proper flex layout with `flex-shrink: 0` for image, `flex: 1` for text
- ✅ No border on thumbnail (matches v12 styling)

**DO NOT:**
- ❌ Remove thumbnail display
- ❌ Change thumbnail size
- ❌ Add borders or change styling from v12

---

### 4. Progress Bar and Duplicate Detection
**Status:** ✅ PROTECTED  
**Location:** `app_enhanced.py` - Bulk import endpoints and `database_integration.py`  
**Last Verified:** 2025-01-XX  
**Why Protected:** User spent days implementing this. It's critical for user experience.

**Required Elements:**
- ✅ Visual progress bar during bulk import
- ✅ Status messages showing: "Importing X reviews..."
- ✅ Success message with counts: "✓ Imported: X | ❌ Failed: Y | 🔄 Duplicates: Z"
- ✅ Database-level duplicate detection based on `source_review_id`
- ✅ Duplicate count returned in API response

**DO NOT:**
- ❌ Remove progress bar
- ❌ Remove duplicate detection
- ❌ Remove status messages
- ❌ Simplify error reporting

---

## 📧 EMAIL SYSTEM FEATURES

### 5. Review Request Email System
**Status:** ✅ PROTECTED  
**Location:** `app_enhanced.py` - Email routes and webhooks  
**Last Verified:** 2025-01-XX

**Required Elements:**
- ✅ Standalone review submission page (`/review/submit`)
- ✅ Pre-filled customer name and email from URL parameters
- ✅ Webhook triggers: `orders/create` and `orders/fulfilled`
- ✅ Email settings page with customization options
- ✅ Review acknowledgment emails after submission

**DO NOT:**
- ❌ Remove standalone review page
- ❌ Remove pre-fill functionality
- ❌ Remove webhook integration
- ❌ Simplify email customization

---

## 🎨 UI/UX FEATURES

### 6. Review Widget Layout
**Status:** ✅ PROTECTED  
**Location:** `templates/widget.html`  
**Last Verified:** 2025-01-XX

**Required Elements:**
- ✅ Stars below avatar/user photo and date
- ✅ Rating number inline with stars
- ✅ "Was it helpful?" inline with social media share icons
- ✅ No "Not Helpful" button (thumbs down removed)
- ✅ Compact photo display (no "No photos" placeholder)
- ✅ "Be the first to write a review" clickable link

**DO NOT:**
- ❌ Change review card layout
- ❌ Add back "Not Helpful" button
- ❌ Add bulky placeholders
- ❌ Change star placement

---

### 7. Parent Page Modals
**Status:** ✅ PROTECTED  
**Location:** `app_enhanced.py` - `sakura-reviews.js` ScriptTag  
**Last Verified:** 2025-01-XX  
**Why Protected:** User explicitly requested modals open on parent page, not in iframe.

**Required Elements:**
- ✅ Review submission modal opens on parent Shopify page (not iframe)
- ✅ Photo lightbox opens on parent page
- ✅ Full-page overlay styling
- ✅ `window.postMessage` communication between iframe and parent

**DO NOT:**
- ❌ Move modals back to iframe
- ❌ Remove parent page modal injection
- ❌ Simplify modal styling

---

## 🔍 DATABASE INTEGRATION

### 8. Database Import Methods
**Status:** ✅ PROTECTED  
**Location:** `database_integration.py`  
**Last Verified:** 2025-01-XX  
**Why Protected:** User spent months building this. It's the core of the import system.

**Required Methods:**
- ✅ `import_single_review()` - With duplicate detection
- ✅ `import_reviews_bulk()` - Efficient bulk import with ON CONFLICT
- ✅ Duplicate checking based on `source_review_id`
- ✅ Quality score calculation
- ✅ Sentiment analysis

**DO NOT:**
- ❌ Remove database integration
- ❌ Remove duplicate detection
- ❌ Simplify to "simulation mode"
- ❌ Remove bulk import optimization

---

## 📊 STATISTICS AND FILTERING

### 9. Review Statistics Display
**Status:** ✅ PROTECTED  
**Location:** `app_enhanced.py` - Bookmarklet overlay  
**Last Verified:** 2025-01-XX

**Required Elements:**
- ✅ Stats bar showing: Total Loaded, AI Recommended, With Photos, Avg Quality
- ✅ Dynamic counts that update based on filters
- ✅ Pink gradient background
- ✅ Large, readable numbers

**DO NOT:**
- ❌ Remove stats display
- ❌ Simplify to fewer metrics
- ❌ Remove dynamic updates

---

### 10. Filter and Sort System
**Status:** ✅ PROTECTED  
**Location:** `app_enhanced.py` - `get_product_reviews()` and client-side filtering  
**Last Verified:** 2025-01-XX

**Required Elements:**
- ✅ Default filter: "AI Recommended" with smart fallback
- ✅ Smart sorting: AI Recommended → Text → Photos → Rating → Quality
- ✅ Filter buttons: All, With Photos, AI Recommended, 4-5★, 3★
- ✅ Country filter dropdown
- ✅ Translation toggle

**DO NOT:**
- ❌ Change default filter
- ❌ Remove smart sorting logic
- ❌ Simplify filter options
- ❌ Remove country/translation features

---

## 🚨 PROTECTION MECHANISMS

### Before Making ANY Changes:

1. **Check This File First** - Read `PROTECTED_FEATURES.md` before modifying code
2. **Verify Feature Exists** - Use `grep` to find feature locations
3. **Test After Changes** - Ensure protected features still work
4. **Document Changes** - Update this file if adding new protected features
5. **Get Approval** - For major changes, get explicit approval

### Git Protection:

```bash
# Before committing, run:
grep -r "Bulk Imports:" app_enhanced.py
grep -r "importAIRecommended\|import45Star\|import3Star" app_enhanced.py
grep -r "rk-import-loader" app_enhanced.py
```

### Automated Checks:

- [ ] All 6 bulk import buttons present
- [ ] "Bulk Imports:" label exists
- [ ] Warning message present
- [ ] Progress loader system functional
- [ ] Product thumbnail displays
- [ ] Duplicate detection works
- [ ] Database integration active (not simulation mode)

---

## 📝 ADDING NEW PROTECTED FEATURES

When you develop a new feature that should be protected:

1. Add it to this file with:
   - Feature name and description
   - File location and line numbers
   - Required elements
   - "DO NOT" list
   - Why it's protected

2. Update the checklist above

3. Commit with message: `"Feature: Add [feature] to PROTECTED_FEATURES.md"`

---

## ⚠️ VIOLATION REPORTING

If you notice a protected feature has been removed or simplified:

1. **IMMEDIATELY** restore it from git history or v12 backup
2. Update this file with the violation
3. Add a comment in code: `# PROTECTED: Do not remove - See PROTECTED_FEATURES.md`
4. Notify the project owner

---

**Last Updated:** 2025-01-XX  
**Maintained By:** Project Owner  
**Review Frequency:** Before every major refactor

