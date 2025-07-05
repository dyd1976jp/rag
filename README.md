# RAG-Chat 系统

RAG-Chat是一个基于检索增强生成（Retrieval-Augmented Generation, RAG）技术的智能聊天系统，采用现代化的微服务架构和依赖注入设计模式，支持多种文档格式的上传、处理和智能问答。

## 🚀 架构特性

### 核心架构
- **🏗️ 模块化设计**: 采用FastAPI依赖注入(DI)和组件化架构
- **📦 组件化RAG**: 可插拔的RAG组件（Loader、Splitter、Embedder、Retriever、Generator、Pipeline）
- **🐳 容器化部署**: Docker多阶段构建，支持开发/测试/生产环境
- **🔄 CI/CD流程**: 自动化测试、代码质量检查、安全扫描和部署
- **📈 监控告警**: Prometheus + Grafana监控体系

### 技术栈
- **后端**: FastAPI + Python 3.10 + Pydantic
- **数据库**: MongoDB + Milvus向量数据库 + Redis缓存
- **AI模型**: OpenAI GPT + Embedding模型
- **前端**: React + TypeScript + TailwindCSS
- **部署**: Docker + Nginx + GitHub Actions

## 文档导航

- [主文档](README.md) - 系统概述、安装和使用说明
- [项目文档](docs/README.md) - 开发文档和工作流程指南
- [测试文档](docs/testing/README.md) - 测试相关说明和指南

## 🛠️ 系统要求

### 后端依赖
- Python 3.10+
- MongoDB 5.0+
- Milvus 向量数据库 2.3+
- Redis 6.0+
- OpenAI API 或兼容的本地模型API

### 前端依赖
- Node.js 18+
- npm 或 yarn

### 开发工具
- pytest (测试框架)
- black (代码格式化)
- ruff (快速代码检查)
- mypy (类型检查)
- pre-commit (Git钩子)

### 部署工具
- Docker & Docker Compose
- Nginx (反向代理)
- GitHub Actions (CI/CD)

## 🏗️ 架构设计

### 依赖注入架构
系统采用FastAPI的依赖注入机制，实现了松耦合的组件化设计：

```python
# 统一的依赖提供者
from app.dependencies import (
    get_rag_pipeline,
    get_document_loader,
    get_text_splitter,
    get_embedder,
    get_retriever,
    get_generator
)

# API路由中使用依赖注入
@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    rag_pipeline: IRagPipeline = Depends(get_rag_pipeline)
):
    return await rag_pipeline.process_document(file.filename, current_user.id)
```

### RAG组件化设计
RAG流程被拆分为独立的可配置组件：

- **DocumentLoader**: 支持多种文档格式加载
- **TextSplitter**: 智能文本分割和块管理
- **Embedder**: 向量嵌入生成（支持OpenAI/本地模型）
- **Retriever**: 基于Milvus的高性能向量检索
- **Generator**: LLM答案生成（支持多种模型）
- **RagPipeline**: 流程编排和管理

### 容器化部署架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │    │   Frontend App  │    │  Frontend Admin │
│   (Port 80/443) │    │   (Port 3000)   │    │   (Port 3001)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌─────────────────────────────────────────────────────┐
         │              RAG Backend API                        │
         │              (Port 8000)                           │
         └─────────────────────────────────────────────────────┘
                                 │
    ┌────────────────┬───────────┼───────────┬────────────────┐
    │                │           │           │                │
┌───▼───┐    ┌──────▼──┐    ┌───▼───┐   ┌──▼──┐    ┌────────▼────────┐
│MongoDB│    │ Milvus  │    │ Redis │   │Etcd │    │ Monitoring      │
│       │    │ Vector  │    │ Cache │   │     │    │ (Prometheus +   │
│       │    │   DB    │    │       │   │     │    │  Grafana)       │
└───────┘    └─────────┘    └───────┘   └─────┘    └─────────────────┘
```

## 📦 安装说明

### 方式一：Docker Compose（推荐）

```bash
# 克隆仓库
git clone https://github.com/yourusername/RAG-chat.git
cd RAG-chat

