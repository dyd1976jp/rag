# 后端管理脚本

此目录包含后端系统的管理和维护脚本，用于数据库管理、用户管理等后端特定的任务。

## 脚本列表

### create_admin.py
- **用途**：创建或更新管理员用户
- **使用方法**：`python -m scripts.create_admin --email admin@example.com --username admin --password securepassword`
- **说明**：用于创建具有管理员权限的用户

### inspect_vectors.py
- **用途**：检查向量数据库中的向量数据
- **使用方法**：`python -m scripts.inspect_vectors`
- **说明**：用于调试和检查向量存储的状态

### export_documents.py
- **用途**：导出文档数据
- **使用方法**：`python -m scripts.export_documents`
- **说明**：将系统中的文档导出为可移植的格式

### check_stored_data.py
- **用途**：检查存储的数据完整性
- **使用方法**：`python -m scripts.check_stored_data`
- **说明**：验证数据存储的完整性和一致性

### initialize_milvus.py
- **用途**：初始化Milvus数据库
- **使用方法**：`python -m scripts.initialize_milvus`
- **说明**：设置和初始化Milvus向量数据库

### rebuild_collection.py
- **用途**：重建数据集合
- **使用方法**：`python -m scripts.rebuild_collection`
- **说明**：用于重建或重组数据集合的结构 