# 数据库管理脚本

此目录包含RAG-Chat项目的数据库相关管理和维护脚本，用于数据库初始化、向量数据库管理、数据完整性检查等任务。

## 📋 脚本列表

### 数据库初始化

#### init_db.py
- **用途**: 初始化数据库（Python版本）
- **使用方法**: `python scripts/database/init_db.py`
- **功能**:
  - 初始化MongoDB连接和集合
  - 初始化Milvus向量数据库
  - 创建必要的索引
  - 设置数据库schema

#### init_db.sh
- **用途**: 数据库初始化脚本（Shell版本）
- **使用方法**: `./scripts/database/init_db.sh`
- **功能**:
  - 检查数据库服务状态
  - 安装Python依赖
  - 调用Python初始化脚本

### 向量数据库管理

#### initialize_milvus.py
- **用途**: 初始化Milvus向量数据库
- **使用方法**: `python scripts/database/initialize_milvus.py`
- **功能**:
  - 创建Milvus集合
  - 设置向量索引
  - 配置动态字段

#### inspect_vectors.py
- **用途**: 检查向量数据库中的向量数据
- **使用方法**: `python scripts/database/inspect_vectors.py`
- **功能**:
  - 列出所有集合
  - 查询向量数据
  - 搜索相似文档
  - 显示集合统计

**参数选项**:
```bash
python scripts/database/inspect_vectors.py \
  --list                           # 列出所有集合
  --collection rag_documents       # 指定集合
  --stats                          # 显示统计信息
  --query 10                       # 查询前10条记录
  --search "查询文本"              # 搜索相似文档
  --top-k 5                        # 返回前5个结果
```

### 数据完整性检查

#### check_stored_data.py
- **用途**: 检查存储的数据完整性
- **使用方法**: `python scripts/database/check_stored_data.py`
- **功能**:
  - 检查MongoDB文档
  - 验证向量存储
  - 数据一致性检查

#### rebuild_collection.py
- **用途**: 重建数据集合
- **使用方法**: `python scripts/database/rebuild_collection.py`
- **功能**:
  - 备份现有数据
  - 重建集合结构
  - 迁移数据
  - 验证完整性

### 数据导出

#### export_documents.py
- **用途**: 导出文档数据
- **使用方法**: `python scripts/database/export_documents.py`
- **功能**:
  - 导出MongoDB文档
  - 支持层级结构
  - JSON格式输出
  - 包含元数据

## 🚀 使用指南

### 首次部署初始化
```bash
# 1. 检查数据库服务
./scripts/database/init_db.sh

# 2. 或者直接运行Python脚本
python scripts/database/init_db.py

# 3. 初始化Milvus
python scripts/database/initialize_milvus.py
```

### 日常维护
```bash
# 检查数据完整性
python scripts/database/check_stored_data.py

# 查看向量数据
python scripts/database/inspect_vectors.py --list
python scripts/database/inspect_vectors.py --collection rag_documents --stats

# 导出数据备份
python scripts/database/export_documents.py
```

### 数据重建
```bash
# 重建集合（谨慎操作）
python scripts/database/rebuild_collection.py
```

## 🔧 配置要求

### 环境变量
```bash
MONGODB_URL="mongodb://localhost:27017"
MONGODB_DB="ragchat"
MILVUS_HOST="localhost"
MILVUS_PORT="19530"
```

### 服务依赖
- **MongoDB**: localhost:27017
- **Milvus**: localhost:19530

### Python环境
```bash
export PYTHONPATH=/path/to/RAG-chat/backend
```

## 📊 数据库结构

### MongoDB集合
- `documents`: 文档元数据
- `users`: 用户信息
- `collections`: 文档集合

### Milvus集合
- `rag_documents`: 向量数据
- 支持动态字段
- 768维向量

### 索引结构
```python
# MongoDB索引
documents.title
documents.file_path (unique)
documents.created_at

# Milvus索引
vector (IVF_FLAT)
```

## ⚠️ 注意事项

1. **数据备份**: 执行重建操作前请确保已备份重要数据
2. **服务状态**: 确保MongoDB和Milvus服务正在运行
3. **权限要求**: 需要数据库读写权限
4. **磁盘空间**: 确保有足够空间存储数据和备份

## 🔧 故障排除

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查MongoDB
   mongo --eval "db.adminCommand('ismaster')"
   
   # 检查Milvus
   curl http://localhost:9091/health
   ```

2. **权限不足**
   ```bash
   # 检查MongoDB权限
   mongo ragchat --eval "db.runCommand({connectionStatus: 1})"
   ```

3. **集合不存在**
   ```bash
   # 重新初始化
   python scripts/database/init_db.py
   ```

4. **向量维度不匹配**
   ```bash
   # 检查嵌入模型配置
   python -c "from app.core.embedding import get_embedding_model; print(get_embedding_model().dimension)"
   ```

### 数据恢复
```bash
# 从备份恢复MongoDB
mongorestore --db ragchat /path/to/backup

# 重建Milvus集合
python scripts/database/rebuild_collection.py
```

## 📈 最佳实践

### 数据库维护
- 定期备份数据
- 监控数据库性能
- 及时清理过期数据
- 优化查询索引

### 向量数据管理
- 定期检查向量质量
- 监控存储空间使用
- 优化检索性能
- 维护索引健康

### 安全考虑
- 限制数据库访问权限
- 加密敏感数据
- 记录操作日志
- 定期安全审计

## 📞 支持

如遇到数据库问题，请检查：
1. 数据库服务是否正常运行
2. 网络连接是否稳定
3. 配置参数是否正确
4. 磁盘空间是否充足

## 🔄 数据迁移流程

### 升级迁移
1. 备份现有数据
2. 停止相关服务
3. 运行迁移脚本
4. 验证数据完整性
5. 重启服务
6. 测试功能正常
