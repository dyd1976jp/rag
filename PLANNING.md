# RAG项目规划文档 (PLANNING.md)

## 项目概述

本项目是一个基于检索增强生成(Retrieval-Augmented Generation, RAG)技术的智能聊天系统，能够利用用户上传的知识库文档进行智能回答。系统已完成核心功能开发，正在进行优化和完善阶段。

### 项目目标
1. ✅ 构建企业级RAG知识库系统
2. ✅ 支持多种文档格式的智能处理（PDF、TXT、MD等）
3. ✅ 提供高性能、可扩展的检索服务
4. ✅ 实现精准的问答和知识管理功能

### 项目架构

#### 系统架构
- **前后端分离架构**
  - 前端：React + TypeScript + TailwindCSS（主应用）
  - 后端：FastAPI + Python 3.10
  - 数据层：MongoDB + Milvus向量数据库

#### 部署架构
- **容器化部署**
  - Docker容器化支持
  - 支持单机/集群部署
  - 基于shell脚本的自动化部署

## 文件存储位置规划

### 1. 目录结构规划

#### 1.1 根目录结构
```
RAG-chat/                           # 项目根目录
├── README.md                       # 项目主要说明文档
├── PLANNING.md                     # 项目规划文档（本文件）
├── TASK.md                         # 任务管理文档
├── pyproject.toml                  # Python项目配置文件
├── docker-compose.yml              # Docker开发环境配置
├── docker-compose.prod.yml         # Docker生产环境配置
├── Dockerfile                      # Docker镜像构建文件
├── .env.example                    # 环境变量示例文件
├── .gitignore                      # Git忽略文件配置
├── backend/                        # 后端应用目录
├── frontend-app/                   # 前端应用目录
├── data/                           # 数据存储目录
├── docs/                           # 项目文档目录
├── scripts/                        # 脚本工具目录
├── tests/                          # 根级测试目录（如有需要）
├── temp/                           # 临时文件目录
├── logs/                           # 日志文件目录
├── monitoring/                     # 监控配置目录
├── nginx/                          # Nginx配置目录
├── examples/                       # 示例代码目录
└── 参考项目/                       # 参考项目目录
```

#### 1.2 后端目录结构（backend/）
```
backend/
├── README.md                       # 后端说明文档
├── pyproject.toml                  # 后端项目配置
├── requirements.txt                # 生产环境依赖
├── requirements-dev.txt            # 开发环境依赖
├── app/                            # 应用核心代码
│   ├── __init__.py
│   ├── main.py                     # FastAPI应用入口
│   ├── dependencies.py             # 依赖注入
│   ├── core/                       # 核心配置模块
│   │   ├── __init__.py
│   │   ├── config.py               # 应用配置
│   │   ├── security.py             # 安全配置
│   │   └── paths.py                # 路径配置
│   ├── api/                        # API路由模块
│   │   ├── __init__.py
│   │   ├── router.py               # 主路由
│   │   ├── auth/                   # 认证相关API
│   │   ├── admin/                  # 管理员API
│   │   └── v1/                     # API版本1
│   ├── models/                     # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py                 # 用户模型
│   │   └── ...
│   ├── schemas/                    # Pydantic模式
│   │   ├── __init__.py
│   │   └── ...
│   ├── services/                   # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── auth/                   # 认证服务
│   │   ├── llm/                    # LLM服务
│   │   └── user/                   # 用户服务
│   ├── rag/                        # RAG核心模块
│   │   ├── __init__.py
│   │   ├── components/             # RAG组件
│   │   ├── interfaces.py           # 接口定义
│   │   └── ...
│   ├── db/                         # 数据库模块
│   │   ├── __init__.py
│   │   ├── session.py              # 数据库会话
│   │   └── ...
│   └── utils/                      # 工具函数
├── database/                       # 数据库相关
│   ├── __init__.py
│   ├── config/                     # 数据库配置
│   ├── models/                     # 数据库模型
│   └── scripts/                    # 数据库脚本
├── tests/                          # 后端测试
│   ├── __init__.py
│   ├── conftest.py                 # pytest配置
│   ├── unit/                       # 单元测试
│   ├── integration/                # 集成测试
│   ├── performance/                # 性能测试
│   ├── fixtures/                   # 测试夹具
│   ├── mocks/                      # 模拟对象
│   ├── data/                       # 测试数据
│   ├── utils/                      # 测试工具
│   └── scripts/                    # 测试脚本
├── scripts/                        # 后端专用脚本
├── data/                           # 后端数据文件
├── debug/                          # 调试文件
├── reports/                        # 测试报告
├── htmlcov/                        # 覆盖率报告
└── coverage.json                   # 覆盖率数据
```

