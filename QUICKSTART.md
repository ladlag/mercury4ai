# Quick Start Guide

Get Mercury4AI up and running in 5 minutes!

## Prerequisites

- Docker and Docker Compose installed
- 2GB free RAM
- 10GB free disk space

## Steps

### 1. Clone and Configure

```bash
git clone https://github.com/ladlag/mercury4ai.git
cd mercury4ai
```

**Optional Configuration**: The application works with default settings. For production or custom setups, create a `.env` file:

```bash
cp .env.example .env
# Generate a secure API key
openssl rand -hex 32
# Update API_KEY in .env with the generated key
```

**Note**: Without a `.env` file, the default `API_KEY` is `your-secure-api-key-change-this`. Change this in production.

### 2. Start Services

```bash
docker compose up -d
```

Wait 30-60 seconds for all services to start.

### 3. Verify Installation

```bash
chmod +x validate.sh
./validate.sh
```

Or manually:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/health
```

Should return:
```json
{
  "status": "healthy",
  "database": "healthy",
  "redis": "healthy",
  "minio": "healthy"
}
```

### 4. Create Your First Task

Using one of the examples:

```bash
curl -X POST http://localhost:8000/api/tasks/import?format=json \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: text/plain" \
  --data-binary @examples/task_simple_scraping.yaml
```

Response will include the task ID:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Simple Web Scraping (No LLM)",
  "message": "Task imported successfully"
}
```

### 5. Run the Task

```bash
curl -X POST http://localhost:8000/api/tasks/550e8400-e29b-41d4-a716-446655440000/run \
  -H "X-API-Key: your-api-key"
```

Response:
```json
{
  "run_id": "660e8400-e29b-41d4-a716-446655440111",
  "status": "pending",
  "message": "Task run started"
}
```

### 6. Check Progress

```bash
# Check run status
curl -H "X-API-Key: your-api-key" \
  http://localhost:8000/api/runs/660e8400-e29b-41d4-a716-446655440111

# Get detailed results
curl -H "X-API-Key: your-api-key" \
  http://localhost:8000/api/runs/660e8400-e29b-41d4-a716-446655440111/result
```

### 7. Access Results

Results are stored in MinIO:

- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **API Documentation**: http://localhost:8000/docs

Check the bucket `mercury4ai` for run artifacts organized by date.

## Troubleshooting

### Services won't start

```bash
# Check service status
docker compose ps

# Check logs
docker compose logs -f

# Restart services
docker compose restart
```

### API not responding

```bash
# Check API logs
docker compose logs -f api

# Verify API is running
curl http://localhost:8000/
```

### Worker not processing jobs

```bash
# Check worker logs
docker compose logs -f worker

# Restart workers
docker compose restart worker
```

### Database errors

```bash
# Check database
docker compose exec postgres psql -U mercury4ai -d mercury4ai -c "SELECT 1;"

# Restart database
docker compose restart postgres
```

## Next Steps

1. **Read the full documentation**: [README.md](README.md)
2. **Review task examples**: [examples/](examples/)
3. **Learn about deployment**: [DEPLOYMENT.md](DEPLOYMENT.md)
4. **Configure LLM extraction**: Add your LLM API keys to tasks
5. **Customize crawl behavior**: Modify task configurations
6. **Scale workers**: Adjust `deploy.replicas` in docker-compose.yml

## Common Tasks

### Create a custom task

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Custom Task",
    "urls": ["https://example.com/page"],
    "crawl_config": {"verbose": true},
    "deduplication_enabled": true,
    "fallback_download_enabled": true,
    "fallback_max_size_mb": 10
  }'
```

### List all tasks

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/tasks
```

### Export a task

```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:8000/api/tasks/TASK_ID/export?format=yaml > my_task.yaml
```

### View logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f worker
```

### Stop services

```bash
docker compose down

# With volume cleanup
docker compose down -v
```

## Getting Help

- Check logs: `docker compose logs -f`
- Review [README.md](README.md) for detailed documentation
- Check [DEPLOYMENT.md](DEPLOYMENT.md) for production setup
- Open an issue: https://github.com/ladlag/mercury4ai/issues

## Success!

You now have a fully functional web crawling orchestrator running! 🎉

Visit http://localhost:8000/docs to explore the interactive API documentation.
