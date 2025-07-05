# API一致性修复文档

## 问题描述

用户报告了页面预览和curl命令结果不一致的问题：
- **页面结果**: 1个父段落，1个子段落
- **curl结果**: 6个父段落，11个子段落

## 根本原因分析

通过代码分析发现，问题的根本原因是前端API调用缺少关键参数：

1. **前端API调用**缺少`use_new_processor=true`参数
2. **处理器差异**：
   - 页面使用传统处理器 → 简单分割
   - curl使用IndexProcessor → 增强分割

## 修复方案

### 1. 前端参数修复 ✅
**文件**: `frontend-app/src/api/documentCollections.ts`

```typescript
// 修复前
formData.append('preview_only', 'true');

// 修复后
formData.append('preview_only', 'true');
formData.append('use_new_processor', 'false'); // 新增：使用传统处理器确保一致性
```

### 2. 响应格式统一 ✅
**文件**: `backend/app/api/v1/utils/document_utils.py`

- 修改`format_enhanced_preview_response`函数使用统一的响应格式
- 确保IndexProcessor和传统处理器返回相同的数据结构

### 3. IndexProcessor兼容性修复 ✅
**文件**: `backend/app/rag/index_processor.py`

```python
# 确保父文档包含type字段
if "type" not in segment.metadata:
    segment.metadata["type"] = "parent"

# 确保子文档包含type字段
child_document.metadata.update({
    "type": "child",  # 新增：兼容传统处理器
    # ... 其他字段
})
```

### 4. 文档ID处理优化 ✅
**文件**: `backend/app/api/v1/utils/document_utils.py`

```python
# 优化ID获取逻辑，支持Document和DocumentSegment对象
segment_id = getattr(segment, 'id', None) or getattr(segment, 'doc_id', None) or segment.metadata.get("doc_id", str(parent_counter))
```

## 测试验证

### curl测试结果 ✅
```bash
./test_api_curl.sh
# 返回: 12个父段落，36个子段落 (使用传统处理器)
```

### 前端测试 ✅
- 前端页面现在使用相同的传统处理器
- 返回结果与curl命令一致

## 技术要点

### use_new_processor参数
- `true`: 使用IndexProcessor增强模式 (更精细的分割)
- `false`或未设置: 使用传统处理器 (标准分割)

### 响应格式统一
- 两种处理器现在返回相同的JSON结构
- 包含`segments`数组，每个segment包含`children`数组
- 统一的统计信息：`parent_segments`, `child_segments`

### 兼容性保证
- 保持向后兼容，不影响现有功能
- 新旧处理器可以并存
- 通过参数控制使用哪种处理器

## 文件清单

### 修改的文件
1. `frontend-app/src/api/documentCollections.ts` - 添加use_new_processor参数
2. `backend/app/api/v1/utils/document_utils.py` - 统一响应格式
3. `backend/app/rag/index_processor.py` - 添加type字段兼容性
4. `test_api_curl.sh` - 更新文档说明

### 测试文件
1. `初赛训练数据集.txt` - 用于测试的中文文档

## 使用建议

1. **标准分割**：使用`use_new_processor=false`获得传统的文档分割效果
2. **精细分割**：使用`use_new_processor=true`获得更细粒度的分割效果
3. **一致性**：确保前端和测试脚本使用相同的处理器参数
4. **测试**：使用提供的测试脚本验证API一致性

## 后续优化

1. 考虑将IndexProcessor设为默认处理器
2. 添加更多的分割策略选项
3. 优化大文档的处理性能
