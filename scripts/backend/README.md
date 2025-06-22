# 后端管理脚本

此目录包含RAG-Chat后端系统的管理和维护脚本，主要用于用户管理、系统配置和服务维护。

## 📋 脚本列表

### 用户管理

#### create_admin.py
- **用途**: 创建或更新管理员用户
- **使用方法**: `python scripts/backend/create_admin.py --email admin@example.com --username admin --password securepassword`
- **功能**:
  - 创建管理员账户
  - 设置管理员权限
  - 更新现有管理员信息

**参数选项**:
```bash
python scripts/backend/create_admin.py \
  --email admin@example.com \
  --username admin \
  --password securepassword \
  --full-name "System Administrator"
```

### 数据迁移

#### migrate_collections.py
- **用途**: 集合数据迁移
- **使用方法**: `python scripts/backend/migrate_collections.py`
- **功能**:
  - 迁移文档集合
  - 更新数据结构
  - 保持数据完整性

### 系统验证

#### verify_milvus_fixes.py
- **用途**: Milvus修复验证
- **使用方法**: `python scripts/backend/verify_milvus_fixes.py`
- **功能**:
  - 验证Milvus配置
  - 测试动态字段功能
  - 检查集合兼容性
  - 验证向量操作

## 🚀 使用指南

### 创建管理员用户
```bash
# 创建新的管理员
python scripts/backend/create_admin.py \
  --email admin@ragchat.com \
  --username admin \
  --password your_secure_password

# 创建带完整信息的管理员
python scripts/backend/create_admin.py \
  --email admin@ragchat.com \
  --username admin \
  --password your_secure_password \
  --full-name "RAG Chat Administrator"
```

### 数据迁移
```bash
# 运行集合迁移
python scripts/backend/migrate_collections.py

# 检查迁移状态
python scripts/backend/migrate_collections.py --status
```

### 系统验证
```bash
# 验证Milvus修复
python scripts/backend/verify_milvus_fixes.py

# 详细验证报告
python scripts/backend/verify_milvus_fixes.py --verbose
```

## 🔧 配置要求

### 环境变量
确保设置以下环境变量：
```bash
MONGODB_URL="mongodb://localhost:27017"
MONGODB_DB="ragchat"
MILVUS_HOST="localhost"
MILVUS_PORT="19530"
```

### 数据库连接
- **MongoDB**: 用于用户数据和文档元数据
- **Milvus**: 用于向量数据存储

### Python路径
```bash
export PYTHONPATH=/path/to/RAG-chat/backend
```

## 📊 脚本功能详解

### create_admin.py
**功能特性**:
- 密码强度验证
- 邮箱格式检查
- 重复用户检测
- 权限级别设置

**安全特性**:
- 密码哈希存储
- 输入验证
- 错误处理

### migrate_collections.py
**迁移类型**:
- 文档集合结构更新
- 索引重建
- 数据格式转换
- 关系维护

**安全措施**:
- 数据备份
- 回滚机制
- 完整性检查

### verify_milvus_fixes.py
**验证项目**:
- 连接测试
- 集合管理器测试
- 动态字段创建测试
- 现有集合兼容性测试
- 向量操作测试

## ⚠️ 注意事项

1. **数据备份**: 运行迁移脚本前请备份数据
2. **权限要求**: 确保有数据库操作权限
3. **服务状态**: 确保相关服务正在运行
4. **环境一致**: 在正确的Python环境中运行

## 🔧 故障排除

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查MongoDB状态
   systemctl status mongod
   # 检查Milvus状态
   docker ps | grep milvus
   ```

2. **权限不足**
   ```bash
   # 检查数据库权限
   mongo --eval "db.runCommand({connectionStatus: 1})"
   ```

3. **Python模块导入错误**
   ```bash
   # 设置Python路径
   export PYTHONPATH=/path/to/RAG-chat/backend
   # 安装依赖
   pip install -r requirements.txt
   ```

4. **配置文件问题**
   ```bash
   # 检查配置文件
   cat backend/app/core/config.py
   ```

## 📈 最佳实践

### 用户管理
- 使用强密码策略
- 定期更新管理员密码
- 限制管理员账户数量
- 记录管理操作日志

### 数据迁移
- 迁移前完整备份
- 在测试环境先验证
- 分批次迁移大数据
- 监控迁移进度

### 系统维护
- 定期运行验证脚本
- 监控系统性能
- 及时处理告警
- 保持文档更新

## 🔒 安全考虑

1. **密码安全**: 使用强密码并定期更换
2. **访问控制**: 限制脚本执行权限
3. **日志记录**: 记录所有管理操作
4. **数据保护**: 敏感数据加密存储

## 📞 支持

如遇到后端管理问题，请检查：
1. 数据库服务是否正常
2. 环境变量是否正确
3. Python依赖是否完整
4. 网络连接是否稳定
