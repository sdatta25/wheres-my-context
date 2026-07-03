# Deploy Where's My Context

## Option 1: Vercel (Recommended — 2 minutes)

```bash
# 1. Fork the repo
# 2. Connect to Vercel dashboard

# 3. Set environment variables in Vercel:
MEMORY_ENGINE=cognee_cloud
COGNEE_CLOUD_URL=https://tenant-xxx.aws.cognee.ai
COGNEE_TENANT_ID=your-tenant-id
COGNEE_API_KEY=your-api-key
SEED_ON_START=1

# 4. Deploy (auto-deploys on git push)
```

**Result:** `https://your-project.vercel.app` (live in ~1 minute)

---

## Option 2: Docker (Production)

```dockerfile
# Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t where-my-context .
docker run -e MEMORY_ENGINE=cognee_cloud \
  -e COGNEE_CLOUD_URL=... \
  -e COGNEE_API_KEY=... \
  -p 8000:8000 where-my-context
```

---

## Option 3: Heroku (Free tier + $7/month)

```bash
heroku create your-app-name
git push heroku main
heroku config:set MEMORY_ENGINE=cognee_cloud
heroku config:set COGNEE_CLOUD_URL=...
heroku config:set COGNEE_API_KEY=...
```

---

## Environment Variables

| Var | Required? | Example |
|-----|-----------|---------|
| `MEMORY_ENGINE` | Yes | `cognee_cloud` or `demo` |
| `COGNEE_CLOUD_URL` | If engine=cognee_cloud | `https://tenant-abc.aws.cognee.ai` |
| `COGNEE_TENANT_ID` | If engine=cognee_cloud | Your tenant ID |
| `COGNEE_API_KEY` | If engine=cognee_cloud | Your API key |
| `PORT` | No (default 8000) | `8000` |
| `SEED_ON_START` | No (default 1) | `0` to skip seeding |

---

## Development

```bash
./run.sh  # starts on http://localhost:8000
```

Or manually:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

---

## Testing Your Deployment

1. Visit `https://your-app.vercel.app`
2. Check `/api/status` → should show engine + memory count
3. Add a memory → graph should update
4. Ask a question → should get an answer
5. Recall → should show context brief for new session

---

## Troubleshooting

**Graph is empty:**  
→ Set `SEED_ON_START=1` or click "Seed demo" button

**Cognee Cloud errors:**  
→ Check API key + tenant ID are correct in env vars  
→ Verify `COGNEE_CLOUD_URL` ends with `.ai` (not trailing slash)

**Frontend won't load:**  
→ Check backend is running: `curl http://localhost:8000`  
→ Clear browser cache

**Slow responses:**  
→ Cognee Cloud might be cognifying — takes a few seconds on first call  
→ Check `/api/status` health metrics
