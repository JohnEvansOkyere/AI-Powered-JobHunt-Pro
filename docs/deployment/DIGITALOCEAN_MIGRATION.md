# VeloxaHire — DigitalOcean Migration (run web + jobs as separate processes)

**Status:** Planned (currently on Render free tier — no background workers, so
periodic jobs do not run on their own).
**Goal:** Move the VeloxaHire backend to a DigitalOcean droplet where the **web
API**, the **Celery worker**, and the **Celery beat scheduler** each run as their
own long-lived process — so ATS sync, scraping, and recommendations run
automatically, independent of the web server.

This mirrors how the VeloxaRecruit (ATS) backend already runs on DO (systemd +
Gunicorn + Nginx).

---

## 1. Why the split

The FastAPI app and the background jobs are **different workloads** and must be
**different processes**:

| Process | Command | What it does | How many |
|---|---|---|---|
| **Web API** | `gunicorn app.main:app -k uvicorn.workers.UvicornWorker` | Serves HTTP (jobs browse, auth, handoff, `/ops`) | 1 service, N workers |
| **Celery worker** | `celery -A app.tasks.celery_app worker` | Executes queued tasks (scrape, sync, recommendations, cleanup) | 1 service, low concurrency |
| **Celery beat** | `celery -A app.tasks.celery_app beat` | Fires the schedule — enqueues tasks at the right time | **Exactly one. Never two.** |
| **Redis** | `redis-server` | Broker + result backend for Celery | 1 |

> ⚠️ **Beat must be a single instance.** Two beat processes = every job fires
> twice (double scraping, double recommendations, duplicate digests). If you
> ever keep the Render service alive alongside DO, make sure **only one** runs
> beat.

---

## 2. The jobs that will start running (from `app/tasks/celery_app.py`)

Once beat + worker are up, these run on their own:

| Schedule key | Task | When |
|---|---|---|
| `sync-ats-jobs-every-10-minutes` | `scheduler.sync_ats_jobs` | every 10 min — **mirrors recruiter jobs from VeloxaRecruit** |
| `scrape-recent-jobs-every-3-days` | `scheduler.scrape_recent_jobs` | 06:00 UTC, every 3rd day |
| `generate-recommendations-every-12-hours` | `scheduler.generate_recommendations_for_all` | every 12h |
| `backfill-empty-users-hourly` | `scheduler.generate_recommendations_for_empty_users` | hourly (:15) |
| `dispatch-whatsapp-digests-hourly` | `notifications.dispatch_whatsapp_digests` | hourly (:00) |
| `cleanup-expired-saved-jobs-daily` | `scheduler.cleanup_expired_saved_jobs` | 00:00 UTC |
| `cleanup-expired-recommendations-daily` | `scheduler.cleanup_expired_recommendations` | 00:05 UTC |
| `cleanup-old-jobs-daily` | `scheduler.cleanup_old_jobs` | 00:10 UTC |

Once this is live, the manual `POST /ops/ats-sync/backfill` (and any external
cron hitting it) can be retired — beat handles the 10-minute sync.

---

## 3. Droplet sizing

- **Minimum 2 GB RAM** (4 GB recommended). The recommendation/embeddings tasks
  and the worker are memory-hungry; on a 1 GB box the worker will OOM-kill.
- Ubuntu 22.04 LTS. 1–2 vCPU is fine to start.
- Redis runs on the same droplet (localhost) — no managed Redis needed initially.

---

## 4. One-time provisioning

```bash
# As root on the droplet
apt update && apt upgrade -y
apt install -y python3.11 python3.11-venv python3-pip redis-server nginx git certbot python3-certbot-nginx

systemctl enable --now redis-server      # broker + result backend
```

Deploy the code (CI or manual):

```bash
mkdir -p /var/www/veloxahire && cd /var/www/veloxahire
git clone <your-repo-url> .                 # or rsync your build
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn                         # not yet in requirements; web prod server
```

Create `/var/www/veloxahire/backend/.env` (NEVER commit it). Use
`backend/.env.example` as the source of truth, and make sure these are set:

```env
# Celery broker/backend — local Redis on the droplet
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Core app (same values you use on Render)
DATABASE_URL=...                 # Supabase Postgres
SUPABASE_URL=...
SUPABASE_KEY=...
SUPABASE_SERVICE_KEY=...
SUPABASE_JWT_SECRET=...

# Ecosystem integration (recruiter-job sync + apply handoff)
ATS_SYNC_ENABLED=true
ATS_PUBLISHED_JOBS_URL=https://api.veloxarecruit.com/integrations/published-jobs
ATS_SYNC_TOKEN=...               # == VeloxaRecruit CANDIDATE_SYNC_TOKEN
HANDOFF_TOKEN_SECRET=...         # == VeloxaRecruit HANDOFF_TOKEN_SECRET
CRON_SECRET=...

# AI + scraper keys (OpenAI, Adzuna, Jooble, etc.) — see .env.example
ENVIRONMENT=production
```

