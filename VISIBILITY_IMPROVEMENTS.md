# 数据清洗功能可见性改进 / Data Cleaning Visibility Improvements

## 版本 / Version: 2024-01-08

## 改进内容 / Improvements

本次更新显著提升了数据清洗功能的可见性，解决了用户看不到清洗执行、日志和文件生成的问题。

This update significantly improves the visibility of data cleaning features, resolving issues where users couldn't see cleaning execution, logs, and file generation.

### 主要变更 / Key Changes

#### 1. 日志级别优化 / Log Level Optimization

将关键的清洗日志从 DEBUG 级别提升到 INFO 级别，确保用户无需启用调试模式即可看到：

Critical cleaning logs elevated from DEBUG to INFO level, ensuring users can see them without enabling debug mode:

- Stage 1 清洗启用消息 / Stage 1 cleaning enabled message
- Markdown 提取和清洗统计 / Markdown extraction and cleaning statistics  
- Stage 2 LLM 提取状态 / Stage 2 LLM extraction status
- 文件保存确认 / File save confirmations

#### 2. 清晰的两阶段标识 / Clear Two-Stage Identification

所有日志消息现在明确标识清洗阶段：

All log messages now clearly identify the cleaning stage:

- **Stage 1 (crawl4ai)**: 自动移除 headers, footers, navigation / Automatic removal of headers, footers, navigation
- **Stage 2 (LLM)**: 使用自定义 prompt 和 schema 的结构化提取 / Structured extraction using custom prompt and schema

#### 3. 启动配置横幅 / Startup Configuration Banner

任务开始时显示完整的清洗配置，包括：

Tasks now display complete cleaning configuration at startup, including:

```
================================================================================
Starting crawl task: {task_name}
Task ID: {task_id}
Run ID: {run_id}
URLs to crawl: {count}
================================================================================
Data Cleaning Configuration:
  • Stage 1 (crawl4ai): ENABLED - Removes headers, footers, navigation
  • Stage 2 (LLM extraction): ENABLED/DISABLED
    - Provider: {provider}
    - Model: {model}
    - Prompt template: {length} characters
    - Output schema: configured/not configured
================================================================================
```

#### 4. URL 处理总结 / URL Processing Summary

每个 URL 处理完成后显示生成的文件类型：

After processing each URL, displays the types of files generated:

```
✓ Successfully processed URL 1/5: {url}
  Generated files: raw markdown, cleaned markdown (Stage 1), structured JSON (Stage 2)
```

#### 5. 任务完成总结 / Task Completion Summary

任务结束时显示详细的执行总结：

At task completion, displays detailed execution summary:

```
================================================================================
✓ Crawl task {task_id} completed successfully
Summary:
  - URLs crawled: {count}
  - URLs failed: {count}
  - Documents created: {count}
  - MinIO path: {path}
  - Data cleaning performed: Stage 1 (crawl4ai cleaning), Stage 2 (LLM extraction)
================================================================================
```

### 受影响的文件 / Files Modified

- `app/services/crawler_service.py`: 更新清洗日志级别和消息 / Updated cleaning log levels and messages
- `app/workers/crawl_worker.py`: 添加配置横幅和执行总结 / Added configuration banner and execution summary

### 日志示例对比 / Log Examples Comparison

#### 改进前 (Before)

用户可能看到很少或没有日志输出：

Users might see little or no log output:

```
INFO - Starting crawl task abc123, run def456
INFO - Task name: My Task, URLs to crawl: 1
INFO - LLM config: provider=openai, model=deepseek-chat
INFO - Executing crawl for: https://example.com
INFO - Saved raw markdown to MinIO: ...
INFO - Crawl task abc123 completed successfully
INFO - Summary: 1 URLs crawled, 0 failed, 1 documents created
```

#### 改进后 (After)

用户现在可以看到完整的清洗流程：

Users now see the complete cleaning process:

```
================================================================================
Starting crawl task: My Task
Task ID: abc123
Run ID: def456
URLs to crawl: 1
================================================================================
Data Cleaning Configuration:
  • Stage 1 (crawl4ai): ENABLED - Removes headers, footers, navigation
  • Stage 2 (LLM extraction): ENABLED - Extracts structured data
    - Provider: openai
    - Model: deepseek-chat
    - Prompt template: 234 characters
    - Output schema: configured
================================================================================
Stage 1 cleaning enabled: PruningContentFilter will remove headers, footers, and navigation
Executing crawl for: https://example.com
Stage 2 extraction enabled: LLM will extract structured data using custom schema
Extracted raw markdown: 8000 characters
Stage 1 cleaning completed: 8000 -> 3200 chars (reduced 60.0%)
Stage 2 extraction completed: Successfully extracted structured data from https://example.com
Saved raw markdown to MinIO: 2024-01-08/def456/markdown/doc123.md
Saved cleaned markdown (Stage 1) to MinIO: 2024-01-08/def456/markdown/doc123_cleaned.md
Saved structured data (Stage 2) to MinIO: 2024-01-08/def456/json/doc123.json
✓ Successfully processed URL 1/1: https://example.com
  Generated files: raw markdown, cleaned markdown (Stage 1), structured JSON (Stage 2)
================================================================================
✓ Crawl task abc123 completed successfully
Summary:
  - URLs crawled: 1
  - URLs failed: 0
  - Documents created: 1
  - MinIO path: 2024-01-08/def456
  - Data cleaning performed: Stage 1 (crawl4ai cleaning), Stage 2 (LLM extraction)
================================================================================
```

### 如何查看新日志 / How to View New Logs

#### Docker Compose 环境 / Docker Compose Environment

```bash
# 实时查看 worker 日志
# View worker logs in real-time
docker compose logs -f worker

# 查看最近的日志
# View recent logs
docker compose logs --tail=100 worker

# 查看特定时间段的日志
# View logs from specific time period
docker compose logs --since 5m worker
```

#### 通过 API / Via API

```bash
# 获取运行日志和 manifest
# Get run logs and manifest
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/runs/{run_id}/logs"
```

### 故障排除 / Troubleshooting

#### 问题：看不到任何日志 / Issue: No Logs Visible

**原因 / Cause**: Worker 可能未运行或日志级别设置不正确

**解决方案 / Solution**:
```bash
# 检查 worker 是否运行
# Check if worker is running
docker compose ps worker

# 如果未运行，启动 worker
# If not running, start worker
docker compose up -d worker

# 查看 worker 启动日志
# View worker startup logs
docker compose logs worker
```

#### 问题：只看到 Stage 1，没有 Stage 2 / Issue: Only Stage 1, No Stage 2

**原因 / Cause**: 任务未配置 `prompt_template`

**解决方案 / Solution**: 在任务配置中添加 `prompt_template` 和 `output_schema`

```yaml
prompt_template: |
  请提取文章的标题和内容
output_schema:
  type: object
  properties:
    title: {type: string}
    content: {type: string}
```

参考：`TROUBLESHOOTING_LLM_EXTRACTION.md`

#### 问题：清洗率为 0% / Issue: Cleaning Rate 0%

**原因 / Cause**: 
1. 页面内容已经很干净
2. PruningContentFilter 未正常工作

**解决方案 / Solution**:
1. 检查原始页面是否确实有冗余内容
2. 查看日志中是否有 "No fit_markdown extracted" 警告
3. 尝试使用 CSS 选择器精确定位主内容区域

```yaml
crawl_config:
  css_selector: "article, .main-content, .article-body"
```

### 下一步优化 / Future Enhancements

1. 添加进度条显示爬取进度 / Add progress bar for crawl progress
2. 提供实时 WebSocket 日志推送 / Provide real-time WebSocket log streaming
3. 在 API 响应中包含清洗统计 / Include cleaning statistics in API responses
4. 添加日志过滤和搜索功能 / Add log filtering and search functionality

### 反馈 / Feedback

如有问题或建议，请访问：

For issues or suggestions, please visit:
- GitHub Issues: https://github.com/ladlag/mercury4ai/issues
- Documentation: See TROUBLESHOOTING_LLM_EXTRACTION.md

---

**变更作者 / Change Author**: GitHub Copilot  
**审核状态 / Review Status**: 待审核 / Pending Review  
**兼容性 / Compatibility**: 向后兼容 / Backward Compatible  
