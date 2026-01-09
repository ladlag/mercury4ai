# Changelog: Cleaning Process Optimization

## Overview

This update implements 5 major improvements to the cleaning process in Mercury4AI, addressing issues with Stage 1 and Stage 2 cleaning, template management, and user experience.

## New Features

### 1. Template and Schema File References

Tasks can now reference reusable template files instead of inline content:

**Before:**
```yaml
prompt_template: |
  请从这篇新闻文章中提取以下信息：
  - 标题
  - 作者
  ...
```

**After:**
```yaml
prompt_template: "@prompt_templates/news_article_zh.txt"
output_schema: "@schemas/news_article_zh.json"
```

**Benefits:**
- Reusable templates across multiple tasks
- Easier maintenance and updates
- Centralized template management
- Supports both prompt templates and output schemas

**Implementation:**
- New `app/core/template_resolver.py` module
- Automatic resolution during task import
- Error handling for missing files
- Compatible with existing inline content

**Available Templates:**
- `@prompt_templates/news_article_zh.txt` - Chinese news extraction
- `@prompt_templates/news_article_en.txt` - English news extraction
- `@prompt_templates/product_info_zh.txt` - Product information
- `@prompt_templates/detail_page_extract_full.txt` - Full detail page
- `@prompt_templates/list_page_extract_urls.txt` - List page URLs
- `@schemas/news_article_zh.json` - Chinese news schema
- `@schemas/news_article_en.json` - English news schema
- `@schemas/product_info_zh.json` - Product schema
- And more...

### 2. Default Prompt Template Configuration

Configure a default prompt template that applies to all tasks without explicit prompt configuration:

```bash
# .env file
DEFAULT_PROMPT_TEMPLATE=@prompt_templates/detail_page_extract_full.txt
```

**Benefits:**
- Consistent extraction behavior across tasks
- Simplified task configuration
- Support for inline text or file references
- Tasks can still override with their own prompts

**Implementation:**
- New `DEFAULT_PROMPT_TEMPLATE` setting in `app/core/config.py`
- New `get_prompt_template()` function in `app/workers/crawl_worker.py`
- Automatic fallback when task prompt is not specified
- Clear logging to indicate source of prompt

### 3. Enhanced Stage 2 Logging

Stage 2 (LLM extraction) now provides clear feedback when disabled:

**Example Output:**
```
  • Stage 2 (LLM extraction): DISABLED - No prompt_template configured
    Reason: Neither task.prompt_template nor DEFAULT_PROMPT_TEMPLATE is set
    To enable Stage 2 extraction:
      1. Add 'prompt_template' to your task configuration, OR
      2. Set DEFAULT_PROMPT_TEMPLATE in environment (.env file)
      3. You can use file references like: @prompt_templates/detail_page_extract_full.txt
```

**Benefits:**
- Users immediately understand why Stage 2 is disabled
- Actionable suggestions for enabling it
- Clear distinction between different failure reasons
- No more silent skipping

**Logged Reasons:**
- No LLM provider/model configured
- No API key available
- No prompt template (with suggestions)
- Configuration incomplete

### 4. Stage 1 Cleaning Diagnostics

Automatic detection and diagnosis of ineffective Stage 1 cleaning:

**Example Output:**
```
⚠ Stage 1 cleaning reduced very little content (< 5%)
Possible reasons:
  1. Page content is already clean (no headers/footers/navigation)
  2. Page structure prevents PruningContentFilter from working effectively
  3. css_selector not configured - crawl4ai processed entire page

Recommendations to improve Stage 1 cleaning:
  • Add 'css_selector' to crawl_config to target main content area:
    Example selectors: 'article, .article, .content, .main, .main-content,
                       .detail, .detail-content, #content, #main, .post-content'
  • Inspect the page HTML to find the main content container CSS selector
  • Use browser DevTools to identify the right selector
```

**Benefits:**
- Automatic problem detection
- Clear explanation of possible causes
- Specific recommendations for improvement
- Lists recommended CSS selectors
- Indicates whether css_selector is already configured

**Implementation:**
- Detection when reduction < 5%
- Updated logging in `app/services/crawler_service.py`
- Context-aware suggestions
- Non-intrusive warnings

### 5. Optimized PruningContentFilter Threshold

Adjusted default threshold for Chinese educational content:

**Changes:**
- Default threshold: `0.48` → `0.40`
- Rationale: Chinese characters have higher information density
- Better suited for Chinese educational websites
- Configurable per-task override

**Configuration:**
```yaml
crawl_config:
  content_filter_threshold: 0.35  # Override default
```

**Threshold Guide:**
- `0.30-0.40`: More inclusive, keeps more content (recommended for Chinese)
- `0.40-0.50`: Balanced (default)
- `0.50-0.80`: Stricter, only high-density blocks

