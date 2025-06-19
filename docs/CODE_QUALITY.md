# RAG-Chat 代码质量指南

## 概述

本文档定义了RAG-Chat项目的代码质量标准和最佳实践，旨在确保代码的可维护性、可读性和一致性。

## 代码风格标准

### Python代码规范

#### 1. 基础规范
- 遵循 **PEP 8** 代码风格指南
- 使用 **Black** 进行代码格式化（行长度限制为100字符）
- 使用 **isort** 进行导入语句排序
- 使用 **flake8** 进行代码检查

#### 2. 命名规范
```python
# 变量和函数：snake_case
user_name = "john"
def get_user_info():
    pass

# 类名：PascalCase
class DocumentProcessor:
    pass

# 常量：UPPER_SNAKE_CASE
MAX_FILE_SIZE = 1024 * 1024

# 私有成员：前缀下划线
def _internal_method():
    pass
```

#### 3. 类型注解
所有公共函数和方法必须包含类型注解：

```python
from typing import List, Dict, Optional, Any

def process_documents(
    documents: List[str], 
    options: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    处理文档列表
    
    Args:
        documents: 文档内容列表
        options: 处理选项
        
    Returns:
        处理结果，失败时返回None
    """
    pass
```

#### 4. 文档字符串
使用Google风格的文档字符串：

```python
def calculate_similarity(text1: str, text2: str) -> float:
    """
    计算两个文本的相似度
    
    使用余弦相似度算法计算文本向量之间的相似度。
    
    Args:
        text1: 第一个文本
        text2: 第二个文本
        
    Returns:
        相似度分数，范围[0, 1]
        
    Raises:
        ValueError: 当输入文本为空时
        
    Example:
        >>> similarity = calculate_similarity("hello", "hi")
        >>> print(f"相似度: {similarity:.2f}")
    """
    pass
```

## 代码结构规范

### 1. 文件长度限制
- **单个文件不超过500行**
- **单个函数不超过50行**
- **单个类不超过200行**

### 2. 模块组织
```
app/
├── api/                    # API层
│   ├── v1/
│   │   ├── endpoints/      # 端点实现
│   │   └── utils/          # API工具函数
│   └── deps.py            # 依赖注入
├── core/                   # 核心配置
├── models/                 # 数据模型
├── schemas/                # Pydantic模式
├── services/               # 业务逻辑层
└── utils/                  # 通用工具
```

### 3. 导入顺序
使用isort自动排序，遵循以下顺序：
1. 标准库导入
2. 第三方库导入
3. 本地应用导入

```python
# 标准库
import os
import sys
from typing import List, Dict

# 第三方库
from fastapi import FastAPI, Depends
from pydantic import BaseModel

# 本地导入
from app.core.config import settings
from app.models.user import User
```

## 错误处理规范

### 1. 异常处理
```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def safe_process_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    安全地处理文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        处理结果，失败时返回None
    """
    try:
        # 处理逻辑
        result = process_file(file_path)
        return result
    except FileNotFoundError:
        logger.error(f"文件不存在: {file_path}")
        return None
    except PermissionError:
        logger.error(f"文件权限不足: {file_path}")
        return None
    except Exception as e:
        logger.error(f"处理文件时出错: {file_path}, 错误: {e}")
        return None
```

### 2. 日志记录
```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def example_function():
    logger.info("开始处理")
    try:
        # 业务逻辑
        pass
    except Exception as e:
        logger.error(f"处理失败: {e}", exc_info=True)
        raise
    finally:
        logger.info("处理完成")
```

## 测试规范

### 1. 测试结构
```
tests/
├── unit/                   # 单元测试
├── integration/            # 集成测试
├── fixtures/               # 测试数据
└── conftest.py            # pytest配置
```

### 2. 测试命名
```python
def test_should_return_user_when_valid_id_provided():
    """测试：提供有效ID时应返回用户信息"""
    pass

def test_should_raise_error_when_invalid_id_provided():
    """测试：提供无效ID时应抛出错误"""
    pass
```

### 3. 测试覆盖率
- 目标覆盖率：**80%以上**
- 关键业务逻辑：**90%以上**

## 性能优化指南

### 1. 数据库查询优化
```python
# 好的做法：使用索引和限制结果
async def get_recent_documents(limit: int = 10) -> List[Document]:
    cursor = db.documents.find().sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)

# 避免：查询所有数据
async def get_all_documents() -> List[Document]:
    cursor = db.documents.find()  # 可能返回大量数据
    return await cursor.to_list(length=None)
```

### 2. 异步编程
```python
import asyncio
from typing import List

# 并发处理
async def process_documents_concurrently(documents: List[str]) -> List[Any]:
    tasks = [process_single_document(doc) for doc in documents]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]
```

## 安全规范

### 1. 输入验证
```python
from pydantic import BaseModel, validator

class DocumentUpload(BaseModel):
    filename: str
    content: str
    
    @validator('filename')
    def validate_filename(cls, v):
        if not v or len(v) > 255:
            raise ValueError('文件名无效')
        return v
    
    @validator('content')
    def validate_content(cls, v):
        if len(v) > 1024 * 1024:  # 1MB限制
            raise ValueError('内容过大')
        return v
```

### 2. 敏感信息处理
```python
import os
from typing import Optional

def get_api_key() -> Optional[str]:
    """从环境变量获取API密钥"""
    return os.getenv('API_KEY')

# 避免在代码中硬编码敏感信息
# API_KEY = "sk-1234567890"  # 错误做法
```

## 代码审查清单

### 提交前检查
- [ ] 代码通过所有测试
- [ ] 代码符合风格规范（Black + isort + flake8）
- [ ] 添加了必要的类型注解
- [ ] 添加了文档字符串
- [ ] 添加了适当的错误处理
- [ ] 添加了相关测试
- [ ] 更新了相关文档

### 审查要点
- [ ] 代码逻辑清晰易懂
- [ ] 函数和类职责单一
- [ ] 没有重复代码
- [ ] 性能考虑合理
- [ ] 安全性检查通过
- [ ] 错误处理完善

## 工具配置

### 开发环境设置
```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 设置pre-commit钩子
pre-commit install

# 运行代码检查
black --check .
isort --check-only .
flake8 .
mypy .

# 运行测试
pytest --cov=app tests/
```

### IDE配置
推荐使用VSCode并安装以下扩展：
- Python
- Pylance
- Black Formatter
- isort
- Flake8

## 持续改进

### 定期审查
- **每月**：代码质量指标审查
- **每季度**：代码规范更新
- **每年**：工具链升级

### 指标监控
- 代码覆盖率
- 代码复杂度
- 技术债务
- 性能指标

---

遵循这些规范将帮助我们维护高质量的代码库，提高开发效率和系统稳定性。
