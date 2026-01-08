# LLM 提取问题排查指南 / LLM Extraction Troubleshooting Guide

本文档帮助解决"清洗后的markdown与原始markdown相同"和"没有生成JSON文件"的问题。

This guide helps resolve issues where "cleaned markdown is identical to raw markdown" and "no JSON files are generated".

## 问题1: 没有LLM提取 / Issue 1: No LLM Extraction

### 症状 / Symptoms
- 日志中看到 `LLM config: provider=openai, model=deepseek-chat`
- 但没有看到 `Configuring LLM extraction with provider=...`
- 没有生成JSON文件
- `structured_data` 为空

### 原因 / Root Cause
**缺少 `prompt_template` 配置**

LLM提取需要两个必需字段:
1. `llm_provider` + `llm_model` + `llm_params` (LLM配置)
2. **`prompt_template`** (提取指令) ← **缺少这个!**

LLM extraction requires two mandatory components:
1. `llm_provider` + `llm_model` + `llm_params` (LLM config)
2. **`prompt_template`** (extraction instructions) ← **Missing this!**

### 解决方法 / Solution

#### 方法1: 使用完整的任务配置 / Method 1: Use Complete Task Configuration

确保你的任务配置包含 `prompt_template`:

```yaml
name: "My Custom Task"
urls:
  - "https://www.bjhdedu.cn/gongkai/tzgg/202504/t20250423_79350.html"

# LLM配置
llm_provider: openai
llm_model: deepseek-chat
llm_params:
  api_key: "your-actual-api-key-here"  # ← 替换为真实API key
  base_url: "https://api.deepseek.com"
  temperature: 0.1
  max_tokens: 4000

# ← 必需！LLM提取指令
prompt_template: |
  请从这篇文章中提取以下信息：
  - 标题
  - 发布日期
  - 正文内容
  - 作者（如果有）
  
  以JSON格式返回结果。

# ← 可选，但推荐使用
output_schema:
  type: object
  properties:
    title:
      type: string
      description: "文章标题"
    published_date:
      type: string
      description: "发布日期"
    content:
      type: string
      description: "正文内容"
    author:
      type: string
      description: "作者姓名"
  required: ["title", "content"]

crawl_config:
  verbose: true
  wait_for: "body"

deduplication_enabled: true
fallback_download_enabled: true
fallback_max_size_mb: 10
```

#### 方法2: 使用示例任务文件 / Method 2: Use Example Task Files

推荐使用仓库中的示例文件：

```bash
# 使用列表页抓取示例
curl -X POST "http://localhost:8000/api/tasks/import?format=yaml" \
  -H "X-API-Key: your-mercury-api-key" \
  -H "Content-Type: text/plain" \
  --data-binary @examples/task_bjhdedu_list_crawl.yaml

# 或使用其他示例
# examples/task_chinese_llm_deepseek.json
# examples/task_news_with_template.yaml
# examples/task_product_with_template.yaml
```

**重要**: 记得修改示例文件中的 `api_key`!

**Important**: Remember to replace the `api_key` in example files!

### 验证配置 / Verify Configuration

创建任务后，检查任务详情:

```bash
# 获取任务详情
curl -H "X-API-Key: your-mercury-api-key" \
  "http://localhost:8000/api/tasks/{task_id}"
```

确认返回的JSON中包含:
```json
{
  "prompt_template": "请从这篇文章中提取...",  // ← 应该有内容
  "output_schema": {...},  // ← 可选
  "llm_provider": "openai",
  "llm_model": "deepseek-chat",
  "llm_params": {
    "api_key": "your-key",  // ← 应该有真实的key
    "base_url": "https://api.deepseek.com"
  }
}
```

### 日志验证 / Log Verification

运行任务后，检查worker日志应该看到:

```
INFO - Prompt template configured: 53 chars
INFO - Output schema configured: 234 chars
INFO - Configuring LLM extraction with provider=openai, model=deepseek-chat
INFO - API key present: sk-xxxxxx...
INFO - LLM extraction strategy configured successfully
INFO - Successfully parsed structured data for https://...
INFO - Saved structured data (LLM extraction) to MinIO: .../json/xxx.json
```

如果没有看到这些日志，说明 `prompt_template` 没有配置。

## 问题2: Markdown清洗没有效果 / Issue 2: Markdown Cleaning Not Working

### 症状 / Symptoms
```
Crawl4ai cleaning: 7784 -> 7784 chars (reduced 0.0%)
```
清洗前后字符数相同。

### 原因 / Root Cause
**已修复！** 在之前的版本中，markdown生成器没有配置 `PruningContentFilter`，导致无法去除header、footer、navigation等冗余内容。

**Fixed!** In previous versions, the markdown generator was not configured with `PruningContentFilter`, which prevented removal of headers, footers, navigation, and other redundant content.

### 解决方案 / Solution
**最新代码已自动启用内容过滤** - 现在系统会自动使用 `PruningContentFilter` 清洗markdown。

**Content filtering now enabled automatically** - The system now automatically uses `PruningContentFilter` to clean markdown.

你会在日志中看到 / You will see in logs:
```
DEBUG - Markdown generator configured with PruningContentFilter for content cleaning
DEBUG - Extracted raw markdown: 7784 characters
DEBUG - Extracted fit markdown (cleaned by crawl4ai): 3245 characters
INFO - Crawl4ai cleaning: 7784 -> 3245 chars (reduced 58.3%)
```

### 清洗策略 / Cleaning Strategy

系统现在使用两阶段清洗 / The system now uses two-stage cleaning:

#### Stage 1: Crawl4ai自动清洗 (PruningContentFilter)
- **自动启用** - 无需配置
- 移除：headers, footers, navigation, sidebars, ads
- 保留：core content with text density >= 48%
- 结果：生成 `fit_markdown` (cleaned version)

