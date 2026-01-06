# Mercury4AI Architecture

## Overview

Mercury4AI is a production-ready web crawling orchestrator that combines FastAPI, crawl4ai, RQ (Redis Queue), PostgreSQL, and MinIO to provide scalable, LLM-powered structured data extraction from web pages.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                              │
│  (HTTP Clients, curl, Web Browser, Python SDK)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP/REST API
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      FastAPI Application                          │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Tasks     │  │    Runs     │  │   Health    │             │
│  │   API       │  │    API      │  │   Check     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │   Import/   │  │    Auth     │                               │
│  │   Export    │  │  Middleware │                               │
│  └─────────────┘  └─────────────┘                               │
└───────────┬──────────────────────┬──────────────────────────────┘
            │                      │
            │ Metadata             │ Job Queue
            │                      │
┌───────────▼──────────┐  ┌────────▼──────────┐
│   PostgreSQL         │  │      Redis        │
│                      │  │                   │
│  - Tasks Config      │  │  - Job Queue      │
│  - Run Status        │  │  - Worker Status  │
│  - Documents         │  │  - Task State     │
│  - URL Registry      │  │                   │
└──────────────────────┘  └───────┬───────────┘
                                  │
                                  │ Poll Jobs
                                  │
                   ┌──────────────▼──────────────┐
                   │      RQ Workers             │
                   │  (Multiple Instances)       │
                   │                             │
                   │  ┌──────────────────────┐  │
                   │  │  Crawl Worker        │  │
                   │  │                      │  │
                   │  │  - Task Execution    │  │
                   │  │  - URL Crawling      │  │
                   │  │  - LLM Extraction    │  │
                   │  │  - Media Download    │  │
                   │  └──────────────────────┘  │
                   └────────┬────────────────────┘
                            │
                            │ Uses
                            │
              ┌─────────────▼─────────────┐
              │     Crawler Service       │
              │                           │
              │  ┌────────────────────┐  │
              │  │    crawl4ai        │  │
              │  │  - Page Rendering  │  │
              │  │  - JS Execution    │  │
              │  │  - Content Extract │  │
              │  │  - LLM Integration │  │
              │  └────────────────────┘  │
              └─────────┬─────────────────┘
                        │
                        │ External API Calls
                        │
    ┌───────────────────┴───────────────────┐
    │                                       │
    ▼                                       ▼
┌─────────────────┐              ┌─────────────────┐
│   LLM Providers │              │  Target Websites│
│                 │              │                 │
│ - OpenAI        │              │ - Dynamic Pages │
│ - DeepSeek      │              │ - Static Pages  │
│ - Qwen          │              │ - APIs          │
│ - ERNIE         │              │                 │
│ - Anthropic     │              │                 │
└─────────────────┘              └─────────────────┘

        Storage Layer
        
