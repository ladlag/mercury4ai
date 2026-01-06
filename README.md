# Mercury4AI - Crawl4ai Orchestrator

A production-ready web crawling orchestrator built with FastAPI, RQ (Redis Queue), PostgreSQL, MinIO, and crawl4ai. This system enables LLM-powered structured data extraction from web pages with automatic image/attachment handling and comprehensive result archiving.

**Optimized for Chinese LLMs**: Recommended default is DeepSeek (深度求索) for cost-effective, high-quality extraction.

## Features

- **FastAPI RESTful API** with API Key authentication
- **Task Queue Processing** using RQ and Redis
- **LLM-Powered Extraction** via crawl4ai with schema-based structured output
- **Chinese LLM Support** - DeepSeek (深度求索), Qwen (通义千问), ERNIE (文心一言)
- **PostgreSQL Storage** for tasks, runs, and documents
- **MinIO Object Storage** for artifacts (markdown, JSON, images, attachments, logs)
- **Reusable Templates** for prompts and output schemas
- **Intelligent Media Handling** with fallback download strategy
- **URL Deduplication** and incremental crawling support
- **Task Import/Export** in JSON and YAML formats
- **Complete Artifact Archiving** with manifest and resource index
- **Docker Compose** deployment for easy setup

## Documentation

📚 **Complete documentation:**
- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
- **[CONFIG.md](CONFIG.md)** - Complete configuration guide with all options explained
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and design principles
- **[prompt_templates/README.md](prompt_templates/README.md)** - Reusable templates guide

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

For detailed architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/ladlag/mercury4ai.git
cd mercury4ai
```

### 2. Configure Environment (Optional)

The application will work out-of-the-box with default configurations. For production deployments or custom configurations:

```bash
cp .env.example .env
# Edit .env and set your API_KEY and other configurations
```

**Important**: 
- The default `API_KEY` is `your-secure-api-key-change-this`. Change this in production by setting the `API_KEY` environment variable or creating a `.env` file.
- If you don't create a `.env` file, the application will use defaults from `.env.example`. This is suitable for development and testing.

**For LLM-powered extraction**, set default LLM configuration in your `.env` file.

**Recommended: Use DeepSeek (cost-effective Chinese LLM)**:
```bash
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=deepseek-chat
DEFAULT_LLM_API_KEY=your-deepseek-api-key-here
DEFAULT_LLM_BASE_URL=https://api.deepseek.com
DEFAULT_LLM_TEMPERATURE=0.1
```

See [CONFIG.md](CONFIG.md) for complete configuration options.

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

### Example Task Configurations

See the `examples/` directory for sample task configurations:

**Basic Examples:**
- `task_news_extraction.json` - Full LLM configuration specified in task
- `task_product_extraction.yaml` - Full LLM configuration in YAML format
- `task_with_default_llm.yaml` - Uses default LLM config from environment (recommended)
- `task_partial_llm_override.json` - Partial override (uses default API key, custom model/temperature)
- `task_simple_scraping.yaml` - No LLM extraction, basic scraping only

**Chinese LLM Examples (国产大模型):**
- `task_chinese_llm_deepseek.json` - DeepSeek configuration example (recommended)
- `task_chinese_llm_qwen.yaml` - Qwen/Tongyi Qianwen configuration
- `task_bjhdedu_list_crawl.yaml` - Real-world list page crawling with Chinese LLM

For detailed Chinese LLM setup, see [CONFIG.md](CONFIG.md#chinese-llm-setup).

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

See [CONFIG.md](CONFIG.md) for complete configuration guide.

Key environment variables:
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
  - Supported providers: openai, anthropic, groq, **deepseek**, **qwen**, **ernie**, etc.
  - **Recommended**: DeepSeek (深度求索) for cost-effective Chinese LLM
- **Prompt Template**: Instruction for LLM extraction (can reference reusable templates)
- **Output Schema**: JSON Schema for structured output (can reference reusable schemas)
- **Deduplication**: Enable/disable URL deduplication
- **Date Filtering**: Only crawl content after a specific date
- **Fallback Download**: Automatic retry for failed media downloads

See [CONFIG.md](CONFIG.md) for detailed configuration options and examples.

## LLM Support

### Default Configuration (Recommended)

Set default LLM config in `.env` to avoid repetition:

```bash
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=deepseek-chat
DEFAULT_LLM_API_KEY=your-deepseek-api-key
DEFAULT_LLM_BASE_URL=https://api.deepseek.com
DEFAULT_LLM_TEMPERATURE=0.1
```

Then tasks only need prompt and schema:

```json
{
  "name": "Simple Task",
  "urls": ["https://example.com"],
  "prompt_template": "Extract the title and content...",
  "output_schema": {
    "type": "object",
    "properties": {
      "title": {"type": "string"},
      "content": {"type": "string"}
    }
  }
}
```

### Chinese LLM Support (国产大模型)

Mercury4AI fully supports Chinese domestic LLMs:

- **DeepSeek (深度求索)** - Recommended default, cost-effective
- **Qwen (通义千问)** - Alibaba's LLM with multiple models
- **ERNIE (文心一言)** - Baidu's LLM

**Quick Example with DeepSeek:**
```json
{
  "llm_provider": "openai",
  "llm_model": "deepseek-chat",
  "llm_params": {
    "api_key": "your-deepseek-api-key",
    "base_url": "https://api.deepseek.com",
    "temperature": 0.1
  },
  "prompt_template": "请提取文章的标题和内容..."
}
```

For complete Chinese LLM setup and examples, see [CONFIG.md](CONFIG.md#chinese-llm-setup).

## Reusable Templates

Create reusable prompt templates and output schemas for consistent extraction:

**Directory structure:**
```
prompt_templates/    # Reusable prompt templates
  ├── news_article_zh.txt
  ├── product_info_zh.txt
  └── ...
