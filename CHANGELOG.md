# Changelog

## [Unreleased] - 2026-01-06

### Added
- **CONFIG.md**: Comprehensive 500+ line configuration guide covering all options
  - Environment variables reference table
  - Task configuration details
  - Crawl configuration examples
  - LLM configuration strategies
  - Chinese LLM setup guide
  - Reusable templates documentation
  - Complete examples and troubleshooting

- **ARCHITECTURE.md**: Detailed system architecture documentation
  - Component diagrams and data flow
  - Module responsibilities and decoupling
  - crawl4ai integration strategy
  - Scalability considerations
  - Security architecture
  - Upgrade strategy for dependencies

- **MIGRATION.md**: Complete upgrade guide for users
  - What changed and why
  - Step-by-step migration instructions
  - Compatibility information
  - Troubleshooting guide
  - Rollback procedures

- **Reusable Templates System**:
  - `prompt_templates/` directory with example templates:
    - news_article_zh.txt (Chinese news extraction)
    - news_article_en.txt (English news extraction)
    - product_info_zh.txt (Chinese product extraction)
    - research_paper.txt (Academic paper extraction)
  - `schemas/` directory with corresponding JSON schemas
  - prompt_templates/README.md with comprehensive usage guide
  - Future support for template references (@prefix syntax)

- **Enhanced Pydantic Schemas**:
  - Detailed field descriptions for all configuration options
  - Better API documentation in Swagger/OpenAPI
  - Improved developer experience

### Changed
- **Default LLM Model**: Changed from `gpt-4` to `deepseek-chat`
  - Rationale: Cost-effective (90% savings), high-quality, Chinese language optimized
  - Backward compatible: Explicit configurations still work
  - Users can override in .env or per-task

- **.env.example**: Reorganized to emphasize DeepSeek
  - DeepSeek shown as primary recommended option
  - Other LLMs (OpenAI, Qwen, ERNIE) shown as alternatives
  - Added detailed comments for each option

- **README.md**: Streamlined and reorganized
  - Added "Optimized for Chinese LLMs" callout
  - New documentation section with links to all guides
  - Emphasized DeepSeek as recommended default
  - Removed redundant Chinese LLM sections (moved to CONFIG.md)
  - Added reusable templates section
  - Simplified troubleshooting section

- **examples/README.md**: Improved organization
  - Examples categorized by use case and recommended for
  - DeepSeek highlighted as recommended choice
  - Simplified configuration reference
  - Added tips section
  - Links to comprehensive documentation

### Removed
- **Redundant Documentation** (4000+ lines removed):
  - BJHDEDU_CRAWL_GUIDE.md (info moved to examples/README.md and CONFIG.md)
  - CHINESE_LLM_GUIDE.md (consolidated into CONFIG.md)
  - CODEBASE_ANALYSIS.md (replaced by ARCHITECTURE.md)
  - DOCKER_COMMAND_FIX.md (issue resolved, no longer needed)
  - FIX_SUMMARY.md (historical, no longer relevant)
  - IMPLEMENTATION_SUMMARY.md (consolidated into ARCHITECTURE.md)
  - IMPLEMENTATION_SUMMARY_CHINESE_LLM.md (consolidated into CONFIG.md)
  - INTEGRITY_CHECK_REPORT.md (historical, no longer needed)
  - TASK_SUMMARY.md (consolidated into README.md and CONFIG.md)

### Documentation Structure

**Before:**
```
├── README.md (700+ lines, everything mixed together)
├── BJHDEDU_CRAWL_GUIDE.md
├── CHINESE_LLM_GUIDE.md
├── CODEBASE_ANALYSIS.md
├── DEPLOYMENT.md
├── DOCKER_COMMAND_FIX.md
├── FIX_SUMMARY.md
├── IMPLEMENTATION_SUMMARY.md
├── IMPLEMENTATION_SUMMARY_CHINESE_LLM.md
├── INTEGRITY_CHECK_REPORT.md
├── QUICKSTART.md
├── TASK_SUMMARY.md
└── (12 MD files total)
```