#### 1.3 前端目录结构（frontend-app/）
```
frontend-app/
├── README.md                       # 前端说明文档
├── package.json                    # Node.js项目配置
├── package-lock.json               # 依赖锁定文件
├── tsconfig.json                   # TypeScript配置
├── tsconfig.node.json              # Node.js TypeScript配置
├── vite.config.ts                  # Vite构建配置
├── tailwind.config.js              # TailwindCSS配置
├── postcss.config.js               # PostCSS配置
├── index.html                      # HTML入口文件
├── public/                         # 静态资源
│   ├── favicon.ico
│   └── ...
├── src/                            # 源代码
│   ├── main.tsx                    # 应用入口
│   ├── App.tsx                     # 主应用组件
│   ├── components/                 # 可复用组件
│   ├── pages/                      # 页面组件
│   ├── hooks/                      # 自定义Hooks
│   ├── services/                   # API服务
│   ├── utils/                      # 工具函数
│   ├── types/                      # TypeScript类型定义
│   ├── styles/                     # 样式文件
│   └── assets/                     # 资源文件
├── dist/                           # 构建输出目录
└── node_modules/                   # Node.js依赖
```

#### 1.4 数据目录结构（data/）
```
data/
├── README.md                       # 数据目录说明
├── raw/                            # 原始数据
│   ├── documents/                  # 原始文档
│   └── datasets/                   # 原始数据集
├── processed/                      # 处理后数据
│   ├── uploads/                    # 上传文件处理结果
│   ├── vectors/                    # 向量数据
│   ├── embeddings/                 # 嵌入数据
│   ├── cache/                      # 缓存数据
│   ├── splitter_cache/             # 分割器缓存
│   ├── exports/                    # 导出数据
│   └── results/                    # 处理结果
├── uploads/                        # 用户上传文件
├── exports/                        # 数据导出
├── cache/                          # 系统缓存
│   └── splitter/                   # 分割器缓存
├── temp/                           # 临时数据
├── test_data/                      # 测试数据
├── db/                             # 数据库文件
│   ├── mongodb/                    # MongoDB数据
│   ├── milvus/                     # Milvus数据
│   └── chroma/                     # ChromaDB数据
├── vectors/                        # 向量存储
├── embeddings/                     # 嵌入存储
├── results/                        # 结果存储
├── splitter_cache/                 # 分割缓存
└── chroma/                         # ChromaDB存储
```

#### 1.5 文档目录结构（docs/）
```
docs/
├── README.md                       # 文档目录说明
├── API_REFERENCE.md                # API参考文档
├── ARCHITECTURE.md                 # 架构文档
├── CODE_QUALITY.md                 # 代码质量标准
├── DEPENDENCIES.md                 # 依赖管理文档
├── api/                            # API文档
│   ├── README.md
│   ├── API_DOCUMENTATION.md        # API详细文档
│   ├── API_DOCUMENTATION_SUMMARY.md
│   ├── ENDPOINT_UNIFICATION.md     # 端点统一文档
│   └── api_endpoints_summary.json  # API端点摘要
├── development/                    # 开发文档
│   ├── README.md
│   ├── CONTRIBUTING.md             # 贡献指南
│   ├── DEVLOG.md                   # 开发日志
│   ├── WORKFLOW.md                 # 工作流程
│   ├── TASKS.md                    # 任务管理
│   ├── TASK_TEMPLATE.md            # 任务模板
│   └── debugging/                  # 调试文档
├── deployment/                     # 部署文档
│   └── STARTUP_GUIDE.md            # 启动指南
├── testing/                        # 测试文档
│   ├── README.md
│   └── api_test_report.md          # API测试报告
├── fixes/                          # 修复文档
│   ├── fix_summary.md              # 修复摘要
│   ├── utf8_encoding_fix.md        # UTF-8编码修复
│   └── ...                         # 其他修复文档
├── github_templates/               # GitHub模板
│   └── ISSUE_TEMPLATE/             # Issue模板
├── implementation_summary.md       # 实现摘要
└── parent_child_numbering_system.md # 父子编号系统
```

