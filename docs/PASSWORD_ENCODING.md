# Password URL Encoding Guide

## The Problem

If your database password contains special characters like `@`, `#`, `%`, `&`, etc., they need to be URL-encoded in the `DATABASE_URL`.

## Quick Fix

### Option 1: Use Connection Pooler (Recommended - No Encoding Needed)

The Connection Pooler URL from Supabase handles special characters automatically.

1. Go to Supabase Dashboard → Project Settings → Database
2. Copy **Connection Pooling** → **Session mode** connection string
3. Paste directly into `.env` - no encoding needed!

### Option 2: URL Encode Your Password

If you must use direct connection, encode special characters:

#### Special Character Encoding

| Character | Encoded |
|-----------|---------|
| `@` | `%40` |
| `#` | `%23` |
| `%` | `%25` |
| `&` | `%26` |
| `+` | `%2B` |
| `=` | `%3D` |
| `?` | `%3F` |
| `/` | `%2F` |
| `:` | `%3A` |
| ` ` (space) | `%20` or `+` |

#### Example

**Password:** `Promzy199728@@`

**Encoded:** `Promzy199728%40%40`

**DATABASE_URL:**
```env
DATABASE_URL=postgresql://postgres:Promzy199728%40%40@db.jeixjsshohfyxgosfzuj.supabase.co:5432/postgres
```

#### Python Script to Encode

```python
from urllib.parse import quote_plus

password = "Promzy199728@@"
encoded = quote_plus(password)
print(f"Original: {password}")
print(f"Encoded:  {encoded}")
# Output: Promzy199728%40%40
```

## Your Current Issue

Your password `Promzy199728@@` contains `@@`, which breaks URL parsing.

**Solution:** Use Connection Pooler URL (no encoding needed) OR encode as `Promzy199728%40%40`

## Best Practice

**Always use Connection Pooler URL** - it:
- ✅ Handles special characters automatically
- ✅ More reliable (no IPv6 issues)
- ✅ Better for production
- ✅ No encoding needed

Get it from: Supabase Dashboard → Project Settings → Database → Connection Pooling

