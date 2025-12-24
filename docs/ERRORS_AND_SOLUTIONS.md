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

### Error: "cannot import name 'get_current_user' from 'app.core.security'"

**Error Message:**
```
ImportError: cannot import name 'get_current_user' from 'app.core.security'
```

**Cause:**
- `get_current_user` is located in `app.api.v1.dependencies`, not `app.core.security`
- Wrong import path in CV endpoints file

**Solution:**
```python
# ❌ Wrong
from app.core.security import get_current_user

# ✅ Correct
from app.api.v1.dependencies import get_current_user
```

**Fixed in**: `backend/app/api/v1/endpoints/cvs.py`

---

### Error: "cannot import name 'get_model_router' from 'app.ai.router'"

**Error Message:**
```
ImportError: cannot import name 'get_model_router' from 'app.ai.router'
```

**Cause:**
- Function `get_model_router()` was not defined in the router module
- CV parser was trying to use a function that didn't exist

**Solution:**
Added `get_model_router()` function to `backend/app/ai/router.py`:
```python
def get_model_router() -> ModelRouter:
    """Get or create the global model router instance."""
    global _model_router
    if _model_router is None:
        _model_router = ModelRouter()
    return _model_router
```

Also updated router to handle missing AI provider dependencies gracefully with try/except imports.

---

### Error: "ModuleNotFoundError: No module named 'groq'"

**Error Message:**
```
ModuleNotFoundError: No module named 'groq'
```

**Cause:**
- AI provider dependencies not installed
- Router tries to import all providers at module level

**Solution:**
1. **Install missing dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Or make imports optional** (already done):
   - Router now uses try/except for provider imports
   - Providers are only initialized if dependencies are installed
   - System works with any combination of available providers

---

## CV Upload Errors

### Error: "cannot access local variable 'json' where it is not associated with a value"

**Error Message:**
```
Error parsing CV: cannot access local variable 'json' where it is not associated with a value
```

**Cause:**
- `json` module was imported inside a try block in `cv_parser.py`
- If an exception occurred before the import, `json` wasn't available in the except block
- The except block tried to catch `json.JSONDecodeError` but `json` wasn't in scope

**Solution:**
Move `json` import to the top of the file:
```python
# ✅ Correct - import at top
import json
from typing import Dict, Any, Optional

# ❌ Wrong - import inside try block
try:
    import json  # This might not be available in except block
    ...
except json.JSONDecodeError:  # Error: json not defined
    ...
```

**Fixed in**: `backend/app/services/cv_parser.py`

---

### Error: "2 validation errors for CVResponse - created_at/updated_at"

**Error Message:**
```
2 validation errors for CVResponse
created_at
  Input should be a valid string [type=string_type, input_value=datetime.datetime(...), input_type=datetime]
updated_at
  Input should be a valid string [type=string_type, input_value=datetime.datetime(...), input_type=datetime]
```

**Cause:**
- SQLAlchemy returns `datetime` objects for `created_at` and `updated_at`
- Pydantic model expected strings but received datetime objects
- `from_attributes=True` doesn't automatically serialize datetime to string

**Solution:**
Use Pydantic's `field_serializer` to convert datetime to ISO format string:
```python
from datetime import datetime
from pydantic import BaseModel, field_serializer

class CVResponse(BaseModel):
    created_at: datetime
    updated_at: datetime
    
    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime, _info):
        """Serialize datetime to ISO format string."""
        return dt.isoformat() if dt else None
    
    class Config:
        from_attributes = True
```

**Fixed in**: `backend/app/api/v1/endpoints/cvs.py`

---

### Error: "No available provider for task: TaskType.JOB_ANALYSIS"

**Error Message:**
```
No available provider for task: TaskType.JOB_ANALYSIS
No provider available for task: TaskType.JOB_ANALYSIS
```

**Cause:**
- CV parser was using wrong task type (`TaskType.JOB_ANALYSIS` instead of `TaskType.CV_PARSING`)
- No AI provider configured or API keys not set
- Router couldn't find appropriate provider for the task

**Solutions:**

1. **Use Correct Task Type:**
   ```python
   # ✅ Correct
   response = await self.ai_router.generate(
       task_type=TaskType.CV_PARSING,  # Use CV_PARSING, not JOB_ANALYSIS
       prompt=prompt,
   )
   ```

