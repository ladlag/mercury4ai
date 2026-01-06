# 国产大模型支持文档 / Chinese LLM Support Guide

Mercury4AI 现已支持国产大模型进行智能数据提取和清洗。

## 支持的国产大模型

### 1. Deepseek (深度求索)

**模型列表：**
- `deepseek-chat`: 通用对话模型，适合各类文本提取任务
- `deepseek-coder`: 代码优化模型，适合技术文档提取
- `deepseek-reasoner`: 推理模型，适合复杂逻辑分析

**配置示例：**
```json
{
  "llm_provider": "deepseek",
  "llm_model": "deepseek-chat",
  "llm_params": {
    "api_key": "sk-xxxxxxxxxxxxxxxx",
    "temperature": 0.1,
    "max_tokens": 4000
  }
}
```

**获取API密钥：** https://platform.deepseek.com/

### 2. Qwen / 通义千问 (阿里云)

**模型列表：**
- `qwen-plus`: 增强版本，平衡性能和成本
- `qwen-turbo`: 快速推理版本，适合大批量处理
- `qwen-max`: 最强能力版本，适合复杂任务

**配置示例：**
```json
{
  "llm_provider": "qwen",
  "llm_model": "qwen-plus",
  "llm_params": {
    "api_key": "sk-xxxxxxxxxxxxxxxx",
    "temperature": 0.1,
    "max_tokens": 4000
  }
}
```

**获取API密钥：** https://dashscope.aliyun.com/

### 3. ERNIE / 文心一言 (百度)

**模型列表：**
- `ernie-bot`: 通用版本
- `ernie-bot-turbo`: 快速推理版本
- `ernie-bot-4`: 最新最强版本

**配置示例：**
```json
{
  "llm_provider": "ernie",
  "llm_model": "ernie-bot",
  "llm_params": {
    "api_key": "xxxxxxxxxxxxxxxx",
    "temperature": 0.1,
    "max_tokens": 4000
  }
}
```

**获取API密钥：** https://cloud.baidu.com/product/wenxinworkshop

## 数据采集与清洗

### 1. 智能数据采集

crawl4ai 通过国产大模型可以实现：
- 自动识别页面结构
- 提取关键信息
- 过滤无关内容
- 格式标准化

**示例提示词：**
```
请从这个页面中提取所有新闻文章，包括：
- 标题
- 作者
- 发布时间
- 正文内容
- 关键词

请忽略广告、导航栏、页脚等无关内容。
```

### 2. 数据清洗

国产大模型在数据清洗方面的优势：
- **智能去重**: 识别语义相似的重复内容
- **格式统一**: 将不同格式的日期、数字等统一标准化
- **内容过滤**: 自动识别和过滤低质量内容
- **信息补全**: 根据上下文补充缺失的信息
- **中文优化**: 对中文内容有更好的理解和处理能力

**清洗示例提示词：**
```
请清洗并标准化以下数据：
1. 将所有日期转换为 YYYY-MM-DD 格式
2. 去除 HTML 标签和特殊字符
3. 统一数字格式（使用阿拉伯数字）
4. 修正明显的错别字
5. 删除重复的内容
```

### 3. 结构化输出

使用 JSON Schema 定义输出结构，确保数据质量：

```json
{
  "output_schema": {
    "type": "object",
    "properties": {
      "title": {
        "type": "string",
        "description": "文章标题，已清洗"
      },
      "publish_date": {
        "type": "string",
        "format": "date",
        "description": "发布日期，YYYY-MM-DD格式"
      },
      "content": {
        "type": "string",
        "description": "正文内容，已去除HTML标签"
      }
    },
    "required": ["title", "content"]
  }
}
```

## 实战案例：列表页抓取

### 场景：北京海淀教育网列表页

**目标URL:** https://www.bjhdedu.cn/zxfw/fwzt/szx/

**配置文件:** `examples/task_bjhdedu_list.yaml`

**关键配置说明：**

1. **JavaScript 执行** - 确保动态内容加载：
```yaml
js_code: |
  await new Promise(resolve => setTimeout(resolve, 2000));
  window.scrollTo(0, document.body.scrollHeight);
```

2. **智能提取** - 使用中文提示词：
```yaml
prompt_template: |
  请从这个列表页中提取所有的内容项。
  每个列表项应该包含：标题、链接、发布时间、摘要等。
```

3. **结构化输出** - 定义清晰的数据结构：
```yaml
output_schema:
  type: object
  properties:
    items:
      type: array
      items:
        type: object
        properties:
          title: {type: string}
          url: {type: string}
          publish_date: {type: string}
```

## 最佳实践

### 1. 提示词优化

**中文网站推荐使用中文提示词：**
```
✓ 好的示例：
"请提取页面中所有的新闻标题和链接"

✗ 避免：
"Extract all news titles and links from the page"
```

### 2. 温度参数设置

```yaml
temperature: 0.1  # 数据提取任务，使用较低的温度
temperature: 0.7  # 内容生成任务，可以使用较高的温度
```

### 3. Token 限制

```yaml
max_tokens: 4000  # 短内容提取
max_tokens: 8000  # 长文章处理
```

### 4. 成本控制

- **Deepseek**: 性价比最高，推荐用于大规模爬取
- **Qwen-turbo**: 速度快，适合实时处理
- **ERNIE-bot**: 企业级支持，适合生产环境

## 常见问题

### Q: 如何切换不同的大模型？

A: 只需修改配置文件中的 `llm_provider` 和 `llm_model` 字段：

```yaml
# 从 Deepseek 切换到 Qwen
llm_provider: "qwen"
llm_model: "qwen-plus"
llm_params:
  api_key: "your-qwen-api-key"
```

### Q: 数据清洗由谁完成？

A: 大模型会根据你的提示词自动完成数据清洗工作。你可以在 `prompt_template` 中明确指定清洗要求。

### Q: 如何处理验证码和登录？

A: crawl4ai 支持通过 JavaScript 代码处理登录和验证码：

```yaml
js_code: |
  // 填写登录表单
  document.querySelector('#username').value = 'user';
  document.querySelector('#password').value = 'pass';
  document.querySelector('#submit').click();
  // 等待登录完成
  await new Promise(resolve => setTimeout(resolve, 3000));
```

### Q: 支持哪些其他国产模型？

A: 理论上支持所有兼容 OpenAI API 格式的模型。如需添加其他模型，可以修改 `app/services/crawler_service.py` 中的 `CHINESE_LLM_PROVIDERS` 配置。

**添加新提供商的步骤：**

1. 在 `CHINESE_LLM_PROVIDERS` 字典中添加配置：
```python
'your_provider': {
    'model_prefix': 'openai/',  # 或 'provider_name/' 根据LiteLLM要求
    'base_url': 'https://api.yourprovider.com/v1',  # 或 None 使用默认
}
```

2. 配置说明：
   - `model_prefix`: LiteLLM识别的模型前缀，如 `openai/` 表示OpenAI兼容
   - `base_url`: API基础URL，使用OpenAI兼容格式的提供商需要设置

3. 使用示例：
```yaml
llm_provider: "your_provider"
llm_model: "your-model-name"
llm_params:
  api_key: "your-api-key"
```

## 技术支持

遇到问题？请提交 Issue: https://github.com/ladlag/mercury4ai/issues
