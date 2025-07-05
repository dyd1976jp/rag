# RAG-Chat 后端API curl调用大全

## 基础信息
- **基础URL**: `http://localhost:8000`
- **认证方式**: Bearer Token (JWT)
- **内容类型**: `application/json` (除特殊说明外)

## 🔐 认证模块 (`/api/v1/auth`)

### 1. 用户注册
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "securepassword"
  }'
```

### 2. 用户登录
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=securepassword"
```

**响应示例**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {...}
}
```

## 🤖 大语言模型管理 (`/api/v1/llm`)

**注意**: 以下所有请求需要在请求头中包含JWT令牌：
```bash
-H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 1. 获取所有LLM模型
```bash
curl -X GET "http://localhost:8000/api/v1/llm/?skip=0&limit=100" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 2. 获取默认LLM模型
```bash
curl -X GET "http://localhost:8000/api/v1/llm/default" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 3. 创建新的LLM模型配置
```bash
curl -X POST "http://localhost:8000/api/v1/llm/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GPT-4",
    "provider": "openai",
    "model_id": "gpt-4",
    "api_url": "https://api.openai.com/v1",
    "api_key": "your-api-key",
    "description": "OpenAI GPT-4 模型",
    "context_window": 8192,
    "max_output_tokens": 4096,
    "is_default": false
  }'
```

### 4. 更新LLM模型配置
```bash
curl -X PUT "http://localhost:8000/api/v1/llm/{llm_id}" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Model Name",
    "description": "Updated description"
  }'
```

### 5. 删除LLM模型
```bash
curl -X DELETE "http://localhost:8000/api/v1/llm/{llm_id}" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 6. 测试LLM模型
```bash
curl -X POST "http://localhost:8000/api/v1/llm/{llm_id}/test" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?"
  }'
```

### 7. 发现本地模型
```bash
curl -X GET "http://localhost:8000/api/v1/llm/discover-models?provider=lmstudio&url=http://0.0.0.0:1234" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 8. 注册发现的模型
```bash
curl -X POST "http://localhost:8000/api/v1/llm/register-discovered" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "llm_model_id": "model-id",
    "provider": "lmstudio",
    "name": "Local Model",
    "api_url": "http://0.0.0.0:1234",
    "description": "本地模型",
    "context_window": 4096,
    "set_as_default": false
  }'
```

## 🔍 模型发现 (`/api/v1/discover`)

### 1. 发现本地服务中的模型
```bash
curl -X GET "http://localhost:8000/api/v1/discover/?provider=lmstudio&url=http://0.0.0.0:1234" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 📚 RAG检索增强生成 (`/api/v1/rag`)

### 1. 上传文档
```bash
curl -X POST "http://localhost:8000/api/v1/rag/documents/upload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/your/document.pdf" \
  -F "collection_id=your-collection-id" \
  -F "chunk_size=1000" \
  -F "chunk_overlap=200" \
  -F "preview_only=false"
```

### 2. 预览文档分割
```bash
curl -X POST "http://localhost:8000/api/v1/rag/documents/upload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@/path/to/your/document.pdf" \
  -F "collection_id=your-collection-id" \
  -F "chunk_size=1000" \
  -F "chunk_overlap=200" \
  -F "preview_only=true"
```

### 3. 搜索文档
```bash
curl -X POST "http://localhost:8000/api/v1/rag/search" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "你的搜索问题",
    "collection_id": "your-collection-id",
    "top_k": 5
  }'
```

### 4. RAG聊天
```bash
curl -X POST "http://localhost:8000/api/v1/rag/chat" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "基于文档回答我的问题",
    "collection_id": "your-collection-id",
    "llm_id": "your-llm-id"
  }'
```

### 5. 获取文档列表
```bash
curl -X GET "http://localhost:8000/api/v1/rag/documents?collection_id=your-collection-id&skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 6. 删除文档
```bash
curl -X DELETE "http://localhost:8000/api/v1/rag/documents/{document_id}" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 📁 文档集合管理 (`/api/v1/rag/collections`)

### 1. 获取所有文档集
```bash
curl -X GET "http://localhost:8000/api/v1/rag/collections/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 2. 创建文档集
```bash
curl -X POST "http://localhost:8000/api/v1/rag/collections/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "我的文档集",
    "description": "文档集描述",
    "chunk_size": 1000,
    "chunk_overlap": 200
  }'
```