┌────────────────────────────────────────────┐
│              MinIO Object Storage          │
│                                            │
│  mercury4ai/                               │
│    └── YYYY-MM-DD/                         │
│        └── {runId}/                        │
│            ├── json/                       │
│            │   └── {docId}.json           │
│            ├── markdown/                   │
│            │   └── {docId}.md             │
│            ├── images/                     │
│            │   └── {filename}.jpg         │
│            ├── attachments/                │
│            │   └── {filename}.pdf         │
│            └── logs/                       │
│                ├── run_manifest.json       │
│                └── resource_index.json     │
└────────────────────────────────────────────┘
```

## Component Details

### 1. FastAPI Application Layer

**Purpose**: REST API for task management and orchestration

**Responsibilities**:
- Accept and validate task configurations
- Manage task lifecycle (create, read, update, delete)
- Queue tasks for execution
- Provide run status and results
- Handle authentication and authorization
- Import/export task configurations

**Key Modules**:
- `app/api/tasks.py` - Task management endpoints
- `app/api/runs.py` - Run status and results endpoints
- `app/api/import_export.py` - Task import/export
- `app/api/health.py` - Health check endpoint
- `app/core/auth.py` - API key authentication

**Design Principles**:
- Stateless API design
- Pydantic models for validation
- Dependency injection for database/services
- API key authentication on all endpoints

### 2. Task Queue (Redis + RQ)

**Purpose**: Asynchronous job processing and worker coordination

**Why RQ**:
- Simple Python-based queue
- Easy monitoring and debugging
- Built-in retry mechanisms
- Worker management
- Job serialization

**Job Flow**:
1. API receives task run request
2. Creates job in Redis queue
3. Worker picks up job
4. Executes crawl task
5. Updates status in PostgreSQL
6. Stores results in MinIO

**Queue Configuration**:
- Queue name: `crawl_tasks`
- Job timeout: Configurable per task
- Retry policy: 3 attempts with exponential backoff
- Worker concurrency: Configurable via `WORKER_CONCURRENCY`

### 3. Crawler Service (crawl4ai Integration)

**Purpose**: Web page crawling and content extraction

**crawl4ai Usage**:
- **Async crawler** for high performance
- **JavaScript execution** for dynamic content
- **Wait conditions** for SPA compatibility
- **CSS selectors** for targeted extraction
- **LLM integration** for structured extraction
- **Media handling** for images and attachments

**Key Features**:
- Respects crawl4ai's native capabilities
- No duplicate functionality
- Minimal wrapper around crawl4ai
- Seamless upgrades to newer crawl4ai versions

**Service Design**:
```python
class CrawlerService:
    async def crawl_url(
        url: str,
        crawl_config: Dict,
        llm_config: Optional[Dict],
        prompt_template: Optional[str],
        output_schema: Optional[Dict]
    ) -> Dict
```

**Separation of Concerns**:
- Crawling: crawl4ai handles all web interaction
- LLM Extraction: crawl4ai's LLMExtractionStrategy
- Media Download: Custom fallback mechanism
- Storage: MinIO client for artifact storage

### 4. Data Layer

#### PostgreSQL

**Purpose**: Structured metadata storage

**Tables**:
- `crawl_task` - Task configurations
- `crawl_task_run` - Run instances and status
- `document` - Extracted documents metadata
- `document_image` - Image metadata and tracking
- `document_attachment` - Attachment metadata
- `crawled_url_registry` - URL deduplication

**Indexes**:
- Primary keys on all tables
- Foreign keys with CASCADE delete
- Indexes on frequently queried columns
- Composite indexes for common queries

#### MinIO

**Purpose**: Object storage for artifacts and results

**Storage Structure**:
```
mercury4ai/
  ├── YYYY-MM-DD/          # Date-based partitioning
  │   └── {runId}/         # Run-specific folder
  │       ├── json/        # Structured data
  │       ├── markdown/    # Raw content
  │       ├── images/      # Downloaded images
  │       ├── attachments/ # Downloaded files
  │       └── logs/        # Run logs and manifests
```

**Benefits**:
- S3-compatible API
- Presigned URLs for secure access
- Automatic retention policies
- Scalable storage
- Easy backup and replication

### 5. LLM Integration

**Purpose**: Structured data extraction from unstructured content

**Supported Providers**:
- **OpenAI** (GPT-3.5, GPT-4)
- **DeepSeek** (deepseek-chat) - Recommended default
- **Qwen** (qwen-turbo, qwen-plus, qwen-max)
- **ERNIE** (ernie-bot-turbo)
- **Anthropic** (Claude)
- **Groq** and others via OpenAI-compatible API

**LLM Configuration Flow**:
1. Load default LLM config from environment
2. Merge with task-specific config (task overrides defaults)
3. Pass to crawl4ai's LLMExtractionStrategy
4. crawl4ai handles LLM API calls
5. Structured data returned according to schema

**Chinese LLM Support**:
- All major Chinese LLMs supported
- OpenAI-compatible API interfaces
- Custom base_url configuration
- Model prefixes handled automatically
- Chinese prompt templates supported

### 6. Worker Process

**Purpose**: Execute crawl tasks asynchronously

**Worker Lifecycle**:
```
┌──────────────┐
│  Poll Queue  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Pick Job    │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│  Update Status:      │
│  running             │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  For each URL:       │
│  1. Check registry   │
│  2. Crawl page       │
│  3. Extract data     │
│  4. Download media   │
│  5. Store artifacts  │
│  6. Update DB        │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  Update Status:      │
│  completed/failed    │
└──────┬───────────────┘
       │
       ▼
