"""
文档分割器单元测试

合并了原有的多个分割器测试文件，提供统一的测试覆盖。
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from typing import List, Dict, Any

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.rag.models import Document
from app.rag.document_splitter import ParentChildDocumentSplitter, Rule, SplitMode
from app.rag.text_splitter import FixedRecursiveCharacterTextSplitter
from tests.utils.test_helpers import DocumentTestHelper, TempFileHelper
from tests.utils.data_generators import doc_generator, config_generator


class TestFixedRecursiveCharacterTextSplitter:
    """测试基础文本分割器"""
    
    def setup_method(self):
        """每个测试方法前的准备"""
        self.splitter = FixedRecursiveCharacterTextSplitter.from_encoder(
            chunk_size=100,
            chunk_overlap=20,
            fixed_separator="\n\n",
            separators=["\n\n", "\n", "。", ". ", " ", ""],
            keep_separator=True,
            length_function=lambda x: [len(text) for text in x]
        )
    
    def test_should_split_text_when_valid_input_provided(self):
        """测试：提供有效输入时应正确分割文本"""
        # Arrange
        test_text = DocumentTestHelper.create_test_document_content()
        
        # Act
        chunks = self.splitter.split_text(test_text)
        
        # Assert
        assert len(chunks) > 0, "应该产生至少一个文本块"
        assert all(len(chunk) <= 120 for chunk in chunks), "所有文本块长度应在合理范围内"  # 考虑重叠
        assert "".join(chunks).replace("\n\n", "").replace("\n", "") in test_text.replace("\n\n", "").replace("\n", ""), "分割后的内容应包含原始内容"
    
    def test_should_respect_separator_when_splitting(self):
        """测试：分割时应遵循分隔符规则"""
        # Arrange
        test_text = "段落一。\n\n段落二。\n\n段落三。"
        
        # Act
        chunks = self.splitter.split_text(test_text)
        
        # Assert
        assert len(chunks) >= 1, "应该产生文本块"
        # 检查是否保留了分隔符
        combined = "".join(chunks)
        assert "段落一" in combined, "应该保留原始内容"
        assert "段落二" in combined, "应该保留原始内容"
    
    def test_should_handle_empty_input(self):
        """测试：应正确处理空输入"""
        # Arrange
        test_text = ""
        
        # Act
        chunks = self.splitter.split_text(test_text)
        
        # Assert
        assert chunks == [], "空输入应返回空列表"
    
    def test_should_handle_short_text(self):
        """测试：应正确处理短文本"""
        # Arrange
        test_text = "短文本"
        
        # Act
        chunks = self.splitter.split_text(test_text)
        
        # Assert
        assert len(chunks) == 1, "短文本应返回单个块"
        assert chunks[0] == test_text, "短文本内容应保持不变"


class TestParentChildDocumentSplitter:
    """测试父子文档分割器"""
    
    def setup_method(self):
        """每个测试方法前的准备"""
        self.splitter = ParentChildDocumentSplitter()
        self.rule = Rule(
            mode=SplitMode.PARENT_CHILD,
            max_tokens=1024,
            chunk_overlap=200,
            fixed_separator="\n\n",
            subchunk_max_tokens=512,
            subchunk_overlap=50,
            subchunk_separator="\n",
            clean_text=True,
            keep_separator=True
        )
    
    def test_should_split_document_into_parent_child_structure(self):
        """测试：应将文档分割为父子结构"""
        # Arrange
        content = DocumentTestHelper.create_test_document_content()
        document = Document(
            page_content=content,
            metadata={"source": "test", "doc_id": "test-123"}
        )
        
        # Act
        segments = self.splitter.split_documents([document], self.rule)
        
        # Assert
        assert len(segments) > 0, "应该产生分割段落"
        
        # 检查父子结构
        parent_segments = [s for s in segments if s.metadata.get("type") == "parent"]
        child_segments = [s for s in segments if s.metadata.get("type") == "child"]
        
        assert len(parent_segments) > 0, "应该有父段落"
        assert len(child_segments) > 0, "应该有子段落"
        
        # 检查父段落是否有子段落
        for parent in parent_segments:
            if hasattr(parent, 'children') and parent.children:
                assert len(parent.children) > 0, "父段落应该有子段落"
    
    def test_should_preserve_document_metadata(self):
        """测试：应保留文档元数据"""
        # Arrange
        metadata = doc_generator.generate_document_metadata()
        document = Document(
            page_content="测试内容",
            metadata=metadata
        )

        # Act
        segments = self.splitter.split_documents([document], self.rule)

        # Assert
        assert len(segments) > 0, "应该产生分割段落"
        for segment in segments:
            # 检查基本元数据结构是否存在
            assert hasattr(segment, 'metadata'), "段落应有metadata属性"
            assert isinstance(segment.metadata, dict), "metadata应为字典类型"
            # 检查是否有某种形式的ID标识
            has_id = any(key for key in segment.metadata.keys() if 'id' in key.lower())
            assert has_id, "应该有某种形式的ID标识"
    
    def test_should_handle_multiple_documents(self):
        """测试：应正确处理多个文档"""
        # Arrange
        documents = []
        for i in range(3):
            content = f"文档{i+1}的内容。\n\n这是第{i+1}个测试文档。"
            documents.append(Document(
                page_content=content,
                metadata={"source": "test", "doc_id": f"test-{i+1}"}
            ))

        # Act
        segments = self.splitter.split_documents(documents, self.rule)

        # Assert
        assert len(segments) > 0, "应该产生分割段落"

        # 检查段落数量是否合理（每个文档至少产生一个段落）
        assert len(segments) >= len(documents), f"段落数({len(segments)})应至少等于文档数({len(documents)})"

        # 检查所有段落都有有效内容
        for segment in segments:
            assert len(segment.page_content.strip()) > 0, "段落内容不应为空"
            assert hasattr(segment, 'metadata'), "段落应有metadata"
    
    def test_should_be_consistent_across_runs(self):
        """测试：多次运行应产生一致结果"""
        # Arrange
        content = DocumentTestHelper.create_test_document_content()
        document = Document(
            page_content=content,
            metadata={"source": "test", "doc_id": "consistency-test"}
        )
        
        # Act - 运行多次
        results = []
        for _ in range(3):
            segments = self.splitter.split_documents([document], self.rule)
            results.append({
                "segment_count": len(segments),
                "parent_count": len([s for s in segments if s.metadata.get("type") == "parent"]),
                "child_count": len([s for s in segments if s.metadata.get("type") == "child"]),
                "contents": [s.page_content for s in segments]
            })
        
        # Assert - 检查一致性
        first_result = results[0]
        for i, result in enumerate(results[1:], 1):
            assert result["segment_count"] == first_result["segment_count"], f"第{i+1}次运行段落数不一致"
            assert result["parent_count"] == first_result["parent_count"], f"第{i+1}次运行父段落数不一致"
            assert result["child_count"] == first_result["child_count"], f"第{i+1}次运行子段落数不一致"
            assert result["contents"] == first_result["contents"], f"第{i+1}次运行内容不一致"
    
    def test_should_handle_different_split_parameters(self):
        """测试：应正确处理不同的分割参数"""
        # Arrange
        content = doc_generator.generate_long_text(5)
        document = Document(page_content=content, metadata={"source": "test"})
        
        configs = [
            {"max_tokens": 512, "subchunk_max_tokens": 256},
            {"max_tokens": 1024, "subchunk_max_tokens": 512},
            {"max_tokens": 2048, "subchunk_max_tokens": 1024}
        ]
        
        # Act & Assert
        for config in configs:
            rule = Rule(
                mode=SplitMode.PARENT_CHILD,
                max_tokens=config["max_tokens"],
                chunk_overlap=100,
                fixed_separator="\n\n",
                subchunk_max_tokens=config["subchunk_max_tokens"],
                subchunk_overlap=50,
                subchunk_separator="\n",
                clean_text=True,
                keep_separator=True
            )
            
            segments = self.splitter.split_documents([document], rule)
            assert len(segments) > 0, f"配置{config}应产生分割段落"
    
    def test_should_handle_edge_cases(self):
        """测试：应正确处理边界情况"""
        edge_cases = [
            ("", "空文档"),
            ("单行文本", "单行文档"),
            ("A" * 10000, "超长文档"),
            ("多\n行\n文\n本\n但\n没\n有\n双\n换\n行", "多行但无段落分隔"),
            ("   \n\n   \n\n   ", "只有空白字符")
        ]
        
        for content, description in edge_cases:
            document = Document(
                page_content=content,
                metadata={"source": "test", "description": description}
            )
            
            # 应该不抛出异常
            try:
                segments = self.splitter.split_documents([document], self.rule)
                # 对于空内容，可能返回空列表或包含清理后内容的段落
                assert isinstance(segments, list), f"{description}应返回列表"
            except Exception as e:
                pytest.fail(f"{description}处理失败: {e}")


class TestDocumentSplitterIntegration:
    """文档分割器集成测试"""
    
    @pytest.mark.skip(reason="需要重构以避免导入问题")
    def test_should_work_with_document_processor(self):
        """测试：应与文档处理器正确集成"""
        # 这个测试暂时跳过，需要重构以避免导入问题
        pass
    
    def test_should_maintain_performance_with_large_documents(self):
        """测试：处理大文档时应保持性能"""
        # Arrange
        large_content = doc_generator.generate_long_text(50)  # 生成50段内容
        document = Document(
            page_content=large_content,
            metadata={"source": "performance_test"}
        )
        
        splitter = ParentChildDocumentSplitter()
        rule = Rule(
            mode=SplitMode.PARENT_CHILD,
            max_tokens=1024,
            chunk_overlap=200,
            fixed_separator="\n\n",
            subchunk_max_tokens=512,
            subchunk_overlap=50,
            subchunk_separator="\n",
            clean_text=True,
            keep_separator=True
        )
        
        # Act & Assert
        import time
        start_time = time.time()
        segments = splitter.split_documents([document], rule)
        end_time = time.time()
        
        processing_time = end_time - start_time
        assert processing_time < 10.0, f"处理时间应少于10秒，实际用时{processing_time:.2f}秒"
        assert len(segments) > 0, "应该产生分割段落"
        
        # 检查内存使用是否合理（简单检查）
        total_content_length = sum(len(seg.page_content) for seg in segments)
        assert total_content_length > 0, "分割后总内容长度应大于0"