---

## 5. systemd services (the three processes)

### Web API — `/etc/systemd/system/veloxahire.service`
```ini
[Unit]
Description=VeloxaHire FastAPI (web)
After=network.target redis-server.service

[Service]
User=www-data
WorkingDirectory=/var/www/veloxahire/backend
EnvironmentFile=/var/www/veloxahire/backend/.env
ExecStart=/var/www/veloxahire/backend/venv/bin/gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker -w 2 -b 127.0.0.1:8000 \
    --timeout 120 --graceful-timeout 30
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### Celery worker — `/etc/systemd/system/veloxahire-worker.service`
```ini
[Unit]
Description=VeloxaHire Celery worker
After=network.target redis-server.service

[Service]
User=www-data
WorkingDirectory=/var/www/veloxahire/backend
EnvironmentFile=/var/www/veloxahire/backend/.env
ExecStart=/var/www/veloxahire/backend/venv/bin/celery -A app.tasks.celery_app worker \
    --loglevel=info --concurrency=2 --max-tasks-per-child=200
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Celery beat — `/etc/systemd/system/veloxahire-beat.service`
```ini
[Unit]
Description=VeloxaHire Celery beat (scheduler) - SINGLE INSTANCE ONLY
After=network.target redis-server.service

[Service]
User=www-data
WorkingDirectory=/var/www/veloxahire/backend
EnvironmentFile=/var/www/veloxahire/backend/.env
ExecStart=/var/www/veloxahire/backend/venv/bin/celery -A app.tasks.celery_app beat \
    --loglevel=info --schedule=/var/www/veloxahire/backend/celerybeat-schedule
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable + start all three:
```bash
chown -R www-data:www-data /var/www/veloxahire
systemctl daemon-reload
systemctl enable --now veloxahire veloxahire-worker veloxahire-beat
```

---

## 6. Nginx reverse proxy

`/etc/nginx/sites-available/veloxahire` → proxy to `127.0.0.1:8000`:
```nginx
server {
    server_name api.veloxahire.com;   # your VeloxaHire backend domain
    client_max_body_size 25M;         # CV uploads
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```
```bash
ln -s /etc/nginx/sites-available/veloxahire /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d api.veloxahire.com     # SSL
```

Then update the **frontend** `NEXT_PUBLIC_API_URL` (Vercel) and the
**VeloxaRecruit** `ATS_PUBLISHED_JOBS_URL` stays the same (it points at the ATS,
not VeloxaHire). Update CORS/allowed-origins on the backend if needed.

---

## 7. Deploy / update flow

```bash
cd /var/www/veloxahire && git pull
cd backend && source venv/bin/activate && pip install -r requirements.txt
# restart all three so code + schedule changes take effect
systemctl restart veloxahire veloxahire-worker veloxahire-beat
```

(Optional: a graceful web reload that preserves in-flight requests —
`systemctl reload veloxahire` if you switch Gunicorn to support SIGHUP.)

---

## 8. Verify it's actually working

```bash
# services up?
systemctl status veloxahire veloxahire-worker veloxahire-beat --no-pager

# worker reachable + tasks registered?
cd /var/www/veloxahire/backend && source venv/bin/activate
celery -A app.tasks.celery_app inspect ping
celery -A app.tasks.celery_app inspect registered | grep scheduler

# beat is firing? watch the log around a :*0 minute
journalctl -u veloxahire-beat -f

# the real proof — ATS sync ran on its own (no manual backfill):
curl https://api.veloxahire.com/api/v1/ops/ats-sync/status -H "X-Cron-Secret: <CRON_SECRET>"
#   -> last_success_at recent, last_trigger="scheduled", counts populated
```

---

## 9. Gotchas / checklist

- [ ] **Exactly one beat.** Decommission Render (or at least its scheduler) so jobs don't double-fire.
- [ ] **Redis must be running** before worker/beat (systemd `After=redis-server.service` handles ordering).
- [ ] **`gunicorn` is not in `requirements.txt`** yet — add it (or install in the venv) for the web service.
- [ ] **Memory:** keep worker `--concurrency` low (2) and `--max-tasks-per-child` set, to bound the embeddings/recommendation memory like the ATS droplet does.
- [ ] **Same secrets, same values:** `ATS_SYNC_TOKEN` and `HANDOFF_TOKEN_SECRET` must still match VeloxaRecruit's `CANDIDATE_SYNC_TOKEN` / `HANDOFF_TOKEN_SECRET`.
- [ ] **`.env` is never committed** — it's gitignored; set it on the droplet only.
- [ ] After cutover, **retire the external cron** that was hitting `/ops/ats-sync/backfill` (beat now owns the 10-minute sync). Keep the backfill endpoint for manual recovery.
- [ ] Optional later: a `render.yaml`/`Procfile` or a deploy GitHub Action mirroring the VeloxaRecruit CI/CD.
```
