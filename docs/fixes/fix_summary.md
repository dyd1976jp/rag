# RAG 文档上传错误修复总结

## 问题描述

用户在使用 RAG 文档上传 API 时遇到了 `AttributeError: 'DocumentProcessor' object has no attribute 'use_cache'` 错误。

## 根本原因分析

通过代码分析发现了以下问题：

### 1. DocumentProcessor 类缺少必要属性
- `use_cache` 属性未定义，但在 `clean_document` 方法中被引用
- `min_content_length` 属性未定义，但在 `validate_document` 方法中被引用
- `stop_words` 和 `punctuation_translator` 属性未定义，但在 `extract_keywords` 方法中被引用

### 2. Document 类不一致性
- `app.rag.document_processor.py` 中定义了简单的 Document 类
- `app.rag.models.py` 中定义了 Pydantic Document 类（带 source 属性）
- API 端点使用 Pydantic Document 类，但 DocumentProcessor 期望简单的 Document 类

### 3. API 响应模型不匹配
- 预览模式返回的字段与 `DocumentUploadResponse` 模型不匹配

## 修复方案

### 1. 修复 DocumentProcessor 类
在 `backend/app/rag/document_processor.py` 中：

```python
def __init__(self):
    """初始化文档处理器"""
    self.max_content_length = int(os.environ.get("DOC_MAX_CONTENT_LENGTH", "100000"))
    self.min_content_length = int(os.environ.get("DOC_MIN_CONTENT_LENGTH", "10"))
    self.cache_enabled = os.environ.get("DOC_CACHE_ENABLED", "true").lower() == "true"
    self.use_cache = self.cache_enabled  # 为了向后兼容，添加这个别名
    self.cache_dir = os.environ.get("DOC_CACHE_DIR", "data/cache")
    
    # 初始化停用词和标点符号翻译器
    self.stop_words = set(['的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'])
    self.punctuation_translator = str.maketrans('', '', string.punctuation + '，。！？；：""''（）【】《》')
```

### 2. 统一 Document 类使用
将 `DocumentProcessor` 修改为使用正确的 Pydantic Document 类：

```python
from .models import Document  # 使用正确的 Pydantic Document 类
```

### 3. 修复 API 响应模型
移除严格的响应模型限制，允许预览模式返回额外字段：

```python
@router.post("/documents/upload")  # 移除 response_model=DocumentUploadResponse
```

### 4. 修复 Document 构造函数调用
移除不存在的 `source` 参数：

```python
document = Document(
    page_content=content,
    metadata={
        "source": file.filename if file else "direct_input",
        "created_at": datetime.now().isoformat(),
        "doc_id": str(uuid.uuid4()),
        "document_id": str(uuid.uuid4())
    }
)
```

## 测试结果

修复后的测试结果：

### 预览模式测试 ✅
```bash
curl -X POST 'http://localhost:8000/api/v1/rag/documents/preview-split' \
  -H 'Authorization: Bearer [TOKEN]' \
  -F 'file=@/Users/tei/go/RAG-chat/data/uploads/初赛训练数据集.pdf' \
  -F 'parent_chunk_size=1024' \
  -F 'parent_chunk_overlap=200' \
  -F 'parent_separator=\n\n' \
  -F 'child_chunk_size=512' \
  -F 'child_chunk_overlap=50' \
  -F 'child_separator=\n'
```

**结果**: 成功返回文档分割预览，包含父子文档结构

### 文档上传预览模式测试 ✅
```bash
curl -X POST 'http://localhost:8000/api/v1/rag/documents/upload' \
  -H 'Authorization: Bearer [TOKEN]' \
  -F 'file=@/Users/tei/go/RAG-chat/data/uploads/初赛训练数据集.pdf' \
  -F 'preview_only=true' \
  [其他参数...]
```

**结果**: 成功返回 `{"success": true, "message": "文档预览成功"}`

### 实际上传模式测试 ⚠️
实际上传模式失败，但这是预期的，因为需要 Milvus 和嵌入模型服务：
```
"RAG服务不可用，请确保Milvus和嵌入模型服务已启动"
```

## 修复的文件列表

1. `backend/app/rag/document_processor.py` - 修复 DocumentProcessor 类
2. `backend/app/api/v1/endpoints/rag.py` - 修复 API 端点和 Document 构造

## 验证步骤

1. ✅ DocumentProcessor 初始化不再报错
2. ✅ 文档清洗功能正常工作
3. ✅ 预览分割功能正常工作
4. ✅ 文档上传预览模式正常工作
5. ⚠️ 实际上传需要外部服务（Milvus + 嵌入模型）

## 结论

所有与 DocumentProcessor 相关的错误已修复。文档上传的预览功能现在可以正常工作。实际上传功能需要启动 Milvus 向量数据库和嵌入模型服务才能完全测试。
