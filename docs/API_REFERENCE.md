# RAG-Chat API 参考文档

## 概述

RAG-Chat 提供了完整的RESTful API，支持文档管理、智能问答、用户管理等功能。所有API都采用依赖注入架构，确保高性能和可扩展性。

## 基础信息

- **Base URL**: `http://localhost:8000` (开发环境)
- **API版本**: v1
- **认证方式**: JWT Bearer Token
- **数据格式**: JSON
- **字符编码**: UTF-8

## 认证

### 获取访问令牌

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your_password"
}
```

**响应示例**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 使用令牌

在请求头中包含访问令牌：
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 文档管理 API

### 1. 统一文档上传和预览接口

**端点**: `POST /api/v1/rag/documents/upload`

**描述**: 统一的文档上传和预览API接口，通过`preview_only`参数区分两种模式

**功能模式**:
- `preview_only=true`: 仅进行文档切割预览，返回切割结果但不存储到向量数据库
- `preview_only=false`: 执行完整的文档上传流程，包括切割、向量化和存储到数据库

**请求参数**:
- `file` (file, required): 要上传的文档文件
- `parent_chunk_size` (int, optional): 父块大小，默认1024
- `parent_chunk_overlap` (int, optional): 父块重叠，默认200
- `parent_separator` (string, optional): 父块分隔符，默认"\n\n"
- `child_chunk_size` (int, optional): 子块大小，默认512
- `child_chunk_overlap` (int, optional): 子块重叠，默认50
- `child_separator` (string, optional): 子块分隔符，默认"\n"
- `preview_only` (bool, optional): 是否仅预览模式，默认false

**支持格式**: PDF, TXT, MD

**预览模式请求示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/rag/documents/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf" \
  -F "parent_chunk_size=1024" \
  -F "parent_chunk_overlap=200" \
  -F "preview_only=true"
```

**正式上传请求示例**:
```bash
curl -X POST "http://localhost:8000/api/v1/rag/documents/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf" \
  -F "parent_chunk_size=1024" \
  -F "parent_chunk_overlap=200" \
  -F "preview_only=false"
```

**统一响应格式**:
```json
{
  "success": true,
  "message": "文档切割预览生成成功",
  "preview_mode": true,
  "doc_id": "preview_123456",
  "total_segments": 25,
  "parent_segments": 5,
  "child_segments": 20,
  "parentContent": "完整文档内容...",
  "childrenContent": ["子块1内容", "子块2内容", "..."],
  "segments": [
    {
      "id": 0,
      "content": "父块内容...",
      "start": 0,
      "end": 1024,
      "length": 1024,
      "type": "parent",
      "children": [...]
    }
  ],
  "document_overview": {
    "title": "文档标题",
    "total_length": 5120,
    "total_segments": 25,
    "parent_segments": 5,
    "child_segments": 20
  }
}
```

### 2. 批量上传文档

**端点**: `POST /api/v1/rag/documents/batch-upload`

**描述**: 批量上传多个文档

**请求参数**:
- `files` (file[], required): 要上传的文档文件列表
- 其他参数同单文档上传

### 3. 获取文档列表

**端点**: `GET /api/v1/rag/documents`

**描述**: 获取用户的所有文档

**响应示例**:
```json
{
  "documents": [
    {
      "id": "doc_123456",
      "file_name": "document.pdf",
      "upload_time": "2024-01-15T10:30:00Z",
      "segments_count": 15,
      "status": "processed"
    }
  ]
}
```

### 4. 获取单个文档

**端点**: `GET /api/v1/rag/documents/{doc_id}`

**描述**: 获取指定文档的详细信息

### 5. 删除文档

**端点**: `DELETE /api/v1/rag/documents/{doc_id}`

**描述**: 删除指定文档及其所有相关数据

## 智能问答 API

### 1. RAG聊天

**端点**: `POST /api/v1/rag/chat`

**描述**: 基于上传的文档进行智能问答

**请求体**:
```json
{
  "message": "什么是人工智能？",
  "conversation_id": "conv_123",
  "search_all": false,
  "top_k": 5,
  "temperature": 0.7
}
```

