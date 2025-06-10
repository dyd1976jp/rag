# RAG-Chat 系统

RAG-Chat是一个基于检索增强生成（Retrieval-Augmented Generation, RAG）技术的聊天系统，能够利用用户上传的知识库文档进行智能回答。

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
pip install -r requirements.txt
```

### 3. 安装前端依赖
```bash
cd frontend
npm install
# 或使用 yarn
yarn install
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

### 1. 启动后端

```bash
cd backend
uvicorn app.main:app --reload
```

### 2. 启动前端

```bash
cd frontend
npm run dev
# 或使用 yarn
yarn dev
```

### 3. 访问系统

打开浏览器访问 http://localhost:3000

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

1. **上传文档后看不到内容怎么办？**
   - 检查Milvus服务是否正常运行
   - 查看后端日志确认文档处理状态

2. **RAG功能不工作怎么办？**
   - 确认已上传并成功处理了文档
   - 检查Milvus和嵌入模型服务是否正常

3. **系统响应很慢怎么办？**
   - 检查网络连接
   - 考虑使用本地部署的模型服务降低延迟