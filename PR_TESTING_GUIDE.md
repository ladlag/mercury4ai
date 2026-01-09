# PR 测试指南 / PR Testing Guide

## 概述 / Overview

本 PR 修复了两个关键问题：
1. Stage 2 fallback 调用 crawl4ai API 参数错误导致 TypeError
2. Stage 1 在 xschu 等站点清洗效率低（0% reduction）

This PR fixes two critical issues:
1. Stage 2 fallback TypeError due to incorrect crawl4ai API parameters
2. Stage 1 cleaning inefficiency (0% reduction) on sites like xschu

## 快速验证 / Quick Verification

### 1. 验证 Fallback 修复 / Verify Fallback Fix

**测试场景 / Test Scenario:**
创建一个任务，配置 LLM，观察 fallback 是否能正常工作而不出现 TypeError。

Create a task with LLM config and observe if fallback works without TypeError.

**测试任务配置 / Test Task Config:**

```yaml
name: "Test Stage 2 Fallback"
urls:
  - "https://www.bjhdedu.cn/gongkai/tzgg/202504/t20250423_79350.html"

llm_provider: openai
llm_model: deepseek-chat
llm_params:
  api_key: "sk-your-actual-key-here"  # 替换为真实 API key
  base_url: "https://api.deepseek.com"
  temperature: 0.1

prompt_template: |
  从页面中提取以下信息：
  - 标题
  - 发布日期
  - 正文内容

output_schema:
  type: object
  properties:
    title: {type: string}
    published_date: {type: string}
    content: {type: string}

crawl_config:
  stage2_fallback_enabled: true  # 确保 fallback 启用
  wait_for: "body"

deduplication_enabled: true
```

**期望日志 / Expected Logs:**

✅ **成功的日志：**
```
INFO - Attempting Stage 2 FALLBACK extraction...
INFO -   - HTML content available: 3456 characters
INFO -   - Source: cleaned
INFO - Stage 2 FALLBACK extraction START
INFO -   - URL: https://www.bjhdedu.cn/...
INFO -   - Input type: HTML
INFO -   - Input size: 3456 characters
INFO - Stage 2 FALLBACK extraction END - SUCCESS
INFO -   - Elapsed time: 2.34s
INFO -   - Output size: 512 bytes
INFO -   - Output keys: ['title', 'published_date', 'content']
INFO -   - Items returned: 1
INFO - ✓ Stage 2 FALLBACK succeeded: 512 bytes extracted
```

❌ **之前的错误（已修复）：**
```
ERROR - TypeError: LLMExtractionStrategy.aextract() got an unexpected keyword argument 'markdown'
```

### 2. 验证 Content Selector 改进 / Verify Content Selector Improvement

**测试场景 / Test Scenario:**
在 xschu.cn 站点测试，验证使用精确 selector 后 Stage 1 清洗效率提高。

Test on xschu.cn to verify Stage 1 cleaning improvement with precise selector.

**测试任务配置 / Test Task Config:**

```yaml
name: "Test xschu Content Selector"
urls:
  - "https://www.xschu.cn/article/detail.jsp?id=12345"  # 替换为实际 URL

crawl_config:
  # xschu 站点特定选择器
  content_selector: "div.w-770 section.box div#content"
  wait_for: "body"

# 可以不配置 LLM，只测试 Stage 1
deduplication_enabled: true
```

**期望日志 / Expected Logs:**

✅ **使用 content_selector 后：**
```
INFO - Content selector applied: 'div.w-770 section.box div#content' (reason: user-provided content_selector)
INFO - Stage 1 cleaning completed: 7784 -> 3200 chars (reduced 58.9%)
```

❌ **之前（未配置 selector）：**
```
INFO - Using heuristic content selector strategy with 14 candidates
INFO - Stage 1 cleaning completed: 7784 -> 7784 chars (reduced 0.0%)
⚠ Stage 1 cleaning reduced very little content (< 5%)
```

## 完整测试流程 / Complete Testing Procedure

### 步骤 1: 创建测试任务 / Step 1: Create Test Task

```bash
# 保存上面的 YAML 配置为 test_task.yaml
# 然后导入任务
curl -X POST "http://localhost:8000/api/tasks/import?format=yaml" \
  -H "X-API-Key: your-mercury-api-key" \
  -H "Content-Type: text/plain" \
  --data-binary @test_task.yaml

# 记录返回的 task_id
```

### 步骤 2: 运行任务 / Step 2: Run Task

```bash
# 启动任务
curl -X POST "http://localhost:8000/api/tasks/{task_id}/run" \
  -H "X-API-Key: your-mercury-api-key"

# 记录返回的 run_id
```

### 步骤 3: 实时查看日志 / Step 3: Monitor Logs

```bash
# 查看 worker 日志
docker compose logs -f worker

# 或者在另一个终端查看完整日志
docker compose logs worker | grep -A5 -B5 "FALLBACK\|Stage 1 cleaning"
```

