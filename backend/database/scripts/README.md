# 数据库管理脚本

此目录包含数据库相关的管理和维护脚本，用于数据库初始化、向量数据库管理、数据完整性检查等任务。

## 脚本列表

### init_db.py
- **用途**：初始化数据库
- **使用方法**：`python -m database.scripts.init_db`
- **说明**：用于初始化系统数据库

### init_db.sh
- **用途**：数据库初始化脚本（Shell版本）
- **使用方法**：`./init_db.sh`
- **说明**：提供数据库初始化的命令行工具

### initialize_milvus.py
- **用途**：初始化Milvus向量数据库
- **使用方法**：`python -m database.scripts.initialize_milvus`
- **说明**：设置和初始化Milvus向量数据库

### inspect_vectors.py
- **用途**：检查向量数据库中的向量数据
- **使用方法**：`python -m database.scripts.inspect_vectors`
- **说明**：用于调试和检查向量存储的状态

### check_stored_data.py
- **用途**：检查存储的数据完整性
- **使用方法**：`python -m database.scripts.check_stored_data`
- **说明**：验证数据存储的完整性和一致性

### rebuild_collection.py
- **用途**：重建数据集合
- **使用方法**：`python -m database.scripts.rebuild_collection`
- **说明**：用于重建或重组数据集合的结构

### export_documents.py
- **用途**：导出文档数据
- **使用方法**：`python -m database.scripts.export_documents`
- **说明**：将数据库中的文档导出为JSON格式，支持文档层级结构

## 使用说明

1. 首次部署时，建议按以下顺序执行脚本：
   - 先运行 `init_db.py` 或 `init_db.sh` 初始化基础数据库
   - 然后运行 `initialize_milvus.py` 初始化向量数据库

2. 日常维护时：
   - 使用 `check_stored_data.py` 检查数据完整性
   - 使用 `inspect_vectors.py` 调试向量数据
   - 使用 `export_documents.py` 导出文档数据
   - 需要重建数据时使用 `rebuild_collection.py`

3. 注意事项：
   - 执行重建操作前请确保已备份重要数据
   - 建议在非生产环境中测试脚本后再在生产环境使用
   - 导出数据时注意检查输出目录的权限和空间 