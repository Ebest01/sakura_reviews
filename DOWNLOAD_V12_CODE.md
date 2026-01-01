# How to Download app_enhanced.py from Easypanel v12 Service

## Quick Method: Using Easypanel Terminal

1. **Access Easypanel Dashboard**
   - Go to your Easypanel instance
   - Navigate to project: `sakura_reviews`
   - Click on service: `sak_rev_v12`

2. **Open Terminal/Shell**
   - Look for "Terminal", "Shell", or "Console" button
   - Click to open terminal session

3. **Find and Download the File**
   ```bash
   # Find the file location
   find /workspace -name "app_enhanced.py" 2>/dev/null
   find /app -name "app_enhanced.py" 2>/dev/null
   find / -name "app_enhanced.py" 2>/dev/null | grep -v proc
   
   # Once found (e.g., /workspace/app_enhanced.py), copy it
   # Method 1: If Easypanel supports file download
   cp /workspace/app_enhanced.py /tmp/app_enhanced_v12.py
   
   # Method 2: Output to console (then copy-paste)
   cat /workspace/app_enhanced.py
   
   # Method 3: Base64 encode for easy transfer
   base64 /workspace/app_enhanced.py
   # Then decode locally: base64 -d > app_enhanced_v12.py
   ```

## Alternative: Check Git Repository

If the service is connected to a git repo:

```bash
# Check git status
cd /workspace
git log --oneline -20

# Find v12 commit
git log --all --oneline | grep -i v12

# Export specific file from commit
git show <commit-hash>:app_enhanced.py > /tmp/app_enhanced_v12.py
```

## Check Current Database Issue

Before downloading, let's diagnose why database isn't working:

```bash
# Check if database_integration.py exists
ls -la /workspace/database_integration.py

# Check Python imports
python3 -c "from database_integration import DatabaseIntegration; print('OK')"

# Check database connection
python3 -c "import os; from backend.models_v2 import db; print('DB URL:', os.environ.get('DATABASE_URL', 'NOT SET'))"

# Check if tables exist
python3 -c "from backend.models_v2 import Review; print('Review model OK')"
```

## Direct File Access (if enabled)

Try these URLs:
- `https://sakura-reviews-sak-rev-v12.utztjw.easypanel.host/app_enhanced.py`
- `https://sakura-reviews-sak-rev-v12.utztjw.easypanel.host/source/app_enhanced.py`
- `https://sakura-reviews-sak-rev-v12.utztjw.easypanel.host/files/app_enhanced.py`

## Recommended Steps

1. **First, check server logs** in Easypanel to see why `db_integration` is None
2. **Open terminal** in Easypanel for `sak_rev_v12`
3. **Find the file**: `find /workspace -name "app_enhanced.py"`
4. **Copy the content**: `cat /workspace/app_enhanced.py`
5. **Save locally** as `app_enhanced_v12.py`

Then we can compare it with the current version to see what's missing!

