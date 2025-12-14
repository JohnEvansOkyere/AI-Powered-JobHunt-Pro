# Password Reset Guide

## After Changing Your Supabase Database Password

### Step 1: Get Your New Connection String

1. **Go to Supabase Dashboard**
   - Navigate to: https://supabase.com/dashboard
   - Select your project

2. **Get Connection Pooler URL (Recommended)**
   - Go to: **Project Settings** → **Database**
   - Scroll to **Connection Pooling** section
   - Copy the **Session mode** connection string
   - This URL handles special characters automatically

3. **Or Get Direct Connection URL**
   - Go to: **Project Settings** → **Database**
   - Scroll to **Connection string** section
   - Copy the **URI** connection string
   - **Note:** If password has special characters, you'll need to URL-encode them

### Step 2: Update Your .env File

1. **Open your backend/.env file**
   ```bash
   cd backend
   nano .env  # or use your preferred editor
   ```

2. **Update DATABASE_URL**
   ```env
   # Replace the entire DATABASE_URL line with your new connection string
   DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[NEW-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true
   ```

3. **Save the file**

### Step 3: Verify the Update

1. **Check environment variables**
   ```bash
   cd backend
   python scripts/check_env.py
   ```
   - Should show ✅ for DATABASE_URL
   - Should not show warnings about multiple @ signs

2. **Test database connection**
   ```bash
   python scripts/test_db_connection.py
   ```
   - Should show: ✅ Connection successful!

3. **Restart your backend**
   ```bash
   # Stop current backend (Ctrl+C)
   # Then restart
   uvicorn app.main:app --reload
   ```

### Step 4: Verify Backend Works

1. **Check backend logs**
   - Should see: "Creating database engine (pooler: True/False)"
   - Should NOT see connection errors

2. **Test API endpoint**
   ```bash
   curl http://localhost:8000/health
   ```
   - Should return: `{"status": "healthy"}`

## Tips

### ✅ Best Practice: Use Connection Pooler
- More reliable (no IPv6 issues)
- Handles special characters automatically
- Better for production
- Port: **6543**

### ⚠️ If Using Direct Connection
- Port: **5432**
- Must URL-encode special characters in password
- May have IPv6 connectivity issues

### 🔒 Password Best Practices
- Use a strong password (mix of letters, numbers, symbols)
- Avoid `@`, `#`, `%` if possible (or use Connection Pooler)
- Store password securely (never commit to Git)

## Troubleshooting

### Still Getting Connection Errors?

1. **Verify password was actually changed**
   - Check Supabase Dashboard → Project Settings → Database
   - Confirm new password is saved

2. **Check for typos**
   ```bash
   python scripts/check_env.py
   ```
   - Look for any warnings or errors

3. **Test connection directly**
   ```bash
   python scripts/test_db_connection.py
   ```

4. **Check backend logs**
   - Look for specific error messages
   - See [ERRORS_AND_SOLUTIONS.md](./ERRORS_AND_SOLUTIONS.md)

### Connection Pooler vs Direct Connection

| Feature | Connection Pooler | Direct Connection |
|---------|------------------|-------------------|
| Port | 6543 | 5432 |
| Special chars | ✅ Auto-handled | ❌ Need encoding |
| IPv6 issues | ✅ Avoided | ⚠️ May occur |
| Production | ✅ Recommended | ⚠️ Less reliable |

**Recommendation:** Always use Connection Pooler URL.

