# Improved Two-Stage Cleaning Configuration

This document describes the new features added to improve content extraction and Stage 2 LLM extraction success rate.

## New Configuration Fields

### 1. `content_selector` (CrawlConfig)

**Purpose**: Specify a CSS selector to target the main content area for better Stage 1 cleaning.

**Usage**:
```json
{
  "crawl_config": {
    "content_selector": ".content, article, #main-content"
  }
}
```

**Behavior**:
- If provided, crawl4ai will focus on the specified selector(s) for content extraction
- Multiple selectors can be comma-separated (crawl4ai will try each)
- If not provided, the system uses a heuristic with common content selectors:
  - `article`, `main`, `.content`, `#content`, `.main-content`, `.post-content`, etc.
- Takes priority over the legacy `css_selector` field

**When to use**:
- When Stage 1 cleaning is ineffective (e.g., raw and cleaned markdown are nearly identical)
- When you know the specific container for main content on the target site
- For sites with complex navigation/sidebar structures that interfere with cleaning

**Example selectors by site type**:
- News sites: `.article-content, article, .post-content`
- Educational sites: `.detail-content, .content, #main`
- E-commerce: `.product-description, .item-content`
- Government sites: `.content, #content, [role="main"]`
- Chinese educational sites (xschu): `div.w-770 section.box div#content`

**Site-specific selector examples**:

For xschu.cn and similar Chinese educational websites:
```json
{
  "crawl_config": {
    "content_selector": "div.w-770 section.box div#content"
  }
}
```

For bjhdedu.cn:
```json
{
  "crawl_config": {
    "content_selector": ".detail-content, .content, article"
  }
}
```

### 2. `stage2_fallback_enabled` (CrawlConfig)

**Purpose**: Enable fallback LLM extraction when crawl4ai's built-in extraction fails.

**Default**: `true`

**Usage**:
```json
{
  "crawl_config": {
    "stage2_fallback_enabled": true
  }
}
```

**Behavior**:
- When `true`: If crawl4ai's LLM extraction returns empty, the system will retry with a direct LLM call using cleaned HTML content
- When `false`: Stage 2 failures will not trigger a fallback attempt
- The fallback uses the same LLM config, prompt, and schema as the primary extraction
- **Important**: Fallback now uses HTML (not markdown) to match crawl4ai 0.7.8+ API signature: `aextract(url, ix, html)`
- Fallback usage is tracked in `stage2_status.fallback_used`

**When to use**:
- Enable (default) for maximum JSON extraction success rate
- Disable if you want strict adherence to crawl4ai's extraction behavior
- Disable to save LLM API costs when fallback is unlikely to succeed

## Stage 2 Input Source

Stage 2 now uses **cleaned markdown** (from Stage 1) as input to the LLM, rather than raw markdown. This significantly improves extraction quality by:
- Reducing noise (navigation, headers, footers)
- Focusing LLM attention on main content
- Reducing token usage

**Fallback logic**:
1. Prefer `cleaned` (fit_markdown) if available and non-empty
2. Fall back to `raw` markdown if cleaned is empty
3. Log the input source used in Stage 2 START logs

## Monitoring and Logs

### Content Selector Selection

The system logs which selector strategy was chosen:
```
INFO - Content selector applied: 'article, main, .content' (reason: user-provided content_selector)
```

### Stage 1 Cleaning Results

Detailed cleaning statistics are logged:
```
INFO - Stage 1 cleaning completed: 6147 -> 2850 chars (reduced 53.6%)
```

If reduction is < 5%, you'll see a warning with recommendations:
```
WARNING - Stage 1 cleaning reduced very little content (< 5%)
WARNING - Recommendations to improve Stage 1 cleaning:
WARNING -   • Add 'content_selector' to crawl_config to target main content area
```

### Stage 2 Input Source

Stage 2 START logs now include the input source:
```
INFO - Stage 2 (LLM extraction) START
INFO -   - Input source: cleaned
INFO -   - Input size: 2850 characters
```

### Stage 2 Fallback

When fallback is triggered:
```
INFO - Attempting Stage 2 FALLBACK extraction...
INFO - Stage 2 FALLBACK extraction START
INFO -   - Input size: 2850 characters
INFO - Stage 2 FALLBACK extraction END - SUCCESS
INFO -   - Elapsed time: 3.42s
INFO -   - Output size: 1024 bytes
```

### stage2_status Structure

The `stage2_status` object now includes:
```json
{
  "enabled": true,
  "success": true,
  "error": null,
  "output_size_bytes": 1024,
  "fallback_used": true
}
```

## Complete Example

See `examples/task_xschu_with_content_selector.json` for a complete example demonstrating:
- Custom `content_selector` for targeting main content
- `stage2_fallback_enabled` for reliable JSON extraction
- Proper LLM configuration for DeepSeek

## Best Practices

1. **Start with heuristic defaults**: Don't configure `content_selector` unless you see Stage 1 cleaning is ineffective
2. **Use browser DevTools**: Inspect the target site to find the best content selector
3. **Test multiple selectors**: Use comma-separated selectors to increase chances of finding content
4. **Monitor logs**: Check Stage 1 reduction percentage and Stage 2 input source
5. **Keep fallback enabled**: Unless you have a specific reason to disable it

## Troubleshooting

### Stage 1 cleaning is ineffective (< 5% reduction)

**Solution**: Configure `content_selector` with the main content container:
1. Open the target page in browser
2. Right-click on main content → Inspect
3. Find the container element (usually has class like `content`, `article`, etc.)
4. Add the selector to `crawl_config.content_selector`

### Stage 2 always fails without fallback

**Possible causes**:
- Input is too noisy (Stage 1 cleaning ineffective)
- Prompt is unclear or too complex
- Schema is too strict or malformed

**Solutions**:
1. Improve Stage 1 cleaning with `content_selector`
2. Simplify prompt and schema
3. Enable `stage2_fallback_enabled` (default)

### Fallback succeeds but primary extraction fails

**Analysis**: This indicates crawl4ai's extraction had issues, but the fallback logic worked. This is expected behavior when fallback is needed.

**Action**: No action needed - the system is working as designed. The JSON output is valid.