# 复制环境配置
cp .env.example .env
# 编辑 .env 文件，填入必要的配置（如OpenAI API Key）

# 启动开发环境
docker-compose up -d

# 启动生产环境
docker-compose -f docker-compose.prod.yml up -d
```

### 方式二：手动安装

### 1. 克隆仓库
```bash
git clone https://github.com/yourusername/RAG-chat.git
cd RAG-chat
```

### 2. 安装后端依赖
```bash
cd backend

# 生产环境依赖
pip install -r requirements.txt

# 开发环境依赖（包含测试工具和代码检查工具）
pip install -r requirements-dev.txt
```

### 3. 安装前端依赖

#### 主应用前端
```bash
cd frontend-app
npm install
```



### 4. 运行Milvus（必需）

RAG功能依赖于Milvus向量数据库。您可以使用Docker运行Milvus：

```bash
docker run -d --name milvus-standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:latest standalone
```

如果您没有Docker环境，请参考[Milvus官方文档](https://milvus.io/docs/install_standalone-docker.md)安装。

### 5. 配置环境变量

根据您的环境复制对应的配置文件：

```bash
# 开发环境
cp .env.development .env

# 测试环境
cp .env.test .env

# 生产环境
cp .env.production .env
```

然后编辑.env文件，配置必要的参数：

```bash
# 环境配置
APP_ENV=development

# 数据库配置
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=ragchat_dev

# Milvus配置
MILVUS_HOST=localhost
MILVUS_PORT=19530

# AI模型配置
OPENAI_API_KEY=your_api_key_here
LOCAL_MODEL_URL=http://localhost:1234

# 安全配置
SECRET_KEY=your-secret-key-here-at-least-32-characters
```

## 运行系统

### 快速启动（推荐）

我们提供了便捷的脚本来启动整个系统：

```bash
# 启动系统（后端 + 前端）
./scripts/start.sh

