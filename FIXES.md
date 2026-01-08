# 修复说明 / Fix Summary

## 已修复的问题 / Issues Fixed

### 问题1: Markdown清洗无效 / Issue 1: Markdown Cleaning Not Working

#### 症状 / Symptom
```
Crawl4ai cleaning: 6251 -> 6251 chars (reduced 0.0%)
```

#### 根本原因 / Root Cause
Markdown生成器没有配置内容过滤器（`PruningContentFilter`），导致无法去除header、footer、navigation等冗余内容。

The markdown generator was not configured with a content filter (`PruningContentFilter`), preventing removal of headers, footers, navigation, and other redundant content.

#### 修复方案 / Fix
1. 导入 `PruningContentFilter` from `crawl4ai.content_filter_strategy`
2. 配置markdown生成器使用 `PruningContentFilter`:
   - `threshold=0.48`: 保留文本密度 >= 48% 的内容块
   - `threshold_type="dynamic"`: 动态调整阈值
   - `min_word_threshold=0`: 包含满足密度要求的短块
3. 更新 `extract_markdown_versions()` 正确处理 `MarkdownGenerationResult` 对象
4. 不再将 `raw_markdown` 作为 `fit_markdown` 的后备选项

#### 预期结果 / Expected Result
现在你会看到类似的日志 / Now you will see logs like:
```
DEBUG - Markdown generator configured with PruningContentFilter for content cleaning
DEBUG - Extracted raw markdown: 6251 characters
DEBUG - Extracted fit markdown (cleaned by crawl4ai): 2834 characters
INFO - Crawl4ai cleaning: 6251 -> 2834 chars (reduced 54.7%)
```

---

### 问题2: LLM提取未执行 / Issue 2: LLM Extraction Not Running

#### 症状 / Symptom
```
WARNING - No prompt_template configured - LLM extraction will be skipped even if LLM config is present
```
- 没有看到 "Configuring LLM extraction with provider=..." 日志
- 没有生成JSON文件
- `structured_data` 为空

#### 根本原因 / Root Cause
任务配置中缺少 `prompt_template` 字段。

The task configuration is missing the `prompt_template` field.

LLM提取需要两个必需组件 / LLM extraction requires two mandatory components:
1. LLM配置: `llm_provider` + `llm_model` + `llm_params.api_key`
2. **提取指令: `prompt_template`** ← 这个缺少了！/ This is missing!

#### 修复方案 / Fix
1. 增强警告消息，提供可操作的指导
2. 引导用户查看 `TROUBLESHOOTING_LLM_EXTRACTION.md`

#### 用户需要做什么 / What Users Need to Do

在任务配置中添加 `prompt_template`:

```yaml
name: "My Custom Task"
urls:
  - "https://www.xschu.com/gongbanzhongxue/84458.html"

# LLM配置
llm_provider: openai
llm_model: deepseek-chat
llm_params:
  api_key: "sk-your-actual-api-key"  # 使用真实的API key
  base_url: "https://api.deepseek.com"
  temperature: 0.1
  max_tokens: 4000

# ← 必需！添加提取指令
prompt_template: |
  请从这篇文章中提取以下信息：
  - 标题
  - 发布日期
  - 正文内容
  - 作者（如果有）
  
  以JSON格式返回结果。

# 可选但推荐
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

#### 预期结果 / Expected Result
配置 `prompt_template` 后，你会看到 / After configuring `prompt_template`, you will see:
```
INFO - Prompt template configured: 87 chars
INFO - Output schema configured
INFO - Configuring LLM extraction with provider=openai, model=deepseek-chat
INFO - LLM extraction strategy configured successfully
INFO - Successfully parsed structured data for https://...
INFO - Saved structured data (LLM extraction) to MinIO: .../json/xxx.json
```

---

## 技术细节 / Technical Details

### 两阶段清洗 / Two-Stage Cleaning

系统现在使用两阶段清洗策略 / The system now uses a two-stage cleaning strategy:

#### Stage 1: Crawl4ai自动清洗 (PruningContentFilter)
- **自动启用** - 无需用户配置 / **Automatically enabled** - no user configuration needed
- 功能 / Features:
  - 移除headers, footers, navigation, sidebars, ads
  - 使用文本密度算法识别核心内容
  - 动态阈值调整
- 输出 / Output:
  - `raw_markdown`: 完整的markdown（包含所有内容）
  - `fit_markdown`: 清洗后的markdown（只包含核心内容）

#### Stage 2: LLM结构化提取 (可选 / Optional)
- **需要配置** `prompt_template` 和 `output_schema`
- 功能 / Features:
  - 按照自定义schema提取结构化数据
  - 进一步清洗和标准化内容
  - 支持复杂的提取逻辑
- 输出 / Output:
  - `structured_data`: JSON格式的结构化数据
  - 保存为 `{document_id}.json` 文件

### 文件结构 / File Structure

抓取后会生成以下文件 / After crawling, the following files are generated:

```
2026-01-08/
└── {run_id}/
    ├── markdown/
    │   ├── {doc_id}.md              # 原始markdown (raw_markdown)
    │   └── {doc_id}_cleaned.md      # 清洗后markdown (fit_markdown) ← 现在会有明显差异
    ├── json/
    │   └── {doc_id}.json            # 结构化数据 (如果配置了LLM提取)
    ├── images/
    │   └── *.jpg, *.png, *.gif      # 下载的图片
    └── logs/
        ├── run_manifest.json
        └── resource_index.json
