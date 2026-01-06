# Docker Command Format Fix

## Issue
If you're experiencing issues where:
- Docker containers show as running (`docker compose ps` shows healthy containers)
- API endpoints return HTTP 502 errors or hang indefinitely
- The API logs show "Uvicorn running on http://0.0.0.0:8000" but no request logs appear
- curl commands to the API timeout or return no response

This is caused by incorrect command format in `docker-compose.yml`.

## Root Cause
When Docker Compose commands are specified as strings (e.g., `command: uvicorn app.main:app --host 0.0.0.0 --port 8000`), Docker executes them via `/bin/sh -c`. This can cause:
- Improper process signal handling
- Incorrect process binding to network interfaces
- The application appearing to start but not actually accepting connections

## Solution
Convert all service commands in `docker-compose.yml` from string format to array format.

### Before (Incorrect)
```yaml
services:
  api:
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
  
  worker:
    command: rq worker --url redis://redis:6379/0 crawl_tasks
    
  minio:
    command: server /data --console-address ":9001"
```

### After (Correct)
```yaml
services:
  api:
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  
  worker:
    command: ["rq", "worker", "--url", "redis://redis:6379/0", "crawl_tasks"]
    
  minio:
    command: ["server", "/data", "--console-address", ":9001"]
```

## How to Apply the Fix

### Option 1: Pull Latest Changes (Recommended)
```bash
cd mercury4ai
git pull origin main
docker compose down
docker compose up -d --build
```

### Option 2: Manual Fix
If you can't pull the latest changes, manually edit your `docker-compose.yml`:

1. Open `docker-compose.yml` in a text editor
2. Find each service with a `command:` field
3. Convert string commands to array format (see examples above)
4. Save the file
5. Restart services:
   ```bash
   docker compose down
   docker compose up -d --build
   ```

## Verification

After applying the fix, verify it works:

```bash
# Wait for services to start (30-60 seconds)
sleep 30

# Test the API endpoint
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/health

# Should return JSON with status information
# If successful, you should see:
# {"status":"healthy","timestamp":"...","database":"healthy","redis":"healthy","minio":"healthy"}
```

Check that the API now logs incoming requests:
```bash
docker compose logs api | tail -20
```

You should now see request logs like:
```
INFO:     127.0.0.1:xxxxx - "GET /api/health HTTP/1.1" 200 OK
```

## Additional Notes

- This fix is already applied in the latest version of the repository
- The issue affects Docker Compose configurations but not standalone Docker runs using the Dockerfile CMD
- All service commands should use array format for consistency and reliability
- If you still experience issues after applying this fix, see [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting section

## Related Issues
- Docker Compose string vs array command format: https://docs.docker.com/compose/compose-file/05-services/#command
- Process signal handling in containers
