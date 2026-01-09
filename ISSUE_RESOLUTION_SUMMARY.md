# 问题解决总结 / Issue Resolution Summary

## 原始问题 / Original Issue

**用户反馈：**
> "到底有没有llm数据清洗功能啊，怎么改了这么多遍都没有看到执行、也没有日志、没有文件生成？"

**翻译：**
> "Does it really have LLM data cleaning functionality? Why after so many modifications, I still don't see execution, no logs, and no file generation?"

---

## 问题分析 / Problem Analysis

### 根本原因 / Root Causes

1. **日志级别问题**: 关键的清洗日志使用 `DEBUG` 级别，用户在正常模式下看不到
   - **Log level issue**: Critical cleaning logs used `DEBUG` level, invisible to users in normal mode

2. **术语不清晰**: 日志使用技术术语（如 "fit_markdown", "PruningContentFilter"）而非用户友好的语言
   - **Unclear terminology**: Logs used technical terms instead of user-friendly language

3. **缺少概览**: 任务开始时没有清楚显示启用了哪些清洗阶段
   - **Missing overview**: No clear indication at task start of which cleaning stages are enabled

4. **缺少总结**: 任务结束时没有总结生成了哪些文件
   - **Missing summary**: No summary of what files were generated at task completion

---

## 解决方案 / Solution

### 核心改进 / Core Improvements

✅ **1. 提升日志可见性**
- 将关键日志从 DEBUG 提升到 INFO 级别
- 用户无需启用调试模式即可看到所有重要信息

✅ **2. 清晰的阶段标识**
- 所有日志使用 "Stage 1" 和 "Stage 2" 标识
- Stage 1: crawl4ai 自动清洗（移除 headers, footers, navigation）
- Stage 2: LLM 结构化提取（使用自定义 prompt 和 schema）

✅ **3. 启动配置横幅**
- 任务开始时显示完整的清洗配置
- 明确告知哪些功能已启用、哪些未启用

✅ **4. 实时进度反馈**
- 每个 URL 处理后显示生成的文件类型
- 实时看到清洗效果（字符数减少百分比）

✅ **5. 完整执行总结**
- 任务结束时显示详细的执行结果
- 包括清洗阶段、生成的文件、MinIO 存储路径

---

## 改进后的日志示例 / Improved Log Examples

### 场景 1: 只有 Stage 1 清洗（无 LLM）

```
================================================================================
Starting crawl task: Simple Web Scraping
Task ID: abc123...
Run ID: def456...
URLs to crawl: 1
================================================================================
Data Cleaning Configuration:
  • Stage 1 (crawl4ai): ENABLED - Removes headers, footers, navigation
  • Stage 2 (LLM extraction): DISABLED - No prompt_template configured
    To enable Stage 2 extraction, add 'prompt_template' to task config
================================================================================
Stage 1 cleaning enabled: PruningContentFilter will remove headers, footers, and navigation
Executing crawl for: https://example.com
Extracted raw markdown: 6500 characters
Stage 1 cleaning completed: 6500 -> 3200 chars (reduced 50.8%)
Saved raw markdown to MinIO: 2026-01-08/def456/markdown/doc123.md
Saved cleaned markdown (Stage 1) to MinIO: 2026-01-08/def456/markdown/doc123_cleaned.md
✓ Successfully processed URL 1/1: https://example.com
  Generated files: raw markdown, cleaned markdown (Stage 1)
================================================================================
✓ Crawl task abc123 completed successfully
Summary:
  - URLs crawled: 1
  - URLs failed: 0
  - Documents created: 1
  - MinIO path: 2026-01-08/def456
  - Data cleaning performed: Stage 1 (crawl4ai cleaning)
================================================================================
```

### 场景 2: 完整的两阶段清洗（Stage 1 + Stage 2）

```
================================================================================
Starting crawl task: News Article Extraction
Task ID: abc123...
Run ID: def456...
URLs to crawl: 3
================================================================================
Data Cleaning Configuration:
  • Stage 1 (crawl4ai): ENABLED - Removes headers, footers, navigation
  • Stage 2 (LLM extraction): ENABLED - Extracts structured data
    - Provider: openai
    - Model: deepseek-chat
    - Prompt template: 234 characters
    - Output schema: configured
================================================================================
Processing URL 1/3: https://news.example.com/article1
Stage 1 cleaning enabled: PruningContentFilter will remove headers, footers, and navigation
Stage 2 extraction enabled: LLM will extract structured data using custom schema
Executing crawl for: https://news.example.com/article1
Extracted raw markdown: 8500 characters
Stage 1 cleaning completed: 8500 -> 3400 chars (reduced 60.0%)
Stage 2 extraction completed: Successfully extracted structured data from https://news.example.com/article1
Saved raw markdown to MinIO: 2026-01-08/def456/markdown/doc123.md
Saved cleaned markdown (Stage 1) to MinIO: 2026-01-08/def456/markdown/doc123_cleaned.md
Saved structured data (Stage 2) to MinIO: 2026-01-08/def456/json/doc123.json
✓ Successfully processed URL 1/3: https://news.example.com/article1
  Generated files: raw markdown, cleaned markdown (Stage 1), structured JSON (Stage 2)

[... 处理其他 URL ...]

================================================================================
✓ Crawl task abc123 completed successfully
Summary:
  - URLs crawled: 3
  - URLs failed: 0
  - Documents created: 3
  - MinIO path: 2026-01-08/def456
  - Data cleaning performed: Stage 1 (crawl4ai cleaning), Stage 2 (LLM extraction)
================================================================================
```

