# Task Configuration Examples

This directory contains example task configurations demonstrating **balanced complexity** and **reusable templates**.

## 📋 Example Categories

### ✅ Recommended: Using Reusable Templates

These examples show the **best practice** - using reusable prompt templates and schemas:

- **`task_step1_list_page.yaml`** - Extract URLs from list page (uses `@prompt_templates/list_page_extract_urls.txt`)
- **`task_step2_detail_pages.yaml`** - Extract details from detail pages (uses `@prompt_templates/detail_page_extract_full.txt`)
- **`task_news_with_template.yaml`** - Chinese news extraction with template
- **`task_product_with_template.yaml`** - Product extraction with template

**Benefits:**
- ✅ Prompts and schemas are reusable across multiple tasks
- ✅ Clean, concise task configuration
- ✅ Easy to maintain and update prompts centrally
- ✅ Consistent extraction logic

### 📚 Reference Examples (Inline Configuration)

These examples show complete inline configuration for reference:

- **`task_simple_scraping.yaml`** - Basic scraping without LLM
- **`task_with_default_llm.yaml`** - Uses default LLM from `.env`
- **`task_chinese_llm_deepseek.json`** - Full DeepSeek configuration
- **`task_chinese_llm_qwen.yaml`** - Full Qwen configuration
- **`task_news_extraction.json`** - Full inline news extraction
- **`task_product_extraction.yaml`** - Full inline product extraction
- **`task_research_paper.json`** - Research paper extraction
- **`task_partial_llm_override.json`** - Partial LLM override
- **`task_bjhdedu_list_crawl.yaml`** - Real-world list page example

## Quick Start

### Using Reusable Templates (Recommended)

```bash
# Step 1: Import list page extraction task
curl -X POST http://localhost:8000/api/tasks/import?format=yaml \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: text/plain" \
  --data-binary @task_step1_list_page.yaml

# Step 2: Run the task and get URLs from results
# Step 3: Import detail page extraction task with those URLs
curl -X POST http://localhost:8000/api/tasks/import?format=yaml \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: text/plain" \
  --data-binary @task_step2_detail_pages.yaml
```

## Configuration Complexity Balance

### ❌ Too Simple (Not Recommended)
```yaml
name: "My Task"
urls: ["https://example.com"]
```
Missing: LLM config, prompts, schemas

### ❌ Too Complex (Not Recommended)
```yaml
name: "My Task"
urls: ["https://example.com"]
prompt_template: |
  Very long prompt embedded here...
  (200 lines)
output_schema:
  type: object
  properties:
    # 50 lines of schema...
```
Problem: Everything embedded, not reusable

### ✅ Balanced (Recommended)
```yaml
name: "My Task"
urls: ["https://example.com"]
crawl_config:
  verbose: true
  wait_for: ".content"
prompt_template: "@prompt_templates/news_article_zh.txt"
output_schema: "@schemas/news_article_zh.json"
deduplication_enabled: true
```
Perfect: Clean config, reusable templates

## API Key Configuration

### Where to Set LLM API Keys

**Three methods (in order of preference):**

1. **Environment Variables (Best for Production)**
   ```bash
   # In .env file
   DEFAULT_LLM_API_KEY=your-deepseek-api-key
   DEFAULT_LLM_BASE_URL=https://api.deepseek.com
   DEFAULT_LLM_MODEL=deepseek-chat
   ```
   
   Tasks automatically use these defaults - no need to specify in each task.

2. **Per-Task Configuration (For Different APIs)**
   ```yaml
   name: "My Task"
   llm_params:
     api_key: "different-api-key"
     base_url: "https://api.deepseek.com"
   ```
   
   Overrides default for this specific task.

3. **Full Specification (For Complete Control)**
   ```yaml
   name: "My Task"
   llm_provider: "openai"
   llm_model: "gpt-4"
   llm_params:
     api_key: "sk-openai-key"
     temperature: 0.3
   ```

### How Prompt and Schema Work Together

**Key Concept**: Both `prompt_template` and `output_schema` are sent to the LLM:

