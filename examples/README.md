# Task Configuration Examples

This directory contains example task configurations in both JSON and YAML formats.

## Examples

### 1. News Article Extraction (`task_news_extraction.json`)

Extracts structured data from news articles including title, author, publication date, content, categories, and summary.

**Usage:**
```bash
curl -X POST http://localhost:8000/api/tasks/import?format=json \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: text/plain" \
  --data-binary @task_news_extraction.json
```

### 2. Product Catalog Scraping (`task_product_extraction.yaml`)

Extracts product information from e-commerce pages including name, price, description, specifications, and availability.

**Usage:**
```bash
curl -X POST http://localhost:8000/api/tasks/import?format=yaml \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: text/plain" \
  --data-binary @task_product_extraction.yaml
```

### 3. Research Paper Extraction (`task_research_paper.json`)

Extracts metadata from research papers including title, authors, abstract, DOI, and keywords.

**Usage:**
```bash
curl -X POST http://localhost:8000/api/tasks/import?format=json \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: text/plain" \
  --data-binary @task_research_paper.json
```

### 4. Simple Web Scraping (`task_simple_scraping.yaml`)

Basic web scraping without LLM extraction - just captures markdown and HTML content.

**Usage:**
```bash
curl -X POST http://localhost:8000/api/tasks/import?format=yaml \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: text/plain" \
  --data-binary @task_simple_scraping.yaml
```

## Creating Your Own Tasks

### Minimal Configuration

```json
{
  "name": "My Task",
  "urls": ["https://example.com"],
  "crawl_config": {},
  "deduplication_enabled": true,
  "fallback_download_enabled": true,
  "fallback_max_size_mb": 10
}
```

### With LLM Extraction

```json
{
  "name": "My LLM Task",
  "urls": ["https://example.com"],
  "crawl_config": {
    "verbose": true
  },
  "llm_provider": "openai",
  "llm_model": "gpt-4",
  "llm_params": {
    "api_key": "your-openai-api-key-here",
    "temperature": 0.1
  },
  "prompt_template": "Extract key information from this page.",
  "output_schema": {
    "type": "object",
    "properties": {
      "title": {"type": "string"}
    }
  },
  "deduplication_enabled": true,
  "fallback_download_enabled": true,
  "fallback_max_size_mb": 10
}
```

**Important**: Include your LLM API key in `llm_params.api_key` for LLM extraction to work.

## Configuration Options

### Required Fields

- `name`: Task name (string)
- `urls`: List of URLs to crawl (array of strings)

### Optional Fields

- `description`: Task description (string)
- `crawl_config`: crawl4ai configuration (object)
  - `verbose`: Enable verbose logging (boolean)
  - `screenshot`: Capture screenshots (boolean)
  - `pdf`: Generate PDFs (boolean)
  - `js_code`: JavaScript to execute (string)
  - `wait_for`: CSS selector to wait for (string)
  - `css_selector`: CSS selector to extract (string)
- `llm_provider`: LLM provider (openai, anthropic, etc.)
- `llm_model`: Model name (gpt-4, claude-3-opus, etc.)
- `llm_params`: LLM parameters (object)
  - **Important**: Include `api_key` in llm_params for LLM extraction
  - Example: `{"api_key": "sk-...", "temperature": 0.1}`
- `prompt_template`: Extraction instruction (string)
- `output_schema`: JSON Schema for output (object)
- `deduplication_enabled`: Enable URL deduplication (boolean, default: true)
- `only_after_date`: Filter by date (ISO datetime string)
- `fallback_download_enabled`: Enable fallback downloads (boolean, default: true)
- `fallback_max_size_mb`: Max download size in MB (integer, default: 10)

## Tips

1. **Start Simple**: Begin with basic configuration and add LLM extraction later
2. **Test Prompts**: Experiment with different prompt templates for best results
3. **Schema Design**: Define clear JSON schemas for consistent extraction
4. **Size Limits**: Adjust `fallback_max_size_mb` based on your needs
5. **Deduplication**: Enable for regular recurring crawls
6. **Screenshots**: Useful for visual verification but increases storage
