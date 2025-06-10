# RAG-chat 贡献指南

感谢您对 RAG-chat 项目的关注！本文档提供了参与项目开发的指南和流程说明。

## 开发流程

### 1. 环境设置

1. 克隆项目仓库
   ```bash
   git clone https://github.com/yourusername/RAG-chat.git
   cd RAG-chat
   ```

2. 设置后端环境
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. 设置前端环境
   ```bash
   cd frontend
   npm install
   ```

4. 配置环境变量
   创建 `backend/.env` 文件，参考 `backend/.env.example` 进行配置。

### 2. 分支管理

- `main`: 稳定版本分支，只接受经过测试的合并请求
- `dev`: 开发分支，新功能的集成在此分支进行
- 功能分支: 基于 `dev` 创建，命名格式为 `feature/功能名称`
- 修复分支: 用于修复 bug，命名格式为 `fix/bug描述`

### 3. 开发工作流

1. 在开始新任务前，更新 TASKS.md 中的任务状态为"进行中"
2. 从 `dev` 分支创建新的功能或修复分支
3. 完成开发后，提交代码并创建合并请求到 `dev` 分支
4. 通过代码审查后，更新 TASKS.md 和 DEVLOG.md
5. 合并到 `dev` 分支

## 编码规范

### 后端 (Python)

- 遵循 PEP 8 编码规范
- 使用类型注释提高代码可读性
- 函数和方法应有文档字符串
- 注释使用中文，与项目语言保持一致
- 测试覆盖率应达到 80% 以上

### 前端 (TypeScript/React)

- 使用 ESLint 和 Prettier 格式化代码
- 组件采用函数式组件和 Hooks
- 使用 TypeScript 类型定义
- 可复用逻辑应提取为自定义 Hooks
- 复杂组件应编写单元测试

## 提交规范

提交信息应遵循以下格式：

```
<类型>(<范围>): <描述>

[可选的详细描述]

[可选的相关任务编号]
```

类型包括：
- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- style: 代码风格调整，不影响功能
- refactor: 代码重构，不新增功能或修复bug
- perf: 性能优化
- test: 添加或修改测试
- chore: 构建过程或辅助工具变动

示例：
```
feat(auth): 添加密码重置功能

实现了用户密码重置流程，包括邮件发送和验证码验证。

相关任务: #42
```

## 代码审查

代码审查主要关注以下几点：

1. 代码质量和可读性
2. 测试覆盖率
3. 性能考虑
4. 安全性问题
5. 与现有代码的一致性

## 文档更新

每次功能更新或 bug 修复，都应相应更新以下文档：

1. 在 DEVLOG.md 中添加新的条目
2. 更新 TASKS.md 中相应任务的状态
3. 如有必要，更新 README.md 和 API 文档

## 问题和讨论

如有任何问题或讨论，请使用 GitHub Issues 或联系项目维护者。

感谢您的贡献！ 