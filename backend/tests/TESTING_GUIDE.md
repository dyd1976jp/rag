# RAG系统测试指南

本指南提供了在RAG系统中编写和维护测试的详细说明和最佳实践。

## 🎯 测试原则

### 1. 测试金字塔
```
    /\
   /  \    E2E Tests (少量)
  /____\
 /      \   Integration Tests (适量)
/__________\  Unit Tests (大量)
```

- **单元测试 (70%)**：快速、独立、专注于单个组件
- **集成测试 (20%)**：测试组件间交互
- **端到端测试 (10%)**：测试完整用户流程

### 2. FIRST 原则
- **Fast**: 测试应该快速运行
- **Independent**: 测试之间应该独立
- **Repeatable**: 测试结果应该可重复
- **Self-Validating**: 测试应该有明确的通过/失败结果
- **Timely**: 测试应该及时编写

## 📝 编写测试

### 测试命名规范
```python
def test_should_return_empty_list_when_no_documents_found():
    """
    测试模式：test_should_[期望行为]_when_[条件]
    
    这种命名方式清楚地表达了：
    - 测试的期望结果
    - 触发条件
    """
    pass
```

### 测试结构 (AAA模式)
```python
def test_cache_service_stores_and_retrieves_data():
    """测试缓存服务存储和检索数据"""
    # Arrange - 准备测试数据和环境
    cache_service = CacheService()
    test_data = {"key": "value"}
    cache_key = "test_key"
    
    # Act - 执行被测试的操作
    cache_service.set(cache_key, test_data)
    result = cache_service.get(cache_key)
    
    # Assert - 验证结果
    assert result == test_data
```

### 使用 Fixtures
```python
@pytest.fixture
def sample_documents():
    """提供测试文档数据"""
    return [
        Document(page_content="文档1", metadata={"id": "1"}),
        Document(page_content="文档2", metadata={"id": "2"})
    ]

@pytest.fixture
def mock_embedding_service():
    """提供模拟的嵌入服务"""
    with patch('app.services.embedding_service') as mock:
        mock.embed_query.return_value = [0.1, 0.2, 0.3]
        yield mock
```

## 🏷️ 测试标记

### 使用标记分类测试
```python
@pytest.mark.unit
@pytest.mark.services
def test_user_service_create_user():
    """单元测试：用户服务创建用户"""
    pass

@pytest.mark.integration
@pytest.mark.api
def test_api_workflow():
    """集成测试：API工作流"""
    pass

@pytest.mark.slow
@pytest.mark.performance
def test_large_document_processing():
    """性能测试：大文档处理"""
    pass
```

### 跳过测试
```python
@pytest.mark.skip(reason="功能尚未实现")
def test_future_feature():
    pass

@pytest.mark.skipif(sys.version_info < (3, 8), reason="需要Python 3.8+")
def test_python38_feature():
    pass
```

## 🎭 Mock 和 Patch

### Mock 外部依赖
```python
def test_document_processor_with_mock_embedding():
    """测试文档处理器（使用模拟嵌入服务）"""
    with patch('app.services.embedding_service') as mock_embedding:
        # 配置模拟对象
        mock_embedding.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]
        
        # 执行测试
        processor = DocumentProcessor()
        result = processor.process_documents(["文档1", "文档2"])
        
        # 验证模拟对象被正确调用
        mock_embedding.embed_documents.assert_called_once_with(["文档1", "文档2"])
        assert len(result) == 2
```

### 使用 MagicMock
```python
def test_retrieval_service_with_magic_mock():
    """使用 MagicMock 测试检索服务"""
    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [
        Document(page_content="结果1", metadata={"score": 0.9}),
        Document(page_content="结果2", metadata={"score": 0.8})
    ]
    
    service = RetrievalService(vector_store=mock_vector_store)
    results = service.search("查询")
    
    assert len(results) == 2
    assert results[0].metadata["score"] == 0.9
```

## 🔄 异步测试

### 测试异步函数
```python
@pytest.mark.asyncio
async def test_async_document_processing():
    """测试异步文档处理"""
    processor = AsyncDocumentProcessor()
    
    # 测试异步方法
    result = await processor.process_async("文档内容")
    
    assert result is not None
    assert result.status == "processed"
```

