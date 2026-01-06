# Task Configuration Examples

This directory contains example task configurations in both JSON and YAML formats.

For complete configuration documentation, see:
- **[CONFIG.md](../CONFIG.md)** - Complete configuration guide
- **[prompt_templates/README.md](../prompt_templates/README.md)** - Reusable templates

## Quick Start

Import any example task:

```bash
# Import JSON task
curl -X POST http://localhost:8000/api/tasks/import?format=json \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: text/plain" \
  --data-binary @task_chinese_llm_deepseek.json

# Import YAML task
curl -X POST http://localhost:8000/api/tasks/import?format=yaml \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: text/plain" \
  --data-binary @task_simple_scraping.yaml
```

## Examples

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

For detailed configuration, see [CONFIG.md](../CONFIG.md#chinese-llm-setup).

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
