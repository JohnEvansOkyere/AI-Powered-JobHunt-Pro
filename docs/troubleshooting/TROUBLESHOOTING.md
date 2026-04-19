# Troubleshooting Guide

> **Note:** For comprehensive error documentation, see [ERRORS_AND_SOLUTIONS.md](./ERRORS_AND_SOLUTIONS.md)

## Database Connection Issues

### Error: "Network is unreachable" when connecting to Supabase

This error typically occurs when:
1. IPv6 connectivity issues
2. Firewall blocking the connection
3. Incorrect DATABASE_URL format
4. Supabase connection pooler not configured

### Solutions

#### 1. Use IPv4 Connection String

Supabase provides different connection strings. For direct connections, use the **IPv4 connection string** instead of IPv6.

**In Supabase Dashboard**:
- Go to Project Settings → Database
- Under "Connection string", select **"URI"** or **"Connection pooling"**
- Use the connection string that starts with `postgresql://` (not IPv6)

**Example**:
```env
# Direct connection (use this if connection pooling doesn't work)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# Connection pooling (recommended for production)
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

#### 2. Use Connection Pooler (Recommended)

Supabase provides a connection pooler that's more reliable:

1. Go to Supabase Dashboard → Project Settings → Database
2. Find "Connection pooling" section
3. Copy the "Session mode" connection string
4. Use port **6543** (pooler) instead of **5432** (direct)

**Format**:
```
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true
```

#### 3. Check Network Connectivity

Test if you can reach Supabase:

```bash
# Test IPv4 connection
ping db.[PROJECT-REF].supabase.co

# Test with psql (if installed)
psql "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
```

#### 4. Verify DATABASE_URL Format

Your DATABASE_URL should be in this format:

```env
DATABASE_URL=postgresql://[USER]:[PASSWORD]@[HOST]:[PORT]/[DATABASE]
```

**Important**:
- Replace `[PASSWORD]` with your actual password (URL-encode special characters)
- Use IPv4 hostname, not IPv6
- Port 5432 for direct, 6543 for pooler

#### 5. URL Encode Password

If your password contains special characters, URL-encode them:

```python
from urllib.parse import quote_plus

password = "your@password#123"
encoded = quote_plus(password)
# Use encoded in DATABASE_URL
```

#### 6. Use Supabase Client Instead (Alternative)

If direct PostgreSQL connection fails, you can use Supabase client for database operations:

```python
from app.core.supabase_client import get_supabase_service_client

supabase = get_supabase_service_client()
# Use supabase.table() for queries instead of SQLAlchemy
```

### Common Issues

#### Issue: IPv6 Address in Error

**Error**: `connection to server at "...supabase.co" (2a05:d01c:...) failed`

**Solution**: Force IPv4 by using the connection pooler or ensuring your DATABASE_URL uses the IPv4 hostname.

#### Issue: Connection Timeout

**Error**: `connection timeout` or `connection refused`

**Solutions**:
1. Check if Supabase project is paused (free tier pauses after inactivity)
2. Verify firewall isn't blocking port 5432 or 6543
3. Try connection pooler (port 6543)
4. Check Supabase status page

#### Issue: Authentication Failed

**Error**: `password authentication failed`

**Solutions**:
1. Reset database password in Supabase Dashboard
2. Verify password in DATABASE_URL matches
3. URL-encode special characters in password
4. Check if using correct user (usually `postgres`)

### Testing Connection

Create a test script:

```python
# test_db_connection.py
from sqlalchemy import create_engine, text
from app.core.config import settings

try:
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Database connection successful!")
        print(f"Result: {result.fetchone()}")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
```

Run it:
```bash
cd backend
python test_db_connection.py
```

### Supabase Connection Settings

In Supabase Dashboard → Project Settings → Database:

1. **Connection Pooling**: Enable if available
2. **Direct Connection**: Use for development
3. **Session Mode**: Recommended for most applications
4. **Transaction Mode**: For specific use cases

### Environment Variables

Ensure your `.env` file has:

```env
# Use connection pooler (recommended)
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true

# OR direct connection (if pooler doesn't work)
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

### Still Having Issues?

1. **Check Supabase Status**: https://status.supabase.com
2. **Verify Project is Active**: Free tier projects pause after inactivity
3. **Check Firewall**: Ensure ports 5432/6543 aren't blocked
4. **Try Different Network**: Test from different network/VPN
5. **Contact Supabase Support**: If issue persists