### 3. 获取文档集详情
```bash
curl -X GET "http://localhost:8000/api/v1/rag/collections/{collection_id}" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4. 更新文档集
```bash
curl -X PUT "http://localhost:8000/api/v1/rag/collections/{collection_id}" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "更新的文档集名称",
    "description": "更新的描述"
  }'
```

### 5. 删除文档集
```bash
curl -X DELETE "http://localhost:8000/api/v1/rag/collections/{collection_id}" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 👑 管理模块 (`/admin/api`)

### 管理员认证

#### 1. 管理员登录
```bash
curl -X POST "http://localhost:8000/admin/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=adminpassword"
```

#### 2. 获取当前管理员信息
```bash
curl -X GET "http://localhost:8000/admin/api/auth/me" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

### MongoDB管理

#### 1. 获取所有集合
```bash
curl -X GET "http://localhost:8000/admin/api/mongodb/collections" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

#### 2. 获取集合数据
```bash
curl -X GET "http://localhost:8000/admin/api/mongodb/collections/users?skip=0&limit=10" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

#### 3. 插入文档
```bash
curl -X POST "http://localhost:8000/admin/api/mongodb/collections/users/documents" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "document": {
      "name": "新用户",
      "email": "newuser@example.com"
    }
  }'
```

#### 4. 更新文档
```bash
curl -X PUT "http://localhost:8000/admin/api/mongodb/collections/users/documents" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {"email": "user@example.com"},
    "update": {"$set": {"name": "更新的名称"}}
  }'
```

#### 5. 删除文档
```bash
curl -X DELETE "http://localhost:8000/admin/api/mongodb/collections/users/documents" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {"email": "user@example.com"}
  }'
```

### 向量存储管理

#### 1. 获取向量存储状态
```bash
curl -X GET "http://localhost:8000/admin/api/vector/status" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

#### 2. 获取向量集合列表
```bash
curl -X GET "http://localhost:8000/admin/api/vector/collections" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

#### 3. 获取集合统计信息
```bash
curl -X GET "http://localhost:8000/admin/api/vector/collections/{collection_name}/stats" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

#### 4. 获取集合样本数据
```bash
curl -X GET "http://localhost:8000/admin/api/vector/collections/{collection_name}/sample?limit=10" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

#### 5. 刷新集合
```bash
curl -X POST "http://localhost:8000/admin/api/vector/collections/{collection_name}/flush" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

### 系统监控

#### 1. 获取系统指标
```bash
curl -X GET "http://localhost:8000/admin/api/system/metrics" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

#### 2. 获取系统信息
```bash
curl -X GET "http://localhost:8000/admin/api/system/info" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

#### 3. 获取进程列表
```bash
curl -X GET "http://localhost:8000/admin/api/system/processes?limit=10&sort_by=cpu_percent" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN"
```

## 🔧 使用说明

### 1. 获取JWT令牌
首先需要注册用户并登录获取JWT令牌：
```bash
# 注册
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"testpass"}')

# 登录获取令牌
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpass" | jq -r '.access_token')

# 使用令牌
curl -X GET "http://localhost:8000/api/v1/llm/" \
  -H "Authorization: Bearer $TOKEN"
```

### 2. 文件上传注意事项
- 文件上传使用 `multipart/form-data` 格式
- 使用 `-F` 参数而不是 `-d` 参数
- 文件路径使用 `@` 前缀

### 3. 错误处理
所有API都返回标准的HTTP状态码：
- `200`: 成功
- `400`: 请求错误
- `401`: 未认证
- `403`: 权限不足
- `404`: 资源不存在
- `500`: 服务器错误

### 4. 分页参数
大多数列表API支持分页：
- `skip`: 跳过的记录数（默认0）
- `limit`: 返回的记录数（默认100）

## 📝 API统计总结

- **总端点数**: 24个
- **认证模块**: 2个端点
- **LLM管理**: 8个端点
- **模型发现**: 1个端点
- **RAG功能**: 6个端点
- **文档集合**: 5个端点
- **管理模块**: 12个端点（认证2个 + MongoDB 5个 + 向量存储5个 + 系统监控3个）

所有API都遵循RESTful设计原则，支持标准的HTTP方法和状态码。
