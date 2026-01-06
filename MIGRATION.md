# Migration Guide

## Overview

This guide helps you migrate to the optimized version of Mercury4AI with improved documentation and default Chinese LLM support.

## What Changed

### 1. Default LLM Model

**Before:**
```bash
DEFAULT_LLM_MODEL=gpt-4
```

**After:**
```bash
DEFAULT_LLM_MODEL=deepseek-chat
```

**Impact:** If you were relying on the default without explicitly setting it, your tasks will now use DeepSeek instead of GPT-4.

**Action Required:**
- **If you want to keep using GPT-4**: Set `DEFAULT_LLM_MODEL=gpt-4` in your `.env` file
- **If you want to use DeepSeek**: Update `DEFAULT_LLM_API_KEY` and `DEFAULT_LLM_BASE_URL` in your `.env` file

### 2. Documentation Structure

**Removed Files:**
- BJHDEDU_CRAWL_GUIDE.md
- CHINESE_LLM_GUIDE.md
- CODEBASE_ANALYSIS.md
- DOCKER_COMMAND_FIX.md
- FIX_SUMMARY.md
- IMPLEMENTATION_SUMMARY.md
- IMPLEMENTATION_SUMMARY_CHINESE_LLM.md
- INTEGRITY_CHECK_REPORT.md
- TASK_SUMMARY.md

**New Files:**
- **CONFIG.md** - Comprehensive configuration guide (consolidates info from removed files)
- **ARCHITECTURE.md** - System architecture documentation
- **prompt_templates/README.md** - Reusable templates guide

**Impact:** Links to removed documentation files will break.

**Action Required:**
- Update any bookmarks or references to use new documentation structure
- See [CONFIG.md](CONFIG.md) for Chinese LLM setup (replaces CHINESE_LLM_GUIDE.md)
- See [ARCHITECTURE.md](ARCHITECTURE.md) for system design (replaces CODEBASE_ANALYSIS.md)

### 3. Reusable Templates

**New Feature:** You can now create reusable prompt templates and output schemas.

**New Directories:**
```
prompt_templates/    # Reusable prompt templates
  ├── news_article_zh.txt
  ├── news_article_en.txt
  ├── product_info_zh.txt
  └── research_paper.txt
schemas/            # Reusable JSON schemas
  ├── news_article_zh.json
  ├── news_article_en.json
  ├── product_info_zh.json
  └── research_paper.json
```

**Impact:** No breaking changes. This is a new optional feature.

**Action Required:** None. You can continue using inline prompts and schemas.

**Future Enhancement:** Tasks will support referencing templates like:
```json
{
  "prompt_template": "@prompt_templates/news_article_zh.txt",
  "output_schema": "@schemas/news_article_zh.json"
}
```

### 4. Enhanced Pydantic Schemas

**Before:**
```python
class CrawlConfigSchema(BaseModel):
    js_code: Optional[str] = None
    wait_for: Optional[str] = None
```

**After:**
```python
class CrawlConfigSchema(BaseModel):
    js_code: Optional[str] = Field(None, description="JavaScript code to execute...")
    wait_for: Optional[str] = Field(None, description="CSS selector to wait for...")
```

**Impact:** API documentation (Swagger/OpenAPI) will show better field descriptions.

**Action Required:** None. This is backward compatible.

## Migration Steps

### Step 1: Update Environment Configuration

**Option A: Continue with Current LLM**

If you want to keep your current LLM configuration:

```bash
# Add to .env or keep existing settings
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4
DEFAULT_LLM_API_KEY=your-existing-api-key
```

**Option B: Switch to DeepSeek (Recommended)**

For cost savings and Chinese language support:

```bash
# Update .env
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=deepseek-chat
DEFAULT_LLM_API_KEY=your-deepseek-api-key
DEFAULT_LLM_BASE_URL=https://api.deepseek.com
DEFAULT_LLM_TEMPERATURE=0.1
```

Get DeepSeek API key: https://platform.deepseek.com/

### Step 2: Update Documentation References

Update any internal documentation or scripts that reference removed files:

**Old Reference → New Reference:**
- `CHINESE_LLM_GUIDE.md` → `CONFIG.md#chinese-llm-setup`
- `BJHDEDU_CRAWL_GUIDE.md` → `examples/README.md` or custom documentation
- `CODEBASE_ANALYSIS.md` → `ARCHITECTURE.md`
- `IMPLEMENTATION_SUMMARY*.md` → `README.md` or `ARCHITECTURE.md`

### Step 3: Review Existing Tasks

No changes required for existing tasks. They will continue to work as before.

**Optional:** Consider updating tasks to use reusable templates:

1. Identify common prompt patterns across tasks
2. Extract to template files in `prompt_templates/`
3. Extract output schemas to `schemas/`
4. Update task configurations to reference templates (future feature)

### Step 4: Test Migration

```bash
# Start services
docker-compose up -d

# Verify health
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/health

# Test existing task
curl -X POST http://localhost:8000/api/tasks/{task_id}/run \
  -H "X-API-Key: your-api-key"
```

## Compatibility

### Backward Compatibility

✅ **Fully backward compatible:**
- Existing task configurations work without changes
- API endpoints remain unchanged
- Database schema unchanged
- Docker Compose configuration unchanged

✅ **Non-breaking changes:**
- New documentation structure
- Enhanced field descriptions
- New optional templates feature

⚠️ **Potential impact:**
- Default LLM model changed (only affects tasks not explicitly configured)
- Removed documentation files (affects external references)

### Forward Compatibility

This version is designed for seamless upgrades:
- Clean crawl4ai integration (no custom modifications)
- Modular architecture (easy to update components)
- Template system (ready for future enhancements)

## Troubleshooting

### Issue: Tasks using wrong LLM after upgrade

**Cause:** Tasks were relying on default LLM configuration.

**Solution:** Either:
1. Set desired default in `.env`
2. Or explicitly configure LLM in each task

### Issue: Documentation links broken

**Cause:** References to removed documentation files.

**Solution:** Update references to new documentation structure:
- See [README.md](README.md#additional-documentation) for documentation map

### Issue: DeepSeek API errors

**Cause:** Invalid or missing DeepSeek API key.

**Solution:**
1. Get API key from https://platform.deepseek.com/
2. Add to `.env`: `DEFAULT_LLM_API_KEY=your-key-here`
3. Add base URL: `DEFAULT_LLM_BASE_URL=https://api.deepseek.com`

## Rollback Procedure

If you need to rollback:

```bash
# 1. Stop services
docker-compose down

# 2. Checkout previous version
git checkout <previous-commit>

# 3. Restore .env if needed
git checkout <previous-commit> .env.example
cp .env.example .env
# Edit .env with your settings

# 4. Start services
docker-compose up -d
```

## Getting Help

- **Configuration issues**: See [CONFIG.md](CONFIG.md)
- **Architecture questions**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Quick start**: See [QUICKSTART.md](QUICKSTART.md)
- **Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Issues**: https://github.com/ladlag/mercury4ai/issues

## Benefits of Upgrading

1. **Cost Savings**: DeepSeek is significantly cheaper than GPT-4
2. **Better Chinese Support**: Optimized for Chinese language content
3. **Clearer Documentation**: Comprehensive, organized documentation
4. **Reusable Templates**: Share extraction logic across tasks
5. **Better API Docs**: Enhanced field descriptions in Swagger
6. **Cleaner Codebase**: Removed 4000+ lines of redundant docs
7. **Future-Ready**: Architecture designed for easy updates

## Next Steps

After migration:

1. **Explore Templates**: Check `prompt_templates/` for examples
2. **Optimize Costs**: Consider switching to DeepSeek
3. **Read New Docs**: Familiarize yourself with new documentation structure
4. **Create Templates**: Extract common patterns to reusable templates
5. **Provide Feedback**: Report any issues or suggestions

## Version Compatibility

This upgrade is compatible with:
- Docker: 20.10+
- Docker Compose: 2.0+
- Python: 3.8+
- crawl4ai: 0.7.8+

No database migrations required.