#### 1.6 脚本目录结构（scripts/）
```
scripts/
├── README.md                       # 脚本目录说明
├── backend/                        # 后端脚本
│   ├── README.md
│   ├── create_admin.py             # 创建管理员
│   ├── migrate_collections.py      # 集合迁移
│   └── verify_milvus_fixes.py      # Milvus修复验证
├── database/                       # 数据库脚本
│   ├── README.md
│   ├── __init__.py
│   ├── init_db.py                  # 数据库初始化
│   ├── init_db.sh                  # 数据库初始化脚本
│   ├── initialize_milvus.py        # Milvus初始化
│   ├── check_stored_data.py        # 检查存储数据
│   ├── export_documents.py         # 导出文档
│   ├── inspect_vectors.py          # 检查向量
│   └── rebuild_collection.py       # 重建集合
├── deployment/                     # 部署脚本
│   ├── README.md
│   ├── restart_backend.sh          # 重启后端
│   └── restart_backend_with_init.sh # 重启并初始化
├── setup/                          # 安装脚本
│   ├── README.md
│   └── initialize.sh               # 项目初始化
├── testing/                        # 测试脚本
│   ├── README.md
│   ├── run_tests.py                # 运行测试
│   ├── test_api_endpoints.sh       # API端点测试
│   ├── test_document_upload.sh     # 文档上传测试
│   ├── test_document_upload_detailed.sh # 详细上传测试
│   ├── test_endpoint_consistency.sh # 端点一致性测试
│   └── test_utf8_fix.sh            # UTF-8修复测试
└── tools/                          # 工具脚本
    ├── README.md
    ├── api_summary.py              # API摘要生成
    ├── code_quality_check.py       # 代码质量检查
    ├── generate_api_docs.py        # API文档生成
    ├── fix_symlinks.sh             # 修复符号链接
    ├── validate_symlinks.sh        # 验证符号链接
    ├── sync_github_templates.sh    # 同步GitHub模板
    └── weekly_maintenance_check.sh # 周维护检查
```

#### 1.7 其他目录结构
```
temp/                               # 临时文件目录
├── config_backup/                  # 配置备份
├── data_backup/                    # 数据备份
├── requirements-backup/            # 依赖备份
├── tests-backup/                   # 测试备份
├── deleted-tests-backup/           # 已删除测试备份
├── shell_tests_backup/             # Shell测试备份
├── tests-backup-20250627-215030/   # 时间戳备份
└── temp/                           # 临时子目录

logs/                               # 日志目录
├── app/                            # 应用日志
├── services/                       # 服务日志
├── tests/                          # 测试日志
├── maintenance/                    # 维护日志
└── app.log                         # 主应用日志

monitoring/                         # 监控配置
├── prometheus.yml                  # Prometheus配置
└── alert_rules.yml                 # 告警规则

nginx/                              # Nginx配置
├── nginx.conf                      # 开发环境配置
└── nginx.prod.conf                 # 生产环境配置

examples/                           # 示例代码
├── parent_child_numbering_demo.py  # 父子编号示例
└── unified_document_api_demo.py    # 统一文档API示例

参考项目/                           # 参考项目目录
└── (参考项目文件)                  # 开发参考资料
```

### 2. 文件分类规则

#### 2.1 源代码文件组织
- **按功能模块组织**：
  - `backend/app/api/` - API路由和端点
  - `backend/app/services/` - 业务逻辑服务
  - `backend/app/rag/` - RAG核心功能
  - `backend/app/models/` - 数据模型定义
  - `backend/app/schemas/` - API数据模式

