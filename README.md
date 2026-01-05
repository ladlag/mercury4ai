# Mercury4AI - Crawl4ai Orchestrator

A production-ready web crawling orchestrator built with FastAPI, RQ (Redis Queue), PostgreSQL, MinIO, and crawl4ai. This system enables LLM-powered structured data extraction from web pages with automatic image/attachment handling and comprehensive result archiving.

## Features

- **FastAPI RESTful API** with API Key authentication
- **Task Queue Processing** using RQ and Redis
- **LLM-Powered Extraction** via crawl4ai with schema-based structured output
- **PostgreSQL Storage** for tasks, runs, and documents
- **MinIO Object Storage** for artifacts (markdown, JSON, images, attachments, logs)
- **Intelligent Media Handling** with fallback download strategy
- **URL Deduplication** and incremental crawling support
- **Task Import/Export** in JSON and YAML formats
- **Complete Artifact Archiving** with manifest and resource index
- **Docker Compose** deployment for easy setup

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   FastAPI   │────────▶│    Redis     │◀────────│ RQ Workers  │
│     API     │         │   (Queue)    │         │  (Crawler)  │
└─────────────┘         └──────────────┘         └─────────────┘
       │                                                 │
       ▼                                                 ▼
┌─────────────┐                                  ┌─────────────┐
│ PostgreSQL  │                                  │    MinIO    │
│  (Metadata) │                                  │  (Storage)  │
└─────────────┘                                  └─────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/ladlag/mercury4ai.git
cd mercury4ai
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and set your API_KEY and other configurations
```

**Important**: Change the `API_KEY` in `.env` to a secure value.

### 3. Start Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- Redis (port 6379)
- MinIO (port 9000, console 9001)
- FastAPI API (port 8000)
- RQ Workers (2 instances by default)

### 4. Verify Health

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/health
```

### 5. Access Services

- **API Documentation**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **API**: http://localhost:8000

## Usage Guide

### Create a Crawl Task

Create a task to crawl one or more URLs:

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example News Crawl",
    "description": "Crawl news articles with LLM extraction",
    "urls": ["https://example.com/article1", "https://example.com/article2"],
    "crawl_config": {
      "verbose": true,
      "screenshot": false
    },
    "llm_provider": "openai",
    "llm_model": "gpt-4",
    "llm_params": {
      "api_key": "your-openai-api-key-here",
      "temperature": 0.1
    },
    "prompt_template": "Extract the title, author, publication date, and main content from this article.",
    "output_schema": {
      "type": "object",
      "properties": {
        "title": {"type": "string"},
        "author": {"type": "string"},
        "date": {"type": "string"},
        "content": {"type": "string"}
      }
    },
    "deduplication_enabled": true,
    "fallback_download_enabled": true,
    "fallback_max_size_mb": 10
  }'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Example News Crawl",
  ...
}
```

### Start a Task Run

```bash
curl -X POST http://localhost:8000/api/tasks/{task_id}/run \
  -H "X-API-Key: your-api-key"
```

Response:
```json
{
  "run_id": "660e8400-e29b-41d4-a716-446655440111",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Task run started"
}
```

### Check Run Status

```bash
curl http://localhost:8000/api/runs/{run_id} \
  -H "X-API-Key: your-api-key"
```

Response:
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440111",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "started_at": "2024-01-15T10:30:00",
  "completed_at": "2024-01-15T10:32:00",
  "urls_crawled": 2,
  "urls_failed": 0,
  "documents_created": 2,
  "minio_path": "2024-01-15/660e8400-e29b-41d4-a716-446655440111"
}
```

### Get Run Results

```bash
curl http://localhost:8000/api/runs/{run_id}/result \
  -H "X-API-Key: your-api-key"
```

Returns detailed information including all documents, images, and attachments.

### Get Run Logs and Artifacts

```bash
curl http://localhost:8000/api/runs/{run_id}/logs \
  -H "X-API-Key: your-api-key"
```

Returns MinIO paths and presigned URLs for downloading artifacts.

### Export/Import Tasks

Export a task to YAML:
```bash
curl http://localhost:8000/api/tasks/{task_id}/export?format=yaml \
  -H "X-API-Key: your-api-key" \
  -o task.yaml
```

Import a task from JSON:
```bash
curl -X POST http://localhost:8000/api/tasks/import?format=json \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: text/plain" \
  --data-binary @task.json
```

### List All Tasks

```bash
curl http://localhost:8000/api/tasks \
  -H "X-API-Key: your-api-key"
```

## MinIO Storage Structure

