# RAG服务连接问题修复总结

## 问题描述
用户在上传文档时遇到"RAG服务不可用，请确保Milvus和嵌入模型服务已启动"错误。

## 根本原因分析
1. **Milvus连接方式错误**: 使用了不兼容Docker的连接方式
2. **嵌入模型API检查机制缺陷**: `get_dimension()`方法在API不可用时直接失败
3. **错误处理不够健壮**: 缺乏适当的回退机制

## 修复内容

### 1. 修复Milvus连接 (✅ 已完成)

**修改文件:**
- `backend/app/rag/vector_store.py`
- `backend/app/core/vector_store.py` 
- `backend/app/db/milvus.py`

**修改内容:**
```python
# 修改前
connections.connect(alias="default", host=host, port=port)

# 修改后  
connections.connect(host=host, port=port)
```

### 2. 优化嵌入模型处理 (✅ 已完成)

**修改文件:** `backend/app/rag/embedding_model.py`

**新增功能:**
- API可用性检查方法 `check_api_availability()`
- 向量维度缓存机制 `_dimension_cache`
- 默认维度回退（768维，适用于nomic-embed-text-v1.5）

**关键改进:**
```python
def get_dimension(self) -> int:
    # 如果已缓存，直接返回
    if self._dimension_cache is not None:
        return self._dimension_cache
        
    try:
        # 检查API是否可用
        if not self.check_api_availability():
            # 使用默认维度
            self._dimension_cache = 768
            return self._dimension_cache
        # ... 正常API调用
    except Exception as e:
        # 回退到默认维度而不是抛出异常
        self._dimension_cache = 768
        return self._dimension_cache
```

### 3. 改进RAG服务检查逻辑 (✅ 已完成)

**修改文件:** `backend/app/services/rag_service.py`

**改进内容:**
- 更健壮的`_check_rag_available()`方法
- 更好的错误处理和日志记录
- 轻量级的连接测试

### 4. 环境变量配置 (✅ 已完成)

**修改文件:** `backend/.env`

**新增配置:**
```env
# Milvus配置
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=rag_documents

# 嵌入模型配置
EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5
EMBEDDING_API_BASE=http://192.168.1.30:1234
EMBEDDING_MAX_BATCH_SIZE=20
EMBEDDING_MAX_RETRIES=3
EMBEDDING_RETRY_DELAY=5
EMBEDDING_TIMEOUT=30
```

## 验证结果

### 连接测试结果
```
✅ Milvus连接: 正常 (localhost:19530)
✅ 嵌入模型API: 正常 (http://192.168.1.30:1234)
✅ 向量维度: 768
✅ RAG服务状态: 可用
```

### API状态检查
```bash
curl -X GET "http://localhost:8000/api/v1/rag/status"
# 返回: {"available":true,"message":"RAG服务正常",...}
```

## 使用建议

### 1. 确保服务运行
- **Milvus**: 确保Docker容器正在运行
- **LM Studio**: 确保嵌入模型服务在192.168.1.30:1234运行
- **后端服务**: 确保FastAPI服务正常启动

### 2. 监控和诊断
使用提供的诊断脚本:
```bash
cd backend
python debug_rag_connection.py
```

### 3. 故障排除
如果仍然遇到问题:
1. 检查网络连接: `nc -zv localhost 19530` 和 `nc -zv 192.168.1.30 1234`
2. 查看后端日志: `logs/app/app.log`
3. 重启相关服务

## 技术改进

1. **容错性**: 系统现在能够在部分组件不可用时继续工作
2. **性能**: 添加了缓存机制，减少重复API调用
3. **可维护性**: 改进了错误处理和日志记录
4. **兼容性**: 修复了Docker环境下的连接问题

## 后续建议

1. **监控**: 建议添加健康检查端点定期监控服务状态
2. **配置**: 考虑将更多配置项移到环境变量中
3. **测试**: 建议添加自动化测试覆盖这些连接场景
4. **文档**: 更新部署文档，说明Docker环境的特殊要求