2. **Configure AI Provider:**
   - Set at least one AI provider API key in `.env`:
     ```env
     OPENAI_API_KEY=your_key_here
     # OR
     GEMINI_API_KEY=your_key_here
     # OR
     GROQ_API_KEY=your_key_here
     ```
   - Install required dependencies:
     ```bash
     pip install openai google-generativeai groq
     ```

3. **Handle Missing Providers Gracefully:**
   - CV parser already has fallback logic
   - If AI parsing fails, it returns basic structure
   - CV upload still succeeds, just without AI-extracted data

**Fixed in**: `backend/app/services/cv_parser.py`

---

### Error: "'UploadResponse' object has no attribute 'get'"

**Error Message:**
```
Error uploading CV: 'UploadResponse' object has no attribute 'get'
```

**Cause:**
- Supabase Python client's `upload()` method returns an `UploadResponse` object, not a dictionary
- Code was trying to use `.get("error")` on an object that doesn't have that method
- Similar issue with `create_signed_url()` response

**Solution:**
Handle both object and dict responses:
```python
# Upload to Supabase Storage
storage_response = supabase.storage.from_(bucket).upload(...)

# Check for errors - handle both object and dict
error_msg = None
if hasattr(storage_response, 'error') and storage_response.error:
    error_msg = str(storage_response.error)
elif isinstance(storage_response, dict) and storage_response.get("error"):
    error_msg = storage_response.get("error")

if error_msg:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to upload file: {error_msg}"
    )
```

**Fixed in**: `backend/app/api/v1/endpoints/cvs.py`

---

### Error: "400 Bad Request" on CV Upload

**Error Message:**
```
INFO: "POST /api/v1/cvs/upload HTTP/1.1" 400 Bad Request
```

**Common Causes:**

1. **File has no extension**
   - File must have `.pdf` or `.docx` extension
   - Check filename includes extension

2. **Invalid file type**
   - Only PDF and DOCX are supported
   - `.doc` files are not supported (must convert to `.docx`)

3. **File too large**
   - Maximum size is 10MB
   - Compress or reduce file size

4. **Empty file**
   - File has 0 bytes
   - Ensure file has content

5. **Content-Type header issue** (Frontend)
   - Don't manually set `Content-Type: multipart/form-data`
   - Browser must set it automatically with boundary parameter

**Solutions:**

1. **Check File Extension:**
   ```bash
   # Ensure file has .pdf or .docx extension
   ls -la resume.pdf  # Should show .pdf
   ```

2. **Check File Size:**
   ```bash
   # Check file size (must be < 10MB)
   ls -lh resume.pdf
   ```

3. **Frontend Fix:**
   ```typescript
   // ❌ Wrong - manually setting Content-Type
   const formData = new FormData()
   formData.append('file', file)
   await apiClient.post('/api/v1/cvs/upload', formData, {
     headers: {
       'Content-Type': 'multipart/form-data',  // Don't do this!
     }
   })
   
   // ✅ Correct - let browser set Content-Type
   const formData = new FormData()
   formData.append('file', file)
   await apiClient.post('/api/v1/cvs/upload', formData)  // No headers!
   ```

4. **Check Backend Logs:**
   - Backend logs show exact validation failure
   - Look for: "CV upload request received - filename: ..."
   - Check which validation failed

**See Also**: [CV_UPLOAD_TROUBLESHOOTING.md](./CV_UPLOAD_TROUBLESHOOTING.md)

---

## AI Router Errors

### Error: "ModuleNotFoundError: No module named 'tiktoken'"

**Error Message:**
```
ModuleNotFoundError: No module named 'tiktoken'
```

**Cause:**
- `tiktoken` package not installed in the virtual environment
- Required for accurate token counting in the AI router

**Solutions:**

1. **Install tiktoken:**
   ```bash
   cd backend
   source venv/bin/activate  # Activate virtual environment
   pip install tiktoken
   ```

2. **Or install from requirements:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Fallback Available:**
   - The router has a fallback token estimation (1 token ≈ 4 characters)
   - Works without tiktoken, but less accurate
   - Router will log a warning but continue to function

**Note:** The router is designed to work without tiktoken, but accuracy is better with it installed.

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