#### Stage 2: LLM结构化提取 (可选 / Optional)
- **需要配置** `prompt_template` 和 `output_schema`
- 提取：按照自定义schema的结构化数据
- 结果：生成JSON文件

```yaml
prompt_template: |
  请从这篇文章中提取核心内容，忽略以下内容：
  - 页面头部、尾部、导航菜单
  - 广告、推荐链接
  - 版权声明
  - 社交媒体分享按钮
  
  只提取：
  - 文章标题
  - 正文内容
  - 发布日期
```

### 进一步优化 / Further Optimization

如果默认的清洗效果不够理想，可以使用以下方法进一步优化：

If the default cleaning is not sufficient, you can further optimize using:

#### 方法A: 使用CSS选择器精确定位 / Method A: Use CSS Selectors

在 `crawl_config` 中指定主内容区域:

```yaml
crawl_config:
  verbose: true
  css_selector: "article, .main-content, .article-body"  # ← 只抓取主要内容
  wait_for: ".content"
```

这样crawl4ai只会提取指定区域的内容，效果更精准。

#### 方法B: 配置LLM提取 / Method B: Configure LLM Extraction

LLM提取会进一步清洗和结构化内容，是最强大的方式。参见"问题1"的配置方法。


## 完整诊断流程 / Complete Diagnostic Process

### 步骤1: 检查任务配置 / Step 1: Check Task Configuration

```bash
# 导出任务配置
curl -H "X-API-Key: your-mercury-api-key" \
  "http://localhost:8000/api/tasks/{task_id}/export?format=yaml" \
  > my_task_export.yaml

# 检查文件内容
cat my_task_export.yaml
```

确认包含:
- ✅ `prompt_template`: 有内容
- ✅ `output_schema`: 有定义 (可选)
- ✅ `llm_params.api_key`: 不是 "your-xxx-key-here"

### 步骤2: 运行任务并查看日志 / Step 2: Run Task and Check Logs

```bash
# 启动任务
RUN_ID=$(curl -s -X POST "http://localhost:8000/api/tasks/{task_id}/run" \
  -H "X-API-Key: your-mercury-api-key" | jq -r '.run_id')

echo "Run ID: $RUN_ID"

# 实时查看worker日志
docker compose logs -f worker
```

### 步骤3: 检查关键日志 / Step 3: Check Key Logs

应该看到的日志:

```
✅ INFO - Task name: xxx, URLs to crawl: X
✅ INFO - LLM config: provider=openai, model=deepseek-chat
✅ DEBUG - API key is configured in LLM params
✅ INFO - Prompt template configured: XXX chars          ← 如果缺少，说明没配置prompt
✅ INFO - Configuring LLM extraction with provider=...   ← 如果缺少，检查上一行
✅ DEBUG - Using standard LLM provider: openai
✅ INFO - LLM extraction strategy configured successfully
✅ INFO - Successfully parsed structured data for https://...
✅ INFO - Saved structured data (LLM extraction) to MinIO: .../json/xxx.json  ← JSON文件!
```

如果看到:
```
❌ WARNING - No prompt_template configured - LLM extraction will be skipped
```
说明 `prompt_template` 字段为空。

### 步骤4: 检查结果 / Step 4: Check Results

```bash
# 获取运行结果
curl -H "X-API-Key: your-mercury-api-key" \
  "http://localhost:8000/api/runs/$RUN_ID/result" | jq '.'

# 检查文档的 json_path
curl -H "X-API-Key: your-mercury-api-key" \
  "http://localhost:8000/api/runs/$RUN_ID/result" | jq '.documents[].json_path'
```

如果 `json_path` 不为 null，说明LLM提取成功！

## 常见错误 / Common Mistakes

### 错误1: API Key是占位符 / Mistake 1: Placeholder API Key
```yaml
llm_params:
  api_key: "your-deepseek-api-key"  # ❌ 这是占位符!
```

**修复 / Fix:**
```yaml
llm_params:
  api_key: "sk-abcd1234..."  # ✅ 使用真实的API key
```

### 错误2: 忘记配置prompt_template / Mistake 2: Forgot prompt_template
```yaml
name: "My Task"
urls: ["https://..."]
llm_provider: openai
llm_model: deepseek-chat
llm_params:
  api_key: "sk-..."
# ❌ 缺少 prompt_template!
```

**修复 / Fix:**
```yaml
name: "My Task"
urls: ["https://..."]
llm_provider: openai
llm_model: deepseek-chat
llm_params:
  api_key: "sk-..."
prompt_template: |  # ✅ 添加提取指令
  请提取文章的标题和内容。
```

### 错误3: Provider配置错误 / Mistake 3: Incorrect Provider
```yaml
llm_provider: deepseek  # ❌ 对于DeepSeek应该用 "openai"
llm_model: deepseek-chat
```

**修复 / Fix:**
```yaml
llm_provider: openai  # ✅ 正确
llm_model: deepseek-chat
llm_params:
  base_url: "https://api.deepseek.com"  # ← 重要!
```

## 获取更多帮助 / Get More Help

1. 查看示例文件: `examples/task_*.yaml` 和 `examples/task_*.json`
2. 阅读配置文档: `CONFIG.md`
3. 查看架构文档: `ARCHITECTURE.md`
4. 查看快速入门: `QUICKSTART.md`

如果问题仍然存在，提供以下信息:
- 完整的任务配置 (export as YAML)
- Worker日志 (docker compose logs worker)
- 运行结果 (GET /api/runs/{run_id}/result)

If the issue persists, provide:
- Complete task configuration (export as YAML)
- Worker logs (docker compose logs worker)
- Run result (GET /api/runs/{run_id}/result)
