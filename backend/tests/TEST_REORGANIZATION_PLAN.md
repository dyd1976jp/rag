# 测试重组计划

## 当前测试文件分析

### 🔍 发现的问题
1. **重复测试文件**: 多个功能相似的测试脚本
2. **分散的测试**: 同类测试分布在不同目录
3. **命名不规范**: 测试文件命名不一致
4. **缺少测试数据管理**: 测试数据分散

### 📊 测试文件分类

#### 1. 文档分割相关测试 (重复度高)
**需要合并的文件:**
- `integration/test_document_split_fix.py` - 文档分割修复测试
- `integration/test_document_split_consistency.py` - 分割一致性测试
- `integration/test_splitter_fix.py` - 分割器修复测试
- `integration/test_splitter_debug.py` - 分割器调试测试
- `services/document_processing/test_document_splitter.py` - 文档分割器单元测试

**合并目标:** `tests/unit/test_document_splitter.py` + `tests/integration/test_document_processing.py`

#### 2. API端点测试 (重复度中)
**需要合并的文件:**
- `integration/test_api_fix.py` - API修复测试
- `integration/test_simple_api.py` - 简单API测试
- `api/test_llm_api.py` - LLM API测试
- `test_llm_endpoints.py` - LLM端点测试

**合并目标:** `tests/integration/test_api_endpoints.py`

#### 3. 模型发现测试 (重复度高)
**需要合并的文件:**
- `test_discover.py` - 发现接口测试
- `test_discover_endpoints.py` - 发现端点测试
- `discover/test_api.py` - 发现API测试
- `discover/test_service.py` - 发现服务测试
- `discover/test_discover_client.py` - 发现客户端测试

**合并目标:** `tests/unit/test_llm_discovery.py` + `tests/integration/test_discovery_api.py`

#### 4. 验证和修复测试 (功能重复)
**已整理的文件:**
- `backend/debug/verify_fix.py` - 修复验证（已移动到debug目录）
- `backend/debug/final_verification.py` - 最终验证测试（已移动到debug目录）
- `integration/test_pdf_detailed.py` - PDF详细测试

**处理方案:** 保留核心功能，移除重复验证

### 🎯 重组目标结构

```
tests/
├── unit/                           # 单元测试
│   ├── test_document_processor.py  # 文档处理器测试
│   ├── test_document_splitter.py   # 文档分割器测试
│   ├── test_llm_discovery.py       # LLM发现功能测试
│   ├── test_embedding_model.py     # 嵌入模型测试
│   └── test_user_service.py        # 用户服务测试
├── integration/                    # 集成测试
│   ├── test_api_endpoints.py       # API端点集成测试
│   ├── test_document_processing.py # 文档处理集成测试
│   ├── test_discovery_api.py       # 发现API集成测试
│   └── test_rag_workflow.py        # RAG工作流测试
├── fixtures/                       # 测试数据
│   ├── documents/                  # 测试文档
│   ├── responses/                  # 模拟响应
│   └── configs/                    # 测试配置
├── utils/                          # 测试工具
│   ├── test_helpers.py             # 测试辅助函数
│   ├── mock_services.py            # 模拟服务
│   └── data_generators.py          # 测试数据生成器
└── conftest.py                     # pytest配置
```

### 📋 执行计划

#### 阶段1: 创建新的测试结构
1. 创建标准化的测试目录结构
2. 创建测试工具和辅助函数
3. 建立测试数据管理

#### 阶段2: 合并重复测试
1. 合并文档分割相关测试
2. 合并API端点测试
3. 合并模型发现测试

#### 阶段3: 优化测试质量
1. 统一测试命名规范
2. 添加测试文档和注释
3. 提高测试覆盖率

#### 阶段4: 清理和验证
1. 删除重复的测试文件
2. 运行完整测试套件验证
3. 更新测试文档

### 🔧 测试标准

#### 命名规范
- 单元测试: `test_<module_name>.py`
- 集成测试: `test_<feature_name>_integration.py`
- 测试函数: `test_should_<expected_behavior>_when_<condition>()`

#### 测试结构
```python
class TestDocumentSplitter:
    """文档分割器测试类"""
    
    def setup_method(self):
        """每个测试方法前的准备"""
        pass
    
    def test_should_split_document_when_valid_input_provided(self):
        """测试：提供有效输入时应正确分割文档"""
        # Arrange
        # Act  
        # Assert
        pass
```

#### 测试覆盖率目标
- 单元测试覆盖率: 90%+
- 集成测试覆盖率: 80%+
- 关键业务逻辑: 95%+

### 📈 预期效果

#### 数量优化
- 测试文件数量: 70+ → 30-
- 重复测试: 15+ → 0
- 测试代码行数: 减少40%

#### 质量提升
- 测试可维护性提升
- 测试执行速度提升
- 测试覆盖率提升
- 测试文档完善

### ⚠️ 风险控制

#### 备份策略
- 移动文件前先备份到temp/tests-backup/
- 保留原始测试文件直到新测试验证通过

#### 验证策略
- 每个阶段完成后运行测试套件
- 确保测试覆盖率不降低
- 验证所有测试用例都被保留
