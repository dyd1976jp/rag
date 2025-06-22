# RAG系统测试

本目录包含RAG系统的全面测试套件，采用现代化的测试组织结构和最佳实践。

## 🏗️ 测试架构

### 目录结构
```
tests/
├── unit/                    # 单元测试
│   ├── api/                # API层测试
│   │   └── v1/endpoints/   # API端点测试
│   ├── core/               # 核心模块测试
│   ├── db/                 # 数据库层测试
│   ├── models/             # 数据模型测试
│   ├── rag/                # RAG系统测试
│   └── services/           # 服务层测试
├── integration/            # 集成测试
├── performance/            # 性能测试
├── fixtures/               # 测试数据和配置
├── utils/                  # 测试工具
├── mocks/                  # Mock对象
├── scripts/                # 测试脚本
└── data/                   # 测试数据文件
```

### 测试分类
- **单元测试**: 测试单个组件的功能
- **集成测试**: 测试组件间的交互
- **性能测试**: 测试系统性能和负载能力

## 🚀 快速开始

### 运行所有测试
```bash
# 使用新的统一测试脚本
python scripts/run_tests.py --all

# 或使用 pytest 直接运行
pytest
```

### 运行特定类型的测试
```bash
# 单元测试
python scripts/run_tests.py --unit

# 集成测试
python scripts/run_tests.py --integration

# 性能测试
python scripts/run_tests.py --performance

# API测试
python scripts/run_tests.py --api

# RAG系统测试
python scripts/run_tests.py --rag

# 服务层测试
python scripts/run_tests.py --services
```

### 运行特定模块测试
```bash
# 缓存服务测试
python scripts/run_tests.py --cache

# 嵌入模型测试
python scripts/run_tests.py --embedding

# 检索服务测试
python scripts/run_tests.py --retrieval

# 自定义路径测试
python scripts/run_tests.py --test-path unit/rag/
```

### 高级选项
```bash
# 生成覆盖率报告
python scripts/run_tests.py --all --coverage

# 并行运行测试
python scripts/run_tests.py --all --parallel

# 详细输出
python scripts/run_tests.py --all --verbose
```

## 📋 测试标记

我们使用 pytest 标记来分类和过滤测试：

```bash
# 按标记运行测试
pytest -m unit          # 单元测试
pytest -m integration   # 集成测试
pytest -m api           # API测试
pytest -m slow          # 慢速测试
pytest -m rag           # RAG系统测试
```

### 可用标记
- `unit`: 单元测试
- `integration`: 集成测试
- `performance`: 性能测试
- `slow`: 慢速测试
- `api`: API测试
- `document`: 文档相关测试
- `rag`: RAG系统测试
- `db`: 数据库测试
- `services`: 服务层测试

## 🔧 配置

### pytest 配置
测试配置在 `pytest.ini` 文件中定义，包括：
- 测试发现规则
- 标记定义
- 覆盖率配置
- 日志配置

### 环境变量
测试运行时会自动设置以下环境变量：
- `TESTING=true`: 标识测试环境
- `LOG_LEVEL=DEBUG`: 启用调试日志

## 📦 测试依赖

测试依赖项在以下文件中定义：
- `requirements-dev.txt`: 开发和测试依赖
- `pyproject.toml`: 项目配置和依赖

安装测试依赖：
```bash
pip install -r requirements-dev.txt
```

## 🛠️ 测试工具

### 测试辅助工具
- `utils/test_helpers.py`: 通用测试辅助函数
- `utils/data_generators.py`: 测试数据生成器
- `utils/api_client.py`: API测试客户端
- `utils/token_generator.py`: 测试令牌生成器

### Mock 对象
- `mocks/mongodb_mock.py`: MongoDB模拟对象

### 测试数据
- `fixtures/`: 测试配置和响应数据
- `data/`: 测试文档和数据文件

## 📊 覆盖率报告

生成详细的覆盖率报告：
```bash
python scripts/run_tests.py --all --coverage
```

覆盖率报告将生成在 `coverage_html/` 目录中，包括：
- 整体覆盖率统计
- 按模块的覆盖率详情
- 未覆盖代码的高亮显示

## 🧪 编写测试

### 测试命名规范
- 测试文件：`test_*.py`
- 测试类：`Test*`
- 测试方法：`test_*`

### 测试结构
```python
import pytest
from unittest.mock import Mock, patch

class TestYourComponent:
    """组件测试类"""

    @pytest.fixture
    def mock_dependency(self):
        """测试依赖的fixture"""
        return Mock()

    @pytest.mark.unit
    def test_should_do_something_when_condition_met(self, mock_dependency):
        """
        测试描述：应该在满足条件时执行某操作

        验证：
        - 条件满足时的行为
        - 返回值正确性
        - 副作用验证
        """
        # Arrange - 准备测试数据

        # Act - 执行被测试的操作

        # Assert - 验证结果
```

### 最佳实践
1. **使用描述性的测试名称**：测试名应清楚描述测试的内容
2. **遵循 AAA 模式**：Arrange（准备）、Act（执行）、Assert（断言）
3. **使用适当的标记**：为测试添加合适的 pytest 标记
4. **编写文档字符串**：为复杂测试添加详细说明
5. **使用 fixtures**：复用测试设置和清理逻辑
6. **Mock 外部依赖**：隔离被测试的组件

## 🔍 调试测试

### 运行单个测试
```bash
pytest tests/unit/services/test_cache_service.py::TestCacheService::test_init_success -v
```

### 调试模式
```bash
pytest --pdb  # 在失败时进入调试器
pytest -s     # 显示 print 输出
pytest -v     # 详细输出
```

### 日志调试
测试运行时会自动启用详细日志，可以在测试中使用：
```python
import logging
logger = logging.getLogger(__name__)
logger.info("调试信息")
```

## 🚨 故障排除

### 常见问题

1. **导入错误**
   - 确保项目根目录在 Python 路径中
   - 检查相对导入路径是否正确

2. **测试数据库连接**
   - 确保测试使用 Mock 数据库
   - 检查 `conftest.py` 中的数据库配置

3. **异步测试问题**
   - 使用 `@pytest.mark.asyncio` 标记异步测试
   - 确保正确处理事件循环

4. **缓存问题**
   - 清理 `__pycache__` 目录
   - 重新安装依赖

### 获取帮助
```bash
python scripts/run_tests.py --help  # 查看所有可用选项
pytest --help                       # 查看 pytest 选项
```

## 📈 持续集成

测试套件设计为在 CI/CD 环境中运行：
- 所有测试都使用 Mock 对象，无需外部依赖
- 支持并行执行以提高速度
- 生成标准化的测试报告和覆盖率数据

---

**注意**: 这个测试套件已经过重新组织和优化，采用了现代化的测试架构和最佳实践。如果您发现任何问题或有改进建议，请及时反馈。