# Errors and Solutions Guide

This document catalogs common errors encountered during development and their solutions.

## Table of Contents

1. [Database Connection Errors](#database-connection-errors)
2. [Authentication Errors](#authentication-errors)
3. [Profile Errors](#profile-errors)
4. [SQLAlchemy Errors](#sqlalchemy-errors)
5. [Frontend Errors](#frontend-errors)
6. [API Errors](#api-errors)

---

## Database Connection Errors

> **Quick Fix:** See [DATABASE_SETUP.md](./DATABASE_SETUP.md) for step-by-step instructions to fix your connection.

### Error: "Network is unreachable" when connecting to Supabase

**Error Message:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) connection to server at "db.xxx.supabase.co" failed: Network is unreachable
```

**Cause:**
- IPv6 connectivity issues
- Firewall blocking connection
- Incorrect DATABASE_URL format
- Supabase project paused (free tier)

**Solutions:**

1. **Use Connection Pooler (Recommended)**
   ```env
   # In .env file
   DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true
   ```
   - Get this from Supabase Dashboard → Project Settings → Database → Connection Pooling
   - Uses port 6543 (pooler) instead of 5432 (direct)

2. **Use Direct IPv4 Connection**
   ```env
   DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
   - Ensure it's IPv4, not IPv6
   - URL-encode special characters in password

3. **Check Supabase Project Status**
   - Free tier projects pause after inactivity
   - Go to Supabase Dashboard and wake up the project

4. **Verify Network/Firewall**
   - Ensure ports 5432 or 6543 aren't blocked
   - Try from different network

**See Also:** [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

---

### Error: "connection to server on socket" (Unix socket error)

**Error Message:**
```
psycopg2.OperationalError: connection to server on socket "@db.xxx.supabase.co/.s.PGSQL.5432" failed: Connection refused
```

**Cause:**
- Password contains special characters (like `@`, `#`, `%`) that break URL parsing
- psycopg2 is interpreting hostname as a Unix socket path instead of TCP/IP
- Multiple `@` signs in URL (password contains `@` character)

**Solutions:**

1. **Use Connection Pooler (Easiest - Recommended)**
   - Connection Pooler handles special characters automatically
   - Get URL from: Supabase Dashboard → Project Settings → Database → Connection Pooling
   - Format: `postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true`
   - **No password encoding needed!**

2. **URL Encode Your Password**
   - If password is `Promzy199728@@`, encode as `Promzy199728%40%40`
   - Special characters: `@` = `%40`, `#` = `%23`, `%` = `%25`, etc.
   - See [PASSWORD_ENCODING.md](./PASSWORD_ENCODING.md) for full guide
   
   ```python
   from urllib.parse import quote_plus
   password = "Promzy199728@@"
   encoded = quote_plus(password)  # Returns: "Promzy199728%40%40"
   ```

3. **Check Your URL Format**
   ```bash
   cd backend
   python scripts/check_env.py
   ```
   - This will detect if your password contains `@` and needs encoding
   - Shows exact issue with your DATABASE_URL

4. **Backend Auto-Fix**
   - The backend now automatically URL-encodes passwords if it detects multiple `@` signs
   - Check backend logs for: "URL-encoded password in DATABASE_URL"

**Example Fix:**
```env
# ❌ Wrong (password contains @@)
DATABASE_URL=postgresql://postgres:Promzy199728@@@db.xxx.supabase.co:5432/postgres

# ✅ Correct (URL-encoded)
DATABASE_URL=postgresql://postgres:Promzy199728%40%40@db.xxx.supabase.co:5432/postgres

# ✅ Best (Connection Pooler - no encoding needed)
DATABASE_URL=postgresql://postgres.xxx:Promzy199728@@@aws-0-us-east-1.pooler.supabase.com:6543/postgres?pgbouncer=true
```

---

### Error: "password authentication failed"

**Error Message:**
```
psycopg2.OperationalError: password authentication failed for user "postgres"
```

**Solutions:**

1. **Reset Database Password**
   - Go to Supabase Dashboard → Project Settings → Database
   - Click "Reset database password"
   - Update DATABASE_URL with new password

2. **URL Encode Password**
   ```python
   from urllib.parse import quote_plus
   password = "your@password#123"
   encoded = quote_plus(password)
   # Use encoded in DATABASE_URL
   ```

3. **Verify User**
   - Ensure using `postgres` user (not custom user)
   - Check connection string format

---

## Authentication Errors

### Error: "Invalid authentication credentials"

**Error Message:**
```
HTTPException: 401 Unauthorized - Invalid authentication credentials
```

**Cause:**
- Invalid or expired JWT token
- Token not sent in request
- Supabase Auth configuration issue

**Solutions:**

1. **Check Token in Request**
   - Verify `Authorization: Bearer <token>` header is sent
   - Token should come from Supabase Auth session

2. **Refresh Session**
   ```typescript
   // Frontend
   const { data: { session } } = await supabase.auth.getSession()
   // Use session.access_token
   ```

3. **Verify Supabase Configuration**
   - Check `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - Ensure keys match your Supabase project

4. **Check Token Expiration**
   - Tokens expire after set time
   - Implement token refresh logic

---

### Error: "Could not validate credentials"

**Error Message:**
```
HTTPException: 401 Unauthorized - Could not validate credentials
```

**Cause:**
- Backend can't verify token with Supabase
- Network issue reaching Supabase Auth API
- Invalid token format

**Solutions:**

1. **Check Backend Supabase Configuration**
   ```python
   # Verify in backend/.env
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_anon_key
   SUPABASE_SERVICE_KEY=your_service_key
   ```

2. **Test Token Verification**
   ```python
   # Test in Python shell
   from app.core.supabase_client import get_supabase_service_client
   supabase = get_supabase_service_client()
   # Try to get user with token
   ```

3. **Check Network Connectivity**
   - Backend must be able to reach Supabase Auth API
   - Verify no firewall blocking

---

## Profile Errors

### Error: "Profile not found" - Auto-redirect Loop

**Symptom:**
- Frontend keeps redirecting to `/profile/setup`
- Backend returns 500 error when creating profile

**Cause:**
- Database connection issue preventing profile creation
- Profile endpoint failing to auto-create profile

**Solutions:**

1. **Fix Database Connection** (See Database Connection Errors above)

2. **Run Auto-Profile SQL**
   ```sql
   -- In Supabase SQL Editor
   -- Run: docs/SUPABASE_AUTO_PROFILE.sql
   ```
   This creates a trigger to auto-create profiles on signup

3. **Check Backend Logs**
   - Look for database connection errors
   - Verify DATABASE_URL is correct

4. **Manual Profile Creation**
   ```sql
   -- For existing users
   INSERT INTO public.user_profiles (user_id)
   SELECT id FROM auth.users
   WHERE id NOT IN (SELECT user_id FROM public.user_profiles)
   ON CONFLICT (user_id) DO NOTHING;
   ```

---

### Error: "Profile already exists" when creating

**Error Message:**
```
HTTPException: 400 Bad Request - Profile already exists. Use PUT to update.
```

**Cause:**
- Trying to create profile when one already exists
- Database trigger created profile automatically

**Solution:**
- Use `PUT /api/v1/profiles` to update instead of `POST`
- Or check if profile exists first using `GET /api/v1/profiles/me`

---

## SQLAlchemy Errors

### Error: "Attribute name 'metadata' is reserved"

**Error Message:**
```
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
```

**Cause:**
- SQLAlchemy reserves `metadata` attribute name
- Can't use it as a column name directly

**Solution:**
- Use different Python attribute name, map to database column:
  ```python
  user_metadata = Column("metadata", JSONB, default={}, nullable=True)
  ```
- Python uses `user_metadata`, database column is `metadata`

---

### Error: UUID Type Issues

**Error Message:**
```
sqlalchemy.exc.ProgrammingError: can't adapt type 'UUID'
```

**Cause:**
- Mixing UUID objects and strings
- Database expects specific UUID format

**Solutions:**

1. **Convert UUID to String for JSON**
   ```python
   return {
       "id": str(profile.id),  # Convert UUID to string
       "user_id": str(profile.user_id),
   }
   ```

2. **Convert String to UUID for Queries**
   ```python
   user_id = uuid.UUID(str(user_id_str))
   profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
   ```

3. **Use Helper Function**
   ```python
   def profile_to_response(profile: UserProfile) -> UserProfileResponse:
       return UserProfileResponse(
           id=str(profile.id),  # Always convert UUIDs
           user_id=str(profile.user_id),
           # ... other fields
       )
   ```

---

## Frontend Errors

### Error: Auto-redirect to Profile Setup

**Symptom:**
- User automatically redirected to `/profile/setup` even after login
- Happens immediately on dashboard load

**Cause:**
- Profile loading fails (database error)
- Frontend thinks profile doesn't exist
- Redirects before backend can auto-create

**Solutions:**

1. **Fix Database Connection** (Primary issue)

2. **Update Dashboard Logic**
   ```typescript
   // Don't redirect immediately on error
   // Give backend time to auto-create profile
   useEffect(() => {
     if (!profileLoading && !profile) {
       const timer = setTimeout(() => {
         if (!profile) {
           router.push('/profile/setup')
         }
       }, 1000) // Wait 1 second
       return () => clearTimeout(timer)
     }
   }, [profile, profileLoading, router])
   ```

3. **Better Error Handling**
   ```typescript
   // In useProfile hook
   if (error.message?.includes('Database') || error.message?.includes('connection')) {
     // Don't redirect on connection errors
     toast.error('Database connection error')
     setProfile(null)
   }
   ```

---

### Error: "Failed to load profile"

**Error Message:**
- Toast notification: "Failed to load profile"
- Console shows API error

**Solutions:**

1. **Check Backend is Running**
   ```bash
   # Verify backend is running
   curl http://localhost:8000/health
   ```

2. **Check API URL**
   ```env
   # In frontend/.env.local
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. **Check Authentication**
   - Ensure user is logged in
   - Token is being sent in request
   - Token is valid

4. **Check Network Tab**
   - Open browser DevTools → Network
   - Check if request is being made
   - Check response status and error message

---

## API Errors

### Error: 500 Internal Server Error

**Error Message:**
```
INFO: "GET /api/v1/profiles/me HTTP/1.1" 500 Internal Server Error
```

**Common Causes:**

1. **Database Connection Failed**
   - Check DATABASE_URL in backend/.env
   - Verify database is accessible
   - See Database Connection Errors

2. **UUID Conversion Error**
   - Invalid user ID format
   - Check user ID from auth token

3. **SQLAlchemy Model Error**
   - Reserved attribute names
   - Type mismatches
   - See SQLAlchemy Errors

**Solutions:**

1. **Check Backend Logs**
   ```bash
   # Look for detailed error in terminal
   # Backend should show full traceback
   ```

2. **Test Database Connection**
   ```python
   # In Python shell
   from app.core.database import engine
   with engine.connect() as conn:
       print("✅ Database connected")
   ```

3. **Verify Environment Variables**
   ```bash
   # Check all required env vars are set
   cat backend/.env
   ```

---

### Error: 404 Not Found

**Error Message:**
```
HTTPException: 404 Not Found - Profile not found
```

**Solutions:**

1. **Profile Auto-Creation**
   - Backend should auto-create profile if missing
   - If not working, check database connection

2. **Manual Profile Creation**
   ```sql
   INSERT INTO public.user_profiles (user_id)
   VALUES ('user-uuid-here');
   ```

3. **Check User ID**
   - Verify user ID from auth token
   - Ensure user exists in auth.users

---

## Quick Diagnostic Commands

### Test Database Connection
```bash
cd backend
python -c "
from app.core.database import engine
from sqlalchemy import text
try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('✅ Database connection successful!')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
"
```

### Test Backend API
```bash
# Health check
curl http://localhost:8000/health

# With auth token
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/profiles/me
```

### Test Frontend API Client
```typescript
// In browser console
const response = await fetch('http://localhost:8000/api/v1/profiles/me', {
  headers: {
    'Authorization': `Bearer ${session.access_token}`
  }
})
console.log(await response.json())
```

---

## Prevention Tips

1. **Always check database connection first** when seeing 500 errors
2. **Use connection pooler** for Supabase (more reliable)
3. **Handle errors gracefully** in frontend (don't redirect on connection errors)
4. **Log errors** in backend for debugging
5. **Test database connection** before starting development
6. **Keep environment variables** in sync between frontend and backend

---

## Getting Help

If errors persist:

1. Check backend logs for detailed error messages
2. Verify all environment variables are set correctly
3. Test database connection independently
4. Check Supabase project status
5. Review this document for similar errors
6. Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for more solutions

