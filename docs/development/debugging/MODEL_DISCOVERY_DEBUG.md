# 模型发现功能调试指南

本文档提供了如何使用和调试模型发现功能的说明。

## 功能概述

模型发现功能允许应用程序自动发现本地运行的模型服务（如LM Studio或Ollama）中的可用模型，并将它们注册到系统中。

主要API端点如下：

1. **发现模型**：`GET /api/v1/discover/?provider={provider}&url={url}`
   - 用于发现本地服务中的模型
   - 参数：
     - `provider`: 提供商名称，如lmstudio或ollama
     - `url`: 服务的API地址，如http://localhost:1234

2. **注册模型**：`POST /api/v1/discover/register`
   - 用于将发现的模型注册到系统中
   - 参数（JSON body）：
     - `llm_model_id`: 模型ID
     - `provider`: 提供商名称
     - `name`: 显示名称
     - `api_url`: API URL
     - `description`（可选）: 模型描述
     - `context_window`（可选）: 上下文窗口大小
     - `set_as_default`（可选）: 是否设置为默认模型

## 本地调试方法

### 方法1：使用VSCode调试

1. 在VSCode中，打开`backend/app/api/v1/endpoints/discover.py`文件
2. 在`discover_models`函数的开始处（如第17行，`print("\n" + "*"*50)`这一行）设置断点
3. 按F5键或点击"运行和调试"按钮，选择"Debug Uvicorn (从backend目录)"配置
4. 等待应用程序启动完成
5. 使用浏览器或curl访问以下URL：
   ```
   http://localhost:8000/api/v1/discover/?provider=lmstudio&url=http://localhost:1234
   ```
6. 断点将被触发，您可以检查请求参数和调用堆栈

### 方法2：使用测试脚本

我们提供了几个测试脚本来帮助您测试和调试模型发现功能：

1. **测试客户端**（`test_discover_client.py`）
   - 用于测试discover API端点
   - 运行方法：
     ```bash
     cd backend
     python test_discover_client.py
     ```

2. **服务层测试**（`test_service.py`）
   - 用于直接测试`llm_service.discover_local_models`函数
   - 运行方法：
     ```bash
     cd backend
     python test_service.py
     ```

3. **路由测试**（`test_route.py`）
   - 创建一个简单的FastAPI应用程序，用于测试路由注册
   - 运行方法：
     ```bash
     cd backend
     python test_route.py
     ```

## 日志输出

调试时，程序会输出详细的日志，包括：
- 请求参数
- 服务调用过程
- 响应结果
- 错误信息（如果有）

## 常见问题与解决方法

1. **404错误（Not Found）**
   - 确认URL路径正确，注意末尾的斜杠"/"
   - 正确路径为：`/api/v1/discover/`（带有末尾斜杠）

2. **认证错误**
   - 确保在请求头中包含有效的认证令牌：
     ```
     Authorization: Bearer <token>
     ```

3. **连接错误**
   - 确保LM Studio或Ollama服务正在运行
   - 检查提供的URL是否正确（应包含http://前缀）

4. **模型不存在**
   - 这可能是由于路由配置问题导致的
   - 尝试使用新的`/api/v1/discover/`端点而不是旧的`/api/v1/llm/discover-models`端点

## 调试Tips

1. 设置断点的最佳位置：
   - `discover.py`中的`discover_models`函数开始处
   - `llm_service.py`中的`discover_local_models`函数开始处

2. 使用VSCode的调试控制台查看变量值和执行临时代码

3. 查看终端输出中的日志信息

4. 使用`test_discover_client.py`脚本进行快速测试 