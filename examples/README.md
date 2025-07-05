# 索引管理器使用示例

本目录包含了完整的索引管理器使用示例，展示如何使用IndexProcessorFactory和ParentChildIndexProcessor进行文档处理。

## 文件结构

```
examples/
├── README.md                    # 本文件 - 使用说明
├── demo.py                      # 快速演示脚本
├── index_manager_usage.py       # 主要示例文件
├── test_index_manager_usage.py  # 单元测试文件
└── sample_documents/            # 示例文档目录
    ├── sample.pdf
    ├── sample.md
    └── sample.txt
```

## 功能特性

### 1. 基础使用示例
- IndexProcessorFactory的初始化和配置
- ParentChildIndexProcessor的创建和使用
- 完整的文档处理流程：提取 → 转换 → 加载 → 检索

### 2. 配置示例
- 递归字符分割器配置
- 段落模式和全文档模式配置
- 预览模式配置
- 性能优化配置

### 3. 实际场景示例
- PDF文档处理
- Markdown文档处理
- 预览模式 vs 完整处理模式对比
- 错误处理和异常情况
- 批量文档处理

### 4. 性能和测试示例
- 性能基准测试（目标<3秒检索时间）
- 检索质量验证
- 并发处理测试
- 内存使用监控
- 70%+测试覆盖率验证

## 快速开始

### 1. 快速演示

最简单的方式是运行演示脚本：

```bash
cd examples
python demo.py
```

这将运行一个完整的演示，展示所有核心功能，包括：
- 🔧 基础使用演示
- ⚙️ 配置示例演示
- 🌟 实际场景演示
- ⚡ 性能测试演示

### 2. 环境准备

确保已安装必要的依赖：

```bash
# 安装Python依赖
pip install -r backend/requirements.txt

# 启动MongoDB
docker run -d -p 27017:27017 --name mongodb mongo:latest

# 启动Milvus
docker run -d -p 19530:19530 --name milvus milvusdb/milvus:latest
```

### 2. 运行基础示例

```bash
# 进入项目根目录
cd /path/to/RAG-chat

# 运行完整示例
python examples/index_manager_usage.py
```

### 3. 运行单元测试

```bash
# 运行示例的单元测试
pytest examples/test_index_manager_usage.py -v

# 运行测试并生成覆盖率报告
pytest examples/test_index_manager_usage.py --cov=examples --cov-report=html
```

## 详细使用说明

### IndexProcessorFactory使用

```python
from backend.app.rag.processor_factory import (
    IndexProcessorFactory,
    ProcessorType,
    ProcessorConfig
)

# 1. 创建工厂实例
factory = IndexProcessorFactory()

# 2. 配置处理器参数
config = ProcessorConfig(
    enable_caching=True,
    cache_ttl_seconds=3600,
    max_concurrent_tasks=5
)

# 3. 创建处理器
processor = factory.get_processor(
    processor_type=ProcessorType.PARENT_CHILD,
    config=config
)
```

### ParentChildIndexProcessor使用

```python
from backend.app.rag.index_processor import ProcessRule
from backend.app.rag.document_splitter import Rule, ParentMode

# 1. 配置处理规则
process_rule = ProcessRule(
    parent_mode=ParentMode.PARAGRAPH,
    segmentation=Rule(
        separator="\n",
        max_tokens=1000,
        chunk_overlap=200
    )
)

# 2. 文档转换
transformed_docs = processor.transform(documents, process_rule)

# 3. 加载到存储系统
await processor.load(transformed_docs, batch_size=10)

# 4. 检索文档
results = await processor.retrieve(
    query="查询内容",
    top_k=5,
    score_threshold=0.7
)
```

### 配置选项说明

#### 分割策略配置

```python
# 段落模式 - 将段落作为父文档
paragraph_config = {
    "parent_mode": ParentMode.PARAGRAPH,
    "segmentation": {
        "separator": "\n",
        "max_tokens": 2000,
        "chunk_overlap": 100
    }
}

# 全文档模式 - 整个文档作为父文档
full_doc_config = {
    "parent_mode": ParentMode.FULL_DOC,
    "segmentation": {
        "separator": "\n",
        "max_tokens": 1000,
        "chunk_overlap": 200
    }
}
```

#### MongoDB和Milvus连接配置

```python
# MongoDB配置
mongodb_config = {
    "url": "mongodb://localhost:27017",
    "database": "rag_examples",
    "collection": "documents"
}

# Milvus配置
milvus_config = {
    "host": "localhost",
    "port": "19530",
    "collection": "example_collection",
    "dimension": 1536
}
```

## 性能基准

### 目标性能指标
- API响应时间：< 1秒
- RAG查询响应时间：< 3秒
- 批量文档处理速度：> 1MB/s
- 测试覆盖率：> 70%

### 性能测试结果示例

```
=== 性能基准测试结果 ===
配置1 (chunk_size=500):  处理时间=0.15s ✓
配置2 (chunk_size=1000): 处理时间=0.23s ✓
配置3 (chunk_size=2000): 处理时间=0.41s ✓

=== 检索性能测试结果 ===
平均检索时间: 0.85s ✓
最大检索时间: 1.2s ✓
最小检索时间: 0.6s ✓
```

## 错误处理

示例包含了完整的错误处理机制：

```python
try:
    # 文档处理逻辑
    result = await processor.transform(documents, rule)
except ProcessingError as e:
    logger.error(f"文档处理失败: {str(e)}")
    return {"status": "error", "error": str(e)}
except Exception as e:
    logger.error(f"未知错误: {str(e)}")
    return {"status": "error", "error": "系统错误"}
```

## 常见问题

### Q1: 如何处理大文档？
A: 使用批量处理和并发配置：
```python
config = ProcessorConfig(
    max_concurrent_tasks=10,
    enable_parallel=True,
    batch_size=50
)
```

### Q2: 如何优化检索性能？
A: 调整分割参数和缓存配置：
```python
rule = Rule(
    max_tokens=1000,  # 适中的块大小
    chunk_overlap=200,  # 适当的重叠
    separator="\n"  # 合适的分隔符
)
```

### Q3: 如何监控系统性能？
A: 使用内置的性能监控功能：
```python
memory_info = example._monitor_memory_usage()
performance_result = await example._run_performance_benchmark()
```

## 扩展开发

### 添加新的处理器类型

1. 继承BaseIndexProcessor
2. 实现必要的方法
3. 在工厂中注册新类型

```python
class CustomIndexProcessor(BaseIndexProcessor):
    def extract(self, extract_setting, **kwargs):
        # 自定义提取逻辑
        pass
    
    def transform(self, documents, **kwargs):
        # 自定义转换逻辑
        pass

# 在工厂中注册
factory.register_processor(ProcessorType.CUSTOM, CustomIndexProcessor)
```

### 添加新的配置选项

```python
@dataclass
class CustomConfig:
    custom_param: str = "default_value"
    custom_threshold: float = 0.8
```

## 贡献指南

1. 遵循项目的代码规范
2. 添加适当的文档字符串
3. 确保测试覆盖率 > 70%
4. 运行所有测试确保通过

```bash
# 运行代码质量检查
flake8 examples/
black examples/

# 运行测试
pytest examples/ --cov=examples --cov-report=term-missing
```

## 许可证

本示例代码遵循项目的开源许可证。
