# RAG-Chat 系统架构文档

## 概述

RAG-Chat 系统采用现代化的微服务架构设计，基于依赖注入模式和组件化思想，实现了高度可扩展、可维护和可测试的RAG应用。

## 架构原则

### 1. 依赖注入 (Dependency Injection)
- 使用FastAPI的内置依赖注入系统
- 统一的依赖提供者模块 (`app/dependencies.py`)
- 松耦合的组件设计，便于测试和替换

### 2. 组件化设计
- RAG流程拆分为独立的可配置组件
- 基于接口的设计，支持多种实现
- 可插拔的组件架构

### 3. 分层架构
```
┌─────────────────────────────────────────────────────────┐
│                    API Layer                            │
│  (FastAPI Routes + Dependency Injection)               │
├─────────────────────────────────────────────────────────┤
│                  Service Layer                          │
│  (Business Logic + RAG Pipeline)                       │
├─────────────────────────────────────────────────────────┤
│                 Component Layer                         │
│  (Loader, Splitter, Embedder, Retriever, Generator)    │
├─────────────────────────────────────────────────────────┤
│                Infrastructure Layer                     │
│  (Database, Vector Store, Cache, External APIs)        │
└─────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. 依赖注入系统

#### 依赖提供者 (`app/dependencies.py`)
```python
# 配置依赖
def get_app_settings() -> Settings

# 数据库依赖
async def get_db_session() -> MongoDB

# RAG组件依赖
def get_document_loader() -> IDocumentLoader
def get_text_splitter() -> ITextSplitter
def get_embedder() -> IEmbedder
async def get_retriever() -> IRetriever
def get_generator() -> IGenerator
async def get_rag_pipeline() -> IRagPipeline

# 服务层依赖
async def get_rag_service() -> RAGService
async def get_llm_service() -> LLMService
```

#### 使用示例
```python
@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    rag_pipeline: IRagPipeline = Depends(get_rag_pipeline)
):
    return await rag_pipeline.process_document(file.filename, current_user.id)
```

### 2. RAG组件系统

#### 组件接口定义 (`app/rag/interfaces.py`)
```python
# 核心接口
class IDocumentLoader(Protocol)
class ITextSplitter(Protocol)
class IEmbedder(Protocol)
class IRetriever(Protocol)
class IGenerator(Protocol)
class IRagPipeline(Protocol)

# 数据模型
class Document(BaseModel)
class DocumentChunk(BaseModel)
class RetrievalResult(BaseModel)
class GenerationResult(BaseModel)
```

#### 组件实现 (`app/rag/components/`)
```
components/
├── __init__.py          # 组件导出
├── loader.py           # 文档加载器实现
├── splitter.py         # 文本分割器实现
├── embedder.py         # 向量嵌入器实现
├── retriever.py        # 文档检索器实现
├── generator.py        # 答案生成器实现
└── pipeline.py         # RAG流程管道实现
```

### 3. 数据流架构

#### 文档处理流程
```
文档上传 → DocumentLoader → TextSplitter → Embedder → Retriever(存储) → 完成
    ↓           ↓              ↓            ↓           ↓
  验证格式    提取内容      智能分割     向量化      存储到Milvus
```

#### 查询处理流程
```
用户查询 → Embedder(查询向量化) → Retriever(检索) → Generator → 返回答案
    ↓           ↓                    ↓              ↓
  预处理     生成查询向量        相似度检索      结合上下文生成
```

## 技术栈详解

### 后端技术栈
- **FastAPI**: 高性能异步Web框架，内置依赖注入
- **Pydantic**: 数据验证和序列化
- **MongoDB**: 文档元数据存储
- **Milvus**: 高性能向量数据库
- **Redis**: 缓存和会话存储
- **OpenAI API**: LLM和嵌入模型服务

### 前端技术栈
- **React 18**: 用户界面框架
- **TypeScript**: 类型安全的JavaScript
- **TailwindCSS**: 实用优先的CSS框架
- **Vite**: 快速构建工具

### 部署技术栈
- **Docker**: 容器化部署
- **Docker Compose**: 多容器编排
- **Nginx**: 反向代理和负载均衡
- **GitHub Actions**: CI/CD自动化

## 部署架构

### 开发环境
```yaml
# docker-compose.yml
services:
  rag-backend:     # FastAPI应用
  mongodb:         # 数据库
  milvus:          # 向量数据库
  redis:           # 缓存
  frontend-app:    # 主应用前端
  frontend-admin:  # 管理后台
  nginx:           # 反向代理
```

### 生产环境
```yaml
# docker-compose.prod.yml
services:
  # 基础服务（同开发环境）
  rag-backend:
  mongodb:
  milvus:
  redis:
  frontend-app:
  frontend-admin:
  nginx:
  
  # 监控服务
  prometheus:      # 指标收集
  grafana:         # 监控面板
  filebeat:        # 日志收集
```

### CI/CD流程
```yaml
# .github/workflows/test.yml (CI)
- 代码质量检查 (black, ruff, mypy)
- 单元测试 (pytest)
- 集成测试
- 安全扫描 (bandit, safety)
- 测试覆盖率报告

# .github/workflows/cd.yml (CD)
- Docker镜像构建
- 安全扫描 (Trivy)
- 多环境部署 (staging, production)
- 健康检查和回滚
```

## 配置管理

### 环境配置
```python
# app/core/config.py
class Settings(BaseSettings):
    # 应用配置
    APP_ENV: str = "development"
    DEBUG: bool = True
    
    # 数据库配置
    MONGODB_URL: str
    MILVUS_HOST: str = "localhost"
    REDIS_URL: str
    
    # AI模型配置
    OPENAI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-ada-002"
    LLM_MODEL: str = "gpt-3.5-turbo"
    
    # RAG配置
    DEFAULT_CHUNK_SIZE: int = 1000
    DEFAULT_TOP_K: int = 5
    
    class Config:
        env_file = ".env"
```

### 多环境支持
- `.env.example`: 配置模板
- `.env`: 本地开发配置
- `.env.test`: 测试环境配置
- `.env.prod`: 生产环境配置

## 安全架构

### 认证授权
- JWT Token认证
- 基于角色的访问控制 (RBAC)
- API密钥管理

### 数据安全
- 敏感数据加密存储
- API请求限流
- 输入验证和清理

### 网络安全
- HTTPS/TLS加密
- CORS配置
- 反向代理安全头

## 监控和日志

### 应用监控
- Prometheus指标收集
- Grafana可视化面板
- 健康检查端点

### 日志管理
- 结构化日志记录
- 日志级别控制
- 集中化日志收集 (Filebeat)

### 性能监控
- API响应时间监控
- 数据库查询性能
- 向量检索性能
- 资源使用监控

## 扩展性设计

### 水平扩展
- 无状态应用设计
- 负载均衡支持
- 数据库分片策略

### 组件扩展
- 插件化组件架构
- 多模型支持
- 自定义处理器

### 功能扩展
- 多租户支持
- 国际化 (i18n)
- 插件系统