- **按文件类型组织**：
  - `.py` - Python源代码文件
  - `.ts/.tsx` - TypeScript/React文件
  - `.js/.jsx` - JavaScript/React文件
  - `.html` - HTML模板文件
  - `.css/.scss` - 样式文件

#### 2.2 配置文件统一存放
- **根级配置文件**：
  - `pyproject.toml` - Python项目配置
  - `docker-compose.yml` - Docker开发配置
  - `docker-compose.prod.yml` - Docker生产配置
  - `.env.example` - 环境变量示例

- **应用级配置文件**：
  - `backend/app/core/config.py` - 后端应用配置
  - `frontend-app/package.json` - 前端项目配置
  - `frontend-app/vite.config.ts` - 前端构建配置

- **服务配置文件**：
  - `nginx/nginx.conf` - Nginx配置
  - `monitoring/prometheus.yml` - 监控配置

#### 2.3 测试文件与源代码对应关系
- **测试文件位置**：
  - `backend/tests/` - 后端测试根目录
  - `backend/tests/unit/` - 单元测试
  - `backend/tests/integration/` - 集成测试
  - `backend/tests/performance/` - 性能测试

- **测试文件命名对应**：
  - 源文件：`backend/app/services/auth/auth.py`
  - 测试文件：`backend/tests/unit/services/auth/test_auth.py`
  - 集成测试：`backend/tests/integration/test_auth_integration.py`

#### 2.4 文档文件分类和存放规则
- **API文档**：`docs/api/` - API相关文档
- **开发文档**：`docs/development/` - 开发指南和流程
- **部署文档**：`docs/deployment/` - 部署和运维文档
- **修复文档**：`docs/fixes/` - 问题修复记录
- **测试文档**：`docs/testing/` - 测试相关文档

#### 2.5 数据文件管理
- **原始数据**：`data/raw/` - 未处理的原始数据
- **处理数据**：`data/processed/` - 经过处理的数据
- **上传文件**：`data/uploads/` - 用户上传的文件
- **缓存数据**：`data/cache/` - 系统缓存文件
- **临时数据**：`data/temp/` - 临时处理文件
- **测试数据**：`data/test_data/` - 测试专用数据

#### 2.6 临时文件和日志文件管理
- **临时文件**：
  - `temp/` - 根级临时文件
  - `temp/config_backup/` - 配置备份
  - `temp/data_backup/` - 数据备份
  - `temp/tests-backup/` - 测试备份

- **日志文件**：
  - `logs/app/` - 应用日志
  - `logs/services/` - 服务日志
  - `logs/tests/` - 测试日志
  - `logs/maintenance/` - 维护日志

### 3. 命名规范

#### 3.1 文件和目录命名约定
- **目录命名**：
  - 使用小写字母和下划线：`user_service/`
  - 复数形式用于集合：`models/`, `services/`, `tests/`
  - 单数形式用于单一概念：`config/`, `core/`

- **Python文件命名**：
  - 模块文件：`user_service.py`
  - 测试文件：`test_user_service.py`
  - 配置文件：`config.py`, `settings.py`
  - 初始化文件：`__init__.py`

- **前端文件命名**：
  - 组件文件：`UserProfile.tsx` (PascalCase)
  - 工具文件：`apiClient.ts` (camelCase)
  - 样式文件：`user-profile.css` (kebab-case)
  - 类型文件：`types.ts`, `interfaces.ts`

#### 3.2 不同类型文件的命名模式
- **API路由文件**：
  - `auth.py` - 认证相关路由
  - `user.py` - 用户相关路由
  - `admin.py` - 管理员路由

- **服务文件**：
  - `auth_service.py` - 认证服务
  - `user_service.py` - 用户服务
  - `llm_service.py` - LLM服务

- **模型文件**：
  - `user.py` - 用户模型
  - `document.py` - 文档模型
  - `collection.py` - 集合模型

- **测试文件**：
  - `test_auth.py` - 认证测试
  - `test_user_service.py` - 用户服务测试
  - `test_integration.py` - 集成测试

#### 3.3 版本控制和备份文件命名规则
- **备份文件**：
  - 时间戳格式：`backup-YYYYMMDD-HHMMSS/`
  - 功能描述：`config_backup/`, `data_backup/`
  - 版本号：`v1.0.0-backup/`

- **临时文件**：
  - 调试文件：`debug_*.py`, `test_*.py`
  - 临时脚本：`temp_*.py`, `fix_*.py`
  - 验证文件：`verify_*.py`, `check_*.py`

### 4. 具体实施计划

#### 4.1 当前需要移动或重组的文件清单

##### 4.1.1 根目录清理（高优先级）
**需要移动的文件**：
- `create_admin.py` → `scripts/backend/create_admin.py` ✅ 已完成
- `init_db.py` → `scripts/database/init_db.py` ✅ 已完成
- `init_db.sh` → `scripts/database/init_db.sh` ✅ 已完成
- `initialize.sh` → `scripts/setup/initialize.sh` ✅ 已完成
- `restart_backend.sh` → `scripts/deployment/restart_backend.sh` ✅ 已完成
- `restart_backend_with_init.sh` → `scripts/deployment/restart_backend_with_init.sh` ✅ 已完成

**需要移动的测试和调试文件**：
- `test_*.py` → `temp/` 或删除（如已过时）
- `debug_*.html` → `temp/`
- `fix_*.py` → `temp/`
- `*_fix_*.txt` → `temp/`
- `*.json` (API响应文件) → `temp/`

**需要保留的根目录文件**：
- `README.md` - 项目主文档
- `PLANNING.md` - 项目规划文档
- `TASK.md` - 任务管理文档
- `pyproject.toml` - Python项目配置
- `docker-compose.yml` - Docker配置
- `docker-compose.prod.yml` - 生产环境配置
- `Dockerfile` - Docker镜像配置

##### 4.1.2 重复文件处理（中优先级）
**需要合并或删除的重复文件**：
- `htmlcov/` (根目录) → 删除，保留 `backend/htmlcov/`
- `coverage.xml` (根目录) → 删除，保留 `backend/coverage.json`
- 重复的测试文件 → 合并到 `backend/tests/`

##### 4.1.3 配置文件统一（中优先级）
**需要检查和统一的配置**：
- 环境变量配置：创建 `.env.example`
- 依赖管理：统一使用 `pyproject.toml`
- 测试配置：统一到 `backend/tests/pytest.ini`

#### 4.2 文件移动的优先级和顺序

##### 第一阶段：根目录清理（立即执行）
1. **移动脚本文件** ✅ 已完成
   - 所有 `.sh` 和 `.py` 脚本文件移动到 `scripts/` 对应子目录

2. **移动测试和调试文件**
   - 临时测试文件移动到 `temp/`
   - 过时的调试文件移动到 `temp/` 或删除

3. **清理重复文件**
   - 删除根目录的重复覆盖率报告
   - 合并重复的配置文件

##### 第二阶段：目录结构优化（1-2天内）
1. **优化后端目录结构**
   - 确保 `backend/app/` 结构符合规范
   - 整理 `backend/tests/` 目录结构
   - 清理 `backend/debug/` 目录

2. **优化数据目录结构**
   - 整理 `data/` 子目录
   - 清理过时的缓存文件
   - 备份重要数据文件

##### 第三阶段：文档和配置整理（3-5天内）
1. **文档结构优化**
   - 整理 `docs/` 目录结构
   - 更新过时的文档内容
   - 统一文档格式

2. **配置管理优化**
   - 创建统一的环境配置
   - 优化Docker配置
   - 统一依赖管理

#### 4.3 需要保留的历史文件处理方式

##### 4.3.1 备份策略
- **重要配置备份**：`temp/config_backup/`
- **数据文件备份**：`temp/data_backup/`
- **测试文件备份**：`temp/tests-backup/`
- **历史版本备份**：`temp/tests-backup-YYYYMMDD-HHMMSS/`

##### 4.3.2 历史文件分类
- **保留文件**：
  - 包含重要业务逻辑的调试文件
  - 有参考价值的测试文件
  - 重要的修复记录文件

- **归档文件**：
  - 移动到 `temp/` 目录
  - 添加时间戳标记
  - 保留6个月后考虑删除

- **删除文件**：
  - 明确过时的临时文件
  - 重复的配置文件
  - 空的或无用的测试文件

