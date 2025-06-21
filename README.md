# RAG-Chat 系统

RAG-Chat是一个基于检索增强生成（Retrieval-Augmented Generation, RAG）技术的聊天系统，能够利用用户上传的知识库文档进行智能回答。

## 文档导航

- [主文档](README.md) - 系统概述、安装和使用说明
- [项目文档](docs/README.md) - 开发文档和工作流程指南
- [测试文档](docs/testing/README.md) - 测试相关说明和指南

## 系统要求

### 后端依赖
- Python 3.8+
- MongoDB
- Milvus 向量数据库
- OpenAI API 或兼容的本地模型API

### 前端依赖
- Node.js 14+
- npm 或 yarn

## 安装说明

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

#### 管理后台前端
```bash
cd frontend-admin
npm install
```

### 4. 运行Milvus（必需）

RAG功能依赖于Milvus向量数据库。您可以使用Docker运行Milvus：

```bash
docker run -d --name milvus-standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:latest standalone
```

如果您没有Docker环境，请参考[Milvus官方文档](https://milvus.io/docs/install_standalone-docker.md)安装。

### 5. 配置环境变量

在backend目录下创建.env文件：

```
MONGODB_URI=mongodb://localhost:27017/ragchat
OPENAI_API_KEY=your_api_key_here
EMBEDDING_API_BASE=http://your_embedding_model_url:port
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
- **管理后台**: http://localhost:5174

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

**启动管理后台**
```bash
cd frontend-admin
npm run dev
```

### 3. 访问系统

- **主应用**: http://localhost:5173
- **管理后台**: http://localhost:5174

### 管理员登录

访问管理后台后，使用以下默认凭据登录：
- **用户名**: admin
- **密码**: adminpassword

⚠️ **注意**: 在生产环境中，请修改默认密码以提高安全性。

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
   - 前端依赖：`cd frontend-app && npm install` 和 `cd frontend-admin && npm install`

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

## 项目文档

- [项目规划文档](PLANNING.md) - 详细的技术架构和开发规划
- [任务清单](TASK.md) - 开发进度和任务管理
- [API文档](docs/api/README.md) - 完整的API接口文档
- [开发文档](docs/development/README.md) - 开发指南和工作流程