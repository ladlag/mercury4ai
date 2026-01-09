# Reusable Templates

This directory contains reusable prompt templates and output schemas that can be referenced by multiple tasks.

## Directory Structure

```
prompt_templates/     # Reusable prompt templates
schemas/             # Reusable JSON schemas for structured output
```

## Using Templates in Tasks

### Reference a Prompt Template

Instead of inline prompts, reference template files:

```json
{
  "name": "My News Task",
  "urls": ["https://example.com/news"],
  "prompt_template": "@prompt_templates/news_article_zh.txt",
  "output_schema": "@schemas/news_article_zh.json"
}
```

### Inline Templates (Current Method)

You can still use inline prompts:

```json
{
  "name": "My Task",
  "urls": ["https://example.com"],
  "prompt_template": "Extract title and content from this page",
  "output_schema": {
    "type": "object",
    "properties": {
      "title": {"type": "string"},
      "content": {"type": "string"}
    }
  }
}
```

## Available Templates

### Prompt Templates

#### Chinese Templates (中文模板)

- **`news_article_zh.txt`** - 中文新闻文章提取
  - 提取：标题、作者、日期、内容、关键词
  - 包含数据清洗指令
  
- **`product_info_zh.txt`** - 中文产品信息提取
  - 提取：产品名、品牌、价格、描述、特性、规格、库存
  - 价格格式化、规格结构化

#### English Templates

- **`news_article_en.txt`** - English news article extraction
  - Extract: title, author, date, content, keywords
  - Includes data cleaning instructions
  
- **`research_paper.txt`** - Research paper extraction
  - Extract: title, authors, abstract, date, journal, DOI, keywords, findings
  - Academic paper specific formatting

### Output Schemas

#### Chinese Schemas (中文结构)

- **`news_article_zh.json`** - 中文新闻文章输出结构
  - Fields: title, author, published_date, content, keywords
  
- **`product_info_zh.json`** - 中文产品信息输出结构
  - Fields: name, brand, price, description, features, specifications, stock_status

#### English Schemas

- **`news_article_en.json`** - English news article output structure
  - Fields: title, author, published_date, content, keywords
  
- **`research_paper.json`** - Research paper output structure
  - Fields: title, authors, abstract, published_date, journal, doi, keywords, main_findings

## Creating Custom Templates

### 1. Create Prompt Template

Create a `.txt` file in `prompt_templates/`:

**`prompt_templates/my_custom_template.txt`:**
```
Extract the following information from this page:
- Field 1
- Field 2
- Field 3

Data cleaning requirements:
1. Remove HTML tags
2. Format dates as YYYY-MM-DD
3. Clean up text

Return result in JSON format.
```

### 2. Create Output Schema

Create a `.json` file in `schemas/`:

**`schemas/my_custom_schema.json`:**
```json
{
  "type": "object",
  "properties": {
    "field1": {
      "type": "string",
      "description": "Description of field 1"
    },
    "field2": {
      "type": "string",
      "description": "Description of field 2"
    },
    "field3": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Description of field 3"
    }
  },
  "required": ["field1", "field2"]
}
```

### 3. Use in Task

Reference your custom templates:

```json
{
  "name": "My Task",
  "urls": ["https://example.com"],
  "prompt_template": "@prompt_templates/my_custom_template.txt",
  "output_schema": "@schemas/my_custom_schema.json"
}
```

## Template Naming Conventions

Follow these conventions for consistency:

1. **Language Suffix**: Add `_zh`, `_en`, etc. for language-specific templates
   - `news_article_zh.txt` (Chinese)
   - `news_article_en.txt` (English)

2. **Descriptive Names**: Use clear, descriptive names
   - ✅ `news_article.txt`
   - ✅ `product_info.txt`
   - ✅ `research_paper.txt`
   - ❌ `template1.txt`
   - ❌ `test.txt`

3. **Version Suffix**: Add version if maintaining multiple versions
   - `news_article_v1.txt`
   - `news_article_v2.txt`

4. **Match Schema Names**: Use same base name for prompts and schemas
   - `prompt_templates/news_article_zh.txt`
   - `schemas/news_article_zh.json`

## Benefits of Reusable Templates

1. **Consistency**: Same extraction logic across all tasks
2. **Maintainability**: Update once, affects all tasks using that template
3. **Reusability**: Share templates across teams and projects
4. **Version Control**: Track changes to extraction logic
5. **Organization**: Centralized template management
6. **Testing**: Test and refine templates independently

## Best Practices

1. **Include Data Cleaning Instructions**: Specify how to clean and format data in prompts
2. **Use Descriptive Field Names**: Make schema properties clear and self-documenting
3. **Add Field Descriptions**: Include descriptions in JSON schemas
4. **Mark Required Fields**: Use `required` array in schemas
5. **Test Thoroughly**: Test templates with various input sources
6. **Document Changes**: Update this README when adding new templates
7. **Use Language-Specific Templates**: Better extraction quality for non-English content

## Template Implementation Status

**Status**: ✅ **SUPPORTED** - Template file references are now fully implemented.

The system supports loading templates from files automatically when you use the `@` prefix syntax:
- **`@prompt_templates/...`** - Load prompt templates from `prompt_templates/` directory
- **`@schemas/...`** - Load output schemas from `schemas/` directory

Both inline templates and file references are supported:
- **Inline**: Embed the prompt/schema directly in task configuration
- **File Reference**: Use `@` prefix to reference template files (recommended for reusability)

See examples below and in the [CONFIG.md](../CONFIG.md) for detailed usage.

## Examples

### Example 1: Chinese News Task

```json
{
  "name": "中文新闻提取任务",
  "description": "提取中文新闻网站的文章",
  "urls": ["https://news.example.cn/article1"],
  "llm_provider": "openai",
  "llm_model": "deepseek-chat",
  "llm_params": {
    "api_key": "your-deepseek-api-key",
    "base_url": "https://api.deepseek.com",
    "temperature": 0.1
  },
  "prompt_template": "@prompt_templates/news_article_zh.txt",
  "output_schema": "@schemas/news_article_zh.json"
}
```

### Example 2: Product Information

```json
{
  "name": "产品信息提取",
  "urls": ["https://shop.example.com/product123"],
  "prompt_template": "@prompt_templates/product_info_zh.txt",
  "output_schema": "@schemas/product_info_zh.json"
}
```

### Example 3: Research Paper

```json
{
  "name": "Research Paper Extraction",
  "urls": ["https://arxiv.org/abs/2301.00001"],
  "llm_model": "gpt-4",
  "prompt_template": "@prompt_templates/research_paper.txt",
  "output_schema": "@schemas/research_paper.json"
}
```

## Contributing

To add new templates:

1. Create prompt template in `prompt_templates/`
2. Create corresponding schema in `schemas/`
3. Test with sample tasks
4. Update this README with template details
5. Submit pull request

## Questions?

See the main documentation:
- [CONFIG.md](../CONFIG.md) - Complete configuration guide
- [README.md](../README.md) - Main project documentation
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture
