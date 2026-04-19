# Deployment Guide

Production deployment instructions for Render (backend) and Vercel (frontend).

## Backend Deployment (Render)

### 1. Prepare Repository

Ensure all code is committed and pushed to your Git repository.

### 2. Create Render Service

1. Go to [render.com](https://render.com) and create a new account
2. Click "New +" → "Web Service"
3. Connect your Git repository
4. Configure the service:
   - **Name**: `ai-job-platform-api` (or your choice)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Root Directory**: `backend`

### 3. Configure Environment Variables

Add all environment variables from `.env.example` in Render dashboard:
- Supabase credentials
- Database URL
- AI provider API keys
- Secret keys
- Redis URL (if using external Redis)

### 4. Add Redis Service (for Celery)

1. Create a new Redis service in Render
2. Note the Redis URL
3. Update `REDIS_URL` in your web service environment variables

### 5. Add Background Worker

1. Create a new "Background Worker" service
2. Connect to the same repository
3. **Start Command**: `celery -A app.tasks.celery_app worker --loglevel=info`
   - Or: `celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4`
4. Use the same environment variables as the web service

### 6. Configure Health Checks

Render will automatically check `/health` endpoint. Ensure it's working.

## Frontend Deployment (Vercel)

### 1. Prepare Repository

Ensure all code is committed and pushed.

### 2. Create Vercel Project

1. Go to [vercel.com](https://vercel.com) and create an account
2. Click "New Project"
3. Import your Git repository
4. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build` (or `yarn build`)
   - **Output Directory**: `.next`

### 3. Configure Environment Variables

Add in Vercel dashboard:
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_URL` (your Render backend URL)

### 4. Deploy

Click "Deploy" and wait for build to complete.

### 5. Update CORS in Backend

Update `CORS_ORIGINS` in backend to include your Vercel domain:
```
CORS_ORIGINS=https://your-app.vercel.app,https://your-custom-domain.com
```

## Post-Deployment Checklist

- [ ] Backend health check works
- [ ] Frontend loads correctly
- [ ] Authentication works
- [ ] API endpoints are accessible
- [ ] CORS is configured correctly
- [ ] Environment variables are set
- [ ] Background workers are running
- [ ] Database migrations are applied
- [ ] Supabase RLS policies are active
- [ ] Storage bucket is configured

## Monitoring

### Backend (Render)

- Monitor logs in Render dashboard
- Set up alerts for errors
- Monitor resource usage

### Frontend (Vercel)

- Check Vercel analytics
- Monitor build logs
- Set up error tracking (Sentry recommended)

## Scaling Considerations

- **Backend**: Render auto-scales, but monitor costs
- **Database**: Supabase has scaling limits on free tier
- **Redis**: Consider managed Redis for production
- **AI Costs**: Monitor API usage and costs
- **Storage**: Monitor Supabase storage usage

## Security Checklist

- [ ] All secrets are in environment variables (not in code)
- [ ] CORS is properly configured
- [ ] RLS policies are active in Supabase
- [ ] API rate limiting is configured
- [ ] HTTPS is enabled (automatic on Vercel/Render)
- [ ] Secrets are rotated regularly

## Troubleshooting

### Backend Won't Start

- Check logs in Render dashboard
- Verify all environment variables are set
- Check database connection
- Verify Python version compatibility

### Frontend Build Fails

- Check build logs in Vercel
- Verify all environment variables
- Check for TypeScript errors
- Verify dependencies are installed

### API Errors

- Check CORS configuration
- Verify backend URL is correct
- Check network requests in browser console
- Verify authentication tokens

