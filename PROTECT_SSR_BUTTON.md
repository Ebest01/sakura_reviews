# 🚨 PROTECT SSR BUTTON CODE 🚨

## ⚠️ CRITICAL: DO NOT REMOVE SSR BUTTON CODE ⚠️

The SSR "Get Reviews" button functionality is **ESSENTIAL** and was developed over **16+ hours**.

### Location in Code

**File**: `app_enhanced.py`  
**Lines**: ~1861-2167  
**Class**: `ReviewKingClient` (inside bookmarklet JavaScript)  
**Endpoint**: `/js/bookmarklet.js`

### Required Methods (DO NOT DELETE)

1. **`setupModalListener()`** - Lines ~1861-1911
   - Detects AliExpress SSR pages
   - Sets up modal detection
   - Initializes product click listener

2. **`setupProductClickListener()`** - Lines ~1913-1964
   - Listens for product clicks on SSR pages
   - Extracts product IDs from various sources
   - Triggers button addition

3. **`addSakuraButton(productId)`** - Lines ~1967-2034
   - Adds "Get Reviews" button to AliExpress modals
   - Multiple retry attempts (10 tries)
   - Multiple selector fallbacks
   - Fallback to modal body insertion

4. **`createSakuraButtonElement(productId)`** - Lines ~2036-2167
   - Creates the button HTML element
   - Styling and event handlers
   - SVG icon included

### Code Markers

The code is protected with markers:

```javascript
// ====================================================================
// ⚠️ CRITICAL SSR BUTTON CODE - DO NOT REMOVE OR MODIFY ⚠️
// ====================================================================
```

```javascript
// ====================================================================
// ✅ END OF CRITICAL SSR BUTTON CODE
// ====================================================================
```

### Verification Checklist

Before making ANY changes to `app_enhanced.py`, verify:

- [ ] `setupModalListener()` method exists
- [ ] `setupProductClickListener()` method exists  
- [ ] `addSakuraButton(productId)` method exists
- [ ] `createSakuraButtonElement(productId)` method exists
- [ ] Start marker comment is present
- [ ] End marker comment is present
- [ ] `isModalPage()` calls `setupModalListener()` when true

### Backup Reference

See `SSR_BUTTON_CODE_BACKUP.py` for complete code reference.

### If Code is Missing

1. Check `SSR_BUTTON_CODE_BACKUP.py` for the full code
2. Restore from backup
3. Verify all 4 methods are present
4. Test on AliExpress SSR page

### Testing

To verify SSR button works:

1. Go to AliExpress search results (SSR page)
2. Run bookmarklet
3. Click any product
4. "Get Reviews" button should appear in the modal's review tab

---

**Last Updated**: 2025-11-01  
**Status**: PROTECTED with code markers and backup file