```
┌─────────────────────────────────────────┐
│  Mercury4AI                             │
│  ├─ Crawls page → Gets content         │
│  ├─ Loads prompt from template file    │
│  ├─ Loads schema from schema file      │
│  └─ Sends to LLM:                       │
│     ┌─────────────────────────────┐    │
│     │ Page Content: "..."         │    │
│     │ Prompt: "Extract title..."  │────┼──→ LLM API
│     │ Schema: {"type":"object"..} │    │
│     └─────────────────────────────┘    │
└─────────────────────────────────────────┘
                  │
                  ▼
         ┌─────────────────┐
         │ LLM Returns:    │
         │ {               │
         │   "title": "X", │
         │   "author": "Y" │
         │ }               │
         └─────────────────┘
```

**The LLM sees both**:
- **Prompt**: "Please extract title, author, date from this article"
- **Schema**: JSON structure with field types and descriptions

**Result**: LLM understands what to extract (from prompt) and how to format it (from schema).

## Examples Overview

### 1. Simple Web Scraping (`task_simple_scraping.yaml`)

Basic web scraping without LLM extraction - just captures markdown and HTML content.

**Best for**: Getting started, testing the system, no LLM needed

### 2. Task with Default LLM (`task_with_default_llm.yaml`)

Uses default LLM configuration from environment variables. Recommended approach for production.

**Best for**: Production use with default LLM settings in `.env`

### 3. Chinese News with DeepSeek (`task_chinese_llm_deepseek.json`)

使用DeepSeek国产大模型提取中文新闻文章的结构化数据。
Uses DeepSeek (recommended Chinese LLM) for extracting structured data from Chinese news.

**Best for**: Chinese content extraction, cost-effective

### 4. Chinese LLM with Qwen (`task_chinese_llm_qwen.yaml`)

使用通义千问提取中文内容。
Uses Qwen/Tongyi Qianwen for Chinese content extraction.

**Best for**: Chinese content, Alibaba Cloud users

### 5. News Article Extraction (`task_news_extraction.json`)

Extracts structured data from English news articles with full LLM configuration.

**Best for**: English news sites, complete configuration example

### 6. Product Extraction (`task_product_extraction.yaml`)

Extracts product information from e-commerce pages.

**Best for**: E-commerce sites, product catalogs

### 7. Research Paper (`task_research_paper.json`)

Extracts metadata from research papers including title, authors, abstract, DOI.

**Best for**: Academic papers, arXiv, journals

### 8. Partial LLM Override (`task_partial_llm_override.json`)

Shows how to override specific LLM parameters while using defaults for others.

**Best for**: Custom temperature or model selection

### 9. Beijing Haidian Education List (`task_bjhdedu_list_crawl.yaml`)

Real-world example of list page crawling with Chinese LLM.

**Best for**: Learning list page crawling patterns

## Supported LLM Providers

### Chinese Providers (国产大模型) - Recommended

#### DeepSeek (深度求索) - Recommended Default ⭐
- **Model**: `deepseek-chat`
- **Provider**: `openai`
- **Base URL**: `https://api.deepseek.com`
- **Best for**: Cost-effective, high-quality Chinese and English content
- **API**: https://platform.deepseek.com/

#### Qwen / 通义千问 (Alibaba)
- **Models**: `qwen-turbo`, `qwen-plus`, `qwen-max`
- **Provider**: `openai`
- **Base URL**: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- **Best for**: Alibaba Cloud integration
- **API**: https://dashscope.aliyun.com/

#### ERNIE / 文心一言 (Baidu)
- **Models**: `ernie-bot-turbo`, `ernie-bot`
- **Provider**: `openai`
- **Base URL**: `https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop`
- **Best for**: Baidu Cloud integration
- **API**: https://cloud.baidu.com/product/wenxinworkshop

### International Providers
- **OpenAI**: GPT-4, GPT-3.5-turbo
- **Anthropic**: Claude 3 Opus, Sonnet, Haiku
- **Groq**: LLaMA models

