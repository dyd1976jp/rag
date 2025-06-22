# 部署管理脚本

此目录包含RAG-Chat项目的部署和服务管理脚本。

## 📋 脚本列表

### restart_backend.sh
- **用途**: 重启后端服务
- **使用方法**: `./scripts/deployment/restart_backend.sh`
- **功能**:
  - 激活Conda环境
  - 设置环境变量
  - 创建必要目录
  - 启动FastAPI后端服务

### restart_backend_with_init.sh
- **用途**: 初始化Milvus集合并重启后端服务
- **使用方法**: `./scripts/deployment/restart_backend_with_init.sh`
- **功能**:
  - 初始化Milvus向量数据库
  - 验证初始化结果
  - 重启后端服务

## 🚀 使用指南

### 常规重启
```bash
# 重启后端服务
./scripts/deployment/restart_backend.sh
```

### 带初始化重启
```bash
# 初始化数据库并重启服务
./scripts/deployment/restart_backend_with_init.sh
```

## 🔧 环境配置

### 环境变量
脚本会自动设置以下环境变量：
```bash
MONGODB_URL="mongodb://localhost:27017"
MONGODB_DB="ragchat"
ENVIRONMENT="development"
LOGLEVEL="INFO"
MILVUS_HOST="localhost"
MILVUS_PORT="19530"
PYTHONPATH="/Users/tei/go/RAG-chat/backend"
```

### 服务端口
- **后端API**: http://localhost:8000
- **MongoDB**: localhost:27017
- **Milvus**: localhost:19530

## 📁 目录要求

脚本会确保以下目录存在：
- `data/uploads/` - 文件上传目录
- `data/chroma/` - Chroma数据库目录

## ⚠️ 注意事项

1. **依赖服务**: 确保MongoDB和Milvus服务正在运行
2. **Conda环境**: 需要预先创建 `rag-chat` Conda环境
3. **端口占用**: 确保8000端口未被占用
4. **权限设置**: 确保脚本有执行权限

## 🔍 服务检查

### 验证服务状态
```bash
# 检查后端API
curl http://localhost:8000/

# 检查MongoDB连接
mongo --eval "db.adminCommand('ismaster')"

# 检查Milvus连接
curl http://localhost:9091/health
```

### 查看日志
```bash
# 查看应用日志
tail -f logs/app/app.log

# 查看服务日志
tail -f logs/services/mongodb/mongodb.log
tail -f logs/services/milvus/milvus.log
```

## 🔧 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 查找占用进程
   lsof -i :8000
   # 终止进程
   kill -9 <PID>
   ```

2. **Conda环境问题**
   ```bash
   # 检查环境
   conda env list
   # 激活环境
   conda activate rag-chat
   ```

3. **数据库连接失败**
   ```bash
   # 启动MongoDB
   brew services start mongodb-community
   # 启动Milvus
   docker start milvus-standalone
   ```

4. **权限问题**
   ```bash
   chmod +x scripts/deployment/*.sh
   ```

## 📞 支持

如遇到部署问题，请检查：
1. 所有依赖服务是否正常运行
2. 环境变量是否正确设置
3. 网络端口是否可用
4. 文件权限是否正确
