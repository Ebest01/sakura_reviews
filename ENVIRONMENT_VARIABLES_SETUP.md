# 🔐 Environment Variables Setup for Email

## ⚠️ **IMPORTANT: Never commit passwords to code!**

All sensitive credentials should be set as **environment variables** in your deployment platform (Easypanel, Heroku, etc.).

---

## 📧 **Email Configuration (Gmail SMTP)**

Set these environment variables in your **Easypanel deployment**:

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=qrel jjni zbmi nvlb
EMAIL_FROM=noreply@sakurareviews.com
EMAIL_FROM_NAME=Sakura Reviews
SUPPORT_EMAIL=sakura.revs@gmail.com
```

---

## 🔧 **How to Set in Easypanel:**

1. **Go to your Easypanel dashboard**
2. **Navigate to your app/service**
3. **Go to "Environment Variables" or "Config" section**
4. **Add each variable:**
   - Click "Add Variable"
   - Name: `SMTP_SERVER`
   - Value: `smtp.gmail.com`
   - Repeat for all variables above

---

## ✅ **Quick Setup Checklist:**

- [ ] `SMTP_SERVER` = `smtp.gmail.com`
- [ ] `SMTP_PORT` = `587`
- [ ] `SMTP_USER` = Your Gmail address
- [ ] `SMTP_PASSWORD` = `qrel jjni zbmi nvlb` (your app password)
- [ ] `EMAIL_FROM` = `noreply@sakurareviews.com`
- [ ] `EMAIL_FROM_NAME` = `Sakura Reviews`
- [ ] `SUPPORT_EMAIL` = `sakura.revs@gmail.com`

---

## 🧪 **Testing:**

After setting environment variables:

1. **Restart your app** (to load new env vars)
2. **Submit a test review** on your store
3. **Check the reviewer's email inbox**
4. **Verify the acknowledgment email was received**

---

## 📝 **Notes:**

- **App Password Format:** Gmail app passwords have spaces (like `qrel jjni zbmi nvlb`) - this is normal, use it exactly as shown
- **Security:** Never commit passwords to Git or share them publicly
- **Environment Variables:** These are stored securely in your deployment platform
- **Restart Required:** After setting env vars, restart the app for changes to take effect

---

## 🚨 **If Emails Don't Send:**

1. **Check logs** for SMTP errors
2. **Verify environment variables** are set correctly
3. **Test SMTP connection** manually if needed
4. **Check Gmail account** for security alerts

---

**Last Updated:** December 2025  
**Status:** Ready to configure