**响应示例**:
```json
{
  "success": true,
  "answer": "人工智能是计算机科学的一个分支...",
  "sources": [
    {
      "content": "相关文档片段内容",
      "file_name": "ai_introduction.pdf",
      "score": 0.95
    }
  ],
  "conversation_id": "conv_123",
  "processing_time": 1.23
}
```

### 2. 文档搜索

**端点**: `POST /api/v1/rag/documents/search`

**描述**: 在文档中搜索相关内容

**请求体**:
```json
{
  "query": "机器学习算法",
  "top_k": 10,
  "collection_id": "optional_collection_id"
}
```

**响应示例**:
```json
{
  "results": [
    {
      "content": "机器学习算法是一种...",
      "metadata": {
        "file_name": "ml_guide.pdf",
        "score": 0.92,
        "position": 5
      }
    }
  ],
  "total_results": 10,
  "search_time": 0.15
}
```

## 文档预览 API

### 1. 文档上传预览模式

**端点**: `POST /api/v1/rag/documents/upload`

**描述**: 上传文档并预览分割结果（设置 preview_only=true）

**请求体** (multipart/form-data):
```
file: 要上传的文件
parent_chunk_size: 1024
parent_chunk_overlap: 200
child_chunk_size: 512
child_chunk_overlap: 50
preview_only: true
```

### 2. 文档切片预览

**端点**: `GET /api/v1/rag/collections/documents/{document_id}/slices/{slice_index}/preview`

**描述**: 预览文档的特定切片

## 系统状态 API

### 1. RAG服务状态

**端点**: `GET /api/v1/rag/status`

**描述**: 检查RAG服务的运行状态

**响应示例**:
```json
{
  "status": "healthy",
  "components": {
    "vector_store_available": true,
    "embedding_model_available": true,
    "retrieval_service_available": true
  },
  "server_info": {
    "version": "1.0.0",
    "uptime": "2 days, 3 hours"
  }
}
```

## 用户管理 API

### 1. 用户注册

**端点**: `POST /api/v1/auth/register`

**请求体**:
```json
{
  "email": "user@example.com",
  "username": "username",
  "password": "secure_password"
}
```

### 2. 用户信息

**端点**: `GET /api/v1/auth/me`

**描述**: 获取当前用户信息

## 错误处理

### 错误响应格式

```json
{
  "success": false,
  "message": "错误描述",
  "error_code": "ERROR_CODE",
  "details": {
    "field": "具体错误信息"
  }
}
```

### 常见错误码

- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未认证或令牌无效
- `403 Forbidden`: 权限不足
- `404 Not Found`: 资源不存在
- `413 Payload Too Large`: 文件过大
- `422 Unprocessable Entity`: 数据验证失败
- `500 Internal Server Error`: 服务器内部错误

## 限制和配额

### 文件上传限制
- 最大文件大小: 50MB
- 支持格式: PDF, TXT, MD, DOC, DOCX
- 单次最大上传文件数: 10个

### API调用限制
- 每分钟最大请求数: 100
- 每小时最大请求数: 1000
- 并发连接数: 50

### 文档处理限制
- 最大文档长度: 1,000,000字符
- 最大分块数: 10,000个
- 检索结果最大数量: 100个

## SDK和工具

### Python SDK示例

```python
import requests

class RAGChatClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
    
    def upload_document(self, file_path):
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{self.base_url}/api/v1/rag/documents/upload",
                files=files,
                headers=self.headers
            )
        return response.json()
    
    def chat(self, message, conversation_id=None):
        data = {
            "message": message,
            "conversation_id": conversation_id
        }
        response = requests.post(
            f"{self.base_url}/api/v1/rag/chat",
            json=data,
            headers=self.headers
        )
        return response.json()

# 使用示例
client = RAGChatClient("http://localhost:8000", "your_token")
result = client.chat("什么是机器学习？")
print(result["answer"])
```

## 更新日志

### v1.0.0 (2024-01-15)
- 初始版本发布
- 支持文档上传和RAG问答
- 实现依赖注入架构
- 添加组件化RAG流程
