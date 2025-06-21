# RAG Chat API 完整文档

> 📍 **文档位置**: 此文档已移动到 `docs/api/API_DOCUMENTATION.md`
> 请访问新位置获取最新的API文档。

## 目录

1. [概述](#概述)
2. [基础信息](#基础信息)
3. [认证说明](#认证说明)
4. [API端点总览](#api端点总览)
   - [1. 认证模块](#1-认证模块-apiv1auth)
   - [2. 大语言模型管理](#2-大语言模型管理-apiv1llm)
   - [3. 模型发现](#3-模型发现-apiv1discover)
   - [4. RAG检索增强生成](#4-rag检索增强生成-apiv1rag)
   - [5. 文档集合管理](#5-文档集合管理-apiv1ragcollections)
   - [6. 管理模块](#6-管理模块-adminapi)
   - [7. 健康检查](#7-健康检查)
5. [HTTP状态码说明](#http状态码说明)
6. [错误响应格式](#错误响应格式)
7. [常见错误示例](#常见错误示例)
8. [环境配置](#环境配置)
9. [配置参数](#配置参数)
10. [使用建议](#使用建议)
11. [技术支持](#技术支持)

## 概述

RAG Chat API 是一个基于检索增强生成(RAG)技术的智能问答系统后端API。系统提供了完整的文档管理、向量检索、大语言模型集成和智能对话功能。

## 基础信息

- **基础URL**: `http://localhost:8000`
- **API版本**: v1
- **认证方式**: Bearer Token (JWT)
- **内容类型**: `application/json`
- **CORS**: 支持跨域请求

## 认证说明

大部分API端点需要认证。在请求头中包含JWT令牌：

```bash
Authorization: Bearer <your_jwt_token>
```

获取令牌请先调用登录接口。

## API端点总览

### 1. 认证模块 (`/api/v1/auth`)

#### 1.1 用户注册
- **端点**: `POST /api/v1/auth/register`
- **描述**: 创建新用户账户
- **认证**: 不需要

**请求体**:
```json
{
  "email": "user@example.com",
  "username": "testuser",
  "password": "securepassword"
}
```

**cURL示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser", 
    "password": "securepassword"
  }'
```

**响应**:
```json
{
  "id": "user_id",
  "email": "user@example.com",
  "username": "testuser",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### 1.2 用户登录
- **端点**: `POST /api/v1/auth/login`
- **描述**: 用户登录获取JWT令牌
- **认证**: 不需要

**请求体** (form-data):
```
username: user@example.com
password: securepassword
```

**cURL示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=securepassword"
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "user_id",
    "email": "user@example.com",
    "username": "testuser",
    "is_active": true,
    "is_superuser": false
  }
}
```

### 2. 大语言模型管理 (`/api/v1/llm`)

#### 2.1 获取所有LLM模型
- **端点**: `GET /api/v1/llm/`
- **描述**: 获取系统中配置的所有LLM模型
- **认证**: 需要

**查询参数**:
- `skip` (int, 可选): 跳过的记录数，默认0
- `limit` (int, 可选): 返回的记录数，默认100，最大100

**cURL示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/llm/?skip=0&limit=10" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json"
```

**响应**:
```json
[
  {
    "id": "llm_id",
    "name": "GPT-3.5 Turbo",
    "provider": "openai",
    "model_type": "gpt-3.5-turbo",
    "model_category": "chat",
    "api_url": "https://api.openai.com/v1/chat/completions",
    "default": true,
    "context_window": 4096,
    "max_output_tokens": 1000,
    "temperature": 0.7,
    "status": "active",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

#### 2.2 获取默认LLM模型
- **端点**: `GET /api/v1/llm/default`
- **描述**: 获取系统默认的LLM模型
- **认证**: 不需要

**cURL示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/llm/default" \
  -H "Content-Type: application/json"
```

#### 2.3 创建LLM模型
- **端点**: `POST /api/v1/llm/`
- **描述**: 创建新的LLM模型配置
- **认证**: 需要（管理员权限）

**请求体**:
```json
{
  "name": "Custom Model",
  "provider": "lmstudio",
  "model_type": "llama-2-7b",
  "model_category": "chat",
  "api_url": "http://localhost:1234/v1/chat/completions",
  "api_key": "optional_api_key",
  "default": false,
  "context_window": 4096,
  "max_output_tokens": 1000,
  "temperature": 0.7,
  "description": "Custom local model"
}
```

**cURL示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/llm/" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Custom Model",
    "provider": "lmstudio",
    "model_type": "llama-2-7b",
    "api_url": "http://localhost:1234/v1/chat/completions"
  }'
```

#### 2.4 更新LLM模型
- **端点**: `PUT /api/v1/llm/{llm_id}`
- **描述**: 更新指定的LLM模型配置
- **认证**: 需要（管理员权限）

#### 2.5 删除LLM模型
- **端点**: `DELETE /api/v1/llm/{llm_id}`
- **描述**: 删除指定的LLM模型
- **认证**: 需要（管理员权限）

#### 2.6 测试LLM模型
- **端点**: `POST /api/v1/llm/test`
- **描述**: 测试指定LLM模型的连接和响应
- **认证**: 需要

**请求体**:
```json
{
  "llm_id": "llm_id",
  "prompt": "你好，请问你是谁？"
}
```

**cURL示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/llm/test" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "llm_id": "llm_id",
    "prompt": "你好，请问你是谁？"
  }'
```

#### 2.7 发现本地模型
- **端点**: `GET /api/v1/llm/discover-models`
- **描述**: 自动发现本地服务(如LM Studio、Ollama)中的可用模型
- **认证**: 需要

**查询参数**:
- `provider` (string, 必需): 提供商名称，如"lmstudio"或"ollama"
- `url` (string, 必需): API URL，如"http://localhost:1234"

**cURL示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/llm/discover-models?provider=lmstudio&url=http://localhost:1234" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json"
```

### 3. 模型发现 (`/api/v1/discover`)

#### 3.1 发现模型
- **端点**: `GET /api/v1/discover/`
- **描述**: 发现本地服务中的模型（与LLM模块中的发现功能相同）
- **认证**: 需要

### 4. RAG检索增强生成 (`/api/v1/rag`)

#### 4.1 文档上传
- **端点**: `POST /api/v1/rag/documents/upload`
- **描述**: 上传文档并进行向量化处理
- **认证**: 需要
- **内容类型**: `multipart/form-data`

**表单参数**:
- `file` (file, 必需): 要上传的文档文件
- `preview_only` (boolean, 可选): 是否仅预览分割结果，默认false
- `collection_id` (string, 可选): 文档集ID

**cURL示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/rag/documents/upload" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -F "file=@/path/to/document.pdf" \
  -F "preview_only=false"
```

**响应**:
```json
{
  "success": true,
  "message": "文档上传成功",
  "doc_id": "document_id",
  "segments_count": 25,
  "processing_time": 3.45
}
```

#### 4.2 文档搜索
- **端点**: `POST /api/v1/rag/documents/search`
- **描述**: 在已上传的文档中搜索相关内容
- **认证**: 需要

**请求体**:
```json
{
  "query": "搜索关键词",
  "top_k": 5,
  "search_all": false,
  "include_parent": true,
  "collection_id": "optional_collection_id"
}
```

**cURL示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/rag/documents/search" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "人工智能的发展",
    "top_k": 5,
    "include_parent": true
  }'
```

**响应**:
```json
{
  "success": true,
  "message": "搜索完成",
  "results": [
    {
      "content": "相关文档内容...",
      "metadata": {
        "doc_id": "doc_id",
        "document_id": "document_id", 
        "file_name": "document.pdf",
        "position": 1,
        "score": 0.95
      }
    }
  ]
}
```

#### 4.3 RAG聊天
- **端点**: `POST /api/v1/rag/chat`
- **描述**: 基于RAG的智能对话
- **认证**: 需要

**请求体**:
```json
{
  "query": "用户问题",
  "conversation_id": "optional_conversation_id",
  "enable_rag": true,
  "top_k": 3,
  "collection_id": "optional_collection_id"
}
```

**cURL示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/rag/chat" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是人工智能？",
    "enable_rag": true,
    "top_k": 3
  }'
```

**响应**:
```json
{
  "success": true,
  "message": "回答生成成功",
  "response": "基于文档内容的AI回答...",
  "sources": [
    {
      "content": "引用的文档片段...",
      "file_name": "document.pdf",
      "score": 0.95
    }
  ],
  "conversation_id": "conv_user_id_llm_id"
}
```

#### 4.4 获取文档列表
- **端点**: `GET /api/v1/rag/documents`
- **描述**: 获取用户上传的所有文档列表
- **认证**: 需要

**cURL示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/rag/documents" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json"
```

#### 4.5 删除文档
- **端点**: `DELETE /api/v1/rag/documents/{document_id}`
- **描述**: 删除指定文档及其向量数据
- **认证**: 需要

**cURL示例**:
```bash
curl -X DELETE "http://localhost:8000/api/v1/rag/documents/document_id" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json"
```

#### 4.6 检查RAG服务状态
- **端点**: `GET /api/v1/rag/status`
- **描述**: 检查RAG服务各组件的运行状态
- **认证**: 需要

**cURL示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/rag/status" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json"
```

**响应**:
```json
{
  "available": true,
  "message": "RAG服务运行正常",
  "status": {
    "vector_store_available": true,
    "embedding_model_available": true,
    "retrieval_service_available": true
  },
  "server_info": {
    "version": "1.0.0",
    "environment": "development"
  }
}
```

### 5. 文档集合管理 (`/api/v1/rag/collections`)

#### 5.1 获取文档集列表
- **端点**: `GET /api/v1/rag/collections/`
- **描述**: 获取用户的所有文档集
- **认证**: 需要

**cURL示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/rag/collections/" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json"
```

**响应**:
```json
{
  "success": true,
  "message": "获取文档集列表成功",
  "data": {
    "collections": [
      {
        "id": "collection_id",
        "name": "技术文档集",
        "description": "包含技术相关的文档",
        "user_id": "user_id",
        "document_count": 5,
        "tags": ["技术", "AI"],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    ]
  }
}
```

#### 5.2 创建文档集
- **端点**: `POST /api/v1/rag/collections/`
- **描述**: 创建新的文档集
- **认证**: 需要

**请求体**:
```json
{
  "name": "新文档集",
  "description": "文档集描述",
  "tags": ["标签1", "标签2"]
}
```

**cURL示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/rag/collections/" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "技术文档集",
    "description": "存储技术相关文档",
    "tags": ["技术", "AI", "机器学习"]
  }'
```

#### 5.3 获取文档集详情
- **端点**: `GET /api/v1/rag/collections/{collection_id}`
- **描述**: 获取指定文档集的详细信息
- **认证**: 需要

**cURL示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/rag/collections/collection_id" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json"
```

#### 5.4 更新文档集
- **端点**: `PUT /api/v1/rag/collections/{collection_id}`
- **描述**: 更新指定文档集的信息
- **认证**: 需要

**请求体**:
```json
{
  "name": "更新后的名称",
  "description": "更新后的描述",
  "tags": ["新标签"]
}
```

**cURL示例**:
```bash
curl -X PUT "http://localhost:8000/api/v1/rag/collections/collection_id" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "更新后的文档集名称",
    "description": "更新后的描述"
  }'
```

#### 5.5 删除文档集
- **端点**: `DELETE /api/v1/rag/collections/{collection_id}`
- **描述**: 删除指定的文档集
- **认证**: 需要

**cURL示例**:
```bash
curl -X DELETE "http://localhost:8000/api/v1/rag/collections/collection_id" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json"
```

#### 5.6 获取文档集中的文档
- **端点**: `GET /api/v1/rag/collections/{collection_id}/documents`
- **描述**: 获取指定文档集中的所有文档
- **认证**: 需要

**cURL示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/rag/collections/collection_id/documents" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json"
```

#### 5.7 添加文档到文档集
- **端点**: `POST /api/v1/rag/collections/{collection_id}/documents/{document_id}`
- **描述**: 将指定文档添加到文档集中
- **认证**: 需要

**cURL示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/rag/collections/collection_id/documents/document_id" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json"
```

#### 5.8 从文档集中移除文档
- **端点**: `DELETE /api/v1/rag/collections/{collection_id}/documents/{document_id}`
- **描述**: 从文档集中移除指定文档
- **认证**: 需要

**cURL示例**:
```bash
curl -X DELETE "http://localhost:8000/api/v1/rag/collections/collection_id/documents/document_id" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json"
```

#### 5.9 获取文档预览
- **端点**: `GET /api/v1/rag/collections/{document_id}/preview/{segment_id}`
- **描述**: 获取文档的分割预览，显示父文档和子文档内容
- **认证**: 需要

**cURL示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/rag/collections/document_id/preview/0" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json"
```

**响应**:
```json
{
  "parentContent": "父文档内容...",
  "childrenContent": [
    "子文档片段1...",
    "子文档片段2..."
  ]
}
```

#### 5.10 获取文档分割参数
- **端点**: `GET /api/v1/rag/collections/{document_id}/splitter-params`
- **描述**: 获取文档的分割参数配置
- **认证**: 需要

**cURL示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/rag/collections/document_id/splitter-params" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json"
```

**响应**:
```json
{
  "chunk_size": 512,
  "chunk_overlap": 50,
  "min_chunk_size": 50,
  "split_by_paragraph": true,
  "paragraph_separator": "\\n\\n",
  "split_by_sentence": true
}
```

### 6. 管理模块 (`/admin/api`)

管理模块提供系统管理功能，需要管理员权限。

#### 6.1 管理员认证

##### 6.1.1 管理员登录
- **端点**: `POST /admin/api/auth/login`
- **描述**: 管理员登录获取管理员令牌
- **认证**: 不需要

**请求体** (form-data):
```
username: admin
password: adminpassword
```

**cURL示例**:
```bash
curl -X POST "http://localhost:8000/admin/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=adminpassword"
```

**响应**:
```json
{
  "access_token": "admin_jwt_token",
  "token_type": "bearer"
}
```

#### 6.2 MongoDB管理

##### 6.2.1 获取所有集合
- **端点**: `GET /admin/api/mongodb/collections`
- **描述**: 获取MongoDB中的所有集合列表
- **认证**: 需要管理员令牌

**cURL示例**:
```bash
curl -X GET "http://localhost:8000/admin/api/mongodb/collections" \
  -H "Authorization: Bearer <admin_jwt_token>" \
  -H "Content-Type: application/json"
```

##### 6.2.2 获取集合文档
- **端点**: `GET /admin/api/mongodb/collections/{collection_name}/documents`
- **描述**: 获取指定集合中的文档
- **认证**: 需要管理员令牌

**查询参数**:
- `skip` (int, 可选): 跳过的文档数，默认0
- `limit` (int, 可选): 返回的文档数，默认20

**cURL示例**:
```bash
curl -X GET "http://localhost:8000/admin/api/mongodb/collections/documents/documents?skip=0&limit=20" \
  -H "Authorization: Bearer <admin_jwt_token>" \
  -H "Content-Type: application/json"
```

##### 6.2.3 更新文档
- **端点**: `PUT /admin/api/mongodb/collections/{collection_name}/documents`
- **描述**: 更新集合中的文档
- **认证**: 需要管理员令牌

**请求体**:
```json
{
  "query": {"_id": "document_id"},
  "update": {"$set": {"field": "new_value"}}
}
```

##### 6.2.4 删除文档
- **端点**: `DELETE /admin/api/mongodb/collections/{collection_name}/documents`
- **描述**: 删除集合中的文档
- **认证**: 需要管理员令牌

**请求体**:
```json
{
  "query": {"_id": "document_id"}
}
```

#### 6.3 向量存储管理

##### 6.3.1 获取向量存储状态
- **端点**: `GET /admin/api/vector/status`
- **描述**: 获取向量存储系统的状态信息
- **认证**: 需要管理员令牌

**cURL示例**:
```bash
curl -X GET "http://localhost:8000/admin/api/vector/status" \
  -H "Authorization: Bearer <admin_jwt_token>" \
  -H "Content-Type: application/json"
```

##### 6.3.2 获取向量集合信息
- **端点**: `GET /admin/api/vector/collections`
- **描述**: 获取所有向量集合的信息
- **认证**: 需要管理员令牌

##### 6.3.3 清理向量数据
- **端点**: `DELETE /admin/api/vector/cleanup`
- **描述**: 清理无效的向量数据
- **认证**: 需要管理员令牌

#### 6.4 系统监控

##### 6.4.1 获取系统状态
- **端点**: `GET /admin/api/system/status`
- **描述**: 获取系统整体运行状态
- **认证**: 需要管理员令牌

**cURL示例**:
```bash
curl -X GET "http://localhost:8000/admin/api/system/status" \
  -H "Authorization: Bearer <admin_jwt_token>" \
  -H "Content-Type: application/json"
```

**响应**:
```json
{
  "system_status": "healthy",
  "services": {
    "mongodb": "connected",
    "milvus": "connected",
    "embedding_model": "loaded"
  },
  "uptime": "2 days, 3 hours",
  "memory_usage": "45%",
  "disk_usage": "23%"
}
```

##### 6.4.2 获取系统日志
- **端点**: `GET /admin/api/system/logs`
- **描述**: 获取系统日志信息
- **认证**: 需要管理员令牌

**查询参数**:
- `level` (string, 可选): 日志级别，如"ERROR", "WARNING", "INFO"
- `limit` (int, 可选): 返回的日志条数，默认100

### 7. 健康检查

#### 7.1 API根端点
- **端点**: `GET /`
- **描述**: API健康检查和欢迎信息
- **认证**: 不需要

**cURL示例**:
```bash
curl -X GET "http://localhost:8000/" \
  -H "Content-Type: application/json"
```

**响应**:
```json
{
  "message": "Welcome to RAG Chat API"
}
```

## HTTP状态码说明

| 状态码 | 说明 | 常见场景 |
|--------|------|----------|
| 200 | 成功 | 请求成功处理 |
| 201 | 创建成功 | 资源创建成功 |
| 400 | 请求错误 | 参数格式错误、验证失败 |
| 401 | 未认证 | 缺少或无效的认证令牌 |
| 403 | 权限不足 | 没有访问权限 |
| 404 | 资源不存在 | 请求的资源未找到 |
| 422 | 参数验证失败 | 请求参数不符合要求 |
| 500 | 服务器错误 | 内部服务器错误 |

## 错误响应格式

所有错误响应都遵循统一格式：

```json
{
  "detail": "错误描述信息",
  "error_type": "错误类型（可选）",
  "errors": [
    {
      "type": "validation_error",
      "loc": ["field_name"],
      "msg": "具体错误信息"
    }
  ]
}
```

## 常见错误示例

### 认证错误
```json
{
  "detail": "Could not validate credentials",
  "error_type": "authentication_error"
}
```

### 参数验证错误
```json
{
  "detail": "请求参数验证失败",
  "errors": [
    {
      "type": "missing",
      "loc": ["body", "query"],
      "msg": "Field required"
    }
  ]
}
```

### 文件上传错误
```json
{
  "detail": "文件上传请求格式错误。请确保使用正确的端点：使用 /documents/upload 端点上传文件，并设置 preview_only=true 进行预览。",
  "error_type": "file_upload_validation_error",
  "suggestion": "对于文档预览分割，请使用 POST /api/v1/rag/documents/upload 端点，并在表单数据中设置 preview_only=true"
}
```

## 环境配置

### 开发环境
- **URL**: `http://localhost:8000`
- **MongoDB**: `mongodb://localhost:27017`
- **Milvus**: `localhost:19530`

### 生产环境
根据实际部署配置调整以下参数：
- 基础URL
- 数据库连接字符串
- 向量数据库配置
- API密钥和安全设置

## 配置参数

### 环境变量
```bash
# 基础配置
ENVIRONMENT=development
LOGLEVEL=INFO

# 数据库配置
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=ragchat
MILVUS_HOST=localhost
MILVUS_PORT=19530

# 安全配置
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=11520

# 文件配置
MAX_FILE_SIZE=104857600  # 100MB
PROCESSING_TIMEOUT=1800  # 30分钟
MAX_SEGMENTS=100000      # 最多10万段落

# OpenAI配置（可选）
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-3.5-turbo
```

## 使用建议

### 1. 认证流程
1. 使用 `/api/v1/auth/register` 注册用户
2. 使用 `/api/v1/auth/login` 获取JWT令牌
3. 在后续请求中携带令牌

### 2. 文档处理流程
1. 配置LLM模型（可选，系统有默认模型）
2. 创建文档集（可选，用于组织文档）
3. 上传文档到系统
4. 使用RAG聊天功能进行智能问答

### 3. 性能优化建议
- 合理设置 `top_k` 参数，避免检索过多结果
- 使用文档集功能组织相关文档，提高检索精度
- 定期清理不需要的文档和向量数据
- 监控系统资源使用情况

### 4. 安全建议
- 定期更换JWT密钥
- 使用HTTPS协议（生产环境）
- 限制文件上传大小和类型
- 定期备份数据库

## 技术支持

如有问题，请检查：
1. 服务是否正常运行（使用健康检查端点）
2. 认证令牌是否有效
3. 请求参数格式是否正确
4. 系统日志中的错误信息

---

*本文档基于 RAG Chat API v1.0.0 生成，最后更新时间：2024年*