**Implementation:**
- Updated `PruningContentFilter` initialization
- New `content_filter_threshold` field in `CrawlConfigSchema`
- Clear logging of threshold being used

## Configuration Changes

### Environment Variables

Added to `.env.example`:
```bash
# Default prompt template for LLM extraction (optional)
# Can be inline text or file reference like @prompt_templates/detail_page_extract_full.txt
# If not set, tasks must provide their own prompt_template
DEFAULT_PROMPT_TEMPLATE=
```

### Schema Changes

Updated `CrawlConfigSchema` in `app/schemas/__init__.py`:
```python
content_filter_threshold: Optional[float] = Field(
    None, 
    description="PruningContentFilter threshold (0.0-1.0, default 0.40 for Chinese content)"
)
```

## Documentation Updates

### TROUBLESHOOTING_LLM_EXTRACTION.md

**New Sections:**
- Advanced Features
  - Using Reusable Templates
  - Using Default Prompt Template
  - Stage 1 Cleaning Diagnostics
- Updated Problem 2 (Markdown Cleaning)
  - Method A: CSS Selectors (with examples)
  - Method B: Adjust Content Filter Threshold
  - Two-stage cleaning strategy explanation

### README.md

**New Sections:**
- Updated Features list with diagnostics
- Using Reusable Templates
- Configuring Default Prompt
- Optimizing Stage 1 Cleaning

## Migration Guide

### For Existing Users

No breaking changes! All features are backward compatible:

1. **Existing tasks continue to work** - Inline prompts and schemas still supported
2. **Optional features** - Template references and default prompt are optional
3. **Default threshold change** - May improve cleaning for Chinese sites automatically
4. **Enhanced logging** - More informative, no action required

### To Adopt New Features

**Step 1: Use Template References (Optional)**
```bash
# Convert existing task
curl -X POST http://localhost:8000/api/tasks/import?format=yaml \
  -H "X-API-Key: your-key" \
  --data-binary @examples/task_news_with_template.yaml
```

**Step 2: Configure Default Prompt (Optional)**
```bash
# Add to .env
echo 'DEFAULT_PROMPT_TEMPLATE=@prompt_templates/detail_page_extract_full.txt' >> .env

# Restart services
docker-compose restart
```

**Step 3: Optimize Stage 1 Cleaning (If Needed)**

If you see warnings about low cleaning effectiveness:
```yaml
# Add to your task's crawl_config
crawl_config:
  css_selector: "article, .content, .main"
  content_filter_threshold: 0.35  # Optional: adjust threshold
```

## Testing

### Unit Tests Passed

- Template resolver functionality
- File reference resolution
- Schema JSON parsing
- Error handling for missing files
- Inline content preservation

### Code Quality Checks Passed

- ✅ Code review: No issues found
- ✅ Security scan (CodeQL): No vulnerabilities
- ✅ Python syntax validation: All files valid

### Manual Testing

Template resolution tested with:
- `examples/task_news_with_template.yaml`
- All available prompt templates
- All available schemas
- Error cases (missing files, invalid references)

## Performance Impact

- **Minimal overhead**: File I/O only during task import
- **Cached in database**: Resolved templates stored, no runtime resolution
- **Same crawling performance**: No impact on crawl speed
- **Improved cleaning**: Better Stage 1 results for Chinese content

## Breaking Changes

**None** - This is a backward-compatible update.

## Known Limitations

1. Template references only work in task import (API/YAML/JSON), not in direct API POST
2. Templates must exist in `prompt_templates/` and `schemas/` directories
3. Default prompt template must be set before task creation to take effect
4. Stage 1 threshold adjustment may require tuning for specific sites

## Future Enhancements

Potential improvements for future releases:

1. Web UI for template management
2. Template versioning
3. Per-domain threshold recommendations
4. Machine learning-based threshold optimization
5. Custom template directories
6. Template inheritance

## Support

For issues or questions:

1. Check [TROUBLESHOOTING_LLM_EXTRACTION.md](TROUBLESHOOTING_LLM_EXTRACTION.md)
2. Review [CONFIG.md](CONFIG.md) for configuration options
3. See examples in `examples/` directory
4. Check worker logs: `docker compose logs -f worker`

## Contributors

- Implementation: GitHub Copilot
- Review: ladlag

## Version

This changelog corresponds to the PR: **Fix and optimize cleaning process with template references and diagnostics**

**Commits:**
- 4738eb5: Implement template references, default prompt, and Stage 1 diagnostics
- 401d063: Update documentation with new features and Stage 1 cleaning guide
- 1615ce9: Update README with new features documentation
