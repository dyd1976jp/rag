# RAG-Chat 依赖管理指南

## 概述

本文档描述了RAG-Chat项目的依赖管理策略和最佳实践。

## 后端依赖结构

### 生产环境依赖
- **文件**: `backend/requirements.txt`
- **用途**: 生产环境运行所需的核心依赖
- **安装**: `pip install -r backend/requirements.txt`

### 开发环境依赖
- **文件**: `backend/requirements-dev.txt`
- **用途**: 开发环境额外需要的工具和测试依赖
- **安装**: `pip install -r backend/requirements-dev.txt`

## 前端依赖结构

### 主应用 (frontend-app)
- **技术栈**: React + TypeScript + Vite
- **主要依赖**: React 18, TailwindCSS, Zustand
- **安装**: `cd frontend-app && npm install`

### 管理后台 (frontend-admin)
- **技术栈**: Vue 3 + TypeScript + Vite
- **主要依赖**: Vue 3, Element Plus, Pinia
- **安装**: `cd frontend-admin && npm install`

## 依赖管理原则

### 版本管理策略
1. **核心框架**: 使用精确版本号 (==)
2. **工具库**: 使用兼容版本号 (>=)
3. **测试工具**: 使用精确版本号以确保一致性

### 依赖分类
1. **生产依赖**: 应用运行必需的包
2. **开发依赖**: 开发和测试过程中需要的包
3. **可选依赖**: 特定功能需要的包

### 安全考虑
1. 定期更新依赖包到最新稳定版本
2. 使用 `pip-audit` 检查安全漏洞
3. 避免使用已知有安全问题的包版本

## 常用命令

### 后端依赖管理
```bash
# 安装生产环境依赖
pip install -r backend/requirements.txt

# 安装开发环境依赖
pip install -r backend/requirements-dev.txt

# 生成依赖锁定文件
pip freeze > backend/requirements-lock.txt

# 检查依赖安全性
pip-audit -r backend/requirements.txt
```

### 前端依赖管理
```bash
# 安装主应用依赖
cd frontend-app && npm install

# 安装管理后台依赖
cd frontend-admin && npm install

# 更新依赖
npm update

# 检查过时依赖
npm outdated
```

## 依赖更新流程

1. **检查更新**: 定期检查依赖包的新版本
2. **测试兼容性**: 在开发环境中测试新版本
3. **更新文档**: 更新相关文档和变更日志
4. **部署验证**: 在测试环境中验证更新效果

## 故障排除

### 常见问题
1. **版本冲突**: 使用虚拟环境隔离依赖
2. **安装失败**: 检查Python版本和系统依赖
3. **运行错误**: 确认所有依赖都已正确安装

### 解决方案
1. 清理缓存: `pip cache purge`
2. 重新安装: `pip install --force-reinstall`
3. 使用虚拟环境: `python -m venv venv`

## 维护计划

- **每月**: 检查依赖更新和安全漏洞
- **每季度**: 更新主要依赖版本
- **每年**: 评估和清理不再使用的依赖