┌──────────────┐
│  Cleanup     │
└──────────────┘
```

**Error Handling**:
- Individual URL failures don't stop task
- Failed URLs tracked separately
- Retry logic for transient errors
- Detailed error logging
- Status updates at each stage

### 7. Module Decoupling

**Design Principles**:

1. **Crawling Module** (app/services/crawler_service.py)
   - Depends only on crawl4ai
   - No database dependencies
   - Stateless operations
   - Returns pure data structures

2. **Task Service** (app/services/task_service.py)
   - Database operations only
   - No crawling logic
   - CRUD operations
   - Data validation

3. **Worker** (app/workers/crawl_worker.py)
   - Orchestrates crawling and storage
   - No direct crawl4ai usage
   - Uses CrawlerService
   - Updates database
   - Manages MinIO storage

4. **API Layer** (app/api/)
   - HTTP interface only
   - Uses TaskService
   - Queue management
   - Response formatting

**Benefits**:
- Easy to test each module
- Clear separation of concerns
- Can replace components independently
- Easy to upgrade dependencies
- No circular dependencies

## Data Flow

### Creating a Task

```
Client → API → Validation → Database → Response
```

### Running a Task

```
Client → API → Queue Job → Redis → Worker Picks → Execute → Update Status
                                        │
                                        ▼
                                  Crawl URLs
                                        │
                                        ▼
                                  For each URL:
                                  - Crawl with crawl4ai
                                  - LLM extraction
                                  - Download media
                                  - Store in MinIO
                                  - Record in PostgreSQL
                                        │
                                        ▼
                                  Complete/Failed
```

### Retrieving Results

```
Client → API → Database Query → MinIO Presigned URLs → Response
```

## Scalability Considerations

### Horizontal Scaling

1. **API Layer**: Multiple FastAPI instances behind load balancer
2. **Workers**: Scale worker replicas in docker-compose
3. **Database**: PostgreSQL read replicas for queries
4. **Redis**: Redis Cluster for large queues
5. **MinIO**: Distributed MinIO setup

### Performance Optimization

1. **Caching**: Redis for frequently accessed data
2. **Connection Pooling**: Database connection pooling
3. **Async Operations**: Async/await throughout stack
4. **Batch Processing**: Process multiple URLs in parallel
5. **CDN**: Serve static content from CDN

### Resource Management

1. **Memory**: Worker process limits
2. **Storage**: MinIO retention policies
3. **Database**: Regular vacuum and analyze
4. **Queue**: Job TTL and dead letter queues

## Security Architecture

### Authentication

- **API Key**: All endpoints require X-API-Key header
- **Validation**: Constant-time comparison
- **Rotation**: Support for key rotation
- **Multiple Keys**: Future support for multiple API keys

### Data Security

- **Network Isolation**: Services on Docker network
- **Encrypted Storage**: MinIO supports encryption at rest
- **Secure Connections**: HTTPS/TLS for production
- **Input Validation**: Pydantic models validate all inputs
- **SQL Injection**: SQLAlchemy ORM prevents injection
- **Size Limits**: Configurable download size limits

### Access Control

- **MinIO**: Presigned URLs with expiration
- **Database**: Limited user permissions
- **API**: Rate limiting (future enhancement)

## Monitoring and Observability

### Logging

- **Structured Logging**: JSON format for easy parsing
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Context**: Request IDs for tracing
- **Persistence**: Docker log drivers

### Metrics

- **Queue Length**: Number of pending jobs
- **Worker Status**: Active workers count
- **Task Success Rate**: Completed vs failed
- **Processing Time**: Average crawl duration
- **Storage Usage**: MinIO bucket size

### Health Checks

- **API**: `/api/health` endpoint
- **Database**: Connection test
- **Redis**: Ping test
- **MinIO**: Bucket access test
- **Workers**: RQ worker status

## Deployment Architecture

### Development

```
Single Docker Compose:
- API (1 instance)
- Worker (1 instance)
- PostgreSQL (1 instance)
- Redis (1 instance)
- MinIO (1 instance)
```

### Production

```
Load Balancer
    │
    ├─── API Instance 1
    ├─── API Instance 2
    └─── API Instance N
              │
         Redis Cluster
              │
    ┌─────────┴─────────┐
    │                   │
