#!/usr/bin/env python3
"""
Database Connection Test Script

Tests the database connection and provides helpful error messages.
"""

import os
import sys
from sqlalchemy import create_engine, text
from urllib.parse import urlparse

def test_connection(database_url: str):
    """Test database connection."""
    print("Testing database connection...")
    print(f"URL: {database_url.split('@')[0]}@***")  # Hide password
    
    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            if row and row[0] == 1:
                print("✅ Database connection successful!")
                return True
            else:
                print("❌ Connection succeeded but query failed")
                return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\nTroubleshooting:")
        
        error_str = str(e)
        if "Network is unreachable" in error_str or "connection" in error_str.lower():
            print("1. Your DATABASE_URL is using direct connection (port 5432)")
            print("2. Try using Connection Pooler instead (port 6543):")
            print("   - Go to Supabase Dashboard → Project Settings → Database")
            print("   - Find 'Connection pooling' section")
            print("   - Copy 'Session mode' connection string")
            print("   - It should look like:")
            print("     postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true")
        
        if "password authentication" in error_str.lower():
            print("1. Password authentication failed")
            print("2. Reset your database password in Supabase Dashboard")
            print("3. Update DATABASE_URL with new password")
        
        if "could not translate host name" in error_str.lower():
            print("1. Invalid hostname in DATABASE_URL")
            print("2. Check your Supabase project reference")
        
        return False

if __name__ == "__main__":
    # Try to load from .env
    from dotenv import load_dotenv
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        print("\nPlease set DATABASE_URL in your .env file:")
        print("DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true")
        sys.exit(1)
    
    # Check if using pooler
    parsed = urlparse(database_url)
    if parsed.port == 6543 or "pooler" in parsed.hostname:
        print("✅ Using Connection Pooler (recommended)")
    elif parsed.port == 5432:
        print("⚠️  Using Direct Connection (may have IPv6 issues)")
        print("   Consider switching to Connection Pooler (port 6543)")
    
    success = test_connection(database_url)
    sys.exit(0 if success else 1)