### 步骤 4: 检查结果 / Step 4: Check Results

```bash
# 获取运行结果
curl -H "X-API-Key: your-mercury-api-key" \
  "http://localhost:8000/api/runs/{run_id}/result" | jq '.'

# 检查关键字段
curl -H "X-API-Key: your-mercury-api-key" \
  "http://localhost:8000/api/runs/{run_id}/result" | jq '.documents[] | {
    id,
    source_url,
    json_path,
    has_structured_data: (.structured_data != null)
  }'

# 检查 resource_index
curl -H "X-API-Key: your-mercury-api-key" \
  "http://localhost:8000/api/runs/{run_id}/resource_index" | jq '.documents[] | {
    id,
    json_path
  }'

# 如果有错误，检查 error_log
curl -H "X-API-Key: your-mercury-api-key" \
  "http://localhost:8000/api/runs/{run_id}/error_log" | jq '.'
```

## 验收标准清单 / Acceptance Checklist

### Issue 1: Stage 2 Fallback 修复 / Fallback Fix

- [ ] Worker 日志中不再出现 `TypeError: ... got an unexpected keyword argument 'markdown'`
- [ ] Fallback 启动日志显示 `Input type: HTML`（不是 markdown）
- [ ] Fallback 成功时生成 `json/{document_id}.json` 文件
- [ ] `resource_index.json` 中 `json_path` 字段非 null
- [ ] Fallback 日志包含 `Output keys` 和 `Items returned` 信息
- [ ] `stage2_status.fallback_used` 字段正确设置为 `true`

### Issue 2: Content Selector 改进 / Selector Improvement

- [ ] 使用 `content_selector` 时日志显示 "user-provided content_selector"
- [ ] xschu 站点配置 `div.w-770 section.box div#content` 后 Stage 1 reduction > 30%
- [ ] 未配置 selector 时使用 heuristic，日志显示 "Top candidates: article, main, ..."
- [ ] Stage 1 cleaning 统计正确显示（前后字符数、百分比）
- [ ] 当 reduction < 5% 时输出诊断建议

### 通用验收 / General Acceptance

- [ ] Stage 2 成功：生成 JSON 文件且 summary 正确统计
- [ ] Stage 2 失败：写入 `error_log.json` 且 `stage` 字段为 "stage2"
- [ ] 无回归：原有功能（如 deduplication、markdown 保存）正常工作
- [ ] 文档完整：CONTENT_SELECTOR_GUIDE.md 和 TROUBLESHOOTING_LLM_EXTRACTION.md 包含 xschu 示例

## 常见问题 / FAQ

### Q1: 如何确认 fallback 被触发？

**A:** 查找日志中的关键字 `Attempting Stage 2 FALLBACK extraction`。如果看到这个日志，说明主要的 LLM 提取失败了，fallback 被触发。

### Q2: 如何知道应该配置什么 selector？

**A:** 
1. 在浏览器中打开目标页面
2. 按 F12 打开开发者工具
3. 点击左上角的"选择元素"图标
4. 点击页面主内容区域
5. 在 Elements 面板中找到包含主内容的容器元素
6. 记录该元素的 class 或 id，构造 selector

**xschu.cn 示例：**
```
主内容容器结构：
<div class="w-770">
  <section class="box">
    <div id="content">
      <!-- 这里是正文 -->
    </div>
  </section>
</div>

→ selector: "div.w-770 section.box div#content"
```

### Q3: Fallback 失败了怎么办？

**A:** 检查以下几点：
1. **API Key 是否正确：** 查看日志中 `API key: present` 
2. **HTML 内容是否可用：** 查看 `HTML content available: X characters`
3. **网络问题：** 检查到 LLM API 的网络连接
4. **Prompt 是否合理：** 尝试简化 prompt_template
5. **Schema 是否正确：** 检查 output_schema 格式

查看详细错误信息：
```bash
docker compose logs worker | grep -A10 "FALLBACK extraction END - ERROR"
```

## 回滚说明 / Rollback Instructions

如果需要回滚到之前的版本：

```bash
# 查看之前的提交
git log --oneline

# 回滚到 PR 之前的提交
git checkout <commit-before-pr>

# 或者直接回滚到 main 分支
git checkout main
```

**注意：** 回滚后，Stage 2 fallback 会再次出现 TypeError。

## 参考文档 / References

- `FIX_SUMMARY_STAGE2_SELECTOR.md` - 详细的修复说明
- `CONTENT_SELECTOR_GUIDE.md` - Content selector 配置指南
- `TROUBLESHOOTING_LLM_EXTRACTION.md` - LLM 提取问题排查

## 获取帮助 / Getting Help

如果测试过程中遇到问题，请提供：
1. 完整的任务配置（YAML 或 JSON）
2. Worker 日志（`docker compose logs worker`）
3. 运行结果（`GET /api/runs/{run_id}/result`）
4. 具体的错误信息或意外行为描述
