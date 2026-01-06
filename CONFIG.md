# Mercury4AI Configuration Guide

Complete guide to configuring Mercury4AI for web crawling and data extraction.

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [Task Configuration](#task-configuration)
3. [Crawl Configuration](#crawl-configuration)
4. [LLM Configuration](#llm-configuration)
5. [Chinese LLM Setup](#chinese-llm-setup)
6. [Reusable Templates](#reusable-templates)

## Environment Variables

Configure Mercury4AI using environment variables in `.env` file or set directly in your environment.

### API Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_HOST` | No | `0.0.0.0` | API server host address |
| `API_PORT` | No | `8000` | API server port |
| `API_KEY` | **Yes** | `your-secure-api-key-change-this` | API authentication key (MUST change in production) |

### Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_HOST` | No | `postgres` | PostgreSQL host |
| `POSTGRES_PORT` | No | `5432` | PostgreSQL port |
| `POSTGRES_DB` | No | `mercury4ai` | Database name |
| `POSTGRES_USER` | No | `mercury4ai` | Database user |
| `POSTGRES_PASSWORD` | **Yes** | `mercury4ai_password` | Database password (MUST change in production) |

### Redis Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_HOST` | No | `redis` | Redis host |
| `REDIS_PORT` | No | `6379` | Redis port |
| `REDIS_DB` | No | `0` | Redis database number |

### MinIO Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MINIO_ENDPOINT` | No | `minio:9000` | MinIO endpoint |
| `MINIO_ACCESS_KEY` | No | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | **Yes** | `minioadmin` | MinIO secret key (MUST change in production) |
| `MINIO_BUCKET` | No | `mercury4ai` | MinIO bucket name |
| `MINIO_SECURE` | No | `false` | Use HTTPS for MinIO |

### Worker Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WORKER_CONCURRENCY` | No | `2` | Number of concurrent workers |

### Crawl Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FALLBACK_DOWNLOAD_ENABLED` | No | `true` | Enable fallback media download |
| `FALLBACK_DOWNLOAD_MAX_SIZE_MB` | No | `10` | Maximum file size for downloads (MB) |

### Default LLM Configuration

Set default LLM configuration to avoid repeating in every task:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEFAULT_LLM_PROVIDER` | No | `openai` | Default LLM provider (openai, anthropic, etc.) |
| `DEFAULT_LLM_MODEL` | No | `deepseek-chat` | Default model name |
| `DEFAULT_LLM_API_KEY` | No | None | Default API key for LLM |
| `DEFAULT_LLM_BASE_URL` | No | None | Default base URL for custom endpoints |
| `DEFAULT_LLM_TEMPERATURE` | No | None | Default temperature (0.0-1.0) |
| `DEFAULT_LLM_MAX_TOKENS` | No | None | Default max tokens |

**Recommended: Use DeepSeek as default** (cost-effective Chinese LLM):
```bash
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=deepseek-chat
DEFAULT_LLM_API_KEY=your-deepseek-api-key
DEFAULT_LLM_BASE_URL=https://api.deepseek.com
DEFAULT_LLM_TEMPERATURE=0.1
```

## Task Configuration

Tasks define what URLs to crawl and how to process them.

### Basic Task Structure

```json
{
  "name": "Task Name (required)",
  "description": "Optional description",
  "urls": ["https://example.com"],
  "crawl_config": {...},
  "llm_provider": "openai",
  "llm_model": "deepseek-chat",
  "llm_params": {...},
  "prompt_template": "Extraction instructions...",
  "output_schema": {...},
  "deduplication_enabled": true,
  "only_after_date": null,
  "fallback_download_enabled": true,
  "fallback_max_size_mb": 10
}
```

### Field Descriptions

#### Core Fields

- **`name`** (required, string, max 255 chars): Human-readable task name
- **`description`** (optional, string): Detailed task description
- **`urls`** (required, array): List of URLs to crawl (at least one required)

#### Crawl Configuration

- **`crawl_config`** (optional, object): crawl4ai-specific settings
  - **`verbose`** (boolean, default: true): Enable detailed logging
  - **`screenshot`** (boolean, default: false): Capture page screenshots
  - **`pdf`** (boolean, default: false): Generate PDF of page
  - **`js_code`** (optional, string): JavaScript to execute on page before crawling
  - **`wait_for`** (optional, string): CSS selector to wait for before crawling
  - **`css_selector`** (optional, string): CSS selector to extract specific content

#### LLM Configuration

- **`llm_provider`** (optional, string): LLM provider name
  - Options: `openai`, `anthropic`, `groq`, etc.
  - Uses `DEFAULT_LLM_PROVIDER` if not specified
  
- **`llm_model`** (optional, string): Model name
  - Examples: `gpt-4`, `gpt-3.5-turbo`, `deepseek-chat`, `qwen-plus`
  - Uses `DEFAULT_LLM_MODEL` if not specified
  
- **`llm_params`** (optional, object): Additional LLM parameters
  - **`api_key`** (string): API key (required if no default set)
  - **`base_url`** (string): Custom API endpoint
  - **`temperature`** (number, 0.0-1.0): Randomness control
  - **`max_tokens`** (integer): Maximum response length
  
- **`prompt_template`** (optional, string): Instructions for LLM extraction
  - Can be inline text or reference to template file
  - Example: `"Extract title, author, and content from this article"`
  
- **`output_schema`** (optional, object): JSON Schema for structured output
  - Defines expected output structure
  - Example: `{"type": "object", "properties": {"title": {"type": "string"}}}`

#### Advanced Options

- **`deduplication_enabled`** (boolean, default: true): Skip already-crawled URLs
- **`only_after_date`** (optional, datetime): Only crawl content after this date
- **`fallback_download_enabled`** (boolean, default: true): Enable fallback media download
- **`fallback_max_size_mb`** (integer, default: 10): Max file size for media downloads

## Crawl Configuration

Detailed crawl4ai configuration options.

### JavaScript Execution

Execute custom JavaScript before crawling:

```json
{
  "crawl_config": {
    "js_code": "window.scrollTo(0, document.body.scrollHeight);"
  }
}
```

**Use cases:**
- Trigger lazy loading
- Click buttons to reveal content
- Scroll to load dynamic content
- Accept cookie notices

### Wait Conditions

Wait for specific elements before crawling:

```json
{
  "crawl_config": {
    "wait_for": ".article-content"
  }
}
```

**Use cases:**
- Wait for dynamic content to load
- Ensure JavaScript rendering completes
- Wait for specific UI elements

### Content Selection

Extract only specific parts of the page:

```json
{
  "crawl_config": {
    "css_selector": "article.main-content"
  }
}
```

**Use cases:**
- Extract specific sections
- Ignore headers/footers
- Focus on main content area

### Screenshots and PDFs

Capture visual content:

```json
{
  "crawl_config": {
    "screenshot": true,
    "pdf": true
  }
}
```

**Note:** These increase storage requirements and processing time.

## LLM Configuration

Configure LLM for structured data extraction.

### Strategy 1: Use Default Configuration (Recommended)

Set defaults in `.env`:
```bash
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=deepseek-chat
DEFAULT_LLM_API_KEY=sk-your-key-here
DEFAULT_LLM_BASE_URL=https://api.deepseek.com
DEFAULT_LLM_TEMPERATURE=0.1
```

Task only needs prompt:
```json
{
  "name": "Simple Task",
  "urls": ["https://example.com"],
  "prompt_template": "Extract title and content",
  "output_schema": {
    "type": "object",
    "properties": {
      "title": {"type": "string"},
      "content": {"type": "string"}
    }
  }
}
```

### Strategy 2: Partial Override

Override specific parameters:
```json
{
  "name": "Custom Model Task",
  "urls": ["https://example.com"],
  "llm_model": "gpt-4",
  "llm_params": {
    "temperature": 0.3
  },
  "prompt_template": "Extract data..."
}
```

### Strategy 3: Full Configuration

Specify everything in task:
```json
{
  "name": "Fully Configured",
  "urls": ["https://example.com"],
  "llm_provider": "openai",
  "llm_model": "gpt-4",
  "llm_params": {
    "api_key": "sk-...",
    "temperature": 0.1,
    "max_tokens": 2000
  },
  "prompt_template": "Extract data...",
  "output_schema": {...}
}
```

## Chinese LLM Setup

Mercury4AI fully supports Chinese domestic LLMs.

### DeepSeek (深度求索) - Recommended Default

**Cost-effective and high-quality Chinese LLM**

**.env Configuration:**
```bash
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=deepseek-chat
DEFAULT_LLM_API_KEY=your-deepseek-api-key
DEFAULT_LLM_BASE_URL=https://api.deepseek.com
DEFAULT_LLM_TEMPERATURE=0.1
```

**Task Configuration:**
```json
{
  "llm_provider": "openai",
  "llm_model": "deepseek-chat",
  "llm_params": {
    "api_key": "your-deepseek-api-key",
    "base_url": "https://api.deepseek.com",
    "temperature": 0.1
  }
}
```

**Get API Key:** https://platform.deepseek.com/

### Qwen / Tongyi Qianwen (通义千问)

**Alibaba's LLM with multiple model sizes**

**Task Configuration:**
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
- `qwen-turbo` - Fast and cost-effective
- `qwen-plus` - Balanced performance
- `qwen-max` - Highest quality

**Get API Key:** https://dashscope.aliyun.com/

### Wenxin Yiyan / ERNIE Bot (文心一言)

**Baidu's LLM**

**Task Configuration:**
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

**Get API Key:** https://cloud.baidu.com/product/wenxinworkshop

### Chinese Language Prompts

Write prompts in Chinese for better results:

```json
{
  "prompt_template": "请从这篇文章中提取以下信息：\n- 标题\n- 作者\n- 发布日期\n- 主要内容\n\n以JSON格式返回结果。",
  "output_schema": {
    "type": "object",
    "properties": {
      "title": {"type": "string", "description": "文章标题"},
      "author": {"type": "string", "description": "作者姓名"},
      "published_date": {"type": "string", "description": "发布日期"},
      "content": {"type": "string", "description": "主要内容"}
    }
  }
}
```

## Reusable Templates

Create reusable prompt templates and output schemas that can be referenced by multiple tasks.

### Prompt Templates

Create template files in `prompt_templates/` directory:

**`prompt_templates/news_article.txt`:**
```
请从这篇新闻文章中提取以下信息：
- 标题
- 作者
- 发布日期
- 主要内容
- 关键词

要求：
1. 移除所有HTML标签
2. 统一日期格式为 YYYY-MM-DD
3. 删除多余的空格和换行
4. 规范化标点符号

以JSON格式返回结果。
```

**Reference in task:**
```json
{
  "name": "News Task",
  "prompt_template": "@prompt_templates/news_article.txt",
  "output_schema": "@schemas/news_article.json"
}
```

### Output Schemas

Create schema files in `schemas/` directory:

**`schemas/news_article.json`:**
```json
{
  "type": "object",
  "properties": {
    "title": {
      "type": "string",
      "description": "文章标题"
    },
    "author": {
      "type": "string",
      "description": "作者姓名"
    },
    "published_date": {
      "type": "string",
      "format": "date",
      "description": "发布日期 (YYYY-MM-DD)"
    },
    "content": {
      "type": "string",
      "description": "主要内容"
    },
    "keywords": {
      "type": "array",
      "items": {"type": "string"},
      "description": "关键词列表"
    }
  },
  "required": ["title", "content"]
}
```

### Benefits of Reusable Templates

1. **Consistency**: Same extraction logic across multiple tasks
2. **Maintainability**: Update once, affects all tasks
3. **Reusability**: Share templates across teams
4. **Version Control**: Track changes to extraction logic
5. **Organization**: Centralized template management

### Template Naming Convention

- Use descriptive names: `news_article`, `product_info`, `research_paper`
- Include language: `news_article_zh`, `news_article_en`
- Version if needed: `news_article_v2`

## Complete Examples

### Example 1: Simple Scraping (No LLM)

```json
{
  "name": "Basic Scraping",
  "description": "Scrape content without LLM processing",
  "urls": ["https://example.com/page1", "https://example.com/page2"],
  "crawl_config": {
    "verbose": true,
    "screenshot": false
  },
  "deduplication_enabled": true
}
```

### Example 2: Using Reusable Templates (Recommended ✅)

**Best practice: Use reusable templates for prompts and schemas**

```json
{
  "name": "News Extraction",
  "description": "Extract news using reusable templates",
  "urls": ["https://news.example.com/article1"],
  "crawl_config": {
    "verbose": true
  },
  "prompt_template": "@prompt_templates/news_article_zh.txt",
  "output_schema": "@schemas/news_article_zh.json",
  "deduplication_enabled": true
}
```

**Benefits:**
- Prompts and schemas are reusable across multiple tasks
- Clean, maintainable configuration
- Centralized template management

### Example 3: List Page URL Extraction

```json
{
  "name": "Extract Product URLs",
  "urls": ["https://shop.example.com/products"],
  "crawl_config": {
    "verbose": true,
    "wait_for": ".product-list"
  },
  "prompt_template": "@prompt_templates/list_page_extract_urls.txt",
  "output_schema": "@schemas/list_page_items.json"
}
```

### Example 4: Detail Page Extraction

```json
{
  "name": "Extract Product Details",
  "urls": [
    "https://shop.example.com/product/1",
    "https://shop.example.com/product/2"
  ],
  "prompt_template": "@prompt_templates/detail_page_extract_full.txt",
  "output_schema": "@schemas/detail_page_full.json",
  "deduplication_enabled": true
}
```

### Example 5: Inline Configuration (For Reference)

When you need custom extraction logic not covered by templates:

```json
{
  "name": "Custom Extraction",
  "urls": ["https://example.com/special"],
  "crawl_config": {
    "verbose": true
  },
  "prompt_template": "Extract specific fields: X, Y, Z with custom logic...",
  "output_schema": {
    "type": "object",
    "properties": {
      "custom_field": {"type": "string"}
    }
  }
}
```

### Example 6: Dynamic Content with JavaScript

```json
{
  "name": "Dynamic Page Scraping",
  "urls": ["https://spa.example.com"],
  "crawl_config": {
    "js_code": "window.scrollTo(0, document.body.scrollHeight);",
    "wait_for": ".content-loaded",
    "css_selector": "article.main"
  }
}
```

## Common Crawling Patterns

### Pattern 1: List Page + Detail Pages (Recommended ✅)

**Scenario**: Extract data from a list page, then crawl each detail page.

This is the most common web scraping pattern, requiring two separate tasks.

#### Step 1: Extract URLs from List Page

**Using reusable template:**

```json
{
  "name": "Extract URLs from List",
  "urls": ["https://shop.example.com/products"],
  "crawl_config": {
    "verbose": true,
    "wait_for": ".product-list"
  },
  "prompt_template": "@prompt_templates/list_page_extract_urls.txt",
  "output_schema": "@schemas/list_page_items.json"
}
```

**Result**: Get list of URLs from `structured_data.items[].url`

#### Step 2: Crawl Detail Pages

**Using reusable template:**

```json
{
  "name": "Extract Product Details",
  "urls": [
    "https://shop.example.com/product/1",
    "https://shop.example.com/product/2"
  ],
  "crawl_config": {
    "verbose": true,
    "wait_for": ".product-detail"
  },
  "prompt_template": "@prompt_templates/detail_page_extract_full.txt",
  "output_schema": "@schemas/detail_page_full.json",
  "deduplication_enabled": true
}
```

**Workflow**:
1. Create and run Task 1 (list page) → Get run_id
2. Get results: `GET /api/runs/{run_id}/result`
3. Extract URLs from `structured_data.items[].url`
4. Create Task 2 with extracted URLs
5. Run Task 2 to get detail page data

**See example files**: `examples/task_step1_list_page.yaml` and `examples/task_step2_detail_pages.yaml`
        "type": "array",
        "items": {"type": "string"},
        "description": "产品图片URL列表"
      }
    }
  },
  "deduplication_enabled": true,
  "fallback_download_enabled": true
}
```

**Workflow**:
1. Create and run Task 1 (list page)
2. Get results from Task 1 via API: `GET /api/runs/{run_id}/result`
3. Extract URLs from the structured data
4. Create Task 2 with the extracted URLs
5. Run Task 2 to get detail page data

### Pattern 2: Paginated List Pages

**Scenario**: Extract data from multiple pages of a paginated list.

```json
{
  "name": "Multi-Page List Crawl",
  "urls": [
    "https://news.example.com/list?page=1",
    "https://news.example.com/list?page=2",
    "https://news.example.com/list?page=3"
  ],
  "crawl_config": {
    "verbose": true,
    "wait_for": ".list-items"
  },
  "prompt_template": "@prompt_templates/list_page_extract_urls.txt",
  "output_schema": "@schemas/list_page_items.json",
  "deduplication_enabled": true
}
```

### Pattern 3: Incremental Updates

**Scenario**: Only crawl new content since last run.

```json
{
  "name": "Daily Updates",
  "urls": ["https://news.example.com/latest"],
  "prompt_template": "@prompt_templates/news_article_zh.txt",
  "output_schema": "@schemas/news_article_zh.json",
  "deduplication_enabled": true,
  "only_after_date": "2024-01-01T00:00:00Z"
}
```

### Pattern 4: Dynamic Content

**Scenario**: Pages that load content dynamically with JavaScript.

```json
{
  "name": "Dynamic Content",
  "urls": ["https://example.com/dynamic"],
  "crawl_config": {
    "verbose": true,
    "wait_for": ".content",
    "js_code": "window.scrollTo(0, document.body.scrollHeight); await new Promise(r => setTimeout(r, 2000));"
  },
  "prompt_template": "@prompt_templates/list_page_extract_urls.txt",
  "output_schema": "@schemas/list_page_items.json"
}
```

### Pattern 5: Category-Based Crawling

**Scenario**: Crawl multiple categories or sections.

```json
{
  "name": "Multi-Category Crawl",
  "urls": [
    "https://shop.example.com/category/electronics",
    "https://shop.example.com/category/books",
    "https://shop.example.com/category/home"
  ],
  "crawl_config": {
    "verbose": true,
    "css_selector": ".product-grid"
  },
  "prompt_template": "@prompt_templates/list_page_extract_urls.txt",
  "output_schema": "@schemas/list_page_items.json"
}
```
            "date": {"type": "string", "format": "date"},
            "content": {"type": "string"}
          }
        }
      }
    }
  },
  "deduplication_enabled": true,
  "only_after_date": "2024-01-01T00:00:00Z"
}
```

### Best Practices for Crawling Patterns

1. **Use Reusable Templates**: Reference `@prompt_templates/` and `@schemas/` files
2. **Split Tasks Logically**: Separate list extraction from detail crawling
3. **Enable Deduplication**: Avoid re-processing same URLs
4. **Use Incremental Updates**: Set `only_after_date` for periodic crawling
5. **Test with Single URL First**: Validate before batch processing

## Best Practices

1. **Use Default LLM Configuration**: Set defaults in `.env` to avoid repetition
2. **Choose DeepSeek for Chinese Content**: Cost-effective and high-quality
3. **Create Reusable Templates**: For consistent extraction across tasks
4. **Test with Single URL First**: Validate configuration before batch processing
5. **Enable Deduplication**: Avoid re-crawling same URLs
6. **Set Reasonable Timeouts**: Balance thoroughness with performance
7. **Monitor Worker Logs**: Check for errors and adjust configuration
8. **Use Chinese Prompts for Chinese Content**: Better extraction quality

## Troubleshooting

### LLM Extraction Not Working

1. Check API key is correct
2. Verify base_url if using custom endpoint
3. Check logs: `docker-compose logs -f worker`
4. Test with simpler prompt first

### URLs Not Being Crawled

1. Check deduplication is not blocking
2. Verify date filters (only_after_date)
3. Check worker is running: `docker-compose ps`
4. Review logs for errors

### Media Download Failures

1. Check fallback_download_enabled is true
2. Increase fallback_max_size_mb if needed
3. Verify network connectivity from worker
4. Check MinIO is accessible

## Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Example Tasks**: See `examples/` directory
- **Quick Start**: See [QUICKSTART.md](QUICKSTART.md)
- **Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
