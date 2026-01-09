# PR Summary: Fix LLM Extraction (Stage 2) Logic with Template File Support

## Problem Statement

Before this PR:
- Stage 2 (LLM extraction) would silently skip when `prompt_template` was missing
- Logs showed generic messages like "Stage 2 extraction disabled: No prompt_template configured"
- Template file references (`@prompt_templates/...` and `@schemas/...`) were documented as "planned for future implementation" but not actually working
- Users had to repeat prompts in every task, even when using the same extraction logic

## Solution Overview

This PR implements:
1. **Full template file reference support** - Load prompts and schemas from files
2. **Default prompt configuration** - Set default prompts in environment variables
3. **Enhanced logging** - Clear status messages with actionable guidance
4. **Backward compatibility** - All existing tasks continue to work

## Implementation Details

### New Components

**1. Template Loader Service (`app/services/template_loader.py`)**
- `resolve_prompt_template(prompt)` - Resolve inline or file reference prompts
- `resolve_output_schema(schema)` - Resolve inline or file reference schemas
- `get_default_prompt_from_env(settings)` - Get default prompt with priority logic
- Security checks to prevent path traversal attacks
- Comprehensive error handling with clear messages

**2. Environment Variables (in `app/core/config.py`)**
- `DEFAULT_PROMPT_TEMPLATE` - Inline prompt text (highest priority)
- `DEFAULT_PROMPT_TEMPLATE_REF` - File reference like `@prompt_templates/default.txt`

**3. Enhanced Worker Logic (`app/workers/crawl_worker.py`)**
- Resolve prompt/schema before crawling starts
- Implement fallback to default prompts when task doesn't provide one
- Enhanced logging showing:
  - Stage 2 status (ENABLED/DISABLED)
  - Prompt source (inline / file / default env / missing)
  - Schema source (inline / file / not configured)
  - Clear guidance when disabled

### Priority Logic

When determining which prompt to use:
```
1. Task-level prompt_template (highest priority)
   ├─ Inline: "Extract..."
   └─ File ref: "@prompt_templates/..."

2. Environment DEFAULT_PROMPT_TEMPLATE
   └─ Inline prompt text

3. Environment DEFAULT_PROMPT_TEMPLATE_REF
   └─ File reference

4. None (Stage 2 disabled with clear guidance)
```

### Log Examples

**Before (Silent Skip):**
```
Stage 2 extraction disabled: No prompt_template configured
```

**After (Clear and Actionable):**
```
Task has no prompt_template - checking for defaults in environment
No default prompt configured in environment

  • Stage 2 (LLM extraction): DISABLED - No prompt_template in task and no default prompt configured
    To enable Stage 2, either:
      1. Add 'prompt_template' to task config (inline or @prompt_templates/...)
      2. Set DEFAULT_PROMPT_TEMPLATE in .env (inline prompt text)
      3. Set DEFAULT_PROMPT_TEMPLATE_REF in .env (@prompt_templates/... reference)
```

**Enabled (Shows All Details):**
```
Loaded prompt template from file: @prompt_templates/news_article_zh.txt (178 chars)
Loaded output schema from file: @schemas/news_article_zh.json

Data Cleaning Configuration:
  • Stage 1 (crawl4ai): ENABLED - Removes headers, footers, navigation
  • Stage 2 (LLM extraction): ENABLED - Extracts structured data
    - Provider: openai
    - Model: deepseek-chat
    - Prompt: @prompt_templates/news_article_zh.txt (178 chars)
    - Schema: @schemas/news_article_zh.json
```

## Testing

### Automated Tests (All Passing ✅)

**Unit Tests:** `tests/test_template_loader.py`
- Test inline prompt resolution
- Test file reference resolution
- Test missing file handling
- Test invalid JSON handling
- Test default prompt priority
- Test security (path traversal prevention)

**Manual Tests:** `tests/manual_test_template_loader.py`
```bash
python tests/manual_test_template_loader.py
# Output: ✓ ALL TESTS PASSED
```

**Demo Scenarios:** `tests/demo_stage2_config.py`
```bash
python tests/demo_stage2_config.py
# Shows 5 demos covering all configuration scenarios
```

### Test Results

```
================================================================================
✓ ALL TESTS PASSED
================================================================================

Tests executed:
✓ Inline Prompt
✓ Prompt File Reference
✓ Prompt File Not Found (Expected Error)
✓ Inline Schema
✓ Schema File Reference
✓ Schema File Not Found (Expected Error)
✓ Default Prompt - Inline
✓ Default Prompt - File Reference
✓ Default Prompt - Priority Test
✓ Security - Path Traversal Protection
```

## Usage Examples

### Example 1: Task with Template File References

**Task Configuration:**
```yaml
name: "新闻文章提取"
urls: ["https://news.example.cn/article1"]
prompt_template: "@prompt_templates/news_article_zh.txt"
output_schema: "@schemas/news_article_zh.json"
```

**Result:**
- Loads prompt from `prompt_templates/news_article_zh.txt`
- Loads schema from `schemas/news_article_zh.json`
- Stage 2 enabled with clear logs
- Generates JSON files in MinIO