```

---

## 验证修复 / Verify the Fix

### 1. 检查Markdown清洗 / Check Markdown Cleaning

运行任务后查看worker日志 / After running a task, check worker logs:

```bash
docker compose logs -f worker
```

应该看到 / You should see:
```
✓ DEBUG - Markdown generator configured with PruningContentFilter for content cleaning
✓ INFO - Crawl4ai cleaning: 6251 -> 2834 chars (reduced 54.7%)
```

如果仍然看到 `reduced 0.0%`，请检查：
- crawl4ai版本是否 >= 0.7.8
- 是否正确安装了依赖

If you still see `reduced 0.0%`, check:
- crawl4ai version >= 0.7.8
- Dependencies are correctly installed

### 2. 检查LLM提取 / Check LLM Extraction

#### 步骤1: 验证任务配置 / Step 1: Verify Task Configuration
```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/tasks/{task_id}" | jq '.prompt_template'
```

应该返回你配置的prompt，而不是 `null`。
Should return your configured prompt, not `null`.

#### 步骤2: 运行任务并查看日志 / Step 2: Run Task and Check Logs
```bash
curl -X POST -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/tasks/{task_id}/run"

docker compose logs -f worker
```

应该看到 / You should see:
```
✓ INFO - Prompt template configured: XX chars
✓ INFO - Configuring LLM extraction with provider=openai, model=deepseek-chat
✓ INFO - LLM extraction strategy configured successfully
✓ INFO - Successfully parsed structured data for https://...
✓ INFO - Saved structured data (LLM extraction) to MinIO: .../json/xxx.json
```

#### 步骤3: 检查结果 / Step 3: Check Results
```bash
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8000/api/runs/{run_id}/result" | jq '.documents[].json_path'
```

应该返回JSON文件路径，而不是 `null`。
Should return JSON file path, not `null`.

---

## 示例配置 / Example Configuration

仓库中的示例文件已包含完整配置 / Example files in the repository include complete configurations:

```bash
# 使用示例任务
examples/task_chinese_llm_deepseek.json
examples/task_news_with_template.yaml
examples/task_bjhdedu_list_crawl.yaml
```

**重要**: 记得修改 `api_key` 为你的真实API key！
**Important**: Remember to replace `api_key` with your actual API key!

---

## 获取帮助 / Get Help

如果问题仍然存在 / If issues persist:
1. 查看 `TROUBLESHOOTING_LLM_EXTRACTION.md` 完整故障排除指南
2. 提供以下信息:
   - 完整的任务配置 (GET /api/tasks/{task_id})
   - Worker日志 (docker compose logs worker)
   - 运行结果 (GET /api/runs/{run_id}/result)

See `TROUBLESHOOTING_LLM_EXTRACTION.md` for complete troubleshooting guide.
