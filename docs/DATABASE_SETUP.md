# Database Setup Guide

Quick guide to fix database connection issues.

## Current Error

You're seeing:
```
connection to server at "db.jeixjsshohfyxgosfzuj.supabase.co" (2a05:d01c:...) failed: Network is unreachable
```

This means you're using **direct connection (port 5432)** which has IPv6 connectivity issues.

## Quick Fix: Use Connection Pooler

### Step 1: Get Connection Pooler URL

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Go to **Project Settings** → **Database**
4. Scroll to **Connection Pooling** section
5. Copy the **"Session mode"** connection string

It should look like:
```
postgresql://postgres.jeixjsshohfyxgosfzuj:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true
```

### Step 2: Update Your .env File

In `backend/.env`, update `DATABASE_URL`:

```env
# OLD (Direct connection - has issues)
# DATABASE_URL=postgresql://postgres:[PASSWORD]@db.jeixjsshohfyxgosfzuj.supabase.co:5432/postgres

# NEW (Connection Pooler - recommended)
DATABASE_URL=postgresql://postgres.jeixjsshohfyxgosfzuj:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true
```

**Key differences:**
- Port **6543** (pooler) instead of **5432** (direct)
- Hostname includes `pooler` and region
- Has `?pgbouncer=true` parameter
- Username format: `postgres.[PROJECT-REF]` instead of just `postgres`

### Step 3: Test Connection

```bash
cd backend
python scripts/test_db_connection.py
```

You should see: `✅ Database connection successful!`

### Step 4: Restart Backend

```bash
# Stop current server (Ctrl+C)
# Restart
uvicorn app.main:app --reload
```

## Alternative: Direct Connection (If Pooler Doesn't Work)

If you must use direct connection:

1. **Get Direct Connection String**
   - Supabase Dashboard → Project Settings → Database
   - Under "Connection string", select **"URI"**
   - Make sure it's IPv4 (not IPv6)

2. **Update .env**
   ```env
   DATABASE_URL=postgresql://postgres:[PASSWORD]@db.jeixjsshohfyxgosfzuj.supabase.co:5432/postgres
   ```

3. **URL Encode Password** (if it has special characters)
   ```python
   from urllib.parse import quote_plus
   password = "your@password#123"
   encoded = quote_plus(password)
   # Use encoded in DATABASE_URL
   ```

## Verify Your Setup

### Check Current DATABASE_URL

```bash
cd backend
python -c "from app.core.config import settings; print('Port:', settings.DATABASE_URL.split(':')[-1].split('/')[0])"
```

### Test Connection

```bash
python scripts/test_db_connection.py
```

## Common Issues

### Issue: "password authentication failed"

**Solution:**
1. Reset password in Supabase Dashboard
2. Update DATABASE_URL with new password
3. URL-encode special characters if needed

### Issue: "could not translate host name"

**Solution:**
- Check project reference in URL matches your Supabase project
- Verify you copied the entire connection string

### Issue: Still getting IPv6 address

**Solution:**
- Use Connection Pooler (always uses IPv4)
- Or contact your network admin about IPv6 connectivity

## Your Project Details

Based on the error, your project reference is: `jeixjsshohfyxgosfzuj`

Your connection pooler URL should be:
```
postgresql://postgres.jeixjsshohfyxgosfzuj:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true
```

Replace:
- `[PASSWORD]` with your database password
- `[REGION]` with your Supabase region (e.g., `us-east-1`, `eu-west-1`)

## Still Having Issues?

1. Check [ERRORS_AND_SOLUTIONS.md](./ERRORS_AND_SOLUTIONS.md)
2. Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
3. Verify Supabase project is active (not paused)
4. Test connection from different network