### Example 2: Using Default Prompt from Environment

**Environment (.env):**
```bash
DEFAULT_PROMPT_TEMPLATE="Extract main content, title, and metadata"
```

**Task Configuration:**
```yaml
name: "简单爬取"
urls: ["https://example.com/page"]
# Note: No prompt_template - uses default from environment
```

**Result:**
- Uses default prompt from environment
- Stage 2 enabled with "DEFAULT_PROMPT_TEMPLATE" source
- No need to repeat prompt in every task

### Example 3: Inline Prompt (Existing Method Still Works)

**Task Configuration:**
```yaml
name: "Quick Test"
urls: ["https://example.com"]
prompt_template: "Extract title and content"
output_schema:
  type: object
  properties:
    title: {type: string}
    content: {type: string}
```

**Result:**
- Uses inline prompt and schema
- Stage 2 enabled with "inline" source
- Backward compatible with existing tasks

## Files Changed

### Core Implementation (6 files)
- `app/services/template_loader.py` ⭐ NEW
- `app/workers/crawl_worker.py` ✏️ Modified
- `app/core/config.py` ✏️ Modified
- `.env.example` ✏️ Modified

### Documentation (4 files)
- `prompt_templates/README.md` ✏️ Modified
- `CONFIG.md` ✏️ Modified
- `CHANGELOG.md` ✏️ Modified
- `STAGE2_USAGE_GUIDE.md` ⭐ NEW

### Tests (4 files)
- `tests/test_template_loader.py` ⭐ NEW
- `tests/manual_test_template_loader.py` ⭐ NEW
- `tests/demo_stage2_config.py` ⭐ NEW
- `tests/README.md` ⭐ NEW

### Examples (2 files)
- `examples/task_news_with_template_ref.yaml` ⭐ NEW
- `examples/task_with_default_prompt.yaml` ⭐ NEW

**Total:** 16 files (8 new, 8 modified)

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Support `@prompt_templates/...` references | ✅ | `resolve_prompt_template()` loads files, tests pass |
| Support `@schemas/...` references | ✅ | `resolve_output_schema()` loads JSON, tests pass |
| Clear error for missing files | ✅ | Error logs show file path and fix suggestions |
| Prevent path traversal | ✅ | Security tests pass, checks file is within allowed directory |
| Support `DEFAULT_PROMPT_TEMPLATE` | ✅ | Environment variable works, demo passes |
| Support `DEFAULT_PROMPT_TEMPLATE_REF` | ✅ | Environment variable works, demo passes |
| Priority logic works correctly | ✅ | Tests verify task > inline env > ref env > disabled |
| Stage 2 no longer silent | ✅ | Clear logs with status and reasons |
| Actionable guidance when disabled | ✅ | Logs show 3 options to enable Stage 2 |
| Backward compatible | ✅ | Existing tasks work, no breaking changes |
| Documentation updated | ✅ | README.md, CONFIG.md, usage guide, examples |

## Migration Guide

### For Existing Users

**No changes required!** Your existing tasks will continue to work.

**Optional improvements:**
1. Move repeated prompts to template files
2. Set default prompt in `.env` to avoid repetition
3. Organize prompts in `prompt_templates/` directory

### For New Users

See `STAGE2_USAGE_GUIDE.md` for:
- Complete setup guide
- Configuration examples
- Troubleshooting tips
- Best practices

## Benefits

1. **✅ No More Silent Failures** - Clear logs show exactly why Stage 2 is disabled
2. **✅ Reusable Templates** - Create once, use in multiple tasks
3. **✅ Easier Maintenance** - Update template file, affects all tasks using it
4. **✅ Better DX** - Clear error messages with actionable guidance
5. **✅ Flexibility** - Support for inline, file references, and defaults
6. **✅ Security** - Path traversal protection prevents malicious file access

## Performance Impact

**Minimal** - Template loading happens once per task execution, not per URL.

## Security Considerations

✅ **Path Traversal Protection**
- Files must be within `prompt_templates/` or `schemas/` directories
- Attempts to access parent directories are blocked
- Security tests verify protection works

✅ **Input Validation**
- JSON schemas are validated before use
- File paths are sanitized
- Clear errors for invalid inputs

## Backward Compatibility

✅ **100% Backward Compatible**
- All existing task configurations work
- Inline prompts and schemas still supported
- No breaking changes to API
- No database schema changes

## Future Improvements

Potential enhancements (not in this PR):
- Template versioning (e.g., `@prompt_templates/news_v2.txt`)
- Template variables (e.g., `{url}`, `{domain}` substitution)
- Template validation endpoint in API
- Template management UI

## Conclusion

This PR successfully addresses all requirements from the issue:
1. ✅ Template file references work
2. ✅ Default prompts from environment work
3. ✅ Stage 2 no longer silently skips
4. ✅ Clear, actionable logging
5. ✅ Backward compatible
6. ✅ Well-tested and documented

**Ready for review and merge! 🚀**