# 停止系统
./scripts/stop.sh
```

启动后，系统将自动在后台运行：
- **后端API服务**: http://localhost:8000
- **主应用**: http://localhost:5173

### 手动启动（单独控制）

如果需要单独控制各个组件：

#### 1. 启动后端
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. 启动前端

**启动主应用**
```bash
cd frontend-app
npm run dev
```



### 3. 访问系统

- **主应用**: http://localhost:5173

### 用户登录

访问主应用后，可以注册新用户或使用现有账户登录。

## 使用指南

### 文档管理
1. 登录系统
2. 导航到"文档"页面
3. 点击"选择文件"上传文档（支持.txt, .pdf, .md格式）
4. 上传完成后，文档将自动处理并向量化存储

### 聊天功能
1. 导航到"聊天"页面
2. 在页面右上角切换RAG功能（默认开启）
3. 输入问题，系统将自动从您的知识库中检索相关信息进行回答
4. 回答中包含引用资料时，可点击"查看引用资料"查看详情

## 注意事项

- **Milvus依赖**：系统的RAG功能完全依赖于Milvus向量数据库，如果Milvus服务不可用，RAG相关功能将无法使用
- **嵌入模型**：系统使用OpenAI的嵌入模型或兼容API生成文本向量，请确保配置了正确的API地址

## 常见问题

### 启动相关问题

1. **端口冲突**
   - 如果8000或5173端口已被占用，请修改启动脚本中的端口设置

2. **依赖问题**
   - 确保已安装所有必要的依赖：`pip install -r backend/requirements.txt`
   - 前端依赖：`cd frontend-app && npm install`

3. **权限问题**
   - 确保脚本有执行权限：`chmod +x scripts/start.sh scripts/stop.sh`

4. **模块导入错误**
   - 如果出现 `ModuleNotFoundError: No module named 'app'` 错误，启动脚本已通过设置 PYTHONPATH 环境变量解决此问题

5. **进程无法正常终止**
   - 如果使用停止脚本后仍有进程未终止，可以手动终止：
   ```bash
   # 查找并终止uvicorn进程
   ps aux | grep uvicorn
   kill -9 <进程ID>

   # 查找并终止vite进程
   ps aux | grep vite
   kill -9 <进程ID>
   ```

### 功能相关问题

6. **上传文档后看不到内容怎么办？**
   - 检查Milvus服务是否正常运行
   - 查看后端日志确认文档处理状态

7. **RAG功能不工作怎么办？**
   - 确认已上传并成功处理了文档
   - 检查Milvus和嵌入模型服务是否正常

8. **系统响应很慢怎么办？**
   - 检查网络连接
   - 考虑使用本地部署的模型服务降低延迟

## 项目结构

```
RAG-chat/
├── backend/                    # 后端API服务
│   ├── app/                   # 应用核心代码
│   │   ├── core/              # 核心配置和基础设施
│   │   │   ├── config.py      # 统一配置管理
│   │   │   ├── paths.py       # 路径配置
│   │   │   └── security.py    # 安全相关
│   │   ├── db/                # 数据库层
│   │   │   ├── connections/   # 数据库连接管理
│   │   │   │   ├── mongodb.py # MongoDB连接管理器
│   │   │   │   └── milvus.py  # Milvus连接管理器
│   │   │   ├── repositories/  # 数据访问层（仓储模式）
│   │   │   └── session.py     # 统一会话管理
│   │   ├── models/            # 数据模型层
│   │   ├── services/          # 业务逻辑层
│   │   ├── api/               # API层
│   │   ├── rag/               # RAG专用模块
│   │   └── utils/             # 通用工具
│   ├── tests/                 # 测试文件
│   │   ├── integration/       # 集成测试（Python版本）
│   │   ├── unit/              # 单元测试
│   │   ├── performance/       # 性能测试
│   │   └── utils/             # 测试工具
│   ├── requirements.txt       # 生产依赖
│   └── requirements-dev.txt   # 开发依赖
├── frontend-app/              # 主应用前端
├── scripts/                   # 管理脚本
│   ├── database/              # 数据库管理脚本
│   ├── testing/               # 测试脚本（Python版本）
│   ├── deployment/            # 部署脚本
│   └── tools/                 # 开发工具脚本
├── data/                      # 数据存储目录
├── temp/                      # 临时文件和备份
├── .github/workflows/         # CI/CD配置
├── .env.development           # 开发环境配置
├── .env.test                  # 测试环境配置
├── .env.production            # 生产环境配置
└── docs/                      # 项目文档
├── scripts/                   # 自动化脚本
├── logs/                      # 日志文件
├── temp/                      # 临时文件（包含从根目录移动的测试HTML和JSON文件）
├── TASK.md                    # 任务清单
├── PLANNING.md                # 项目规划
└── README.md                  # 项目说明
```

## 测试

项目采用现代化的Python测试策略，支持单元测试、集成测试和性能测试。

### 运行测试

```bash
# 运行所有测试
python scripts/testing/run_tests.py --type all

# 运行单元测试
python scripts/testing/run_tests.py --type unit

# 运行集成测试
python scripts/testing/run_tests.py --type integration

# 运行覆盖率测试（目标70%以上）
python scripts/testing/run_tests.py --type coverage

# 详细输出
python scripts/testing/run_tests.py --verbose
```

### 使用pytest直接运行

```bash
cd backend

# 运行所有测试
pytest

# 运行特定测试
pytest tests/integration/test_api_endpoints_comprehensive.py -v

# 运行带覆盖率的测试
pytest --cov=app --cov-report=html
```

### CI/CD

项目配置了GitHub Actions自动化测试，支持：
- 多Python版本测试（3.8-3.11）
- 自动化依赖安装
- 数据库服务自动部署
- 测试覆盖率报告
- 代码质量检查

## 项目文档

- [项目规划文档](PLANNING.md) - 详细的技术架构和开发规划
- [任务清单](TASK.md) - 开发进度和任务管理
- [API文档](docs/api/README.md) - 完整的API接口文档
- [开发文档](docs/development/README.md) - 开发指南和工作流程
- [修复记录](temp/) - 各种问题修复的详细记录

## 开发指南

详细的开发指南请参考 [docs/README.md](docs/README.md)。

## 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。