Artifacts are stored in MinIO with the following structure:

```
mercury4ai/
└── {YYYY-MM-DD}/
    └── {runId}/
        ├── json/
        │   └── {documentId}.json          # Structured data
        ├── markdown/
        │   └── {documentId}.md            # Markdown content
        ├── images/
        │   ├── {filename}.jpg
        │   └── {filename}.png
        ├── attachments/
        │   └── {filename}.pdf
        └── logs/
            ├── run_manifest.json          # Run metadata
            └── resource_index.json        # Resource catalog
```

## Database Schema

### Tables

- **crawl_task**: Task configurations
- **crawl_task_run**: Run instances and status
- **document**: Extracted documents
- **document_image**: Image metadata and storage
- **document_attachment**: Attachment metadata and storage
- **crawled_url_registry**: URL deduplication registry

## Configuration

### Environment Variables

See `.env.example` for all configuration options:

- `API_KEY`: API authentication key (required)
- `POSTGRES_*`: Database configuration
- `REDIS_*`: Redis configuration
- `MINIO_*`: MinIO configuration
- `FALLBACK_DOWNLOAD_*`: Fallback download settings
- `DEFAULT_LLM_*`: Default LLM settings

### Task Configuration

Each task supports:

- **URLs**: List of URLs to crawl
- **Crawl Config**: crawl4ai-specific settings (JS code, CSS selectors, etc.)
- **LLM Config**: Provider, model, and parameters for extraction
  - **Important**: Include your LLM API key in `llm_params`: `{"api_key": "sk-...", "temperature": 0.1}`
  - Supported providers: openai, anthropic, groq, etc.
- **Prompt Template**: Instruction for LLM extraction
- **Output Schema**: JSON Schema for structured output
- **Deduplication**: Enable/disable URL deduplication
- **Date Filtering**: Only crawl content after a specific date
- **Fallback Download**: Automatic retry for failed media downloads

### LLM Extraction

To use LLM-powered structured extraction:

1. Set `llm_provider` (e.g., "openai", "anthropic")
2. Set `llm_model` (e.g., "gpt-4", "claude-3-opus")
3. **Include API key in `llm_params`**: `{"api_key": "your-key-here", "temperature": 0.1}`
4. Define `prompt_template` with extraction instructions
5. Optionally define `output_schema` for structured JSON output

**Example with OpenAI:**
```json
{
  "llm_provider": "openai",
  "llm_model": "gpt-4",
  "llm_params": {
    "api_key": "sk-...",
    "temperature": 0.1,
    "max_tokens": 2000
  },
  "prompt_template": "Extract the title and main content...",
  "output_schema": {
    "type": "object",
    "properties": {
      "title": {"type": "string"},
      "content": {"type": "string"}
    }
  }
}
```

## Development

### Local Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with local settings

# Run database migrations
# (Tables are auto-created on first API startup)

# Run API locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run worker locally (in another terminal)
rq worker --url redis://localhost:6379/0 crawl_tasks
```

### Testing

```bash
# Health check
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/health

# View API docs
open http://localhost:8000/docs
```

## Troubleshooting

### Check Service Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f postgres
```

### Reset Database

```bash
docker-compose down -v
docker-compose up -d
```

### Verify Worker is Running

```bash
docker-compose ps
```

Should show worker service as "Up".

### MinIO Access Issues

Access MinIO console at http://localhost:9001 with credentials from `.env` (default: minioadmin/minioadmin). Verify bucket `mercury4ai` exists.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/` | Root endpoint |
| POST | `/api/tasks` | Create task |
| GET | `/api/tasks` | List tasks |
| GET | `/api/tasks/{id}` | Get task |
| PUT | `/api/tasks/{id}` | Update task |
| DELETE | `/api/tasks/{id}` | Delete task |
| GET | `/api/tasks/{id}/export` | Export task |
| POST | `/api/tasks/import` | Import task |
| POST | `/api/tasks/{id}/run` | Start task run |
| GET | `/api/runs/{id}` | Get run status |
| GET | `/api/runs/{id}/result` | Get run results |
| GET | `/api/runs/{id}/logs` | Get run logs |

All endpoints require `X-API-Key` header.

## Security

- **API Key Authentication**: All endpoints require valid API key
- **Network Isolation**: Services communicate via Docker network
- **Configurable Size Limits**: Prevent excessive downloads
- **Input Validation**: Pydantic models validate all inputs

## License

MIT License

## Support

For issues and questions:
- GitHub Issues: https://github.com/ladlag/mercury4ai/issues
