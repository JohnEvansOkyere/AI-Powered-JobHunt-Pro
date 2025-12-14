#!/bin/bash
# Quick script to help update DATABASE_URL to use Connection Pooler

echo "=========================================="
echo "Database Connection Fix Helper"
echo "=========================================="
echo ""
echo "Current issue: Using direct connection (port 5432) with IPv6 problems"
echo "Solution: Switch to Connection Pooler (port 6543)"
echo ""
echo "📋 Steps to fix:"
echo ""
echo "1. Go to Supabase Dashboard:"
echo "   https://supabase.com/dashboard/project/jeixjsshohfyxgosfzuj/settings/database"
echo ""
echo "2. Scroll to 'Connection Pooling' section"
echo ""
echo "3. Copy the 'Session mode' connection string"
echo "   It should look like:"
echo "   postgresql://postgres.jeixjsshohfyxgosfzuj:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true"
echo ""
echo "4. Update backend/.env file:"
echo "   Replace DATABASE_URL with the Connection Pooler URL"
echo ""
echo "5. Restart your backend server"
echo ""
echo "=========================================="
echo ""
echo "Current DATABASE_URL (first 60 chars):"
if [ -f .env ]; then
    grep "^DATABASE_URL=" .env | head -1 | cut -c1-60
    echo "..."
    echo ""
    echo "Is it using port 6543 (pooler)?"
    if grep "^DATABASE_URL=" .env | grep -q ":6543"; then
        echo "✅ Yes - using Connection Pooler"
    else
        echo "❌ No - still using direct connection (port 5432)"
        echo "   You need to update it to use Connection Pooler!"
    fi
else
    echo "❌ .env file not found in backend directory"
fi
echo ""

