# RAG Chat API 文档说明

本目录包含了RAG Chat系统后端API的完整文档和相关工具。

## 📁 文件说明

### 主要文档
- **`API_DOCUMENTATION.md`** - 完整的API文档，包含所有端点的详细说明、请求/响应示例和cURL命令
- **`API_README.md`** - 本文件，API文档的使用说明

### 工具文件
- **`api_summary.py`** - Python脚本，生成API端点摘要
- **`api_endpoints_summary.json`** - API端点的JSON格式摘要
- **`test_api_endpoints.sh`** - Bash脚本，用于测试API端点的可用性

## 🚀 快速开始

### 1. 查看完整API文档
```bash
# 在浏览器中打开或使用Markdown阅读器查看
open API_DOCUMENTATION.md
```

### 2. 生成API摘要
```bash
# 运行Python脚本生成端点摘要
python3 api_summary.py
```

### 3. 测试API端点
```bash
# 运行测试脚本检查API可用性
./test_api_endpoints.sh
```

## 📊 API概览

RAG Chat API包含以下主要模块：

| 模块 | 基础路径 | 端点数 | 主要功能 |
|------|----------|--------|----------|
| 认证模块 | `/api/v1/auth` | 2 | 用户注册、登录 |
| 大语言模型管理 | `/api/v1/llm` | 7 | LLM模型的CRUD操作 |
| RAG检索增强生成 | `/api/v1/rag` | 6 | 文档上传、搜索、聊天 |
| 文档集合管理 | `/api/v1/rag/collections` | 5 | 文档集的组织管理 |
| 管理模块 | `/admin/api` | 4 | 系统管理功能 |

**总计**: 24个API端点

## 🔐 认证说明

### 用户认证
大部分API端点需要JWT令牌认证：

1. **注册用户**:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"testpass"}'
```

2. **登录获取令牌**:
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpass"
```

3. **使用令牌访问API**:
```bash
curl -X GET "http://localhost:8000/api/v1/llm/" \
  -H "Authorization: Bearer <your_jwt_token>"
```

### 管理员认证
管理模块需要管理员权限：

```bash
# 管理员登录
curl -X POST "http://localhost:8000/admin/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=adminpassword"
```

## 🛠️ 使用示例

### 基本RAG工作流程

1. **上传文档**:
```bash
curl -X POST "http://localhost:8000/api/v1/rag/documents/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.pdf"
```

2. **搜索文档**:
```bash
curl -X POST "http://localhost:8000/api/v1/rag/documents/search" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query":"人工智能","top_k":5}'
```

3. **RAG聊天**:
```bash
curl -X POST "http://localhost:8000/api/v1/rag/chat" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query":"什么是人工智能？","enable_rag":true}'
```

### 文档集合管理

1. **创建文档集**:
```bash
curl -X POST "http://localhost:8000/api/v1/rag/collections/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"技术文档","description":"技术相关文档集合"}'
```

2. **获取文档集列表**:
```bash
curl -X GET "http://localhost:8000/api/v1/rag/collections/" \
  -H "Authorization: Bearer <token>"
```

## 🔧 配置说明

### 环境变量
系统支持以下主要环境变量：

```bash
# 基础配置
ENVIRONMENT=development
LOGLEVEL=INFO

# 数据库配置
MONGODB_URL=mongodb://localhost:27017
MILVUS_HOST=localhost
MILVUS_PORT=19530

# 安全配置
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=11520

# 文件配置
MAX_FILE_SIZE=104857600  # 100MB
```

### 服务依赖
- **MongoDB**: 文档和用户数据存储
- **Milvus**: 向量数据库，用于文档检索
- **Python 3.8+**: 后端运行环境

## 📝 开发说明

### 添加新的API端点
1. 在相应的路由文件中添加端点定义
2. 更新 `API_DOCUMENTATION.md` 文档
3. 更新 `api_summary.py` 中的端点列表
4. 运行测试确保功能正常

### 文档维护
- 所有API变更都应该同步更新文档
- 使用一致的cURL示例格式
- 保持请求/响应示例的准确性

## 🐛 故障排除

### 常见问题

1. **401 Unauthorized**: 检查JWT令牌是否有效
2. **404 Not Found**: 确认端点路径是否正确
3. **422 Validation Error**: 检查请求参数格式
4. **500 Internal Server Error**: 查看服务器日志

### 调试工具
- 使用 `test_api_endpoints.sh` 快速检查端点状态
- 查看 `/api/v1/rag/status` 了解服务状态
- 使用管理端点 `/admin/api/system/status` 监控系统

## 📞 技术支持

如需帮助，请：
1. 查看完整的 `API_DOCUMENTATION.md` 文档
2. 运行测试脚本检查系统状态
3. 查看系统日志获取详细错误信息
4. 确认所有依赖服务正常运行

---

*文档版本: v1.0.0*  
*最后更新: 2024年*
