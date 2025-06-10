# 模型发现功能测试说明文档

本目录包含用于测试模型发现功能的各种测试脚本。这些脚本可以帮助您验证模型发现API的正确性，并进行故障排查。

## 测试脚本概述

| 脚本名称 | 描述 | 用途 |
|---------|------|------|
| `test_discover_client.py` | 模型发现API客户端 | 测试`/api/v1/discover/`端点和注册功能 |
| `test_service.py` | 服务层测试 | 直接测试`llm_service.discover_local_models`函数 |
| `test_route.py` | 路由注册测试 | 检查FastAPI路由注册情况 |
| `test_api_server.py` | 独立测试服务器 | 创建一个专门用于测试的简化API服务器 |
| `test_api.py` | 传统API测试 | 测试原有的`/api/v1/llm/discover-models`端点 |

## 使用方法

### 1. 客户端测试 (`test_discover_client.py`)

用于测试`/api/v1/discover/`端点，可以发现和注册模型：

```bash
cd /Users/tei/go/RAG-chat/backend
python tests/discover/test_discover_client.py
```

主要功能：
- 测试模型发现API
- 测试模型注册API
- 支持交互式测试流程

### 2. 服务层测试 (`test_service.py`)

直接测试底层服务函数，绕过API层：

```bash
cd /Users/tei/go/RAG-chat/backend
python tests/discover/test_service.py
```

主要功能：
- 直接调用`llm_service.discover_local_models`函数
- 打印详细结果信息
- 适合追踪服务层问题

### 3. 路由测试 (`test_route.py`)

检查FastAPI的路由注册情况：

```bash
cd /Users/tei/go/RAG-chat/backend
python tests/discover/test_route.py
```

主要功能：
- 创建一个包含测试路由的FastAPI应用
- 显示所有注册的路由信息
- 验证路由是否正确注册
- 在端口8002上运行一个测试服务器

### 4. 独立API服务器 (`test_api_server.py`)

创建一个专用于测试的简化API服务器：

```bash
cd /Users/tei/go/RAG-chat/backend
python tests/discover/test_api_server.py
```

主要功能：
- 在端口8001上启动一个测试服务器
- 提供`/test/discover-models`端点
- 打印详细的调试信息
- 适合隔离测试API层问题

### 5. 传统API测试 (`test_api.py`)

测试原有的API端点：

```bash
cd /Users/tei/go/RAG-chat/backend
python tests/discover/test_api.py
```

主要功能：
- 测试传统的`/api/v1/llm/discover-models`端点
- 打印详细的请求和响应信息
- 用于验证旧API端点的行为

## 环境要求

运行这些测试脚本需要以下条件：

1. 后端服务正在运行（对于客户端测试）
2. LM Studio或Ollama等本地模型服务正在运行
3. 有效的认证令牌（已在脚本中配置）
4. Python 3.9+及相关依赖（httpx, asyncio等）

## 注意事项

1. 测试脚本中包含硬编码的API URL和认证令牌，可能需要根据您的环境进行调整
2. 所有测试脚本都应该从backend目录运行，以确保导入路径正确
3. 如果测试失败，请检查错误信息和日志输出，以帮助排查问题

## 调试技巧

1. 使用VSCode的调试功能，在关键位置设置断点
2. 检查日志输出中的详细信息
3. 先测试服务层函数，再测试API端点，以便逐层排查问题
4. 确保模型服务（如LM Studio）正在运行并可访问 