**API Key Setup**:
```bash
# In .env - Set your API key once
DEFAULT_LLM_API_KEY=your-api-key-here
DEFAULT_LLM_BASE_URL=https://api.deepseek.com  # Or other provider
```

For detailed configuration, see [CONFIG.md](../CONFIG.md#chinese-llm-setup).

## Complete Workflow: List Page → Detail Pages

This shows the most common pattern with API key configuration.

### Setup (One-Time)

**1. Configure API Key in `.env`:**
```bash
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=deepseek-chat
DEFAULT_LLM_API_KEY=your-deepseek-api-key
DEFAULT_LLM_BASE_URL=https://api.deepseek.com
```

**2. Start Mercury4AI:**
```bash
docker-compose up -d
```

### Step 1: Create and Run List Page Task

**Create `task_step1.yaml`** (see `task_step1_list_page.yaml`):
```yaml
name: "Extract Product URLs"
urls: ["https://shop.example.com/products"]
crawl_config:
  verbose: true
  wait_for: ".product-list"
prompt_template: "@prompt_templates/list_page_extract_urls.txt"
output_schema: "@schemas/list_page_items.json"
```

**Import and run:**
```bash
# Import task
curl -X POST http://localhost:8000/api/tasks/import?format=yaml \
  -H "X-API-Key: your-mercury-api-key" \
  -H "Content-Type: text/plain" \
  --data-binary @task_step1.yaml

# Response: {"id": "task-uuid-1", ...}

# Run task
curl -X POST http://localhost:8000/api/tasks/task-uuid-1/run \
  -H "X-API-Key: your-mercury-api-key"

# Response: {"run_id": "run-uuid-1", ...}
```

### Step 2: Get Results and Extract URLs

```bash
# Get results
curl http://localhost:8000/api/runs/run-uuid-1/result \
  -H "X-API-Key: your-mercury-api-key"
```

**Response:**
```json
{
  "structured_data": {
    "items": [
      {"title": "Product 1", "url": "https://shop.example.com/product/1"},
      {"title": "Product 2", "url": "https://shop.example.com/product/2"},
      {"title": "Product 3", "url": "https://shop.example.com/product/3"}
    ]
  }
}
```

**Extract URLs** (Python example):
```python
import requests

response = requests.get(
    "http://localhost:8000/api/runs/run-uuid-1/result",
    headers={"X-API-Key": "your-mercury-api-key"}
)
urls = [item["url"] for item in response.json()["structured_data"]["items"]]
# urls = ["https://shop.example.com/product/1", ...]
```

### Step 3: Create and Run Detail Pages Task

**Create `task_step2.yaml`** with extracted URLs:
```yaml
name: "Extract Product Details"
urls:
  - https://shop.example.com/product/1
  - https://shop.example.com/product/2
  - https://shop.example.com/product/3
crawl_config:
  verbose: true
  wait_for: ".product-detail"
prompt_template: "@prompt_templates/detail_page_extract_full.txt"
output_schema: "@schemas/detail_page_full.json"
deduplication_enabled: true
```

**Import and run:**
```bash
# Import task
curl -X POST http://localhost:8000/api/tasks/import?format=yaml \
  -H "X-API-Key: your-mercury-api-key" \
  -H "Content-Type: text/plain" \
  --data-binary @task_step2.yaml

# Run task
curl -X POST http://localhost:8000/api/tasks/task-uuid-2/run \
  -H "X-API-Key: your-mercury-api-key"
```

### Step 4: Get Final Results

```bash
curl http://localhost:8000/api/runs/run-uuid-2/result \
  -H "X-API-Key: your-mercury-api-key"
```

**Response:** Complete product details for all products.

**Key Points**:
- ✅ API key set once in `.env` - both tasks use it automatically
- ✅ Templates are reusable - same templates for different sites
- ✅ Clean workflow - two simple tasks, not one complex file
- ✅ Prompt + Schema work together - LLM knows what to extract and format


## Common Crawling Patterns

### Pattern 1: List Page → Detail Pages (Two-Step Workflow)

**Most common pattern**: Extract URLs from list page, then crawl detail pages.

#### Step 1: Extract URLs from List Page

```json
{
  "name": "Step 1: Extract Product URLs",
  "urls": ["https://shop.example.com/products"],
  "prompt_template": "提取所有产品的标题和详情页URL",
  "output_schema": {
    "type": "object",
    "properties": {
      "products": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "title": {"type": "string"},
            "url": {"type": "string"}
          }
        }
      }
    }
  }
}
```

#### Step 2: Crawl Detail Pages

After getting results from Step 1, create a new task with the extracted URLs:

```json
{
  "name": "Step 2: Extract Product Details",
  "urls": [
    "https://shop.example.com/product/1",
    "https://shop.example.com/product/2",
    "https://shop.example.com/product/3"
  ],
  "prompt_template": "提取产品的完整信息：名称、价格、描述、规格",
  "output_schema": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "price": {"type": "string"},
      "description": {"type": "string"},
      "specs": {"type": "object"}
    }
  }
}
```

**See**: `task_bjhdedu_list_crawl.yaml` for real-world example

### Pattern 2: Paginated Lists

Crawl multiple pages of a paginated list:

```json
{
  "name": "Multi-Page News List",
  "urls": [
    "https://news.example.com?page=1",
    "https://news.example.com?page=2",
    "https://news.example.com?page=3"
  ],
  "deduplication_enabled": true
}
```

### Pattern 3: Dynamic Content (Infinite Scroll)

Handle pages with "Load More" or infinite scroll:

```json
{
  "name": "Infinite Scroll Content",
  "urls": ["https://example.com/infinite"],
  "crawl_config": {
    "wait_for": ".content-list",
    "js_code": |
      for (let i = 0; i < 3; i++) {
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(r => setTimeout(r, 2000));
      }
  }
}
```

### Pattern 4: Category-Based Crawling

Crawl multiple categories or sections:

```json
{
  "name": "Multi-Category Crawl",
  "urls": [
    "https://site.com/category/tech",
    "https://site.com/category/business",
    "https://site.com/category/sports"
  ],
  "deduplication_enabled": true
}
```

**For complete examples**, see [CONFIG.md - Common Crawling Patterns](../CONFIG.md#common-crawling-patterns)

## Creating Your Own Tasks

## Configuration Reference

### Required Fields

- **`name`**: Task name (string, 1-255 characters)
- **`urls`**: List of URLs to crawl (array of strings, at least one)

### Optional Fields

For complete field descriptions, see [CONFIG.md](../CONFIG.md).

Key fields:
- `crawl_config` - crawl4ai settings (JS, selectors, screenshots)
- `llm_provider` - LLM provider (openai, anthropic, etc.)
- `llm_model` - Model name (deepseek-chat, gpt-4, etc.)
- `llm_params` - LLM parameters (api_key, temperature, base_url)
- `prompt_template` - Extraction instructions
- `output_schema` - JSON Schema for output structure
- `deduplication_enabled` - Skip already-crawled URLs (default: true)
- `fallback_download_enabled` - Retry failed media downloads (default: true)

## Tips

1. **Start with DeepSeek**: Recommended default for cost-effectiveness
2. **Use Default LLM Config**: Set in `.env` to avoid repetition in tasks
3. **Test Prompts**: Experiment with different prompts for best results
4. **Define Clear Schemas**: Use JSON Schema for consistent extraction
5. **Enable Deduplication**: For recurring crawls of same sites
6. **Use Chinese Prompts**: For Chinese content, write prompts in Chinese
7. **Leverage Templates**: Use reusable templates from `prompt_templates/`

## Additional Documentation

- **[CONFIG.md](../CONFIG.md)** - Complete configuration guide
- **[QUICKSTART.md](../QUICKSTART.md)** - Get started in 5 minutes
- **[ARCHITECTURE.md](../ARCHITECTURE.md)** - System architecture
- **[prompt_templates/README.md](../prompt_templates/README.md)** - Reusable templates
