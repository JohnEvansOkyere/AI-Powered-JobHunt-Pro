#!/bin/bash

# Setup Cron Jobs for Automated Job Management
#
# This script sets up two daily cron jobs:
# 1. Daily job scraping (2 AM)
# 2. Daily database cleanup (3 AM)

BACKEND_DIR="/home/grejoy/Projects/AI-Powered-JobHunt-Pro/backend"
PYTHON_BIN="/home/grejoy/Projects/AI-Powered-JobHunt-Pro/backend/venv/bin/python3"

# Check if running in backend directory
if [ ! -f "daily_job_scraper.py" ]; then
    echo "❌ Error: Must run this script from the backend directory"
    exit 1
fi

echo "🔧 Setting up cron jobs for automated job management..."
echo ""

# Create cron job entries
CRON_SCRAPER="0 2 * * * cd $BACKEND_DIR && $PYTHON_BIN daily_job_scraper.py >> logs/job_scraper.log 2>&1"
CRON_CLEANUP="0 3 * * * cd $BACKEND_DIR && $PYTHON_BIN cleanup_old_jobs.py >> logs/job_cleanup.log 2>&1"

# Create logs directory if it doesn't exist
mkdir -p logs

# Backup existing crontab
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || true

# Check if cron jobs already exist
if crontab -l 2>/dev/null | grep -q "daily_job_scraper.py"; then
    echo "⚠️  Cron jobs already exist. Removing old ones..."
    crontab -l 2>/dev/null | grep -v "daily_job_scraper.py" | grep -v "cleanup_old_jobs.py" | crontab - 2>/dev/null || true
fi

# Add new cron jobs
(crontab -l 2>/dev/null; echo ""; echo "# AI JobHunt Pro - Automated Jobs"; echo "$CRON_SCRAPER"; echo "$CRON_CLEANUP") | crontab -

echo "✅ Cron jobs installed successfully!"
echo ""
echo "📅 Schedule:"
echo "   • Daily job scraping: 2:00 AM (scrapes RemoteOK, SerpAPI)"
echo "   • Daily cleanup:      3:00 AM (archives old jobs, cleans DB)"
echo ""
echo "📝 Logs will be saved to:"
echo "   • Job scraper: $BACKEND_DIR/logs/job_scraper.log"
echo "   • Cleanup:     $BACKEND_DIR/logs/job_cleanup.log"
echo ""
echo "🔍 View current cron jobs:"
echo "   crontab -l"
echo ""
echo "📊 Test manually (without waiting for cron):"
echo "   python3 daily_job_scraper.py"
echo "   python3 cleanup_old_jobs.py"
echo ""
echo "✅ Setup complete!"
