# 父子分块独立编号机制

## 概述

本文档描述了RAG系统中父子分块的独立编号机制，该机制确保了文档结构的清晰性，便于后续的检索和引用。

## 编号规则

### 1. 父块编号
- **独立序列**：父块拥有自己独立的编号序列（1, 2, 3, ...）
- **连续性**：父块编号必须是连续的，不允许跳跃
- **唯一性**：在同一个文档中，每个父块都有唯一的编号

### 2. 子块编号
- **父块内独立**：子块编号在每个父块内部独立计算
- **重置机制**：每个父块内的子块编号都从1开始重新计数
- **连续性**：同一父块内的子块编号必须连续

### 3. 组合编号格式
- **格式**：`父块编号-子块编号`（如：1-1, 1-2, 1-3, 2-1, 2-2, ...）
- **唯一性**：组合编号在整个文档中是唯一的
- **层级关系**：清晰表示子块归属于哪个父块

## 元数据字段

### 父块元数据
```python
{
    "type": "parent",
    "index": 1,              # 兼容性字段，保持原有逻辑
    "parent_number": 1,      # 新增：父块编号
    "id": "uuid",
    "source": "document.txt",
    "original_doc_id": "doc_uuid",
    "doc_hash": "hash_value"
}
```

### 子块元数据
```python
{
    "type": "child",
    "index": 1,              # 兼容性字段，保持原有逻辑
    "parent_id": "parent_uuid",
    "parent_number": 1,      # 父块编号
    "child_number": 1,       # 子块编号（父块内独立）
    "combined_number": "1-1", # 组合编号格式
    "id": "uuid",
    "source": "document.txt",
    "original_doc_id": "doc_uuid",
    "doc_hash": "hash_value"
}
```

## 实现示例

### 编号分配过程

```python
# 父块编号分配
for i, parent_content in enumerate(parent_nodes):
    parent_number = i + 1  # 父块独立编号
    
    # 子块编号分配（每个父块内重新开始）
    for j, child_content in enumerate(child_nodes):
        child_number = j + 1  # 子块编号从1开始
        combined_number = f"{parent_number}-{child_number}"
```

### 编号验证规则

1. **父块编号连续性验证**
```python
parent_numbers = [p.metadata.get("parent_number") for p in parent_segments]
parent_numbers.sort()
expected = list(range(1, len(parent_segments) + 1))
assert parent_numbers == expected
```

2. **子块编号重置验证**
```python
for parent in parent_segments:
    related_children = get_children_by_parent_id(parent.id)
    child_numbers = [c.metadata.get("child_number") for c in related_children]
    child_numbers.sort()
    expected = list(range(1, len(related_children) + 1))
    assert child_numbers == expected
```

3. **组合编号格式验证**
```python
for child in child_segments:
    parent_number = child.metadata.get("parent_number")
    child_number = child.metadata.get("child_number")
    combined_number = child.metadata.get("combined_number")
    expected = f"{parent_number}-{child_number}"
    assert combined_number == expected
```

## 使用场景

### 1. 文档检索
- 通过组合编号快速定位特定的子块
- 根据父块编号获取相关的所有子块
- 维护检索结果的层级关系

### 2. 引用和引证
- 精确引用特定的文档片段
- 提供清晰的文档结构导航
- 支持层级化的内容组织

### 3. 调试和日志
- 清晰的编号便于调试和问题定位
- 日志中可以精确标识文档片段
- 便于跟踪文档处理过程

## 兼容性

### 向后兼容
- 保留原有的 `index` 字段，确保现有代码不受影响
- 新增字段不会破坏现有的数据结构
- 现有的检索逻辑可以继续正常工作

### 渐进式升级
- 可以逐步迁移到新的编号机制
- 支持新旧编号机制并存
- 提供迁移工具和验证机制

## 测试验证

### 单元测试
- 编号分配正确性测试
- 编号规则验证测试
- 兼容性测试

### 集成测试
- 完整文档分割流程测试
- 多文档处理测试
- 性能测试

### 示例测试结果
```
=== 集成编号系统测试结果 ===
父块数量: 4
子块数量: 12

父块 1: ID=d6a7f7aa...
  对应子块数量: 3
    子块 1 (编号: 1-1): ID=fdc51dc7...
    子块 2 (编号: 1-2): ID=00a375a3...
    子块 3 (编号: 1-3): ID=ec960c27...

父块 2: ID=c90e5f41...
  对应子块数量: 4
    子块 1 (编号: 2-1): ID=8420bfa1...
    子块 2 (编号: 2-2): ID=6842e76e...
    子块 3 (编号: 2-3): ID=8dcd262b...
    子块 4 (编号: 2-4): ID=f5bfe89b...

✅ 所有集成编号规则验证通过
```

## 总结

父子分块独立编号机制提供了：

1. **清晰的层级结构**：明确的父子关系和编号体系
2. **独立的编号序列**：父块和子块各自独立的编号机制
3. **重置机制**：子块编号在每个父块内重新开始
4. **组合编号格式**：便于引用和检索的统一格式
5. **向后兼容性**：不破坏现有系统的兼容性设计

这个编号机制确保了文档结构的清晰性，便于后续的检索、引用和维护工作。