### 5. 文件组织执行标准

#### 5.1 新文件创建规则
- **源代码文件**：
  - 后端Python文件：必须放在 `backend/app/` 对应功能目录
  - 前端TypeScript文件：必须放在 `frontend-app/src/` 对应功能目录
  - 测试文件：必须放在 `backend/tests/` 对应目录结构

- **配置文件**：
  - 应用级配置：放在对应应用的 `config/` 目录
  - 项目级配置：放在项目根目录
  - 服务配置：放在对应服务目录（如 `nginx/`, `monitoring/`）

- **文档文件**：
  - API文档：`docs/api/`
  - 开发文档：`docs/development/`
  - 修复记录：`docs/fixes/`
  - 其他文档：`docs/` 对应子目录

- **脚本文件**：
  - 后端脚本：`scripts/backend/`
  - 数据库脚本：`scripts/database/`
  - 部署脚本：`scripts/deployment/`
  - 工具脚本：`scripts/tools/`

#### 5.2 文件移动和重组标准
- **移动前检查**：
  - 检查文件引用关系
  - 确认文件的实际用途
  - 备份重要文件

- **移动优先级**：
  1. 优先移动而非删除相似文件
  2. 保留有历史价值的调试文件
  3. 合并功能相似的文件

- **移动后验证**：
  - 检查引用路径是否正确
  - 运行相关测试确保功能正常
  - 更新文档中的路径引用

#### 5.3 文件维护规范
- **定期清理**：
  - 每月清理 `temp/` 目录过时文件
  - 每季度检查 `data/cache/` 缓存文件
  - 每半年归档历史备份文件

- **版本控制**：
  - 重要文件变更必须提交到Git
  - 临时文件添加到 `.gitignore`
  - 备份文件不提交到版本控制

- **文档同步**：
  - 文件结构变更后及时更新文档
  - 保持 `README.md` 文件的准确性
  - 更新相关的配置文件路径

### 6. 文件组织合规性检查

#### 6.1 自动化检查脚本
创建以下检查脚本：
- `scripts/tools/validate_file_structure.py` - 验证文件结构合规性
- `scripts/tools/check_file_references.py` - 检查文件引用完整性
- `scripts/tools/cleanup_temp_files.py` - 清理临时文件

#### 6.2 合规性检查清单
- [ ] 所有源代码文件在正确的目录结构中
- [ ] 测试文件与源代码文件对应关系正确
- [ ] 配置文件统一管理
- [ ] 文档文件分类清晰
- [ ] 临时文件定期清理
- [ ] 备份文件有明确的保留策略

#### 6.3 违规处理流程
1. **发现违规**：通过自动化脚本或人工检查
2. **评估影响**：确定违规的严重程度和影响范围
3. **制定方案**：制定文件重组或移动方案
4. **执行整改**：按照本规划执行文件移动
5. **验证结果**：确保整改后符合规范
6. **更新文档**：更新相关文档和配置

### 7. 总结

本文件存储位置规划为RAG-chat项目建立了完整的文件组织标准，包括：

1. **清晰的目录层次结构**：7个主要目录，每个目录有明确的用途
2. **详细的文件分类规则**：按功能、类型、用途进行分类
3. **统一的命名规范**：支持Python、TypeScript等多种语言
4. **具体的实施计划**：分阶段执行，优先级明确
5. **完善的维护机制**：定期检查、自动化验证、合规性保证

**执行原则**：
- 所有新文件必须按照本规划创建
- 现有文件逐步按计划重组
- 保持向后兼容，谨慎处理历史文件
- 定期维护，持续优化文件组织结构

**下一步行动**：
1. 立即执行根目录清理（移动测试和调试文件）
2. 创建自动化检查脚本
3. 逐步优化各子目录结构
4. 建立定期维护机制

---

## 技术范围与架构

### 核心概念
RAG系统通过以下方式增强大型语言模型(LLM)：
- **检索阶段**: 根据用户查询从外部文档库中检索相关信息
- **增强阶段**: 将检索到的信息与原始查询结合
- **生成阶段**: 基于增强后的上下文生成准确、相关的回答