Worker Pool          Database Cluster
(N instances)        (Primary + Replicas)
    │
    └─── MinIO Cluster
         (Distributed)
```

## Upgrade Strategy

### crawl4ai Upgrades

1. **Version Pinning**: Specify minimum version in requirements.txt
2. **Compatibility**: Minimal wrapper ensures compatibility
3. **Testing**: Test with sample tasks before production
4. **Rollback**: Keep previous version for quick rollback

**Why it works**:
- No custom crawl4ai modifications
- Use standard APIs only
- No patching or monkey-patching
- Clean dependency management

### Database Migrations

1. **Alembic**: Database migration tool
2. **Version Control**: Track schema changes
3. **Rollback**: Support for migration rollback
4. **Testing**: Test migrations on staging first

### Zero-Downtime Deployment

1. **Blue-Green Deployment**: Switch between versions
2. **Rolling Updates**: Update workers gradually
3. **Database First**: Migrate database before code
4. **Backward Compatibility**: New code works with old schema

## Future Enhancements

### Planned Features

1. **Multi-tenancy**: Support multiple organizations
2. **Webhooks**: Notify on task completion
3. **Scheduling**: Cron-like task scheduling
4. **Real-time Status**: WebSocket for live updates
5. **Result Filtering**: Advanced query capabilities
6. **Batch Operations**: Bulk task operations
7. **Template Library**: Built-in extraction templates
8. **Rate Limiting**: Per-key rate limits

### Architecture Evolution

1. **Microservices**: Split into smaller services if needed
2. **Event Sourcing**: Track all state changes
3. **GraphQL**: Alternative to REST API
4. **gRPC**: High-performance internal communication
5. **Kubernetes**: Container orchestration

## Best Practices

### Code Organization

- Follow Python package structure
- One class per file for services
- Clear module boundaries
- Type hints everywhere
- Comprehensive docstrings

### Error Handling

- Specific exception types
- Graceful degradation
- Retry logic for transients
- Detailed error messages
- Error tracking and alerting

### Testing Strategy

- Unit tests for services
- Integration tests for API
- End-to-end tests for workflows
- Performance tests for scale
- Load tests for capacity planning

### Documentation

- API documentation (OpenAPI/Swagger)
- Code comments for complex logic
- Architecture diagrams
- Deployment guides
- Troubleshooting guides

## Conclusion

Mercury4AI's architecture is designed for:
- **Scalability**: Horizontal scaling of all components
- **Reliability**: Fault tolerance and error handling
- **Maintainability**: Clear module boundaries and decoupling
- **Upgradability**: Clean dependencies and minimal wrappers
- **Performance**: Async operations and efficient storage
- **Security**: Authentication, validation, and isolation

The system leverages best-in-class open source tools (crawl4ai, FastAPI, RQ, PostgreSQL, MinIO) without reinventing the wheel, ensuring long-term maintainability and compatibility with upstream improvements.
