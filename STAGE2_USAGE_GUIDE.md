# Stage 2 (LLM Extraction) Usage Guide

This guide explains how to configure Stage 2 LLM extraction with the new template loading and default prompt features.

## Overview

Mercury4AI has two-stage data cleaning:

- **Stage 1 (crawl4ai)**: Removes headers, footers, navigation (always enabled)
- **Stage 2 (LLM extraction)**: Extracts structured data using LLM with custom schema (optional)

Stage 2 requires:
1. LLM configuration (provider, model, API key)
2. Prompt template (from task or defaults)

## Configuration Methods

### Method 1: Task with Template File References (Recommended ✅)

**Benefits**: Reusable templates, centralized management, version control

**File: `prompt_templates/news_article_zh.txt`**
```text
请从这篇新闻文章中提取以下信息：
- 标题
- 作者
- 发布日期
- 主要内容
- 关键词

数据清洗要求：
1. 移除所有HTML标签
2. 统一日期格式为 YYYY-MM-DD
3. 删除多余的空格和换行

以JSON格式返回结果。
```

**File: `schemas/news_article_zh.json`**
```json
{
  "type": "object",
  "properties": {
    "title": {"type": "string", "description": "文章标题"},
    "author": {"type": "string", "description": "作者姓名"},
    "published_date": {"type": "string", "format": "date"},
    "content": {"type": "string", "description": "主要内容"},
    "keywords": {"type": "array", "items": {"type": "string"}}
  },
  "required": ["title", "content"]
}
```

**Task Configuration:**
```json
{
  "name": "中文新闻提取",
  "urls": ["https://news.example.cn/article1", "https://news.example.cn/article2"],
  "prompt_template": "@prompt_templates/news_article_zh.txt",
  "output_schema": "@schemas/news_article_zh.json"
}
```

**Expected Logs:**
```
Data Cleaning Configuration:
  • Stage 1 (crawl4ai): ENABLED - Removes headers, footers, navigation
  • Stage 2 (LLM extraction): ENABLED - Extracts structured data
    - Provider: openai
    - Model: deepseek-chat
    - Prompt: @prompt_templates/news_article_zh.txt (178 chars)
    - Schema: @schemas/news_article_zh.json
```

**Result:** Generates both markdown and JSON files in MinIO:
- `markdown/{doc_id}.md` - Raw markdown
- `markdown/{doc_id}_cleaned.md` - Stage 1 cleaned markdown
- `json/{doc_id}.json` - Stage 2 structured JSON

---

### Method 2: Task with Inline Prompt

**Benefits**: Quick setup, good for one-off tasks

**Task Configuration:**
```json
{
  "name": "Simple Product Extraction",
  "urls": ["https://shop.example.com/product/123"],
  "prompt_template": "Extract product name, price, and description in JSON format",
  "output_schema": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "price": {"type": "number"},
      "description": {"type": "string"}
    },
    "required": ["name", "price"]
  }
}
```

**Expected Logs:**
```
Data Cleaning Configuration:
  • Stage 1 (crawl4ai): ENABLED - Removes headers, footers, navigation
  • Stage 2 (LLM extraction): ENABLED - Extracts structured data
    - Provider: openai
    - Model: deepseek-chat
    - Prompt: inline (63 chars)
    - Schema: inline
```

---

### Method 3: Using Default Prompt from Environment

**Benefits**: No need to repeat prompts in every task, consistent extraction

**Environment Configuration (`.env`):**
```bash
# LLM Configuration
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=deepseek-chat
DEFAULT_LLM_API_KEY=sk-your-deepseek-api-key
DEFAULT_LLM_BASE_URL=https://api.deepseek.com
DEFAULT_LLM_TEMPERATURE=0.1

# Default Prompt (Option 1: Inline)
DEFAULT_PROMPT_TEMPLATE="Extract the main content, title, and key metadata from this page in JSON format. Include: title, author (if available), publish date (if available), main content, and keywords."

# OR Default Prompt (Option 2: File Reference)
# DEFAULT_PROMPT_TEMPLATE_REF=@prompt_templates/default_extraction.txt
```

**Task Configuration (No Prompt Specified):**
```json
{
  "name": "News Article Crawl",
  "urls": ["https://news.example.com/article1", "https://news.example.com/article2"]
  // Note: No prompt_template field - uses default from environment
}
```

**Expected Logs:**
```
Task has no prompt_template - checking for defaults in environment
Using DEFAULT_PROMPT_TEMPLATE from environment (150 chars)

Data Cleaning Configuration:
  • Stage 1 (crawl4ai): ENABLED - Removes headers, footers, navigation
  • Stage 2 (LLM extraction): ENABLED - Extracts structured data
    - Provider: openai
    - Model: deepseek-chat
    - Prompt: DEFAULT_PROMPT_TEMPLATE (150 chars)
    - Schema: not configured (will use free-form)
```

---

### Method 4: Per-Task LLM Override with Template

**Benefits**: Use different LLM for specific tasks while keeping default for others

**Environment Configuration (`.env`):**
```bash
# Default LLM (DeepSeek)
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=deepseek-chat
DEFAULT_LLM_API_KEY=sk-deepseek-key
DEFAULT_LLM_BASE_URL=https://api.deepseek.com
```

**Task Configuration (Override to use GPT-4):**
```json
{
  "name": "High-Quality Research Paper Extraction",
  "urls": ["https://arxiv.org/abs/2301.00001"],
  "llm_provider": "openai",
  "llm_model": "gpt-4",
  "llm_params": {
    "api_key": "sk-openai-key",
    "temperature": 0.1
  },
  "prompt_template": "@prompt_templates/research_paper.txt",
  "output_schema": "@schemas/research_paper.json"
}
```

---

## Priority Rules