### 技术栈选择（当前版本）

#### 核心框架
- **LangChain 0.2.17**: RAG开发框架
- **Python 3.10**: 主要开发语言
- **FastAPI 0.104.1**: Web框架
- **Uvicorn 0.24.0**: ASGI服务器

#### 数据存储
- **Milvus 2.3.3**: 主要向量数据库
- **FAISS-CPU 1.7.4**: 本地向量检索
- **MongoDB**: 文档元数据存储（Motor 3.3.1驱动）
- **Redis**: 缓存层

#### 文本嵌入模型
- **OpenAI Embeddings**: 主要嵌入模型（OpenAI 1.3.0）
- **LM Studio Embeddings**: 本地部署选项
  - 支持text-embedding-nomic-embed-text-v1.5模型
  - 维度：768，支持中英文
- **Sentence Transformers**: 备选方案
- **自定义Embedding Pipeline**: 支持模型切换

#### 文档处理
- **PyPDF2/pypdf 3.16.0**: PDF文档处理
- **Unstructured 0.12.4**: 通用文档处理
- **pdf2image 1.17.0**: PDF图像转换
- **pytesseract 0.3.10**: OCR支持
- **NLTK 3.8.1**: 文本分析
- **pdfminer.six**: 高级PDF处理

### 系统架构设计

```
用户查询 → FastAPI接口 → 文档检索器 → 向量检索(Milvus 2.3.3) → LLM生成 → 响应输出
    ↓           ↓           ↓                ↓                   ↓         ↓
请求验证 → 认证授权 → 文档预处理 → 向量化(OpenAI/LM Studio) → 结果处理 → 日志记录
```

### 已实现的高级RAG技术

项目已集成以下高级技术：

1. ✅ **分层文档分割**: 父子文档分割策略，提高检索精度
2. ✅ **多格式文档处理**: 支持PDF、TXT、MD等多种格式
3. ✅ **智能文档清洗**: 自动清理和优化文档内容
4. ✅ **向量存储优化**: 基于Milvus的高性能向量检索
5. ✅ **实时状态监控**: 完整的系统状态监控和管理

### 待实现的高级技术

1. **Self-RAG**: 动态决定何时检索和如何检索
2. **Long-Context RAG**: 处理超长文档的能力
3. **Multi-Modal RAG**: 结合文本和图像检索
4. **Atomic RAG**: 将文档分解为原子级事实陈述

## 技术栈详细说明

### 后端技术栈
1. **Web框架**
   - FastAPI: 高性能异步Web框架
   - Uvicorn: ASGI服务器
   - Pydantic: 数据验证

2. **数据存储**
   - MongoDB: 文档存储
   - Milvus: 向量数据库
   - Redis: 缓存层

3. **AI/ML组件**
   - LangChain: RAG框架
   - OpenAI API: LLM服务
   - FAISS: 向量检索
   - Sentence-Transformers: 文本嵌入

4. **文档处理**
   - PyPDF2/pypdf: PDF处理
   - Unstructured: 通用文档处理
   - Tesseract: OCR支持
   - NLTK: 文本分析

### 开发工具链
1. **版本控制**
   - Git
   - GitHub Actions (CI/CD)

2. **开发环境**
   - VSCode
   - Python 3.9+
   - Docker

3. **测试工具**
   - Pytest: 单元测试
   - Locust: 性能测试

### 项目约束

#### 性能约束
1. **响应时间**
   - API响应时间 < 1s
   - RAG查询响应时间 < 5s
   - 批量文档处理速度 > 1MB/s

2. **并发处理**
   - 支持100+并发用户
   - 单机处理能力 > 50 QPS

3. **资源限制**
   - 内存使用 < 16GB
   - CPU使用率 < 80%

#### 安全约束
1. **数据安全**
   - 所有API需要认证
   - 敏感数据加密存储
   - 支持数据访问权限控制

2. **合规要求**
   - 符合数据保护规范
   - 支持审计日志
   - 提供数据备份机制

## 项目里程碑

### 第一阶段：基础架构（已完成 ✅）
- [x] 基础架构搭建
- [x] 依赖环境配置
- [x] 核心组件选型
- [x] 项目结构规范化

