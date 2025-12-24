# Frontend-Backend Connection Diagnostics

## Current Status

### ✅ Backend Status
- **Running**: Yes (Port 8000)
- **Health Check**: Working (`http://localhost:8000/health`)
- **Jobs in Database**: 98 jobs from RemoteOK

### ✅ Frontend Configuration
- **Supabase URL**: Configured
- **Supabase Anon Key**: Configured
- **API URL**: `http://localhost:8000`

## How Authentication Works

**Important**: Login does NOT go through your FastAPI backend!

```
User Login Flow:
1. User enters email/password in frontend
2. Frontend calls Supabase Auth directly (not your backend)
3. Supabase validates credentials
4. Supabase returns JWT token
5. Frontend stores token
6. For API calls (jobs, profile, etc.), frontend sends token to backend
7. Backend validates token with Supabase
```

## Diagnostic Steps

### 1. Check if Frontend is Running

```bash
# Check if Next.js dev server is running
ps aux | grep next | grep -v grep

# Should see something like:
# node /home/grejoy/Projects/AI-Powered-JobHunt-Pro/frontend/.next/...
```

**Expected Port**: 3000

### 2. Check if Backend is Running

```bash
# Check if uvicorn is running
ps aux | grep uvicorn | grep -v grep

# Should see:
# python3 .../uvicorn app.main:app --reload
```

**Expected Port**: 8000

### 3. Test Backend Health

```bash
curl http://localhost:8000/health
```

**Expected Response**:
```json
{"status":"healthy","version":"1.0.0"}
```

### 4. Test Supabase Connection

Open browser console (F12) and run:

```javascript
// Test Supabase connection
const { createClient } = await import('@supabase/supabase-js')
const supabase = createClient(
  'https://jeixjsshohfyxgosfzuj.supabase.co',
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImplaXhqc3Nob2hmeXhnb3NmenVqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU3MTYyOTIsImV4cCI6MjA4MTI5MjI5Mn0.4W3edLHPSOZsjQrpTSppfVixPKbvGdmAse5_OCaVsEI'
)

// Try to get session
const { data, error } = await supabase.auth.getSession()
console.log('Session:', data, 'Error:', error)
```

### 5. Check Browser Console for Errors

When you try to login, open browser DevTools (F12) and check:

**Console Tab**: Look for errors
**Network Tab**: Check if requests are being made

## Common Issues and Solutions

### Issue 1: "Cannot find module" or blank page

**Cause**: Frontend not running or crashed

**Solution**:
```bash
cd /home/grejoy/Projects/AI-Powered-JobHunt-Pro/frontend
npm run dev
```

### Issue 2: Login button does nothing

**Possible Causes**:
1. **JavaScript Error**: Check browser console (F12)
2. **Supabase Down**: Check https://status.supabase.com
3. **Wrong Credentials**: Make sure user exists in Supabase

**Check if user exists**:
```sql
-- Run in Supabase SQL Editor
SELECT email, created_at
FROM auth.users
LIMIT 10;
```

### Issue 3: "Invalid credentials" error

**Cause**: User doesn't exist or wrong password

**Solution**: Create a test user

```bash
# In Supabase Dashboard:
1. Go to Authentication > Users
2. Click "Add user"
3. Add email and password
4. Verify email (or disable email confirmation in Supabase settings)
```

### Issue 4: Backend errors after login

**Cause**: Backend can't validate Supabase JWT token

**Check backend logs**:
```bash
# Look for errors in terminal where uvicorn is running
# Should see errors about JWT validation
```

**Solution**: Verify backend has correct Supabase keys in `.env`:
```env
SUPABASE_URL=https://jeixjsshohfyxgosfzuj.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Issue 5: CORS Error

**Symptom**: Browser console shows CORS policy error

**Cause**: Backend CORS not configured for frontend

**Check backend CORS** in `backend/app/main.py`:
```python
# Should have:
CORS_ORIGINS: List[str] = Field(
    default=["http://localhost:3000"],
    ...
)
```

**Solution**: Already configured correctly in your `.env`

## Testing the Complete Flow

### Step 1: Create Test User (if not exists)

**Option A**: Via Supabase Dashboard
1. Go to https://supabase.com
2. Select your project
3. Authentication > Users > Add User
4. Email: `test@example.com`
5. Password: `Test123!@#`

**Option B**: Via Frontend Signup
1. Visit `http://localhost:3000/auth/signup`
2. Fill in email and password
3. Sign up

### Step 2: Login

1. Visit `http://localhost:3000/auth/login`
2. Enter credentials
3. Click "Sign in"
4. **Watch browser console for errors**

**Expected Behavior**:
- Loading state appears
- After 1-2 seconds, redirected to `/dashboard`
- No errors in console

**If it fails**:
- Check browser console (F12)
- Look for error messages
- Note the error type

### Step 3: Test API Call

After successful login, the dashboard should call:
```
GET http://localhost:8000/api/v1/profiles/me
```

**Check**:
1. Open Network tab in DevTools
2. Filter by "Fetch/XHR"
3. Look for request to `localhost:8000`
4. Check if it has `Authorization: Bearer <token>` header

## Quick Diagnostic Commands

```bash
# 1. Check what's running
netstat -tlnp 2>/dev/null | grep -E ':(3000|8000)'

# 2. Test backend
curl http://localhost:8000/health

# 3. Check frontend logs
# (look at terminal where you ran `npm run dev`)

# 4. Restart everything
pkill -f "next dev"
pkill -f uvicorn
cd /home/grejoy/Projects/AI-Powered-JobHunt-Pro/backend && uvicorn app.main:app --reload &
cd /home/grejoy/Projects/AI-Powered-JobHunt-Pro/frontend && npm run dev
```

## Expected Behavior

### Successful Login Flow

1. **User enters credentials** → Frontend validates format
2. **Frontend calls Supabase Auth** → Supabase validates
3. **Supabase returns JWT** → Frontend stores in localStorage
4. **Frontend redirects to /dashboard** → Dashboard loads
5. **Dashboard calls backend API** → `/api/v1/profiles/me`
6. **Backend validates JWT** → Checks with Supabase
7. **Backend returns data** → Profile, jobs, etc.
8. **Frontend displays data** → User sees dashboard

### Where to Look for Problems

| Step | Check | Tool |
|------|-------|------|
| Login form | No errors | Browser Console (F12) |
| Supabase auth | Request succeeds | Network Tab |
| JWT storage | Token saved | Application > Local Storage |
| Redirect | Goes to /dashboard | Browser URL |
| API call | Request sent | Network Tab |
| Backend response | 200 OK | Network Tab > Response |

## Next Steps

Based on what you see:

**If login form doesn't respond**:
- Check browser console for JavaScript errors
- Verify frontend is running: `ps aux | grep next`
- Restart frontend: `cd frontend && npm run dev`

**If login fails with error**:
- Check error message
- Verify user exists in Supabase
- Check Supabase project is active

**If login succeeds but dashboard is empty**:
- Check Network tab for API calls
- Verify backend is running
- Check backend logs for errors
- Test: `curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/v1/profiles/me`

## Contact Points

- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **Backend Health**: http://localhost:8000/health
- **Backend Docs**: http://localhost:8000/api/docs (if DEBUG=True)
- **Supabase Dashboard**: https://supabase.com/dashboard/project/jeixjsshohfyxgosfzuj

---

**Created**: December 24, 2025
**Purpose**: Diagnose frontend-backend connection issues
