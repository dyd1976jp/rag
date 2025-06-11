# 端点统一文档

## register-from-discovery和register端点统一

### 背景

在之前的版本中，系统存在两个功能重复的API端点：
- `/api/v1/discover/register`
- `/api/v1/llm/register-from-discovery`

这两个端点都用于注册从本地服务发现的LLM模型，但实现方式不同，参数列表也有差异，这容易造成使用上的混淆和维护上的困难。

### 变更内容

1. **创建统一服务方法**：
   - 在`LLMService`中添加`register_discovered_model`方法，统一处理模型注册逻辑
   - 添加更多参数支持（`max_output_tokens`, `temperature`, `custom_options`等）
   - 增强错误处理和日志记录

2. **更新两个端点**：
   - 更新`/api/v1/discover/register`端点，使用新的服务方法
   - 更新`/api/v1/llm/register-from-discovery`端点，保持与`discover`端点一致的参数
   - 添加相同的参数验证和文档

3. **增加测试用例**：
   - 为统一后的端点添加单元测试
   - 测试权限控制
   - 测试服务层方法

### 使用建议

尽管保留了两个端点以保持向后兼容，但建议在新代码中统一使用`/api/v1/llm/register-from-discovery`端点，因为它位于LLM相关API的主要路径下，更符合API的组织逻辑。

### 参数说明

统一后的端点支持以下参数：

| 参数名 | 类型 | 必填 | 默认值 | 描述 |
|-------|------|------|-------|------|
| llm_model_id | string | 是 | - | 模型ID |
| provider | string | 是 | - | 提供商名称 |
| name | string | 是 | - | 显示名称 |
| api_url | string | 是 | - | API URL |
| description | string | 否 | null | 模型描述 |
| context_window | integer | 否 | 8192 | 上下文窗口大小 |
| set_as_default | boolean | 否 | false | 是否设置为默认模型 |
| max_output_tokens | integer | 否 | 1000 | 最大输出token数 |
| temperature | float | 否 | 0.7 | 温度参数 |
| custom_options | object | 否 | null | 自定义选项 |

### 示例

```python
# 使用register-from-discovery端点
import httpx

async def register_model():
    url = "http://localhost:8000/api/v1/llm/register-from-discovery"
    headers = {
        "Authorization": "Bearer YOUR_TOKEN",
        "Content-Type": "application/json"
    }
    data = {
        "llm_model_id": "llama2-7b",
        "provider": "ollama",
        "name": "Llama 2 7B",
        "api_url": "http://localhost:11434/api/generate",
        "description": "Llama 2 7B模型",
        "context_window": 4096,
        "set_as_default": True,
        "max_output_tokens": 2000,
        "temperature": 0.8,
        "custom_options": {
            "stop": ["\n", "Human:", "AI:"]
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
        return response.json() 
``` 