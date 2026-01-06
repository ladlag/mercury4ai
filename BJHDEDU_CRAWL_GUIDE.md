# 北京海淀教育网站爬取指南
# Beijing Haidian Education Website Crawling Guide

本文档详细说明如何使用 Mercury4AI 爬取北京海淀教育网站 (https://www.bjhdedu.cn/zxfw/fwzt/szx/) 的完整步骤。

This document provides detailed steps for crawling the Beijing Haidian Education website (https://www.bjhdedu.cn/zxfw/fwzt/szx/) using Mercury4AI.

---

## 目录 / Table of Contents

1. [系统要求 / System Requirements](#系统要求--system-requirements)
2. [配置检查 / Configuration Check](#配置检查--configuration-check)
3. [启动服务 / Starting Services](#启动服务--starting-services)
4. [导入爬取任务 / Import Crawl Task](#导入爬取任务--import-crawl-task)
5. [执行爬取任务 / Execute Crawl Task](#执行爬取任务--execute-crawl-task)
6. [查看结果 / View Results](#查看结果--view-results)
7. [故障排查 / Troubleshooting](#故障排查--troubleshooting)

---

## 系统要求 / System Requirements

### 必需软件 / Required Software

- Docker (version 20.10+)
- Docker Compose (version 2.0+)
- curl (用于API调用 / for API calls)
- 至少 2GB 可用内存 / At least 2GB free RAM
- 至少 10GB 可用磁盘空间 / At least 10GB free disk space

### 可选软件 / Optional Software

- jq (用于JSON格式化 / for JSON formatting)
- python3 (用于JSON解析 / for JSON parsing)

---

## 配置检查 / Configuration Check

### 步骤 1: 克隆仓库 / Step 1: Clone Repository

```bash
git clone https://github.com/ladlag/mercury4ai.git
cd mercury4ai
```

### 步骤 2: 检查配置文件 / Step 2: Check Configuration Files

#### 2.1 验证 Docker Compose 配置 / Verify Docker Compose Configuration

```bash
# 检查 docker-compose.yml 文件是否存在
ls -la docker-compose.yml

# 验证配置语法
docker compose config
```

**预期输出 / Expected Output:**
- 应该显示完整的 Docker Compose 配置，没有错误信息
- Should display complete Docker Compose configuration without errors

#### 2.2 检查示例任务文件 / Check Example Task Files

```bash
# 列出所有示例文件
ls -la examples/

# 验证 bjhdedu 任务配置文件
cat examples/task_bjhdedu_list_crawl.yaml
```

**文件内容说明 / File Content Description:**

该文件包含以下关键配置 / The file contains the following key configurations:

- **目标URL / Target URL:** `https://www.bjhdedu.cn/zxfw/fwzt/szx/`
- **爬取配置 / Crawl Config:** 包含JavaScript执行、等待时间等设置
- **LLM配置 / LLM Config:** 支持 DeepSeek、Qwen、ERNIE 等国产大模型
- **输出格式 / Output Schema:** 定义了提取数据的JSON结构

#### 2.3 设置环境变量 / Set Environment Variables

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件（可选）
# 默认配置已经可以运行，但建议修改以下项：
nano .env  # 或使用其他编辑器
```

**重要配置项 / Important Configuration Items:**

```bash
# API认证密钥（生产环境请修改）
API_KEY=your-secure-api-key-change-this

# 如果使用国产大模型，配置以下项：
# For using Chinese LLMs, configure the following:

# 方案1: DeepSeek
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=deepseek-chat
DEFAULT_LLM_API_KEY=your-deepseek-api-key
DEFAULT_LLM_BASE_URL=https://api.deepseek.com
DEFAULT_LLM_TEMPERATURE=0.1

# 方案2: Qwen/通义千问
# DEFAULT_LLM_PROVIDER=openai
# DEFAULT_LLM_MODEL=qwen-turbo
# DEFAULT_LLM_API_KEY=your-dashscope-api-key
# DEFAULT_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
# DEFAULT_LLM_TEMPERATURE=0.1
```

### 步骤 3: 验证依赖项 / Step 3: Verify Dependencies

```bash
# 检查 requirements.txt
cat requirements.txt

# 验证关键依赖项
grep -E "fastapi|crawl4ai|sqlalchemy|redis|minio" requirements.txt
```

**预期输出 / Expected Output:**
```
fastapi==0.115.0
crawl4ai>=0.7.8
sqlalchemy==2.0.36
redis==5.2.0
minio==7.2.10
```

---

## 启动服务 / Starting Services

### 步骤 1: 启动所有服务 / Step 1: Start All Services

```bash
# 使用 docker compose 启动所有服务
docker compose up -d
```

**预期输出 / Expected Output:**
```
[+] Running 6/6
 ✔ Network mercury4ai_default       Created
 ✔ Container mercury4ai-postgres    Started
 ✔ Container mercury4ai-redis       Started
 ✔ Container mercury4ai-minio       Started
 ✔ Container mercury4ai-api         Started
 ✔ Container mercury4ai-worker-1    Started
 ✔ Container mercury4ai-worker-2    Started
```

### 步骤 2: 等待服务就绪 / Step 2: Wait for Services Ready

```bash
# 等待 30-60 秒，让所有服务完全启动
echo "等待服务启动... / Waiting for services to start..."
sleep 45

# 检查所有容器状态
docker compose ps
```

**预期输出 / Expected Output:**
所有服务的 STATUS 应该显示 "Up" 或 "Up (healthy)"
All services STATUS should show "Up" or "Up (healthy)"

### 步骤 3: 验证服务健康状态 / Step 3: Verify Service Health

```bash
# 使用提供的验证脚本
chmod +x validate.sh
./validate.sh
```

**或者手动验证每个服务 / Or manually verify each service:**

#### 3.1 检查 PostgreSQL

```bash
docker compose exec postgres pg_isready -U mercury4ai
```

**预期输出:** `/tmp:5432 - accepting connections`

#### 3.2 检查 Redis

```bash
docker compose exec redis redis-cli ping
```

**预期输出:** `PONG`

#### 3.3 检查 MinIO

```bash
curl -f http://localhost:9000/minio/health/live
```

**预期输出:** 返回 200 状态码 / Returns 200 status code

#### 3.4 检查 API 服务

```bash
curl -H "X-API-Key: your-secure-api-key-change-this" http://localhost:8000/api/health
```

**预期输出 / Expected Output:**
```json
{
  "status": "healthy",
  "database": "healthy",
  "redis": "healthy",
  "minio": "healthy"
}
```

### 步骤 4: 查看服务日志 / Step 4: View Service Logs

```bash
# 查看所有服务日志
docker compose logs -f

# 或查看特定服务日志
docker compose logs -f api
docker compose logs -f worker
```

---

## 导入爬取任务 / Import Crawl Task

### 方案 1: 使用 YAML 文件导入（推荐）/ Method 1: Import from YAML File (Recommended)

```bash
# 使用 task_bjhdedu_list_crawl.yaml 文件
curl -X POST "http://localhost:8000/api/tasks/import?format=yaml" \
  -H "X-API-Key: your-secure-api-key-change-this" \
  -H "Content-Type: text/plain" \
  --data-binary @examples/task_bjhdedu_list_crawl.yaml
```

**预期输出 / Expected Output:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Beijing Education List Page Crawl",
  "description": "爬取北京教育列表页 https://www.bjhdedu.cn/zxfw/fwzt/szx/ 的示例配置",
  "message": "Task imported successfully"
}
```

**重要:** 保存返回的任务ID (task_id)，后续步骤需要使用。
**Important:** Save the returned task ID for use in subsequent steps.

### 方案 2: 使用 JSON 直接创建 / Method 2: Create Directly with JSON

```bash
# 创建任务
TASK_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/tasks" \
  -H "X-API-Key: your-secure-api-key-change-this" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "北京海淀教育网站爬取",
    "description": "爬取 https://www.bjhdedu.cn/zxfw/fwzt/szx/ 的教育服务列表",
    "urls": ["https://www.bjhdedu.cn/zxfw/fwzt/szx/"],
    "crawl_config": {
      "verbose": true,
      "screenshot": false,
      "wait_for": ".content",
      "css_selector": ".list-item, .article-list, .content-list",
      "js_code": "await new Promise(resolve => setTimeout(resolve, 2000));"
    },
    "llm_provider": "openai",
    "llm_model": "deepseek-chat",
    "llm_params": {
      "api_key": "your-deepseek-api-key",
      "base_url": "https://api.deepseek.com",
      "temperature": 0.1,
      "max_tokens": 4000
    },
    "prompt_template": "请从这个教育服务列表页面中提取以下信息：\n1. 列表中的所有服务项目\n2. 每个项目的标题\n3. 每个项目的链接URL\n4. 每个项目的描述或摘要\n5. 发布日期（如果有）\n\n将结果组织成JSON数组格式。",
    "output_schema": {
      "type": "object",
      "properties": {
        "page_title": {"type": "string"},
        "items": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "title": {"type": "string"},
              "url": {"type": "string"},
              "description": {"type": "string"},
              "date": {"type": "string"}
            },
            "required": ["title"]
          }
        },
        "total_count": {"type": "integer"}
      },
      "required": ["items"]
    },
    "deduplication_enabled": true,
    "fallback_download_enabled": true,
    "fallback_max_size_mb": 10
  }')

# 提取任务ID
TASK_ID=$(echo "$TASK_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "任务已创建，ID: $TASK_ID"
echo "Task created with ID: $TASK_ID"
```

### 验证任务创建 / Verify Task Creation

```bash
# 查看任务详情（替换 TASK_ID 为实际值）
curl -H "X-API-Key: your-secure-api-key-change-this" \
  "http://localhost:8000/api/tasks/$TASK_ID" | python3 -m json.tool
```

---

## 执行爬取任务 / Execute Crawl Task

### 步骤 1: 启动任务运行 / Step 1: Start Task Run

```bash
# 启动任务（替换 TASK_ID 为实际的任务ID）
RUN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/tasks/$TASK_ID/run" \
  -H "X-API-Key: your-secure-api-key-change-this")

# 提取运行ID
RUN_ID=$(echo "$RUN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['run_id'])")
echo "任务运行已启动，Run ID: $RUN_ID"
echo "Task run started with ID: $RUN_ID"
```

**预期输出 / Expected Output:**
```json
{
  "run_id": "660e8400-e29b-41d4-a716-446655440111",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Task run started"
}
```

### 步骤 2: 监控任务进度 / Step 2: Monitor Task Progress

```bash
# 每隔几秒检查一次状态
watch -n 5 "curl -s -H 'X-API-Key: your-secure-api-key-change-this' \
  http://localhost:8000/api/runs/$RUN_ID | python3 -m json.tool"
```

**或者使用循环检查 / Or use a loop:**

```bash
# 持续检查直到完成
while true; do
  STATUS=$(curl -s -H "X-API-Key: your-secure-api-key-change-this" \
    "http://localhost:8000/api/runs/$RUN_ID" | \
    python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))")
  
  echo "当前状态 / Current status: $STATUS"
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  
  sleep 5
done

echo "任务执行完成！/ Task execution completed!"
```

### 步骤 3: 查看 Worker 日志 / Step 3: View Worker Logs

```bash
# 实时查看 worker 日志
docker compose logs -f worker
```

**典型日志输出 / Typical Log Output:**
```
mercury4ai-worker-1  | Starting crawl task 550e8400-e29b-41d4-a716-446655440000
mercury4ai-worker-1  | Crawling URL: https://www.bjhdedu.cn/zxfw/fwzt/szx/
mercury4ai-worker-1  | Successfully crawled: https://www.bjhdedu.cn/zxfw/fwzt/szx/
mercury4ai-worker-1  | Documents created: 1
mercury4ai-worker-1  | Run completed successfully
```

---

## 查看结果 / View Results

### 步骤 1: 获取运行状态详情 / Step 1: Get Run Status Details

```bash
curl -s -H "X-API-Key: your-secure-api-key-change-this" \
  "http://localhost:8000/api/runs/$RUN_ID" | python3 -m json.tool
```

**预期输出 / Expected Output:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440111",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "started_at": "2024-01-15T10:30:00",
  "completed_at": "2024-01-15T10:32:00",
  "urls_crawled": 1,
  "urls_failed": 0,
  "documents_created": 1,
  "error_message": null,
  "minio_path": "2024-01-15/660e8400-e29b-41d4-a716-446655440111"
}
```

### 步骤 2: 获取爬取结果 / Step 2: Get Crawl Results

```bash
# 获取详细结果，包括提取的数据
curl -s -H "X-API-Key: your-secure-api-key-change-this" \
  "http://localhost:8000/api/runs/$RUN_ID/result" | python3 -m json.tool
```

**结果包含 / Results Include:**
- **documents**: 提取的文档列表 / List of extracted documents
- **structured_data**: LLM提取的结构化数据 / Structured data extracted by LLM
- **images**: 页面中的图片列表 / List of images from the page
- **attachments**: 附件列表 / List of attachments
- **markdown**: 页面的Markdown格式 / Page in Markdown format

**示例结果结构 / Example Result Structure:**
```json
{
  "run": {
    "id": "660e8400-e29b-41d4-a716-446655440111",
    "status": "completed"
  },
  "documents": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440222",
      "url": "https://www.bjhdedu.cn/zxfw/fwzt/szx/",
      "title": "数字校园 - 北京海淀教育",
      "structured_data": {
        "page_title": "数字校园服务专题",
        "items": [
          {
            "title": "海淀区中小学数字校园建设指南",
            "url": "https://www.bjhdedu.cn/...",
            "description": "...",
            "date": "2024-01-10"
          }
        ],
        "total_count": 15
      }
    }
  ],
  "total_documents": 1
}
```

### 步骤 3: 获取日志和工件 / Step 3: Get Logs and Artifacts

```bash
# 获取 MinIO 存储的文件路径和下载链接
curl -s -H "X-API-Key: your-secure-api-key-change-this" \
  "http://localhost:8000/api/runs/$RUN_ID/logs" | python3 -m json.tool
```

**输出包含 / Output Includes:**
- **minio_path**: MinIO存储路径 / MinIO storage path
- **artifacts**: 各类文件的预签名下载URL / Pre-signed download URLs for artifacts
  - JSON文件 / JSON files
  - Markdown文件 / Markdown files
  - 图片文件 / Image files
  - 日志文件 / Log files

### 步骤 4: 访问 MinIO 控制台 / Step 4: Access MinIO Console

```bash
# 在浏览器中打开 MinIO 控制台
# Open MinIO console in browser
echo "MinIO Console: http://localhost:9001"
echo "用户名 / Username: minioadmin"
echo "密码 / Password: minioadmin"
```

**导航到存储桶 / Navigate to Bucket:**
1. 登录 MinIO 控制台 / Login to MinIO console
2. 打开 `mercury4ai` 存储桶 / Open `mercury4ai` bucket
3. 导航到日期文件夹（如 `2024-01-15`）/ Navigate to date folder (e.g., `2024-01-15`)
4. 打开运行ID文件夹 / Open the run ID folder
5. 查看和下载文件：/ View and download files:
   - `json/` - 结构化数据 / Structured data
   - `markdown/` - Markdown内容 / Markdown content
   - `images/` - 图片 / Images
   - `logs/` - 日志和清单 / Logs and manifests

---

## 故障排查 / Troubleshooting

### 问题 1: 服务无法启动 / Issue 1: Services Won't Start

**症状 / Symptoms:**
```bash
docker compose ps
# 显示某些服务状态为 "Exited" 或 "Unhealthy"
```

**解决方案 / Solutions:**

```bash
# 1. 查看服务日志
docker compose logs postgres
docker compose logs redis
docker compose logs minio
docker compose logs api
docker compose logs worker

# 2. 重启服务
docker compose down
docker compose up -d

# 3. 完全清理并重启（警告：会删除数据）
docker compose down -v
docker compose up -d
```

### 问题 2: API 返回 403 Forbidden / Issue 2: API Returns 403 Forbidden

**症状 / Symptoms:**
```json
{"detail": "Invalid API Key"}
```

**解决方案 / Solutions:**

```bash
# 1. 检查 API Key 是否正确
echo $API_KEY

# 2. 确保使用正确的 API Key
export API_KEY="your-secure-api-key-change-this"

# 3. 或在 .env 文件中设置
echo "API_KEY=your-secure-api-key-change-this" >> .env

# 4. 重启 API 服务
docker compose restart api
```

### 问题 3: 任务一直处于 pending 状态 / Issue 3: Task Stuck in Pending Status

**症状 / Symptoms:**
任务运行状态长时间显示 "pending" / Task run status shows "pending" for a long time

**解决方案 / Solutions:**

```bash
# 1. 检查 worker 是否在运行
docker compose ps | grep worker

# 2. 查看 worker 日志
docker compose logs -f worker

# 3. 检查 Redis 连接
docker compose exec redis redis-cli ping

# 4. 重启 worker
docker compose restart worker
```

### 问题 4: LLM 提取失败 / Issue 4: LLM Extraction Fails

**症状 / Symptoms:**
- 任务完成但没有结构化数据 / Task completes but no structured data
- Worker 日志显示 LLM API 错误 / Worker logs show LLM API errors

**解决方案 / Solutions:**

```bash
# 1. 检查 LLM API Key 是否有效
# 在任务配置中确认 llm_params.api_key 正确

# 2. 检查 LLM 服务可用性
# DeepSeek
curl -H "Authorization: Bearer your-deepseek-api-key" \
  https://api.deepseek.com/v1/models

# Qwen
curl -H "Authorization: Bearer your-dashscope-api-key" \
  https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation

# 3. 增加详细日志
# 在 crawl_config 中设置 verbose: true

# 4. 不使用 LLM 进行测试
# 创建一个不带 LLM 配置的简单爬取任务
```

### 问题 5: 无法访问目标网站 / Issue 5: Cannot Access Target Website

**症状 / Symptoms:**
- 爬取失败，错误信息显示连接超时或被拒绝
- Task fails with connection timeout or refused errors

**解决方案 / Solutions:**

```bash
# 1. 测试网络连接
curl -I https://www.bjhdedu.cn/zxfw/fwzt/szx/

# 2. 检查 Docker 容器的网络
docker compose exec worker curl -I https://www.bjhdedu.cn/zxfw/fwzt/szx/

# 3. 如果需要代理，在 docker-compose.yml 中添加：
# environment:
#   - HTTP_PROXY=http://proxy.example.com:8080
#   - HTTPS_PROXY=http://proxy.example.com:8080

# 4. 增加超时时间
# 在 crawl_config 中添加：
# "timeout": 60
```

### 问题 6: MinIO 存储错误 / Issue 6: MinIO Storage Errors

**症状 / Symptoms:**
- Worker 日志显示 MinIO 连接错误
- Worker logs show MinIO connection errors

**解决方案 / Solutions:**

```bash
# 1. 检查 MinIO 服务
curl http://localhost:9000/minio/health/live

# 2. 验证 MinIO 凭据
docker compose exec api env | grep MINIO

# 3. 手动创建 bucket（如果不存在）
docker compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker compose exec minio mc mb local/mercury4ai

# 4. 检查 MinIO 日志
docker compose logs minio
```

### 常用调试命令 / Common Debugging Commands

```bash
# 查看所有容器状态
docker compose ps -a

# 查看特定容器的详细日志
docker compose logs --tail=100 api
docker compose logs --tail=100 worker

# 进入容器进行调试
docker compose exec api bash
docker compose exec worker bash

# 检查数据库连接
docker compose exec postgres psql -U mercury4ai -d mercury4ai -c "SELECT COUNT(*) FROM crawl_task;"

# 检查 Redis 队列
docker compose exec redis redis-cli KEYS "*"
docker compose exec redis redis-cli LLEN rq:queue:crawl_tasks

# 重启单个服务
docker compose restart api
docker compose restart worker

# 查看资源使用情况
docker stats
```

---

## 高级配置 / Advanced Configuration

### 自定义 JavaScript 代码 / Custom JavaScript Code

在 `task_bjhdedu_list_crawl.yaml` 中，可以自定义 JavaScript 代码来处理动态内容：

```yaml
crawl_config:
  js_code: |
    // 等待页面加载
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // 点击"加载更多"按钮
    const loadMoreBtn = document.querySelector('.load-more-btn');
    if (loadMoreBtn) {
      loadMoreBtn.click();
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    
    // 滚动到页面底部
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise(resolve => setTimeout(resolve, 1000));
```

### 使用不同的国产大模型 / Using Different Chinese LLMs

#### DeepSeek 配置 / DeepSeek Configuration
```yaml
llm_provider: openai
llm_model: deepseek-chat
llm_params:
  api_key: "your-deepseek-api-key"
  base_url: "https://api.deepseek.com"
  temperature: 0.1
  max_tokens: 4000
```

#### Qwen 配置 / Qwen Configuration
```yaml
llm_provider: openai
llm_model: qwen-turbo  # 或 qwen-plus, qwen-max
llm_params:
  api_key: "your-dashscope-api-key"
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  temperature: 0.1
```

#### ERNIE 配置 / ERNIE Configuration
```yaml
llm_provider: openai
llm_model: ernie-bot-turbo
llm_params:
  api_key: "your-baidu-api-key"
  base_url: "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop"
  temperature: 0.1
```

---

## 总结 / Summary

### 完整执行流程 / Complete Execution Flow

```bash
# 1. 启动服务
docker compose up -d && sleep 45

# 2. 验证健康状态
./validate.sh

# 3. 导入任务
curl -X POST "http://localhost:8000/api/tasks/import?format=yaml" \
  -H "X-API-Key: your-secure-api-key-change-this" \
  -H "Content-Type: text/plain" \
  --data-binary @examples/task_bjhdedu_list_crawl.yaml

# 4. 启动任务（使用返回的 TASK_ID）
curl -X POST "http://localhost:8000/api/tasks/$TASK_ID/run" \
  -H "X-API-Key: your-secure-api-key-change-this"

# 5. 查看结果（使用返回的 RUN_ID）
curl -s -H "X-API-Key: your-secure-api-key-change-this" \
  "http://localhost:8000/api/runs/$RUN_ID/result" | python3 -m json.tool
```

### 关键要点 / Key Points

1. **确保所有服务健康** / Ensure all services are healthy before starting tasks
2. **正确配置 API Key** / Configure API Key correctly
3. **LLM API Key 必须有效** / LLM API Key must be valid for extraction to work
4. **监控 worker 日志** / Monitor worker logs for troubleshooting
5. **使用 MinIO 控制台** / Use MinIO console to access downloaded files

### 相关文档 / Related Documentation

- [README.md](README.md) - 项目总览 / Project overview
- [QUICKSTART.md](QUICKSTART.md) - 快速开始 / Quick start guide
- [CHINESE_LLM_GUIDE.md](CHINESE_LLM_GUIDE.md) - 国产大模型配置详解 / Chinese LLM configuration
- [DEPLOYMENT.md](DEPLOYMENT.md) - 部署指南 / Deployment guide

---

## 联系和支持 / Contact and Support

如有问题，请访问：
For issues, please visit:

- GitHub Issues: https://github.com/ladlag/mercury4ai/issues
- Documentation: http://localhost:8000/docs (when running)

---

**最后更新 / Last Updated:** 2024-01-15
**版本 / Version:** 1.0.0