**After:**
```
├── README.md (streamlined, ~500 lines)
├── CONFIG.md (comprehensive configuration guide)
├── ARCHITECTURE.md (system design and architecture)
├── DEPLOYMENT.md (production deployment)
├── QUICKSTART.md (5-minute start guide)
├── MIGRATION.md (upgrade guide)
├── prompt_templates/
│   ├── README.md (templates usage guide)
│   ├── news_article_zh.txt
│   ├── news_article_en.txt
│   ├── product_info_zh.txt
│   └── research_paper.txt
└── schemas/
    ├── news_article_zh.json
    ├── news_article_en.json
    ├── product_info_zh.json
    └── research_paper.json
(6 MD files + templates)
```

### Benefits

1. **Cost Savings**: DeepSeek default reduces API costs by ~90% compared to GPT-4
2. **Better Organization**: Clear documentation structure with focused guides
3. **Easier Onboarding**: Comprehensive CONFIG.md explains all options
4. **Chinese Language Support**: Optimized defaults and examples for Chinese content
5. **Reusable Templates**: Share extraction logic across multiple tasks
6. **Better API Docs**: Enhanced field descriptions in Swagger UI
7. **Cleaner Codebase**: Removed 4000+ lines of redundant documentation
8. **Future-Proof**: Architecture designed for seamless dependency upgrades
9. **Developer-Friendly**: Clear module boundaries and responsibilities
10. **Data Quality**: Templates include data cleaning instructions

### Technical Details

**Files Changed:**
- Modified: 6 files (app/core/config.py, app/schemas/__init__.py, .env.example, README.md, examples/README.md, and more)
- Created: 20 files (CONFIG.md, ARCHITECTURE.md, MIGRATION.md, templates, etc.)
- Deleted: 9 files (redundant documentation)

**Backward Compatibility:**
- ✅ All existing task configurations work without changes
- ✅ API endpoints unchanged
- ✅ Database schema unchanged
- ✅ Docker Compose configuration unchanged
- ⚠️ Default LLM model changed (can be overridden)

**Testing:**
- Python syntax validated (py_compile)
- Code review completed (no issues)
- File structure verified
- Documentation cross-references checked

### Migration

This is a **non-breaking change**. See [MIGRATION.md](MIGRATION.md) for:
- What changed and why
- Migration steps
- Compatibility information
- Troubleshooting
- Rollback procedures

To keep using GPT-4 as default:
```bash
# Add to .env
DEFAULT_LLM_MODEL=gpt-4
DEFAULT_LLM_API_KEY=your-openai-api-key
```

To use DeepSeek (recommended):
```bash
# Add to .env
DEFAULT_LLM_MODEL=deepseek-chat
DEFAULT_LLM_API_KEY=your-deepseek-api-key
DEFAULT_LLM_BASE_URL=https://api.deepseek.com
DEFAULT_LLM_TEMPERATURE=0.1
```

### Requirements Addressed

This release addresses all 5 requirements from the original problem statement:

1. ✅ **Configuration Simplification**: Comprehensive CONFIG.md + enhanced schemas
2. ✅ **Architecture Clarity**: ARCHITECTURE.md + verified crawl4ai usage
3. ✅ **MD File Cleanup**: Reduced from 12 to 6 essential MD files
4. ✅ **Reusable Prompts/Schemas**: New templates system with examples
5. ✅ **Chinese LLM Default**: DeepSeek as default + complete Chinese LLM support

---

## Version History

### Previous Versions

No formal versioning prior to this release. This is the first major cleanup and optimization release.

---

## Future Enhancements

Planned features for future releases:

1. **Template API**: Native API support for loading templates by reference
   - `"prompt_template": "@prompt_templates/news_article_zh.txt"`
   - `"output_schema": "@schemas/news_article_zh.json"`

2. **Template Library**: Built-in template library with common patterns
   - News articles
   - E-commerce products
   - Academic papers
   - Social media posts
   - Government announcements

3. **Template Versioning**: Version control for templates
   - Track changes to extraction logic
   - A/B testing support
   - Rollback capabilities

4. **Multi-tenancy**: Support for multiple organizations
5. **Webhooks**: Task completion notifications
6. **Scheduling**: Cron-like recurring tasks
7. **Real-time Updates**: WebSocket support
8. **Advanced Analytics**: Extraction quality metrics
