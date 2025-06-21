# RAG Chat 后端服务

RAG Chat系统的后端服务，基于FastAPI构建，提供完整的RAG功能和API接口。

## 🏗️ 目录结构

```
backend/
├── app/                    # 应用程序源代码
│   ├── api/               # API路由和端点
│   │   ├── v1/           # API v1版本
│   │   └── admin/        # 管理API
│   ├── core/             # 核心功能模块
│   ├── db/               # 数据库相关
│   ├── models/           # 数据模型
│   ├── rag/              # RAG核心功能
│   ├── schemas/          # Pydantic模式
│   ├── services/         # 业务服务层
│   └── utils/            # 工具函数
├── tests/                 # 测试文件
│   ├── api/              # API测试
│   ├── integration/      # 集成测试
│   ├── performance/      # 性能测试
│   ├── unit/             # 单元测试
│   └── data/             # 测试数据
├── database/             # 数据库脚本和配置
├── debug/                # 调试脚本
├── scripts/              # 工具脚本
├── requirements.txt      # 生产依赖
├── requirements-dev.txt  # 开发依赖
└── pyproject.toml       # 项目配置
```

## 🚀 快速开始

### 安装依赖

```bash
# 生产环境依赖
pip install -r requirements.txt

# 开发环境依赖（包含测试工具）
pip install -r requirements-dev.txt
```

### 启动服务

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/
pytest tests/integration/

# 生成覆盖率报告
pytest --cov=app tests/
```

## 📋 主要功能

### API模块
- **认证系统**: 用户注册、登录、JWT令牌管理
- **LLM管理**: 大语言模型的CRUD操作和测试
- **RAG功能**: 文档上传、向量化、检索和问答
- **文档集合**: 文档分组和管理
- **管理接口**: 系统监控和管理功能

### RAG核心
- **文档处理**: 支持PDF、TXT、MD等格式
- **向量存储**: 基于Milvus的向量数据库
- **检索服务**: 高效的相似性搜索
- **生成服务**: 基于检索结果的智能回答

### 数据库支持
- **MongoDB**: 文档和用户数据存储
- **Milvus**: 向量数据库
- **Redis**: 缓存服务（可选）

## 🔧 配置说明

### 环境变量

在backend目录下创建`.env`文件：

```bash
# 数据库配置
MONGODB_URI=mongodb://localhost:27017/ragchat
MILVUS_HOST=localhost
MILVUS_PORT=19530

# API配置
OPENAI_API_KEY=your_api_key_here
EMBEDDING_API_BASE=http://localhost:1234/v1

# 安全配置
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=11520

# 文件配置
MAX_FILE_SIZE=104857600  # 100MB
UPLOAD_DIR=../data/uploads
```

## 📚 开发指南

### 代码结构
- 遵循FastAPI最佳实践
- 使用Pydantic进行数据验证
- 采用依赖注入模式
- 分层架构设计

### 测试策略
- 单元测试覆盖核心业务逻辑
- 集成测试验证API端点
- 性能测试确保系统性能
- 使用pytest和mock进行测试

### 调试工具
- 详细的日志记录
- 调试脚本和工具
- VSCode调试配置
- API测试脚本

## 📖 相关文档

- [API文档](../docs/api/README.md) - 完整的API接口文档
- [调试指南](../docs/development/debugging/) - 调试和故障排除
- [测试文档](tests/README.md) - 测试相关说明