### 第二阶段：核心功能（已完成 ✅）
- [x] 文档处理模块开发
- [x] 向量存储实现
- [x] RAG基础链路搭建
- [x] 多格式文档支持

### 第三阶段：API与界面（已完成 ✅）
- [x] 完整API接口开发（24个端点）
- [x] 前端界面开发（主应用）
- [x] 用户认证系统
- [x] 文档集合管理

### 第四阶段：优化与完善（已完成 ✅）
- [x] 性能优化
- [x] 测试覆盖（91.7%通过率）
- [x] 代码质量提升
- [x] 项目结构整理

### 第五阶段：稳定性提升（已完成 ✅）
- [x] UTF-8编码错误修复
- [x] API一致性优化
- [x] 错误处理完善
- [x] 文档预览功能优化

## 项目目标

### 主要目标
1. 构建功能完整的RAG系统原型
2. 实现多种文档格式的支持
3. 提供用户友好的查询接口
4. 确保系统的可扩展性和可维护性

### 性能指标（当前实现）
- **检索精度**: 相关文档检索准确率 > 90% ✅
- **响应时间**:
  - API响应时间平均 0.010秒 ✅
  - 文档分割预览 < 0.050秒 ✅
  - RAG查询响应 < 3秒 ✅
- **系统稳定性**:
  - 支持100+并发查询 ✅
  - API测试通过率 100% ✅
  - 服务可用性 > 99.9% ✅

## 技术实现策略

### 开发阶段（当前状态）
1. **基础设施阶段** ✅ [已完成]:
   - 环境配置
   - 依赖管理
   - 项目结构搭建
2. **核心功能阶段** ✅ [已完成]:
   - 文档处理模块
   - 向量存储实现
   - RAG链路开发
3. **API开发阶段** ✅ [已完成]:
   - RESTful API设计（24个端点）
   - 认证授权系统
   - 并发处理能力
4. **优化阶段** ✅ [已完成]:
   - 性能调优
   - 测试完善（91.7%通过率）
   - 监控部署
5. **维护阶段** 🔄 [进行中]:
   - 代码质量持续改进
   - 功能增强和优化
   - 文档维护更新

### 质量保证（当前状态）
- ✅ 单元测试覆盖率 91.7% (11/12通过)
- ✅ 集成测试覆盖主要用例
- ✅ 性能测试验证系统负载能力
- ✅ 安全测试确保数据安全
- ✅ API端点全面测试（100%通过率）
- ✅ UTF-8编码问题完全修复
- ✅ 代码质量标准体系建立

## 风险评估与缓解

### 技术风险
- **API依赖**: 使用多个备选API服务
- **向量数据库性能**: 选择合适的数据库解决方案
- **模型幻觉问题**: 实施检索质量验证机制

### 数据风险
- **数据质量**: 建立数据清洗和验证流程
- **版权问题**: 确保使用授权数据源
- **隐私保护**: 实施数据脱敏措施

## 扩展性考虑

### 水平扩展
- 支持分布式向量搜索
- 实现负载均衡机制
- 缓存策略优化

### 功能扩展
- 多语言支持
- 实时数据更新
- 个性化推荐集成
- 对话历史管理

## 成功标准

### 技术标准
- 系统能够准确回答基于文档库的问题
- 检索和生成延迟在可接受范围内
- 系统具备良好的错误处理能力

### 业务标准
- 用户满意度达到预期水平
- 系统能够处理实际业务场景
- 具备商业化部署的可行性

## 后续发展规划

### 短期目标 (1-2个月) - 功能增强
- [ ] 实现Self-RAG动态检索
- [ ] 添加多模态RAG支持
- [ ] 优化长文档处理能力
- [ ] 增强实时监控功能

### 中期目标 (3-6个月) - 扩展应用
- [ ] 集成更多LLM提供商
- [ ] 实现分布式部署
- [ ] 添加高级分析功能
- [ ] 开发移动端应用

### 长期目标 (6个月+) - 生态建设
- [ ] 探索商业化应用场景
- [ ] 建立插件生态系统
- [ ] 考虑开源社区贡献
- [ ] 集成企业级安全功能