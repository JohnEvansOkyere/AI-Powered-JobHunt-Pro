#!/usr/bin/env python3
"""
Check Environment Variables

Quick script to verify your .env file has all required variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

print("=" * 60)
print("Environment Variables Check")
print("=" * 60)

required_vars = {
    "DATABASE_URL": "PostgreSQL connection string",
    "SUPABASE_URL": "Supabase project URL",
    "SUPABASE_KEY": "Supabase anon key",
    "SUPABASE_SERVICE_KEY": "Supabase service key",
    "SECRET_KEY": "JWT secret key",
}

optional_vars = {
    "OPENAI_API_KEY": "OpenAI API key",
    "GEMINI_API_KEY": "Gemini API key",
    "GROK_API_KEY": "Grok API key",
    "GROQ_API_KEY": "Groq API key",
}

print("\n📋 Required Variables:")
print("-" * 60)
all_ok = True
for var, desc in required_vars.items():
    value = os.getenv(var)
    if value:
        # Mask sensitive values
        if "KEY" in var or "PASSWORD" in var or "SECRET" in var:
            display = value[:10] + "..." if len(value) > 10 else "***"
        else:
            display = value[:50] + "..." if len(value) > 50 else value
        print(f"✅ {var:25} = {display}")
        
        # Check for placeholders
        if "[" in value or "your_" in value.lower() or value.strip() == "":
            print(f"   ⚠️  WARNING: Contains placeholder or is empty!")
            all_ok = False
    else:
        print(f"❌ {var:25} = NOT SET")
        print(f"   Description: {desc}")
        all_ok = False

print("\n📋 Optional Variables (AI Providers):")
print("-" * 60)
ai_providers_set = 0
for var, desc in optional_vars.items():
    value = os.getenv(var)
    if value and value.strip():
        display = value[:10] + "..." if len(value) > 10 else "***"
        print(f"✅ {var:25} = {display}")
        ai_providers_set += 1
    else:
        print(f"⚪ {var:25} = Not set (optional)")

print("\n" + "=" * 60)
if all_ok:
    print("✅ All required variables are set!")
    if ai_providers_set == 0:
        print("⚠️  No AI provider keys set - at least one is recommended")
    elif ai_providers_set > 0:
        print(f"✅ {ai_providers_set} AI provider(s) configured")
else:
    print("❌ Some required variables are missing or have placeholders")
    print("\nPlease check your backend/.env file")
    print("See docs/SETUP.md for setup instructions")

print("=" * 60)

# Check DATABASE_URL format specifically
db_url = os.getenv("DATABASE_URL")
if db_url:
    print("\n🔍 DATABASE_URL Analysis:")
    print("-" * 60)
    
    if db_url.startswith("postgresql://"):
        print("✅ Format: postgresql:// (correct)")
    elif db_url.startswith("postgresql+psycopg2://"):
        print("✅ Format: postgresql+psycopg2:// (correct)")
    else:
        print(f"❌ Format: {db_url[:30]}... (should start with postgresql://)")
    
    if "pooler" in db_url or "pgbouncer" in db_url:
        print("✅ Using Connection Pooler (recommended)")
        if ":6543" in db_url:
            print("✅ Port: 6543 (pooler port - correct)")
        else:
            print("⚠️  Port: Should be 6543 for pooler")
    else:
        print("⚠️  Using Direct Connection (may have IPv6 issues)")
        if ":5432" in db_url:
            print("✅ Port: 5432 (direct connection)")
        else:
            print("⚠️  Port: Should be 5432 for direct connection")
    
    if "[" in db_url or "]" in db_url:
        print("❌ Contains placeholder brackets [ ] - replace with actual values")
    
    if db_url.count("@") != 1:
        print("❌ URL format is incorrect (should have exactly one @)")
        print("   This usually means your password contains '@' character")
        print("   Solution: URL-encode your password or use Connection Pooler URL from Supabase")
        print("   Example: If password is 'pass@word', encode it as 'pass%40word'")
        print("   Or better: Use Connection Pooler URL which handles this automatically")
    
    # Check for common issues
    issues = []
    if "your_" in db_url.lower():
        issues.append("Contains 'your_' placeholder")
    if "[PASSWORD]" in db_url or "[PROJECT-REF]" in db_url:
        issues.append("Contains placeholder values like [PASSWORD]")
    if db_url.strip() == "":
        issues.append("Is empty or just whitespace")
    
    if issues:
        print("\n❌ Issues found:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("\n✅ DATABASE_URL format looks good!")

print("\n" + "=" * 60)

