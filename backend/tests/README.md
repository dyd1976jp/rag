# RAG系统测试

本目录包含RAG系统的测试代码。

## 测试结构

- `services/`: 服务层测试
  - `test_cache_service.py`: Redis缓存服务测试
  - `test_retrieval_service.py`: 检索服务测试
  - `test_embedding_model.py`: 嵌入模型测试
  - `test_custom_exceptions.py`: 自定义异常测试
- `rag/`: RAG系统功能测试
  - `test_rag.py`: RAG整体功能测试
  - `test_milvus.py`: Milvus集合测试
  - `test_search.py`: 文档搜索功能测试
  - `test_dataset_id.py`: 数据集ID查询测试
  - `test_rag_status.py`: RAG服务状态测试

## 运行测试

使用以下命令运行所有测试:

```bash
python run_rag_tests.py
```

### 运行特定测试

运行缓存服务测试:

```bash
python run_rag_tests.py --cache
```

运行嵌入模型测试:

```bash
python run_rag_tests.py --embedding
```

运行检索服务测试:

```bash
python run_rag_tests.py --retrieval
```

运行异常处理测试:

```bash
python run_rag_tests.py --exceptions
```

运行RAG功能测试:

```bash
python run_rag_tests.py --test-path rag/
```

### 生成覆盖率报告

```bash
python run_rag_tests.py --coverage
```

覆盖率报告将生成在`coverage_html`目录中。

### 并行运行测试

```bash
python run_rag_tests.py --parallel
```

## 测试依赖

测试依赖项列在`requirements.txt`文件中。安装依赖:

```bash
pip install -r requirements.txt
``` 