---

## 如何查看日志 / How to View Logs

### 方法 1: Docker Compose（推荐）

```bash
# 实时查看 worker 日志
docker compose logs -f worker

# 查看最近 100 行日志
docker compose logs --tail=100 worker

# 查看最近 5 分钟的日志
docker compose logs --since 5m worker
```

### 方法 2: 通过 API

```bash
# 获取运行日志和 manifest
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/runs/{run_id}/logs"
```

---

## 生成的文件位置 / Generated Files Location

所有文件存储在 MinIO 中，按照以下结构组织：

```
mercury4ai/
└── {YYYY-MM-DD}/                    # 日期 / Date
    └── {run_id}/                    # 运行 ID / Run ID
        ├── markdown/
        │   ├── {doc_id}.md                  # 原始 markdown / Raw markdown
        │   └── {doc_id}_cleaned.md          # 清洗后 markdown / Cleaned markdown (Stage 1)
        ├── json/
        │   └── {doc_id}.json                # 结构化数据 / Structured data (Stage 2)
        ├── images/
        │   └── {filename}                   # 图片 / Images
        └── logs/
            ├── run_manifest.json            # 运行清单 / Run manifest
            └── resource_index.json          # 资源索引 / Resource index
```

---

## 验证改进是否生效 / Verify Improvements

### 快速验证步骤

1. **启动服务**
   ```bash
   docker compose up -d
   ```

2. **创建测试任务**（使用示例配置）
   ```bash
   curl -X POST "http://localhost:8000/api/tasks/import?format=yaml" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: text/plain" \
     --data-binary @examples/task_chinese_llm_deepseek.json
   ```

3. **运行任务**
   ```bash
   curl -X POST "http://localhost:8000/api/tasks/{task_id}/run" \
     -H "X-API-Key: your-api-key"
   ```

4. **查看日志**
   ```bash
   docker compose logs -f worker
   ```

### 预期看到的内容

✓ 启动横幅显示清洗配置
✓ "Stage 1 cleaning enabled" 消息
✓ "Stage 1 cleaning completed" 带有统计数据
✓ "Stage 2 extraction enabled/disabled" 消息
✓ 每个 URL 的处理总结
✓ 最终任务完成总结

---

## 常见问题解答 / FAQ

### Q1: 为什么我只看到 Stage 1，没有 Stage 2？

**A:** Stage 2（LLM 提取）需要在任务配置中添加 `prompt_template`。

**示例配置：**
```yaml
prompt_template: |
  请从文章中提取标题、内容和作者信息
output_schema:
  type: object
  properties:
    title: {type: string}
    content: {type: string}
    author: {type: string}
```

参考文档：`TROUBLESHOOTING_LLM_EXTRACTION.md`

### Q2: 清洗率显示 0%，是不是没有工作？

**A:** 可能原因：
1. 页面本身就很干净，没有冗余的 headers/footers
2. 使用 CSS 选择器可以获得更精确的清洗效果

**解决方案：**
```yaml
crawl_config:
  css_selector: "article, .main-content, .article-body"
```

### Q3: 如何下载生成的文件？

**A:** 通过 API 获取预签名 URL：
```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/runs/{run_id}/logs"
```

返回的 JSON 中包含所有文件的下载链接。

---

## 技术细节 / Technical Details

### 修改的文件

1. **app/services/crawler_service.py**
   - 日志级别从 DEBUG 提升到 INFO
   - 添加清洗统计信息
   - 清晰的阶段标识

2. **app/workers/crawl_worker.py**
   - 启动横幅
   - 每个 URL 的总结
   - 最终执行总结

3. **VISIBILITY_IMPROVEMENTS.md**
   - 完整的改进说明文档
   - 示例和故障排除指南

### 向后兼容性

✅ **完全向后兼容**
- 没有 API 变更
- 没有配置格式变更
- 现有任务无需修改
- 仅日志输出格式得到改进

---

## 相关文档 / Related Documentation

📚 **完整文档集：**
- [VISIBILITY_IMPROVEMENTS.md](VISIBILITY_IMPROVEMENTS.md) - 本次改进的详细说明
- [TROUBLESHOOTING_LLM_EXTRACTION.md](TROUBLESHOOTING_LLM_EXTRACTION.md) - LLM 提取问题排查
- [CONFIG.md](CONFIG.md) - 完整配置指南
- [README.md](README.md) - 项目概览和快速开始

---

## 总结 / Summary

✅ **问题已解决 / Issue Resolved**

通过这次改进，系统现在能够：

1. ✓ 清楚地显示数据清洗功能正在执行
2. ✓ 实时显示清洗进度和效果
3. ✓ 明确告知用户生成了哪些文件
4. ✓ 帮助用户快速诊断配置问题

用户不再需要猜测功能是否在工作，所有信息都清晰可见！

---

**变更作者 / Change Author**: GitHub Copilot  
**日期 / Date**: 2026-01-08  
**状态 / Status**: ✓ 完成 / Complete