### 异步 Mock
```python
@pytest.mark.asyncio
async def test_async_service_with_mock():
    """测试异步服务（使用模拟）"""
    with patch('app.services.async_service') as mock_service:
        # 配置异步模拟
        mock_service.process_async.return_value = AsyncMock(return_value="结果")
        
        service = MyAsyncService()
        result = await service.call_external_service()
        
        assert result == "结果"
```

## 📊 测试数据管理

### 使用测试数据生成器
```python
# tests/utils/data_generators.py
class DocumentGenerator:
    @staticmethod
    def create_simple_document(content="测试内容"):
        return Document(
            page_content=content,
            metadata={"source": "test", "created_at": datetime.now()}
        )
    
    @staticmethod
    def create_document_batch(count=5):
        return [
            DocumentGenerator.create_simple_document(f"文档{i}")
            for i in range(count)
        ]
```

### 使用 Fixtures 管理测试数据
```python
@pytest.fixture
def test_documents():
    """提供标准测试文档集合"""
    return DocumentGenerator.create_document_batch(3)

@pytest.fixture
def large_document():
    """提供大文档用于性能测试"""
    content = "测试内容 " * 1000
    return DocumentGenerator.create_simple_document(content)
```

## 🚨 错误和异常测试

### 测试异常处理
```python
def test_service_raises_exception_on_invalid_input():
    """测试服务在无效输入时抛出异常"""
    service = DocumentService()
    
    with pytest.raises(ValueError, match="输入不能为空"):
        service.process_document("")

def test_service_handles_external_api_error():
    """测试服务处理外部API错误"""
    with patch('requests.post') as mock_post:
        mock_post.side_effect = requests.RequestException("网络错误")
        
        service = ExternalAPIService()
        
        # 验证服务正确处理异常
        with pytest.raises(ServiceError):
            service.call_external_api()
```

## 🔍 调试测试

### 使用调试输出
```python
def test_with_debug_output():
    """带调试输出的测试"""
    import logging
    logger = logging.getLogger(__name__)
    
    # 在测试中添加日志
    logger.info("开始测试")
    
    result = some_function()
    
    # 使用 print 进行简单调试（运行时使用 -s 选项）
    print(f"结果: {result}")
    
    assert result is not None
```

### 使用断点调试
```python
def test_with_breakpoint():
    """使用断点调试的测试"""
    data = prepare_test_data()
    
    # 在需要调试的地方设置断点
    breakpoint()  # Python 3.7+
    
    result = process_data(data)
    assert result is not None
```

## 📈 性能测试

### 测试执行时间
```python
import time

def test_function_performance():
    """测试函数性能"""
    start_time = time.time()
    
    # 执行被测试的操作
    result = expensive_operation()
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # 验证执行时间在可接受范围内
    assert execution_time < 5.0, f"执行时间过长: {execution_time}秒"
    assert result is not None
```

### 内存使用测试
```python
import psutil
import os

def test_memory_usage():
    """测试内存使用"""
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # 执行可能消耗大量内存的操作
    result = process_large_dataset()
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # 验证内存增长在合理范围内
    assert memory_increase < 100 * 1024 * 1024, "内存使用过多"  # 100MB
```

## 🔧 测试配置

### 环境特定配置
```python
# conftest.py
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境"""
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    # 设置测试数据库
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    yield
    
    # 清理环境
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
```

## 📋 测试检查清单

在提交代码前，确保：

- [ ] 所有新功能都有对应的测试
- [ ] 测试覆盖率达到要求（>80%）
- [ ] 所有测试都能通过
- [ ] 测试名称清晰描述测试内容
- [ ] 使用了适当的测试标记
- [ ] Mock了所有外部依赖
- [ ] 测试是独立的，不依赖其他测试
- [ ] 添加了必要的文档字符串
- [ ] 遵循了项目的测试规范

---

遵循这些指南将帮助您编写高质量、可维护的测试代码，确保RAG系统的稳定性和可靠性。