schemas/            # Reusable JSON schemas
  ├── news_article_zh.json
  ├── product_info_zh.json
  └── ...
```

**Usage in tasks (future enhancement):**
```json
{
  "name": "News Extraction",
  "urls": ["https://example.com"],
  "prompt_template": "@prompt_templates/news_article_zh.txt",
  "output_schema": "@schemas/news_article_zh.json"
}
```

See [prompt_templates/README.md](prompt_templates/README.md) for details.
```

#### 2. Qwen / Tongyi Qianwen (通义千问)

**Configuration Example:**
```json
{
  "llm_provider": "openai",
  "llm_model": "qwen-turbo",
  "llm_params": {
    "api_key": "your-dashscope-api-key",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "temperature": 0.1
  }
}
```

**Available Models:**
- `qwen-turbo` - Fast, cost-effective
- `qwen-plus` - Balanced performance
- `qwen-max` - Best quality

#### 3. Wenxin Yiyan / ERNIE Bot (文心一言)

**Configuration Example:**
```json
{
  "llm_provider": "openai",
  "llm_model": "ernie-bot-turbo",
  "llm_params": {
    "api_key": "your-baidu-api-key",
    "base_url": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop",
    "temperature": 0.1
  }
}
```

### Example Task Configurations

See the `examples/` directory for complete examples:
- `task_chinese_llm_deepseek.json` - DeepSeek configuration
- `task_chinese_llm_qwen.yaml` - Qwen configuration  
- `task_bjhdedu_list_crawl.yaml` - Real-world list page crawling example with Chinese LLM

### Chinese Language Prompts

You can write prompts in Chinese for better extraction quality:

```yaml
prompt_template: |
  请从这篇文章中提取以下信息：
  - 标题
  - 作者
  - 发布日期
  - 主要内容
  
  以JSON格式返回结果。
```

### Data Cleaning with Chinese LLMs

Both data extraction and cleaning benefit from Chinese LLMs:

1. **Primary Extraction**: Use Chinese LLM to extract structured data
2. **Post-Processing**: The extracted JSON data is automatically cleaned
3. **Custom Cleaning**: Add additional cleaning logic in `prompt_template`

**Example with cleaning instructions:**
```yaml
prompt_template: |
  请提取文章信息，并进行以下数据清洗：
  1. 移除所有HTML标签
  2. 统一日期格式为 YYYY-MM-DD
  3. 删除多余的空格和换行
  4. 规范化标点符号
  
  返回清洗后的JSON数据。
```
**Example with Deepseek (Chinese LLM):**
```json
{
  "llm_provider": "deepseek",
  "llm_model": "deepseek-chat",
  "llm_params": {
    "api_key": "your-deepseek-api-key",
    "temperature": 0.1,
    "max_tokens": 4000
  },
  "prompt_template": "请提取文章的标题和主要内容...",
  "output_schema": {
    "type": "object",
    "properties": {
      "title": {"type": "string"},
      "content": {"type": "string"}
    }
  }
}
```

**Example with Qwen / 通义千问:**
```json
{
  "llm_provider": "qwen",
  "llm_model": "qwen-plus",
  "llm_params": {
    "api_key": "your-qwen-api-key",
    "temperature": 0.1
  },
  "prompt_template": "提取页面中的结构化信息..."
}
```

See `examples/` directory for more examples including Chinese LLM configurations.

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

### API Not Responding

If the API container is running but not responding:

```bash
# Check API logs
docker-compose logs -f api

# Restart services
docker-compose restart api

# Rebuild if needed
docker-compose up -d --build
```

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

For more troubleshooting, see [CONFIG.md](CONFIG.md#troubleshooting).

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
- Documentation: See links below

## Additional Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
- **[CONFIG.md](CONFIG.md)** - Complete configuration guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture
- **[MIGRATION.md](MIGRATION.md)** - Upgrade guide from previous versions
- **[prompt_templates/README.md](prompt_templates/README.md)** - Reusable templates
