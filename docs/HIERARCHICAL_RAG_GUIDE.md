# 层次化RAG架构使用指南

## 概述

本项目现在支持基于Dify架构设计的层次化RAG系统，提供更高效的文档处理和检索性能。

## 核心特性

### 1. 分离式存储架构
- **父段落**: 存储在MongoDB，提供丰富上下文
- **子块**: 部分元数据存储在MongoDB，向量存储在Milvus
- **高效检索**: 仅对子块进行向量搜索，然后聚合到父段落

### 2. 灵活的分割策略
- **段落模式**: 将文档分割为多个父段落，每个父段落包含多个子块
- **全文档模式**: 整个文档作为单一父段落，分割为多个子块
- **智能分割**: 根据内容类型自动优化分割策略

### 3. 高级检索机制
- **子块精确搜索**: 在小粒度子块中进行精确匹配
- **父段落上下文**: 提供更丰富的上下文信息
- **结果聚合**: 按父段落聚合相关子块，避免重复

## 快速开始

### 1. 环境配置

复制配置模板：
```bash
cp .env.hierarchical.example .env.hierarchical
```

编辑配置文件：
```bash
# 启用层次化RAG
ENABLE_HIERARCHICAL_RAG=true

# 基本配置
HIERARCHICAL_PARENT_MODE=paragraph
HIERARCHICAL_PARENT_CHUNK_SIZE=1000
HIERARCHICAL_CHILD_CHUNK_SIZE=300
```

### 2. 数据库迁移

运行迁移脚本：
```bash
# 创建层次化存储的集合和索引
python scripts/database/migrate_to_hierarchical.py --create-collections

# 检查现有数据
python scripts/database/migrate_to_hierarchical.py --check-data

# 验证迁移结果
python scripts/database/migrate_to_hierarchical.py --validate
```

### 3. API使用

#### 层次化文档上传
```bash
curl -X POST "http://localhost:8000/api/v1/rag/documents/upload-hierarchical" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf" \
  -F "parent_mode=paragraph" \
  -F "parent_chunk_size=1000" \
  -F "child_chunk_size=300"
```

#### 层次化搜索
```bash
curl -X POST "http://localhost:8000/api/v1/rag/documents/search-hierarchical" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "搜索内容",
    "top_k": 5,
    "search_all": false
  }'
```

#### 获取文档层次结构
```bash
curl -X GET "http://localhost:8000/api/v1/rag/documents/{doc_id}/hierarchy" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 配置详解

### 父段落配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `parent_mode` | `paragraph` | 父段落模式 (`paragraph`/`full_doc`) |
| `parent_chunk_size` | `1000` | 父段落最大大小 |
| `parent_chunk_overlap` | `100` | 父段落重叠大小 |

### 子块配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `child_chunk_size` | `300` | 子块最大大小 |
| `child_chunk_overlap` | `50` | 子块重叠大小 |
| `min_child_chunk_size` | `50` | 最小子块大小 |

### 索引配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `index_child_chunks_only` | `true` | 仅索引子块到向量数据库 |
| `enable_parent_context` | `true` | 启用父段落上下文 |

## 内容类型优化

系统支持根据内容类型自动优化分割策略：

- **academic**: 学术文档，长段落，复杂句式
- **news**: 新闻文章，标准段落结构
- **dialogue**: 对话内容，问答格式
- **code**: 代码文档，特殊分隔符
- **legal**: 法律文档，特定标点符号

## 性能优化建议

### 1. 文档大小控制
- 单个文档建议不超过100MB
- 对于大文档，建议预先分割

### 2. 分块参数调优
- **父段落大小**: 根据文档类型调整，学术文档可适当增大
- **子块大小**: 根据查询粒度调整，精确查询可适当减小
- **重叠大小**: 保持语义连续性，通常为块大小的10-20%

### 3. 批处理优化
- 批量上传时调整 `HIERARCHICAL_BATCH_SIZE`
- 根据系统资源调整并发数量

## 数据库架构

### MongoDB集合结构

#### documents
```javascript
{
  "_id": ObjectId,
  "id": "doc_uuid",
  "file_name": "document.pdf",
  "user_id": "user_uuid",
  "processing_method": "hierarchical",
  "status": "ready",
  "hierarchical_config": { ... },
  "created_at": ISODate
}
```

#### document_segments
```javascript
{
  "_id": ObjectId,
  "id": "segment_uuid",
  "document_id": "doc_uuid",
  "dataset_id": "user_uuid",
  "content": "父段落内容",
  "position": 0,
  "word_count": 500,
  "child_count": 3,
  "hit_count": 0,
  "created_at": ISODate
}
```

#### child_chunks
```javascript
{
  "_id": ObjectId,
  "id": "chunk_uuid",
  "segment_id": "segment_uuid",
  "document_id": "doc_uuid",
  "dataset_id": "user_uuid",
  "content": "子块内容",
  "position": 0,
  "index_node_id": "vector_db_id",
  "word_count": 150,
  "created_at": ISODate
}
```

### 索引策略

```javascript
// document_segments
db.document_segments.createIndex({"id": 1}, {unique: true})
db.document_segments.createIndex({"document_id": 1, "position": 1})
db.document_segments.createIndex({"dataset_id": 1})

// child_chunks  
db.child_chunks.createIndex({"id": 1}, {unique: true})
db.child_chunks.createIndex({"segment_id": 1, "position": 1})
db.child_chunks.createIndex({"index_node_id": 1, "dataset_id": 1})
```

## 故障排除

### 1. 迁移问题
```bash
# 检查数据完整性
python scripts/database/migrate_to_hierarchical.py --validate

# 重新创建索引
python scripts/database/migrate_to_hierarchical.py --create-collections
```

### 2. 性能问题
- 检查MongoDB索引使用情况
- 调整批处理大小
- 优化分块参数

### 3. 搜索质量问题
- 调整分数阈值
- 优化分块大小
- 检查内容类型设置

## 监控和日志

### 关键指标
- 文档处理时间
- 搜索响应时间
- 索引大小
- 命中率统计

### 日志配置
```bash
# 启用详细日志
HIERARCHICAL_DEBUG_LOGGING=true
HIERARCHICAL_LOG_LEVEL=DEBUG
```

## 版本兼容性

- 新旧架构可以并存
- 渐进式迁移策略
- 向后兼容原有API

## 最佳实践

1. **文档预处理**: 清理格式，统一编码
2. **参数调优**: 根据具体用例调整分块参数
3. **批量处理**: 使用批量上传提高效率
4. **监控优化**: 定期检查性能指标
5. **数据备份**: 定期备份重要数据

## 开发扩展

### 自定义处理器
```python
from app.rag.hierarchical_processor import HierarchicalDocumentProcessor
from app.rag.models import HierarchicalSplittingConfig

# 创建自定义配置
config = HierarchicalSplittingConfig(
    parent_mode="paragraph",
    parent_chunk_size=1200,
    child_chunk_size=400
)

# 使用自定义处理器
processor = HierarchicalDocumentProcessor(config)
```

### 自定义检索器
```python
from app.rag.hierarchical_retriever import HierarchicalRetrievalService

# 初始化检索器
retriever = HierarchicalRetrievalService(vector_store, embedding_model)

# 执行检索
results = await retriever.retrieve_with_parent_context(
    query="搜索内容",
    dataset_id="user_id",
    top_k=5
)
```

## 联系支持

如有问题或建议，请：
1. 查看日志文件
2. 检查配置参数
3. 提交Issue到项目仓库