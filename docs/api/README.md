# RAG Chat API 文档

本目录包含RAG Chat系统的完整API文档和相关工具。

## 📁 文档列表

### 主要文档
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - 完整的API文档，包含所有端点的详细说明、请求/响应示例和cURL命令
- **[API_README.md](API_README.md)** - API文档使用说明和快速开始指南
- **[API_DOCUMENTATION_SUMMARY.md](API_DOCUMENTATION_SUMMARY.md)** - API文档创建总结和统计信息

### 技术文档
- **[ENDPOINT_UNIFICATION.md](ENDPOINT_UNIFICATION.md)** - API端点统一化文档

## 🚀 快速开始

### 查看完整API文档
```bash
# 在浏览器中打开或使用Markdown阅读器查看
open API_DOCUMENTATION.md
```

### 主要API模块

RAG Chat API包含以下主要模块：

1. **认证模块** (`/api/v1/auth`) - 用户注册、登录和JWT令牌管理
2. **大语言模型管理** (`/api/v1/llm`) - LLM模型的CRUD操作和测试
3. **模型发现** (`/api/v1/discover`) - 本地模型自动发现
4. **RAG检索增强生成** (`/api/v1/rag`) - 文档上传、搜索和智能对话
5. **文档集合管理** (`/api/v1/rag/collections`) - 文档集的创建和管理
6. **管理模块** (`/admin/api`) - 系统状态监控和管理

## 📊 API统计

- **总端点数**: 24个
- **公开端点**: 4个（无需认证）
- **需认证端点**: 20个
- **需管理员权限**: 6个

## 🔧 环境配置

### 基础URL
- **开发环境**: `http://localhost:8000`
- **生产环境**: 根据部署配置

### 认证方式
- **类型**: Bearer Token (JWT)
- **请求头**: `Authorization: Bearer <your_jwt_token>`

## API设计原则

1. RESTful设计
2. 版本控制 (/api/v1/...)
3. 统一的错误处理
4. 清晰的参数文档
5. 权限控制

## 📝 使用建议

### 开发者
1. 从 `API_DOCUMENTATION.md` 开始，了解完整的API规范
2. 参考cURL示例进行API集成
3. 注意文件上传使用 `multipart/form-data` 格式

### 前端开发者
1. 重点关注认证流程和令牌管理
2. 参考RAG聊天和文档上传的示例
3. 实现适当的错误处理

### 系统管理员
1. 查看环境配置部分设置系统参数
2. 使用管理模块监控系统状态
3. 参考安全建议配置生产环境

## 目录结构

```
api/
├── README.md                      # 本文件 - API文档导航
├── API_DOCUMENTATION.md           # 完整API文档
├── API_README.md                  # API使用说明
├── API_DOCUMENTATION_SUMMARY.md   # API文档总结
└── ENDPOINT_UNIFICATION.md        # 端点统一文档
```