When determining which prompt to use, the system follows this priority:

1. **Task-level `prompt_template`** (highest priority)
   - Inline: `"prompt_template": "Extract..."`
   - File reference: `"prompt_template": "@prompt_templates/..."`

2. **Environment `DEFAULT_PROMPT_TEMPLATE`** (medium priority)
   - Inline prompt text in `.env`

3. **Environment `DEFAULT_PROMPT_TEMPLATE_REF`** (low priority)
   - File reference in `.env`

4. **None** - Stage 2 disabled (lowest priority)
   - Clear warning with instructions on how to enable

## Common Scenarios

### Scenario A: Stage 2 Disabled - No LLM Config

**Symptom:**
```
Data Cleaning Configuration:
  • Stage 1 (crawl4ai): ENABLED
  • Stage 2 (LLM extraction): DISABLED - No LLM config (missing provider/model or API key)
```

**Solution:** Configure LLM in `.env`:
```bash
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=deepseek-chat
DEFAULT_LLM_API_KEY=sk-your-key
DEFAULT_LLM_BASE_URL=https://api.deepseek.com
```

---

### Scenario B: Stage 2 Disabled - No Prompt

**Symptom:**
```
Task has no prompt_template - checking for defaults in environment
No default prompt configured in environment

  • Stage 2 (LLM extraction): DISABLED - No prompt_template in task and no default prompt configured
    To enable Stage 2, either:
      1. Add 'prompt_template' to task config (inline or @prompt_templates/...)
      2. Set DEFAULT_PROMPT_TEMPLATE in .env (inline prompt text)
      3. Set DEFAULT_PROMPT_TEMPLATE_REF in .env (@prompt_templates/... reference)
```

**Solution (Option 1 - Add to Task):**
```json
{
  "name": "My Task",
  "urls": ["..."],
  "prompt_template": "@prompt_templates/news_article_zh.txt"
}
```

**Solution (Option 2 - Add Default in .env):**
```bash
DEFAULT_PROMPT_TEMPLATE="Extract main content and metadata in JSON format"
```

---

### Scenario C: Template File Not Found

**Symptom:**
```
Prompt template file not found: /path/to/prompt_templates/missing.txt
Reference: @prompt_templates/missing.txt
To fix: Create the file or use an inline prompt
Failed to resolve task prompt_template: @prompt_templates/missing.txt

  • Stage 2 (LLM extraction): DISABLED - Failed to load prompt template: @prompt_templates/missing.txt
```

**Solution:** Create the file or fix the reference:
```bash
# Check file exists
ls prompt_templates/missing.txt

# Or use correct filename
cat prompt_templates/news_article_zh.txt
```

---

### Scenario D: Invalid JSON in Schema File

**Symptom:**
```
Invalid JSON in output schema file /path/to/schemas/bad.json: Expecting ',' delimiter
To fix: Validate the JSON syntax in the schema file
Failed to resolve task output_schema: @schemas/bad.json
```

**Solution:** Validate and fix JSON:
```bash
# Validate JSON
python -m json.tool schemas/bad.json

# Fix syntax errors in the file
```

---

## File Organization

**Recommended directory structure:**
```
mercury4ai/
├── prompt_templates/
│   ├── README.md
│   ├── news_article_zh.txt
│   ├── news_article_en.txt
│   ├── product_info_zh.txt
│   ├── research_paper.txt
│   └── default_extraction.txt
├── schemas/
│   ├── news_article_zh.json
│   ├── news_article_en.json
│   ├── product_info_zh.json
│   └── research_paper.json
└── examples/
    ├── task_news_with_template.yaml
    ├── task_product_with_template.yaml
    └── task_with_default_llm.yaml
```

## Testing Your Configuration

**Test template loading:**
```bash
cd mercury4ai
python tests/manual_test_template_loader.py
```

**Test with demo scenarios:**
```bash
python tests/demo_stage2_config.py
```

**Test with real task:**
```bash
# Create task via API
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d @examples/task_product_with_template.yaml

# Start task
curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/start \
  -H "X-API-Key: your-api-key"

# Check logs
docker-compose logs -f worker
```

## Troubleshooting

**Q: How do I know if Stage 2 is working?**

A: Check the logs for:
1. Initial config: `Stage 2 (LLM extraction): ENABLED`
2. Per-URL: `Generated files: ... structured JSON (Stage 2)`
3. Files in MinIO: Look for `json/{doc_id}.json` files

**Q: My prompt file is loaded but no JSON is generated**

A: Check:
1. LLM API key is valid: `DEFAULT_LLM_API_KEY`
2. LLM API is reachable: Check network/firewall
3. Prompt is appropriate for the content
4. Worker logs for LLM errors

**Q: Can I mix inline and file references?**

A: Yes! You can use:
- Inline prompt + file schema
- File prompt + inline schema
- Both inline
- Both from files

**Q: How do I update a template without restarting?**

A: Just edit the file. Templates are loaded per-task, not at startup.

## Best Practices

1. ✅ **Use template files for reusable prompts** - Easier to maintain
2. ✅ **Set default prompts in .env** - Avoid repeating in every task
3. ✅ **Use descriptive file names** - `news_article_zh.txt` not `template1.txt`
4. ✅ **Match prompt and schema names** - `news_article_zh.txt` + `news_article_zh.json`
5. ✅ **Test templates before deploying** - Use test scripts
6. ✅ **Version control your templates** - Track changes in git
7. ✅ **Document complex prompts** - Add comments explaining logic
8. ✅ **Use language-specific templates** - Better extraction for Chinese content

## Further Reading

- [CONFIG.md](CONFIG.md) - Complete configuration reference
- [prompt_templates/README.md](prompt_templates/README.md) - Template creation guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [examples/](examples/) - Example task configurations
