# RAG-Chat测试文件说明

本文档提供RAG-Chat项目中所有测试文件的综合说明，包括测试的目的、分类、使用方法和注意事项。

## 测试文件分类

RAG-Chat项目的测试文件按功能模块进行组织，主要分为以下几类：

| 类别 | 目录 | 主要测试内容 |
|------|------|------------|
| API测试 | `tests/api/` | API端点功能测试 |
| 服务层测试 | `tests/services/` | 业务逻辑服务测试 |
| 数据库测试 | `tests/db/` | 数据库操作测试 |
| 模型发现测试 | `tests/discover/` | 模型发现和注册功能测试 |
| 模拟数据 | `tests/mocks/` | 测试用模拟数据 |
| 独立测试脚本 | `tests/` (根目录) | 跨层级功能测试和工具脚本 |

## 模块测试文件说明

### 1. API测试 (`tests/api/`)

| 文件名 | 目的 | 主要功能 |
|-------|-----|---------|
| `test_auth_api.py` | 测试认证API | 登录、注册、令牌验证等 |
| `test_llm_api.py` | 测试LLM模型API | 模型管理、查询、删除等 |

### 2. 服务层测试 (`tests/services/`)

| 文件名 | 目的 | 主要功能 |
|-------|-----|---------|
| `test_llm_service.py` | 测试LLM服务层 | 模型配置、测试和调用 |
| `test_user_service.py` | 测试用户服务层 | 用户管理、权限等 |

### 3. 数据库测试 (`tests/db/`)

| 文件名 | 目的 | 主要功能 |
|-------|-----|---------|
| `test_mongodb.py` | 测试MongoDB连接和操作 | 文档CRUD操作 |

### 4. 模型发现测试 (`tests/discover/`)

| 文件名 | 目的 | 主要功能 |
|-------|-----|---------|
| `test_discover_client.py` | 客户端测试 | 测试模型发现API客户端 |
| `test_service.py` | 服务层测试 | LLM服务发现功能测试 |
| `test_api_server.py` | 独立服务器 | 创建测试用API服务器 |
| `test_route.py` | 路由测试 | FastAPI路由注册测试 |
| `test_api.py` | API端点测试 | 测试原有发现模型端点 |

### 5. 根目录测试文件

| 文件名 | 目的 | 主要功能 |
|-------|-----|---------|
| `test_discover_endpoints.py` | 单元测试 | 测试discover_models路由函数 |
| `test_llm_endpoints.py` | 单元测试 | 测试llm路由转发功能 |
| `test_with_token.py` | 认证测试 | 带认证令牌测试API |
| `test_discover.py` | 综合测试 | 测试模型发现功能 |
| `test_discover_alt.py` | 替代实现 | 替代方法测试发现功能 |
| `test_discover_direct.py` | 直接接口测试 | 直接调用接口发现模型 |
| `test_lmstudio_direct.py` | LM Studio测试 | 直接测试LM Studio连接 |

## 测试脚本文件

| 文件名 | 目的 | 主要功能 |
|-------|-----|---------|
| `test_api.sh` | API测试脚本 | Bash脚本测试API端点 |
| `test_discover_curl.sh` | 发现CURL测试 | 使用CURL测试发现API |
| `test_llm_api.sh` | LLM API测试 | 测试LLM API端点 |
| `test_llm_curl.sh` | LLM CURL测试 | 使用CURL测试LLM API |

## 测试工具说明

| 文件名 | 目的 | 主要功能 |
|-------|-----|---------|
| `conftest.py` | pytest配置 | 测试fixture和环境设置 |
| `create_test_token.py` | 创建测试令牌 | 生成测试用认证令牌 |
| `run_tests.py` | 测试运行器 | 自动运行测试套件 |

## 如何运行测试

### 1. 运行所有测试

```bash
cd /Users/tei/go/RAG-chat/backend
python -m pytest
```

### 2. 运行特定目录的测试

```bash
# 运行API测试
python -m pytest tests/api/

# 运行发现功能测试
python -m pytest tests/discover/
```

### 3. 运行单个测试文件

```bash
python -m pytest tests/discover/test_discover_client.py
```

### 4. 运行特定测试函数

```bash
python -m pytest tests/discover/test_discover_client.py::test_discover_models
```

### 5. 使用标记运行测试

```bash
python -m pytest -m "api"  # 运行所有带api标记的测试
```

## 测试环境准备

1. 安装测试依赖

```bash
pip install -r tests/requirements.txt
```

2. 确保相关服务正在运行

   - MongoDB服务
   - 应用后端服务
   - LLM模型服务(如适用)

3. 准备测试数据

```bash
python tests/create_test_token.py  # 创建测试用认证令牌
```

## 测试注意事项

1. **路径问题**: 所有测试应从backend目录运行，以确保导入路径正确
2. **认证问题**: 某些测试需要有效的认证令牌，可能需要先生成或更新
3. **依赖服务**: 确保所需的外部服务(MongoDB等)已启动并配置正确
4. **配置文件**: 测试时应使用测试专用的配置文件或环境变量
5. **网络依赖**: 模型发现测试可能依赖于本地LLM服务(如LM Studio或Ollama)的运行状态

## 测试调试技巧

1. 使用`-v`或`-vv`参数获取更详细的输出:
   ```bash
   python -m pytest -vv tests/discover/
   ```

2. 使用`--pdb`在失败时进入调试器:
   ```bash
   python -m pytest --pdb
   ```

3. 使用`--log-cli-level=INFO`查看日志输出:
   ```bash
   python -m pytest --log-cli-level=INFO
   ```

4. 使用`-x`在首次失败时停止:
   ```bash
   python -m pytest -x
   ```

## 测试文件维护指南

1. 所有新测试应遵循现有的目录结构和命名约定
2. 每个测试文件应包含清晰的文档字符串，说明测试目的和用法
3. 使用pytest装饰器(如`@pytest.mark.asyncio`)标记特殊测试类型
4. 保持测试文件的专注性，每个文件应只测试一个特定功能或模块
5. 使用`pytest.mark`为测试添加标记，便于分类运行 