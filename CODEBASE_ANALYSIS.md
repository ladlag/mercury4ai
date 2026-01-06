# Mercury4AI 代码库功能分析文档

## 目录

1. [项目概述](#项目概述)
2. [系统架构](#系统架构)
3. [核心功能](#核心功能)
4. [业务场景](#业务场景)
5. [业务流程](#业务流程)
6. [数据模型](#数据模型)
7. [技术栈](#技术栈)
8. [部署架构](#部署架构)

---

## 项目概述

### 项目定位
Mercury4AI 是一个生产级的 Web 爬虫编排系统，基于 FastAPI、RQ (Redis Queue)、PostgreSQL、MinIO 和 crawl4ai 构建。该系统旨在通过 LLM（大语言模型）实现智能化的结构化数据提取，并具备自动化图片/附件处理和完整的结果归档能力。

### 核心价值
- **智能提取**: 利用 LLM 进行智能化内容提取和结构化
- **可靠性**: 生产级架构，支持任务队列、错误处理和重试机制
- **可扩展性**: 分布式 Worker 架构，可水平扩展
- **完整性**: 完整保存爬取结果，包括 Markdown、JSON、图片、附件和日志
- **易用性**: RESTful API + 完整的任务配置管理

### 项目特点
1. **FastAPI RESTful API** - 现代化的 API 框架，支持 API Key 认证
2. **任务队列处理** - 基于 RQ 和 Redis 的异步任务队列
3. **LLM 智能提取** - 通过 crawl4ai 集成 LLM，支持基于 Schema 的结构化输出
4. **PostgreSQL 存储** - 持久化存储任务、运行记录和文档数据
5. **MinIO 对象存储** - 存储爬取结果的各类制品（markdown、JSON、图片、附件、日志）
6. **智能媒体处理** - 带有降级下载策略的智能媒体处理
7. **URL 去重** - 支持增量爬取的 URL 去重机制
8. **任务导入导出** - 支持 JSON 和 YAML 格式的任务配置管理
9. **完整制品归档** - 带有清单和资源索引的完整归档系统
10. **Docker Compose 部署** - 一键式容器化部署方案

---

## 系统架构

### 整体架构图

```
┌─────────────────┐         ┌──────────────┐         ┌─────────────────┐
│   FastAPI API   │────────▶│    Redis     │◀────────│   RQ Workers    │
│   (端口 8000)   │         │   (队列)     │         │   (爬虫执行)    │
└─────────────────┘         └──────────────┘         └─────────────────┘
        │                           │                          │
        │                           │                          │
        ▼                           ▼                          ▼
┌─────────────────┐         ┌──────────────┐         ┌─────────────────┐
│   PostgreSQL    │         │    Redis     │         │      MinIO      │
│   (元数据)      │         │   (状态)     │         │   (对象存储)    │
│   (端口 5432)   │         │ (端口 6379)  │         │  (端口 9000)    │
└─────────────────┘         └──────────────┘         └─────────────────┘
```

### 组件说明

#### 1. API 层 (FastAPI)
- **职责**: 接收用户请求，管理任务配置，触发爬取任务
- **端口**: 8000
- **主要端点**:
  - `/api/tasks` - 任务管理（CRUD）
  - `/api/tasks/{id}/run` - 启动任务运行
  - `/api/runs/{id}` - 查询运行状态
  - `/api/runs/{id}/result` - 获取运行结果
  - `/api/health` - 健康检查

#### 2. 任务队列 (Redis + RQ)
- **职责**: 异步任务调度和执行
- **队列名称**: `crawl_tasks`
- **特性**:
  - 任务超时控制（默认 1 小时）
  - 结果保留时间（24 小时）
  - 失败任务保留（24 小时）
  - 支持多 Worker 并发执行

#### 3. Worker 层 (RQ Workers)
- **职责**: 执行实际的网页爬取和数据处理任务
- **实例数量**: 默认 2 个（可通过 docker-compose 调整）
- **核心功能**:
  - 网页爬取（crawl4ai）
  - LLM 内容提取
  - 媒体资源下载
  - 数据持久化
  - 结果归档

#### 4. 数据库 (PostgreSQL)
- **职责**: 存储任务配置、运行记录、文档元数据
- **版本**: PostgreSQL 16
- **核心表**:
  - `crawl_task` - 爬取任务配置
  - `crawl_task_run` - 任务运行记录
  - `document` - 爬取的文档
  - `document_image` - 图片元数据
  - `document_attachment` - 附件元数据
  - `crawled_url_registry` - URL 去重注册表

#### 5. 对象存储 (MinIO)
- **职责**: 存储爬取结果的各类文件
- **端口**: 9000 (API), 9001 (控制台)
- **存储结构**:
  ```
  mercury4ai/
  └── {YYYY-MM-DD}/
      └── {runId}/
          ├── json/          # 结构化数据
          ├── markdown/      # Markdown 内容
          ├── images/        # 图片文件
          ├── attachments/   # 附件文件
          └── logs/          # 运行日志和清单
  ```

#### 6. 缓存层 (Redis)
- **职责**: 
  - 任务队列存储
  - Worker 状态管理
  - 可选的缓存功能
- **版本**: Redis 7

---

## 核心功能

### 1. 任务管理

#### 1.1 任务创建
- **功能**: 创建新的爬取任务配置
- **支持配置**:
  - 基础信息（名称、描述、URL 列表）
  - 爬取配置（JS 执行、等待条件、CSS 选择器等）
  - LLM 配置（提供商、模型、API Key、参数）
  - 提示词模板（指导 LLM 提取）
  - 输出 Schema（定义结构化输出格式）
  - 去重配置
  - 日期过滤
  - 降级下载配置

#### 1.2 任务编辑与删除
- **更新任务**: 支持部分更新（PATCH 语义）
- **删除任务**: 级联删除相关的运行记录和文档

#### 1.3 任务列表与查询
- **列表查询**: 支持分页
- **详情查询**: 获取单个任务的完整配置

#### 1.4 任务导入导出
- **格式支持**: JSON、YAML
- **用途**: 
  - 任务配置备份
  - 跨环境迁移
  - 任务模板分享

### 2. 爬取执行

#### 2.1 任务启动
- **触发方式**: RESTful API 调用
- **执行模式**: 异步执行（通过 RQ 队列）
- **返回信息**: 运行 ID、任务 ID、作业 ID

#### 2.2 网页爬取
- **引擎**: crawl4ai（基于 Playwright）
- **特性**:
  - JavaScript 渲染支持
  - 自定义等待条件
  - CSS 选择器过滤
  - 屏幕截图支持
  - PDF 生成支持
  - 代理支持（通过配置）

#### 2.3 内容提取
- **方式一**: 基础文本提取（Markdown 格式）
- **方式二**: LLM 智能提取（结构化 JSON）
- **LLM 支持**:
  - OpenAI (GPT-3.5, GPT-4)
  - Anthropic (Claude)
  - **国产大模型支持**:
    - DeepSeek（深度求索）
    - Qwen（通义千问）
    - ERNIE（文心一言）
  - 其他 OpenAI 兼容 API

#### 2.4 媒体处理
- **图片下载**:
  - 自动下载页面中的图片
  - 支持降级下载策略
  - 保存原始 URL 和 MinIO 路径
  - 记录下载状态和方法
  
- **附件下载**:
  - 自动识别和下载附件（PDF 等）
  - 大小限制保护
  - 文件名和 MIME 类型记录

#### 2.5 数据持久化
- **数据库存储**: 元数据和结构化数据
- **MinIO 存储**: 文件和大文本内容
- **归档策略**: 按日期和运行 ID 组织

### 3. 结果管理

#### 3.1 运行状态查询
- **状态类型**:
  - `pending` - 等待执行
  - `running` - 执行中
  - `completed` - 完成
  - `failed` - 失败
- **统计信息**:
  - 爬取成功的 URL 数量
  - 爬取失败的 URL 数量
  - 创建的文档数量
  - 开始和结束时间

#### 3.2 结果获取
- **文档列表**: 所有爬取的文档
- **结构化数据**: LLM 提取的 JSON 数据
- **Markdown 内容**: 页面的 Markdown 表示
- **媒体资源**: 图片和附件的下载链接
- **元数据**: 标题、URL、爬取时间等

#### 3.3 日志和制品
- **运行清单** (`run_manifest.json`):
  - 运行元数据
  - 统计信息
  - MinIO 路径引用
  
- **资源索引** (`resource_index.json`):
  - 所有文档的详细信息
  - 媒体资源的完整清单
  - 下载 URL 和路径映射

### 4. 高级特性

#### 4.1 URL 去重
- **机制**: 基于 URL 的去重注册表
- **功能**:
  - 记录每个 URL 的首次爬取时间
  - 记录每个 URL 的最后爬取时间
  - 记录每个 URL 的爬取次数
  - 支持跳过已爬取的 URL

#### 4.2 增量爬取
- **日期过滤**: 只爬取指定日期之后的内容
- **去重支持**: 避免重复爬取相同 URL
- **应用场景**: 定期更新、新闻采集

#### 4.3 降级下载
- **触发条件**: crawl4ai 原生下载失败时
- **降级策略**: 使用 httpx 直接下载
- **限制保护**:
  - 文件大小限制（默认 10MB）
  - 超时控制
  - 错误处理

#### 4.4 LLM 配置管理
- **默认配置**: 通过环境变量设置全局默认值
- **任务级配置**: 任务级别的完整配置
- **部分覆盖**: 任务配置覆盖默认配置
- **配置合并**: 智能合并默认和任务配置

---

## 业务场景

### 场景一：新闻内容采集
**需求描述**: 定期采集新闻网站的文章，提取标题、作者、发布时间和正文内容。

**解决方案**:
1. 创建任务配置，指定新闻网站的 URL 列表
2. 配置 LLM 提取策略，使用提示词："提取文章的标题、作者、发布时间和正文"
3. 定义输出 Schema，确保数据结构一致
4. 启用去重，避免重复采集
5. 设置日期过滤，只采集最新内容
6. 定时执行任务，实现自动化采集

**优势**:
- 自动提取结构化数据
- 保存原始 Markdown 和 JSON
- 自动下载文章图片
- 支持增量更新

### 场景二：产品信息抓取
**需求描述**: 从电商网站抓取产品信息，包括名称、价格、描述、图片等。

**解决方案**:
1. 配置 JavaScript 执行代码，处理动态加载的内容
2. 使用 CSS 选择器定位产品信息区域
3. 配置 LLM 提取产品属性
4. 自动下载产品图片到 MinIO
5. 结构化存储产品数据

**优势**:
- 处理动态网页
- 精确定位内容区域
- 自动化图片管理
- 结构化数据存储

### 场景三：学术论文采集
**需求描述**: 采集学术网站的论文信息，包括标题、摘要、作者、关键词、PDF 附件。

**解决方案**:
1. 创建任务配置，指定论文列表页和详情页
2. 配置 LLM 提取论文元数据
3. 自动下载 PDF 附件
4. 保存完整的论文信息和附件

**优势**:
- 智能识别论文结构
- 自动下载 PDF 文件
- 完整归档论文资料
- 支持批量处理

### 场景四：政府公告采集
**需求描述**: 采集政府网站的公告信息，用于合规监控和信息跟踪。

**解决方案**:
1. 配置任务定期扫描公告列表页
2. 使用国产大模型（如 DeepSeek）进行中文内容提取
3. 提取公告标题、发布日期、正文、附件
4. 启用去重，避免重复采集
5. 存储完整的公告内容和附件

**优势**:
- 支持中文内容理解
- 完整保存公告内容
- 自动化监控更新
- 历史数据完整归档

### 场景五：内容聚合与知识库构建
**需求描述**: 从多个来源采集内容，构建统一的知识库。

**解决方案**:
1. 为每个来源创建独立任务
2. 使用统一的输出 Schema，确保数据一致性
3. 利用 LLM 进行内容标准化和清洗
4. 所有内容统一存储到 PostgreSQL 和 MinIO
5. 通过 API 提供统一的查询接口

**优势**:
- 多源内容统一管理
- 数据格式标准化
- 智能内容清洗
- 易于检索和使用

### 场景六：市场研究与竞品分析
**需求描述**: 定期采集竞品网站信息，进行市场分析。

**解决方案**:
1. 为每个竞品网站创建爬取任务
2. 提取关键业务指标（价格、功能、更新等）
3. 定时执行，跟踪变化
4. 数据存储支持历史对比

**优势**:
- 自动化数据采集
- 结构化数据便于分析
- 历史数据追踪
- 支持多源对比

---

## 业务流程

### 流程一：完整任务生命周期

```
1. 创建任务
   ├─ 用户通过 API 提交任务配置
   ├─ 系统验证配置有效性
   ├─ 生成任务 ID
   └─ 保存到 PostgreSQL

2. 启动运行
   ├─ 用户触发任务执行
   ├─ 创建运行记录（状态：pending）
   ├─ 生成运行 ID
   ├─ 提交到 RQ 队列
   └─ 返回运行 ID 和作业 ID

3. Worker 处理
   ├─ Worker 从队列获取任务
   ├─ 更新运行状态为 running
   ├─ 加载任务配置
   ├─ 合并 LLM 配置（默认 + 任务）
   └─ 开始执行爬取

4. URL 处理（循环）
   ├─ 检查 URL 去重
   ├─ 执行网页爬取
   │   ├─ 渲染 JavaScript
   │   ├─ 应用 CSS 选择器
   │   └─ 提取页面内容
   ├─ LLM 内容提取（可选）
   │   ├─ 构建提示词
   │   ├─ 调用 LLM API
   │   └─ 解析结构化输出
   ├─ 创建文档记录
   ├─ 保存到 MinIO
   │   ├─ Markdown 文件
   │   └─ JSON 文件
   ├─ 处理图片
   │   ├─ 尝试原生下载
   │   ├─ 降级下载（如果失败）
   │   ├─ 上传到 MinIO
   │   └─ 记录元数据
   ├─ 处理附件（同图片）
   └─ 注册 URL 到去重表

5. 完成处理
   ├─ 生成运行清单
   ├─ 生成资源索引
   ├─ 上传日志到 MinIO
   ├─ 更新运行统计
   ├─ 更新运行状态为 completed
   └─ 记录完成时间

6. 结果查询
   ├─ 用户查询运行状态
   ├─ 用户获取运行结果
   ├─ 系统生成预签名 URL
   └─ 用户下载文件
```

### 流程二：LLM 提取流程

```
1. 准备阶段
   ├─ 加载任务的 LLM 配置
   ├─ 合并默认配置
   ├─ 验证 API Key 可用性
   └─ 准备提示词模板

2. 内容提取
   ├─ crawl4ai 获取页面内容
   ├─ 提取 Markdown 格式
   ├─ 构建完整提示词
   │   ├─ 系统提示词
   │   ├─ 用户提示词模板
   │   └─ 页面内容
   └─ 附加输出 Schema（如果有）

3. LLM 调用
   ├─ 选择 LLM 提供商
   ├─ 配置模型参数
   │   ├─ temperature
   │   ├─ max_tokens
   │   └─ 其他参数
   ├─ 发送 API 请求
   └─ 接收响应

4. 结果处理
   ├─ 解析 LLM 输出
   ├─ 验证 JSON 格式
   ├─ 校验 Schema 一致性
   ├─ 清洗和规范化
   └─ 保存结构化数据

5. 错误处理
   ├─ API 调用失败 → 记录错误，跳过 LLM 提取
   ├─ JSON 解析失败 → 保存原始输出
   ├─ Schema 不匹配 → 记录警告，保存原始数据
   └─ 超时 → 重试或降级处理
```

### 流程三：媒体资源处理流程

```
1. 图片发现
   ├─ crawl4ai 解析页面 HTML
   ├─ 提取所有 <img> 标签
   ├─ 获取 src 属性和 alt 文本
   └─ 构建图片列表

2. 图片下载（原生）
   ├─ crawl4ai 尝试下载
   ├─ 保存到临时位置
   ├─ 检查文件有效性
   └─ 记录下载方法：crawl4ai

3. 图片下载（降级）
   ├─ 触发条件：原生下载失败
   ├─ 使用 httpx 直接请求
   ├─ 检查内容类型
   ├─ 检查文件大小限制
   ├─ 下载到临时文件
   └─ 记录下载方法：fallback

4. 上传到 MinIO
   ├─ 生成唯一文件名
   ├─ 确定存储路径
   │   └─ mercury4ai/{date}/{runId}/images/{filename}
   ├─ 上传文件
   ├─ 记录 MinIO 路径
   └─ 删除临时文件

5. 元数据保存
   ├─ 创建 DocumentImage 记录
   ├─ 保存原始 URL
   ├─ 保存 MinIO 路径
   ├─ 保存文件大小和 MIME 类型
   ├─ 记录下载状态（success/failed）
   └─ 关联到文档

6. 附件处理（流程相同）
   ├─ 识别 PDF、DOCX 等附件
   ├─ 下载和上传（同图片）
   └─ 保存到 DocumentAttachment 表
```

### 流程四：URL 去重流程

```
1. 去重检查
   ├─ 任务启用去重？
   │   ├─ 是 → 继续检查
   │   └─ 否 → 跳过，直接爬取
   ├─ 查询去重注册表
   │   └─ SELECT * FROM crawled_url_registry 
   │       WHERE url = ? AND task_id = ?
   └─ URL 已存在？
       ├─ 是 → 跳过此 URL
       └─ 否 → 继续爬取

2. 爬取执行
   └─ 正常执行爬取流程

3. 注册 URL
   ├─ 爬取成功后
   ├─ 检查 URL 是否已在注册表
   ├─ 如果存在：
   │   ├─ 更新 last_crawled_at
   │   └─ crawl_count + 1
   └─ 如果不存在：
       ├─ 创建新记录
       ├─ 设置 first_crawled_at
       ├─ 设置 last_crawled_at
       └─ 设置 crawl_count = 1

4. 应用场景
   ├─ 增量爬取：只处理新 URL
   ├─ 定期更新：跳过已处理内容
   └─ 多任务协同：避免重复工作
```

### 流程五：任务配置管理流程

```
1. 任务导出
   ├─ 用户请求导出任务
   ├─ 系统查询任务配置
   ├─ 序列化为 JSON/YAML
   ├─ 移除敏感信息（可选）
   └─ 返回配置文件

2. 任务导入
   ├─ 用户上传配置文件
   ├─ 解析 JSON/YAML 格式
   ├─ 验证配置有效性
   │   ├─ 必填字段检查
   │   ├─ URL 格式验证
   │   └─ Schema 结构验证
   ├─ 生成新任务 ID
   ├─ 保存到数据库
   └─ 返回新任务信息

3. 配置模板使用
   ├─ 从示例文件开始
   ├─ 修改 URL 列表
   ├─ 调整提示词
   ├─ 更新 Schema
   ├─ 配置 LLM 参数
   └─ 导入系统使用

4. 跨环境迁移
   ├─ 开发环境导出配置
   ├─ 传输到生产环境
   ├─ 修改环境相关配置
   │   ├─ API Key
   │   ├─ Base URL
   │   └─ 其他敏感信息
   └─ 导入生产环境
```

### 流程六：监控和故障恢复

```
1. 健康检查
   ├─ 定期调用 /api/health
   ├─ 检查各组件状态
   │   ├─ PostgreSQL 连接
   │   ├─ Redis 连接
   │   └─ MinIO 连接
   └─ 返回健康状态

2. 任务监控
   ├─ 定期查询运行状态
   ├─ 识别长时间运行的任务
   ├─ 识别失败的任务
   └─ 触发告警（外部实现）

3. 失败处理
   ├─ Worker 捕获异常
   ├─ 记录错误信息
   ├─ 更新运行状态为 failed
   ├─ 保存部分结果
   └─ 保留在队列（24 小时）

4. 重试机制
   ├─ 查看失败的运行记录
   ├─ 分析失败原因
   ├─ 修复问题（如更新配置）
   └─ 重新启动任务运行

5. 日志分析
   ├─ 查看 Worker 日志
   ├─ 下载运行日志（MinIO）
   ├─ 分析错误模式
   └─ 优化任务配置
```

---

## 数据模型

### 数据库表结构

#### 1. crawl_task（爬取任务）
```sql
CREATE TABLE crawl_task (
    id VARCHAR(36) PRIMARY KEY,              -- UUID
    name VARCHAR(255) NOT NULL,              -- 任务名称
    description TEXT,                        -- 任务描述
    urls JSON NOT NULL,                      -- URL 列表（JSON 数组）
    crawl_config JSON NOT NULL,              -- crawl4ai 配置
    llm_provider VARCHAR(50),                -- LLM 提供商
    llm_model VARCHAR(100),                  -- LLM 模型
    llm_params JSON,                         -- LLM 参数（含 API Key）
    prompt_template TEXT,                    -- 提示词模板
    output_schema JSON,                      -- 输出 Schema
    deduplication_enabled BOOLEAN DEFAULT TRUE,  -- 启用去重
    only_after_date TIMESTAMP,               -- 日期过滤
    fallback_download_enabled BOOLEAN DEFAULT TRUE,  -- 启用降级下载
    fallback_max_size_mb INTEGER DEFAULT 10, -- 降级下载最大文件大小
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_created_at (created_at)
);
```

**说明**:
- `urls`: JSON 数组，支持单个或多个 URL
- `crawl_config`: crawl4ai 的所有配置选项
- `llm_params`: 包含 API Key、temperature、max_tokens 等
- `output_schema`: JSON Schema 格式，定义期望的输出结构

#### 2. crawl_task_run（任务运行记录）
```sql
CREATE TABLE crawl_task_run (
    id VARCHAR(36) PRIMARY KEY,              -- UUID
    task_id VARCHAR(36) NOT NULL,            -- 关联任务
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- 状态
    started_at TIMESTAMP,                    -- 开始时间
    completed_at TIMESTAMP,                  -- 完成时间
    urls_crawled INTEGER DEFAULT 0,          -- 成功爬取的 URL 数
    urls_failed INTEGER DEFAULT 0,           -- 失败的 URL 数
    documents_created INTEGER DEFAULT 0,     -- 创建的文档数
    minio_path VARCHAR(500),                 -- MinIO 基础路径
    manifest_path VARCHAR(500),              -- 清单文件路径
    logs_path VARCHAR(500),                  -- 日志文件路径
    error_message TEXT,                      -- 错误信息
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (task_id) REFERENCES crawl_task(id) ON DELETE CASCADE,
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);
```

**状态说明**:
- `pending`: 等待执行
- `running`: 执行中
- `completed`: 成功完成
- `failed`: 执行失败

#### 3. document（文档）
```sql
CREATE TABLE document (
    id VARCHAR(36) PRIMARY KEY,              -- UUID
    run_id VARCHAR(36) NOT NULL,             -- 关联运行记录
    source_url VARCHAR(2000) NOT NULL,       -- 源 URL
    title VARCHAR(500),                      -- 标题
    content TEXT,                            -- Markdown 内容
    structured_data JSON,                    -- LLM 提取的结构化数据
    doc_metadata JSON,                       -- 文档元数据
    crawled_at TIMESTAMP DEFAULT NOW(),      -- 爬取时间
    markdown_path VARCHAR(500),              -- MinIO Markdown 路径
    json_path VARCHAR(500),                  -- MinIO JSON 路径
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (run_id) REFERENCES crawl_task_run(id) ON DELETE CASCADE,
    INDEX idx_run_id (run_id),
    INDEX idx_source_url (source_url),
    INDEX idx_crawled_at (crawled_at)
);
```

**说明**:
- `content`: 页面的 Markdown 表示，便于阅读和处理
- `structured_data`: LLM 提取的 JSON 数据，符合 output_schema
- `doc_metadata`: 页面元数据（title、description、keywords 等）

#### 4. document_image（文档图片）
```sql
CREATE TABLE document_image (
    id VARCHAR(36) PRIMARY KEY,              -- UUID
    document_id VARCHAR(36) NOT NULL,        -- 关联文档
    original_url VARCHAR(2000) NOT NULL,     -- 原始图片 URL
    minio_path VARCHAR(500),                 -- MinIO 存储路径
    alt_text VARCHAR(500),                   -- 图片 alt 文本
    size_bytes BIGINT,                       -- 文件大小（字节）
    mime_type VARCHAR(100),                  -- MIME 类型
    download_status VARCHAR(50) DEFAULT 'pending',  -- 下载状态
    download_method VARCHAR(50),             -- 下载方法
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE CASCADE,
    INDEX idx_document_id (document_id),
    INDEX idx_original_url (original_url)
);
```

**下载状态**:
- `pending`: 等待下载
- `success`: 下载成功
- `failed`: 下载失败
- `skipped`: 跳过（如文件过大）

**下载方法**:
- `crawl4ai`: 使用 crawl4ai 原生下载
- `fallback`: 使用降级下载策略

#### 5. document_attachment（文档附件）
```sql
CREATE TABLE document_attachment (
    id VARCHAR(36) PRIMARY KEY,              -- UUID
    document_id VARCHAR(36) NOT NULL,        -- 关联文档
    original_url VARCHAR(2000) NOT NULL,     -- 原始附件 URL
    minio_path VARCHAR(500),                 -- MinIO 存储路径
    filename VARCHAR(500),                   -- 文件名
    size_bytes BIGINT,                       -- 文件大小（字节）
    mime_type VARCHAR(100),                  -- MIME 类型
    download_status VARCHAR(50) DEFAULT 'pending',  -- 下载状态
    download_method VARCHAR(50),             -- 下载方法
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (document_id) REFERENCES document(id) ON DELETE CASCADE,
    INDEX idx_document_id (document_id),
    INDEX idx_original_url (original_url)
);
```

#### 6. crawled_url_registry（URL 去重注册表）
```sql
CREATE TABLE crawled_url_registry (
    id VARCHAR(36) PRIMARY KEY,              -- UUID
    url VARCHAR(2000) NOT NULL UNIQUE,       -- URL（唯一）
    task_id VARCHAR(36) NOT NULL,            -- 关联任务
    first_crawled_at TIMESTAMP DEFAULT NOW(),  -- 首次爬取时间
    last_crawled_at TIMESTAMP DEFAULT NOW(),   -- 最后爬取时间
    crawl_count INTEGER DEFAULT 1,           -- 爬取次数
    FOREIGN KEY (task_id) REFERENCES crawl_task(id) ON DELETE CASCADE,
    INDEX idx_url (url),
    INDEX idx_task_id (task_id)
);
```

**说明**:
- 每个 URL 在每个任务中只能有一条记录
- 支持跟踪爬取历史
- 用于增量爬取和去重

### 表关系图

```
crawl_task (1) ───┬──< (N) crawl_task_run
                  │
                  └──< (N) crawled_url_registry

crawl_task_run (1) ───< (N) document

document (1) ───┬──< (N) document_image
                │
                └──< (N) document_attachment
```

### MinIO 存储结构

```
mercury4ai/                              # Bucket 名称
└── 2024-01-15/                          # 日期目录（YYYY-MM-DD）
    └── 550e8400-e29b-41d4-a716-446655440111/   # 运行 ID
        ├── json/                        # 结构化数据目录
        │   ├── doc1-uuid.json          # 文档 1 的 JSON 数据
        │   └── doc2-uuid.json          # 文档 2 的 JSON 数据
        ├── markdown/                    # Markdown 内容目录
        │   ├── doc1-uuid.md            # 文档 1 的 Markdown
        │   └── doc2-uuid.md            # 文档 2 的 Markdown
        ├── images/                      # 图片目录
        │   ├── image1.jpg
        │   ├── image2.png
        │   └── ...
        ├── attachments/                 # 附件目录
        │   ├── document.pdf
        │   ├── report.docx
        │   └── ...
        └── logs/                        # 日志和清单目录
            ├── run_manifest.json        # 运行清单
            └── resource_index.json      # 资源索引
```

**文件说明**:

1. **run_manifest.json**（运行清单）:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440111",
  "task_id": "660e8400-e29b-41d4-a716-446655440000",
  "task_name": "Example News Crawl",
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:32:00Z",
  "status": "completed",
  "urls_crawled": 2,
  "urls_failed": 0,
  "documents_created": 2,
  "minio_base_path": "2024-01-15/550e8400-e29b-41d4-a716-446655440111"
}
```

2. **resource_index.json**（资源索引）:
```json
{
  "documents": [
    {
      "document_id": "doc1-uuid",
      "source_url": "https://example.com/article1",
      "title": "Article Title",
      "markdown_path": "markdown/doc1-uuid.md",
      "json_path": "json/doc1-uuid.json",
      "images": [
        {
          "image_id": "img1-uuid",
          "original_url": "https://example.com/img1.jpg",
          "minio_path": "images/image1.jpg",
          "download_status": "success"
        }
      ],
      "attachments": []
    }
  ],
  "total_documents": 2,
  "total_images": 5,
  "total_attachments": 2
}
```

---

## 技术栈

### 后端框架
- **FastAPI 0.115.0**: 现代化的 Python Web 框架
  - 自动 API 文档生成（Swagger/OpenAPI）
  - 高性能异步处理
  - 类型提示和数据验证
  - 依赖注入系统

### 数据库
- **PostgreSQL 16**: 关系型数据库
  - JSON 数据类型支持
  - 事务支持
  - 复杂查询和索引
  - 高可靠性

- **SQLAlchemy 2.0.36**: ORM 框架
  - 对象关系映射
  - 查询构建器
  - 连接池管理
  - 事务管理

- **Alembic 1.14.0**: 数据库迁移工具
  - 版本控制
  - 自动迁移生成
  - 回滚支持

### 任务队列
- **Redis 7**: 内存数据库
  - 任务队列存储
  - 高性能读写
  - 持久化支持
  - Pub/Sub 功能

- **RQ 2.0.0**: Python 任务队列
  - 简单易用的 API
  - 失败重试
  - 任务超时控制
  - Worker 管理

### 对象存储
- **MinIO**: S3 兼容对象存储
  - 高性能存储
  - 分布式架构
  - S3 API 兼容
  - Web 管理界面

### 爬虫引擎
- **crawl4ai 0.7.8+**: AI 驱动的爬虫框架
  - 基于 Playwright
  - JavaScript 渲染
  - LLM 集成
  - 智能内容提取
  - 媒体下载

### 数据验证
- **Pydantic 2.10.0**: 数据验证库
  - 类型验证
  - 数据序列化
  - JSON Schema 生成
  - 自动文档生成

### HTTP 客户端
- **httpx 0.27.2**: 异步 HTTP 客户端
  - HTTP/2 支持
  - 连接池
  - 超时控制
  - 代理支持

### 其他依赖
- **uvicorn 0.32.0**: ASGI 服务器
- **PyYAML 6.0.2**: YAML 解析
- **python-multipart 0.0.20**: 文件上传
- **python-dateutil 2.9.0**: 日期处理

### 容器化
- **Docker**: 容器运行时
- **Docker Compose**: 多容器编排
- **Alpine Linux**: 轻量级基础镜像

---

## 部署架构

### 容器组成

#### 1. postgres 容器
- **镜像**: postgres:16-alpine
- **端口**: 5432
- **存储**: Volume（postgres_data）
- **健康检查**: pg_isready
- **初始化**: init-db.sql

#### 2. redis 容器
- **镜像**: redis:7-alpine
- **端口**: 6379
- **健康检查**: redis-cli ping

#### 3. minio 容器
- **镜像**: minio/minio:latest
- **端口**: 9000 (API), 9001 (Console)
- **存储**: Volume（minio_data）
- **健康检查**: /minio/health/live

#### 4. api 容器
- **构建**: 基于项目 Dockerfile
- **端口**: 8000
- **命令**: uvicorn app.main:app
- **依赖**: postgres, redis, minio（健康检查）
- **挂载**: 
  - ./app:/app/app（代码热重载）
  - ./alembic:/app/alembic（数据库迁移）

#### 5. worker 容器（2 副本）
- **构建**: 基于项目 Dockerfile
- **命令**: rq worker crawl_tasks
- **依赖**: postgres, redis, minio（健康检查）
- **副本数**: 2（可调整）
- **挂载**: ./app:/app/app

### 网络架构

```
外部网络（Host）
    │
    ├─── 8000 ──→ api 容器
    ├─── 9000 ──→ minio 容器（API）
    ├─── 9001 ──→ minio 容器（Console）
    ├─── 5432 ──→ postgres 容器
    └─── 6379 ──→ redis 容器

Docker 内部网络
    │
    ├─── api ←──→ postgres
    ├─── api ←──→ redis
    ├─── api ←──→ minio
    ├─── worker ←──→ postgres
    ├─── worker ←──→ redis
    └─── worker ←──→ minio
```

### 数据持久化

#### Volume 列表
1. **postgres_data**: PostgreSQL 数据
   - 存储所有数据库表和索引
   - 自动备份建议

2. **minio_data**: MinIO 对象存储
   - 存储所有爬取结果
   - 支持分布式部署

#### 挂载目录
1. **./app**: 应用代码（开发模式）
2. **./alembic**: 数据库迁移脚本
3. **./init-db.sql**: 数据库初始化脚本

### 环境配置

#### 必需环境变量
```bash
# API 认证
API_KEY=your-secure-api-key-change-this

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=mercury4ai
POSTGRES_USER=mercury4ai
POSTGRES_PASSWORD=mercury4ai_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=mercury4ai
```

#### 可选环境变量（LLM 默认配置）
```bash
# LLM 配置
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4
DEFAULT_LLM_API_KEY=sk-your-api-key-here
DEFAULT_LLM_BASE_URL=https://api.openai.com/v1
DEFAULT_LLM_TEMPERATURE=0.1
DEFAULT_LLM_MAX_TOKENS=2000
```

### 扩展性设计

#### 水平扩展
1. **Worker 扩展**: 
   ```yaml
   worker:
     deploy:
       replicas: 5  # 增加 Worker 数量
   ```

2. **API 扩展**:
   - 使用负载均衡器（如 Nginx）
   - 多个 API 实例共享同一数据库和 Redis

3. **存储扩展**:
   - PostgreSQL: 主从复制、读写分离
   - MinIO: 分布式集群模式
   - Redis: Redis Cluster 或 Sentinel

#### 性能优化
1. **数据库优化**:
   - 索引优化
   - 查询优化
   - 连接池配置

2. **队列优化**:
   - 调整 Worker 并发数
   - 优化任务优先级
   - 实现任务分片

3. **存储优化**:
   - MinIO 对象生命周期管理
   - 冷热数据分离
   - 压缩和归档

### 监控和运维

#### 健康检查
- **API**: GET /api/health
- **PostgreSQL**: pg_isready
- **Redis**: redis-cli ping
- **MinIO**: /minio/health/live

#### 日志收集
- **容器日志**: docker-compose logs
- **API 日志**: FastAPI 日志输出
- **Worker 日志**: RQ Worker 日志
- **MinIO 日志**: 运行日志存储在 MinIO

#### 备份策略
1. **数据库备份**:
   - 定期 pg_dump
   - 存储到外部位置

2. **MinIO 备份**:
   - 定期同步到备份存储
   - 或使用 MinIO 的镜像功能

3. **配置备份**:
   - 任务配置导出
   - 版本控制

---

## 总结

Mercury4AI 是一个功能完整、架构清晰、易于扩展的 Web 爬虫编排系统。通过 LLM 的集成，它不仅能够爬取网页内容，更能智能地提取和结构化数据。其模块化的设计使得系统易于维护和扩展，而容器化的部署方式则大大简化了运维工作。

### 核心优势

1. **智能化**: LLM 驱动的内容提取，支持复杂的结构化需求
2. **可靠性**: 完善的错误处理、重试机制和数据持久化
3. **易用性**: RESTful API、完整的文档和示例配置
4. **灵活性**: 支持多种 LLM 提供商（包括国产大模型）
5. **可扩展**: 水平扩展、模块化设计、清晰的架构
6. **完整性**: 从爬取到存储的全流程解决方案

### 适用场景

- 内容聚合和知识库构建
- 新闻和文章采集
- 产品信息抓取
- 学术资料收集
- 市场研究和竞品分析
- 政府公告和法规监控
- 任何需要智能化数据提取的场景

### 未来展望

- 支持更多的 LLM 提供商
- 增强的调度和优先级管理
- 分布式爬取支持
- 可视化的任务配置界面
- 更完善的监控和告警系统
- 数据质量评估和优化

---

**文档版本**: 1.0.0  
**最后更新**: 2026-01-06  
**维护者**: Mercury4AI 项目组
