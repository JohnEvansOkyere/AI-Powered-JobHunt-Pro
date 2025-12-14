# Session Mode Connection String Setup

According to [Supabase documentation](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler), **Session mode** uses a different format than Transaction mode.

## Session Mode Format

```
postgres://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
```

**Key differences from Direct Connection:**
- ✅ Port: **5432** (same as direct, but goes through pooler)
- ✅ Hostname: `aws-0-[REGION].pooler.supabase.com` (not `db.[PROJECT-REF].supabase.co`)
- ✅ Username: `postgres.[PROJECT-REF]` (not just `postgres`)

## How to Get Your Session Mode Connection String

### Option 1: From Supabase Dashboard

1. Go to your Supabase Dashboard
2. Click **"Connect"** button (top of the page)
3. In the modal, click the **"Connection Pooling"** tab (or look for pooler options)
4. Select **"Session mode"**
5. Copy the connection string

### Option 2: Construct Manually

If you can't find it in the dashboard, you can construct it manually:

1. **Get your project reference**: `jeixjsshohfyxgosfzuj` (from your current URL)
2. **Get your password**: From your current `DATABASE_URL`
3. **Find your region**: Check your Supabase project settings or try common regions:
   - `us-east-1` (most common for US projects)
   - `us-west-1`
   - `eu-west-1`
   - `ap-southeast-1`
   - `ap-northeast-1`

**Format:**
```env
DATABASE_URL=postgres://postgres.jeixjsshohfyxgosfzuj:[YOUR-PASSWORD]@aws-0-[YOUR-REGION].pooler.supabase.com:5432/postgres
```

**Example:**
```env
DATABASE_URL=postgres://postgres.jeixjsshohfyxgosfzuj:Promzy19970245540271@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

### Option 3: Check Your Project Settings

1. Go to: **Project Settings** → **Database**
2. Look for **"Connection Pooling"** section
3. Find **"Session mode"** connection string

## Verify It Works

After updating your `.env` file:

```bash
cd backend
python scripts/test_db_connection.py
```

Should show: `✅ Database connection successful!`

## Difference: Session Mode vs Transaction Mode

| Feature | Session Mode | Transaction Mode |
|---------|-------------|------------------|
| Port | 5432 | 6543 |
| Hostname | `aws-0-[REGION].pooler.supabase.com` | `db.[PROJECT-REF].supabase.co` |
| Username | `postgres.[PROJECT-REF]` | `postgres` |
| Best for | Persistent backends needing IPv4 | Serverless/edge functions |
| Prepared statements | ✅ Supported | ❌ Not supported |

## Why Session Mode?

- ✅ Supports IPv4 (fixes your IPv6 issue)
- ✅ Works with SQLAlchemy prepared statements
- ✅ Ideal for persistent backend services
- ✅ Same port (5432) as direct connection, but through pooler

