# Deployment Guide

## Production Deployment

### Prerequisites

1. Linux server with Docker and Docker Compose
2. At least 2GB RAM and 10GB disk space
3. Open ports: 8000 (API), 9000-9001 (MinIO - optional)

### Deployment Steps

#### 1. Clone Repository

```bash
git clone https://github.com/ladlag/mercury4ai.git
cd mercury4ai
```

#### 2. Configure Environment

```bash
cp .env.example .env
nano .env  # or vim, vi, etc.
```

**Critical settings to change:**

```env
# REQUIRED: Change this to a secure random string
API_KEY=generate-a-secure-key-here

# Database password
POSTGRES_PASSWORD=change-this-secure-password

# MinIO credentials
MINIO_SECRET_KEY=change-this-secure-key
```

Generate secure keys:
```bash
# For API_KEY
openssl rand -hex 32

# For passwords
openssl rand -base64 24
```

#### 3. Start Services

```bash
docker-compose up -d
```

Check status:
```bash
docker-compose ps
```

All services should show "Up" status.

#### 4. Verify Deployment

```bash
# Health check
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/health

# Should return:
# {
#   "status": "healthy",
#   "timestamp": "...",
#   "database": "healthy",
#   "redis": "healthy",
#   "minio": "healthy"
# }
```

#### 5. Configure Firewall (Optional)

If exposing publicly:

```bash
# Allow API port
sudo ufw allow 8000/tcp

# Optionally allow MinIO (if needed)
sudo ufw allow 9000:9001/tcp
```

### Production Recommendations

#### 1. Use Reverse Proxy

Configure Nginx or Caddy in front of the API:

**Nginx example:**

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 2. Enable HTTPS

Use Let's Encrypt with Certbot:

```bash
sudo certbot --nginx -d api.yourdomain.com
```

#### 3. Configure Worker Scaling

Edit `docker-compose.yml` to scale workers:

```yaml
worker:
  # ...
  deploy:
    replicas: 4  # Increase for more concurrent crawls
```

Or use environment variable:

```bash
WORKER_CONCURRENCY=4 docker-compose up -d
```

#### 4. Set Up Monitoring

Monitor logs:
```bash
docker-compose logs -f --tail=100
```

Monitor resources:
```bash
docker stats
```

#### 5. Database Backups

Create regular PostgreSQL backups:

```bash
# Backup
docker-compose exec postgres pg_dump -U mercury4ai mercury4ai > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T postgres psql -U mercury4ai mercury4ai < backup_20240115.sql
```

#### 6. MinIO Backups

MinIO data is in Docker volume. To backup:

```bash
# Create backup
docker run --rm -v mercury4ai_minio_data:/data -v $(pwd):/backup alpine tar czf /backup/minio_backup_$(date +%Y%m%d).tar.gz /data

# Restore backup
docker run --rm -v mercury4ai_minio_data:/data -v $(pwd):/backup alpine tar xzf /backup/minio_backup_20240115.tar.gz -C /
```

### Maintenance

#### Update Application

```bash
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
```

#### Restart Services

```bash
# All services
docker-compose restart

# Specific service
docker-compose restart api
docker-compose restart worker
```

#### Clean Up Old Data

Clean old RQ jobs:
```bash
docker-compose exec redis redis-cli
> FLUSHDB  # Be careful - this clears all Redis data
```

### Troubleshooting

#### Services Won't Start

Check logs:
```bash
docker-compose logs
```

Common issues:
- Port conflicts: Check if ports 5432, 6379, 8000, 9000 are in use
- Memory: Ensure at least 2GB RAM available
- Permissions: Check Docker permissions

#### Database Connection Errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U mercury4ai -d mercury4ai -c "SELECT 1;"
```

#### Worker Not Processing Jobs

```bash
# Check worker status
docker-compose ps worker

# View worker logs
docker-compose logs -f worker

# Restart worker
docker-compose restart worker
```

#### MinIO Not Accessible

```bash
# Check MinIO status
docker-compose ps minio

# Access MinIO console
# http://localhost:9001
# Login with MINIO_ROOT_USER and MINIO_ROOT_PASSWORD from .env
```

### Performance Tuning

#### Database Performance

In `docker-compose.yml`, add PostgreSQL tuning:

```yaml
postgres:
  environment:
    # ... existing env vars ...
  command: >
    postgres
    -c shared_buffers=256MB
    -c max_connections=100
    -c effective_cache_size=1GB
```

#### Worker Concurrency

Scale based on your workload:
- Light usage: 1-2 workers
- Medium usage: 2-4 workers
- Heavy usage: 4-8 workers

Each worker can process one crawl task at a time.

#### Redis Memory

Monitor Redis memory usage:
```bash
docker-compose exec redis redis-cli INFO memory
```

Configure max memory in `docker-compose.yml`:
```yaml
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

### Security Hardening

1. **Change default credentials** in `.env`
2. **Use firewall** to restrict access
3. **Enable HTTPS** with valid certificates
4. **Rotate API keys** regularly
5. **Limit MinIO access** to internal network only
6. **Regular updates** of Docker images
7. **Monitor logs** for suspicious activity

### Scaling

#### Horizontal Scaling (Multiple Servers)

1. **External PostgreSQL**: Use managed PostgreSQL (AWS RDS, Azure Database)
2. **External Redis**: Use managed Redis (ElastiCache, Azure Cache)
3. **External MinIO**: Use S3-compatible storage (AWS S3, MinIO cluster)
4. **Multiple API instances**: Behind load balancer
5. **Multiple Worker instances**: On different servers

Example with external services:

```env
POSTGRES_HOST=postgres.example.com
REDIS_HOST=redis.example.com
MINIO_ENDPOINT=s3.amazonaws.com
MINIO_BUCKET=your-s3-bucket
```

#### Vertical Scaling (More Resources)

- Increase Docker resource limits
- Use dedicated server with more CPU/RAM
- Optimize database with indexes and query tuning

### Monitoring and Alerts

#### Simple Health Monitoring

Create a cron job:

```bash
# /etc/cron.d/mercury4ai-health
*/5 * * * * curl -f -H "X-API-Key: your-key" http://localhost:8000/api/health || echo "Health check failed" | mail -s "Mercury4AI Alert" admin@example.com
```

#### Log Rotation

Configure Docker log rotation in `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Restart Docker:
```bash
sudo systemctl restart docker
docker-compose up -d
```

### Support

For deployment issues:
- Check logs: `docker-compose logs`
- Verify environment: `docker-compose config`
- Review documentation: README.md
- Open issue: https://github.com/ladlag/mercury4ai/issues
