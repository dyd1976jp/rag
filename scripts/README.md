# RAG-Chat 项目脚本目录

本目录包含RAG-Chat项目的所有管理和维护脚本，按功能分类组织，便于查找和维护。

## 📁 目录结构

```
scripts/
├── setup/          # 环境设置脚本
├── deployment/     # 部署相关脚本  
├── testing/        # 集成测试脚本
├── tools/          # 开发工具脚本
├── backend/        # 后端管理脚本
└── database/       # 数据库管理脚本
```

## 🚀 快速开始

### 首次部署
```bash
# 1. 初始化环境
./scripts/setup/initialize.sh

# 2. 启动后端服务
./scripts/deployment/restart_backend.sh
```

### 日常维护
```bash
# 代码质量检查
python scripts/tools/code_quality_check.py backend/

# API文档生成
python scripts/tools/generate_api_docs.py

# 数据库状态检查
python scripts/database/check_stored_data.py
```

### 测试验证
```bash
# API端点测试
./scripts/testing/test_api_endpoints.sh

# 文档上传测试
./scripts/testing/test_document_upload.sh
```

## 📋 分类说明

### 🔧 setup/ - 环境设置
- 系统环境初始化
- 依赖安装配置
- 目录结构创建

### 🚀 deployment/ - 部署管理
- 服务启动和重启
- 部署脚本
- 环境配置

### 🧪 testing/ - 集成测试
- API端点测试
- 功能验证脚本
- 端到端测试

### 🛠️ tools/ - 开发工具
- 代码质量检查
- 文档生成工具
- 项目分析工具

### ⚙️ backend/ - 后端管理
- 用户管理
- 系统配置
- 服务维护

### 🗄️ database/ - 数据库管理
- 数据库初始化
- 数据迁移
- 备份和恢复

## 📖 使用指南

每个子目录都包含详细的README文档，请参考相应目录的说明：

- [setup/README.md](setup/README.md) - 环境设置指南
- [deployment/README.md](deployment/README.md) - 部署管理指南
- [testing/README.md](testing/README.md) - 测试脚本指南
- [tools/README.md](tools/README.md) - 开发工具指南
- [backend/README.md](backend/README.md) - 后端管理指南
- [database/README.md](database/README.md) - 数据库管理指南

## ⚠️ 注意事项

1. **执行权限**: 确保shell脚本具有执行权限
2. **环境依赖**: 某些脚本需要特定的环境配置
3. **数据备份**: 执行数据库操作前请备份重要数据
4. **测试环境**: 建议先在测试环境中验证脚本功能

## 🔗 向后兼容

为保持向后兼容性，重要脚本在原位置保留了符号链接。如果遇到路径问题，请更新引用路径或使用新的分类路径。

## 📞 支持

如有问题或建议，请参考项目文档或提交Issue。
