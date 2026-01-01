# How to Access Code from Easypanel v12 Service

## Method 1: Using Easypanel Terminal/SSH

1. **Log into Easypanel Dashboard**
   - Go to: https://easypanel.io (or your Easypanel instance)
   - Navigate to your project: `sakura_reviews`
   - Find the service: `sak_rev_v12`

2. **Access Terminal**
   - Click on the `sak_rev_v12` service
   - Look for a "Terminal" or "Shell" button/icon
   - Click it to open a terminal session

3. **Download app_enhanced.py**
   ```bash
   # Find the file
   find /workspace -name "app_enhanced.py" -type f
   
   # Or check common locations
   ls -la /workspace/
   ls -la /app/
   
   # Once found, copy it (if you have access to download)
   cat /workspace/app_enhanced.py > /tmp/app_enhanced_v12.py
   ```

4. **Download via HTTP (if service is running)**
   ```bash
   # If the service has a file serving endpoint or you can curl it
   curl http://localhost:5000/app_enhanced.py > app_enhanced_v12.py
   ```

## Method 2: Using Easypanel File Browser

1. **Access File Browser**
   - In the Easypanel dashboard, look for a "Files" or "File Browser" option
   - Navigate to the `sak_rev_v12` service
   - Browse to find `app_enhanced.py`

2. **Download the File**
   - Right-click on the file
   - Select "Download" or "Export"
   - Save it locally

## Method 3: Using Git (if the service has git access)

```bash
# SSH into the service
ssh user@easypanel-host

# Navigate to the service directory
cd /path/to/sak_rev_v12

# Check git status
git status
git log --oneline -10

# If it's a git repo, you can checkout the v12 commit
git log --all --oneline | grep v12
git show <commit-hash>:app_enhanced.py > app_enhanced_v12.py
```

## Method 4: Direct HTTP Access (if file serving is enabled)

Try accessing the file directly via URL:
```
https://sakura-reviews-sak-rev-v12.utztjw.easypanel.host/app_enhanced.py
```

Or check if there's a source code endpoint:
```
https://sakura-reviews-sak-rev-v12.utztjw.easypanel.host/source
https://sakura-reviews-sak-rev-v12.utztjw.easypanel.host/files/app_enhanced.py
```

## Method 5: Check Deployment Logs/History

1. In Easypanel, go to the `sak_rev_v12` service
2. Look for "Deployment History" or "Build Logs"
3. Check if the source code is visible in the build logs
4. Look for git commit hashes that might help identify the version

## Quick Check: Test Database Connection

Before downloading, let's verify why the database isn't working in the current version:

```bash
# Check if database_integration.py exists
ls -la database_integration.py

# Check database connection
python -c "from database_integration import DatabaseIntegration; print('OK')"

# Check DATABASE_URL environment variable
echo $DATABASE_URL
```

## Recommended Approach

**Easiest method**: Use Easypanel's Terminal/Shell feature to:
1. Navigate to the workspace
2. Find `app_enhanced.py`
3. Use `cat` or `cp` to copy it
4. If Easypanel supports file downloads, download it
5. Or use `base64` encoding to copy via terminal:
   ```bash
   base64 app_enhanced.py
   # Then decode it locally
   ```

