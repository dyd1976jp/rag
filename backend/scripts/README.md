# 后端管理脚本

此目录包含后端系统的通用管理和维护脚本，主要用于用户管理等系统级任务。

## 脚本列表

### create_admin.py
- **用途**：创建或更新管理员用户
- **使用方法**：`python -m scripts.create_admin --email admin@example.com --username admin --password securepassword`
- **说明**：用于创建具有管理员权限的用户

注意：数据库相关的脚本已移至 `database/scripts` 目录，包括：
- 数据库初始化脚本
- 向量数据库管理脚本
- 数据完整性检查脚本
- 数据集合重建脚本
- 文档数据导出脚本 