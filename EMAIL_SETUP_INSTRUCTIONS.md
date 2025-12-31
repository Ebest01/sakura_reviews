# 📧 Email Setup Instructions - Review Acknowledgment Emails

## ✅ **Current Status**

**Review acknowledgment emails are now implemented!** When a customer submits a review, they will receive a confirmation email (like Amazon does).

## ⚙️ **Setup Required**

To activate email sending, you need to configure SMTP settings:

### **Option 1: Gmail SMTP (Easiest for Testing)**

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password:**
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" and "Other (Custom name)"
   - Name it "Sakura Reviews"
   - Copy the 16-character password

3. **Set Environment Variables:**
   ```bash
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-16-char-app-password
   EMAIL_FROM=noreply@sakurareviews.com
   EMAIL_FROM_NAME=Sakura Reviews
   SUPPORT_EMAIL=sakura.revs@gmail.com
   ```

### **Option 2: SendGrid (Recommended for Production)**

1. **Sign up for SendGrid:** https://sendgrid.com
2. **Create API Key:**
   - Go to Settings → API Keys
   - Create new API key with "Mail Send" permissions
   - Copy the API key

3. **Set Environment Variables:**
   ```bash
   SMTP_SERVER=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USER=apikey
   SMTP_PASSWORD=your-sendgrid-api-key
   EMAIL_FROM=noreply@sakurareviews.com
   EMAIL_FROM_NAME=Sakura Reviews
   SUPPORT_EMAIL=sakura.revs@gmail.com
   ```

### **Option 3: Mailgun**

1. **Sign up for Mailgun:** https://mailgun.com
2. **Get SMTP credentials** from your Mailgun dashboard
3. **Set Environment Variables:**
   ```bash
   SMTP_SERVER=smtp.mailgun.org
   SMTP_PORT=587
   SMTP_USER=your-mailgun-smtp-user
   SMTP_PASSWORD=your-mailgun-smtp-password
   EMAIL_FROM=noreply@sakurareviews.com
   EMAIL_FROM_NAME=Sakura Reviews
   SUPPORT_EMAIL=sakura.revs@gmail.com
   ```

## 🔧 **How It Works**

1. **Customer submits review** via widget
2. **Review is saved** to database
3. **Acknowledgment email is sent** automatically (if SMTP configured)
4. **Email includes:**
   - Thank you message
   - Review summary (rating, text)
   - Link to view the review
   - Support contact info

## 📝 **Email Template**

The email template is located at:
```
templates/email-review-acknowledgment.html
```

You can customize:
- Colors and branding
- Message content
- Layout and design

## 🧪 **Testing**

1. **Submit a test review** on your store
2. **Check the email inbox** of the reviewer email
3. **Verify email content** looks correct

## ⚠️ **Important Notes**

- **Email sending is optional** - If SMTP is not configured, reviews still work, just no email is sent
- **Email failures don't break review submission** - If email fails, the review is still saved
- **Check logs** for email sending status: `logger.info` will show if emails are sent

## 📊 **Current Behavior**

- ✅ **If SMTP configured:** Email is sent automatically
- ⚠️ **If SMTP NOT configured:** Review is saved, but no email sent (logged for debugging)

## 🚀 **Next Steps**

1. **Choose an email service** (Gmail for testing, SendGrid/Mailgun for production)
2. **Set environment variables** in your deployment
3. **Test by submitting a review**
4. **Check email inbox** to verify it works

---

**Last Updated:** December 2025  
**Status:** Implemented - Requires SMTP configuration to activate

