# Quick Fix: Database Connection Error

## The Problem

You're seeing this error:
```
sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL from given URL string
```

This means your `DATABASE_URL` in `backend/.env` is either:
- ❌ Empty or missing
- ❌ Has placeholder values (like `[PASSWORD]`)
- ❌ Wrong format
- ❌ Contains invalid characters

## The Fix (2 Minutes)

### Step 1: Get Your Connection String

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project: `jeixjsshohfyxgosfzuj`
3. Click **Project Settings** (gear icon)
4. Click **Database** in the left menu
5. Scroll to **Connection Pooling** section
6. Copy the **"Session mode"** connection string

It will look like:
```
postgresql://postgres.jeixjsshohfyxgosfzuj:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true
```

### Step 2: Update backend/.env

Open `backend/.env` and set:

```env
DATABASE_URL=postgresql://postgres.jeixjsshohfyxgosfzuj:[YOUR-PASSWORD]@aws-0-[YOUR-REGION].pooler.supabase.com:6543/postgres?pgbouncer=true
```

**Important:**
- Replace `[YOUR-PASSWORD]` with your actual database password
- Replace `[YOUR-REGION]` with your region (e.g., `us-east-1`, `eu-west-1`)
- Don't include the brackets `[]` - use actual values

### Step 3: Test

```bash
cd backend
python scripts/test_db_connection.py
```

Should show: `✅ Database connection successful!`

### Step 4: Restart Backend

```bash
# Stop current server (Ctrl+C)
uvicorn app.main:app --reload
```

## What Your DATABASE_URL Should Look Like

✅ **Correct (Connection Pooler):**
```
postgresql://postgres.jeixjsshohfyxgosfzuj:myPassword123@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true
```

✅ **Correct (Direct Connection):**
```
postgresql://postgres:myPassword123@db.jeixjsshohfyxgosfzuj.supabase.co:5432/postgres
```

❌ **Wrong (Has placeholders):**
```
postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

❌ **Wrong (Empty):**
```
DATABASE_URL=
```

❌ **Wrong (Missing):**
```
# DATABASE_URL not set at all
```

## Still Not Working?

1. **Check password has special characters:**
   - If password has `@`, `#`, `%`, etc., URL-encode them
   - Or reset password in Supabase to something simpler

2. **Verify you copied the entire string:**
   - Should include `?pgbouncer=true` at the end (for pooler)
   - Should be one continuous line, no line breaks

3. **Check for extra spaces:**
   - No spaces before/after the URL
   - No quotes around the URL

4. **Test the connection:**
   ```bash
   python scripts/test_db_connection.py
   ```

## Need More Help?

- See [DATABASE_SETUP.md](./DATABASE_SETUP.md) for detailed guide
- See [ERRORS_AND_SOLUTIONS.md](./ERRORS_AND_SOLUTIONS.md) for other errors

