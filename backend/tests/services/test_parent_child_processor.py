import pytest
from app.rag.models import Document, ChildDocument
from app.rag.parent_child_processor import (
    ParentChildIndexProcessor,
    ProcessingRule,
    Segmentation,
    ProcessingError
)
import re

def test_transform_empty_documents():
    """测试处理空文档列表"""
    processor = ParentChildIndexProcessor()
    result = processor.transform([])
    assert result == []

def test_transform_single_document():
    """测试处理单个文档"""
    processor = ParentChildIndexProcessor()
    
    # 创建一个测试文档
    doc = Document(
        page_content="第一章\n\n这是第一段。这是第一段的第二句话。\n\n"
                    "这是第二段。这是第二段的第二句话。\n\n"
                    "第二章\n\n这是第三段。这是第三段的第二句话。",
        metadata={"original_id": "test-doc"}
    )
    
    # 配置适合中文PDF的处理规则
    rule = ProcessingRule(
        segmentation=Segmentation(
            max_tokens=2000,  # 较小的块大小以更好处理PDF内容
            chunk_overlap=100,
            separator="\n\n"  # PDF段落分隔
        ),
        subchunk_segmentation=Segmentation(
            max_tokens=500,   # 更小的子块以处理句子级别
            chunk_overlap=50,
            separator="。"    # 中文句号分隔
        )
    )
    
    # 处理文档
    result = processor.transform([doc], rule=rule)
    
    # 验证结果
    assert len(result) > 0
    
    # 查找父文档
    parent_docs = [d for d in result if d.metadata.get("is_parent")]
    assert len(parent_docs) > 0
    
    # 验证父文档
    parent = parent_docs[0]
    assert parent.metadata["is_parent"]
    assert "doc_id" in parent.metadata
    
    # 验证子文档
    if "child_ids" in parent.metadata:
        child_ids = parent.metadata["child_ids"]
        children = [d for d in result if d.metadata.get("doc_id") in child_ids]
        
        assert len(children) > 0
        for child in children:
            assert isinstance(child, ChildDocument)
            assert child.metadata["parent_id"] == parent.metadata["doc_id"]
            assert child.parent_content == parent.page_content
            
        # 验证子文档内容特征
        for child in children:
            # 确保文本被正确分割
            assert len(child.page_content) > 0
            # 验证是否包含中文内容
            assert re.search(r'[\u4e00-\u9fff]', child.page_content)


def test_transform_with_invalid_content():
    """测试处理无效内容"""
    processor = ParentChildIndexProcessor()
    doc = Document(page_content="", metadata={})
    
    result = processor.transform([doc])
    assert result == []

def test_transform_with_special_characters():
    """测试处理包含特殊字符的文档"""
    processor = ParentChildIndexProcessor()
    doc = Document(
        page_content="。这是一个以句号开头的文档。\n\n  这是包含多个空格的段落  \n\n这是最后一个段落。",
        metadata={}
    )
    
    result = processor.transform([doc])
    assert len(result) > 0
    # 验证内容已被清理
    assert not result[0].page_content.startswith("。")
    assert "  这是包含" not in result[0].page_content

def test_transform_with_error():
    """测试错误处理"""
    processor = ParentChildIndexProcessor()
    
    with pytest.raises(Exception):  # 使用基础异常类，因为会触发pydantic验证错误
        # 创建一个无效的文档对象（page_content不能为None）
        doc = Document(page_content=None, metadata={})

def test_child_document_position():
    """测试子文档位置信息"""
    processor = ParentChildIndexProcessor()
    doc = Document(
        page_content="第一段。\n\n第二段。\n\n第三段。",
        metadata={}
    )
    
    rule = ProcessingRule(
        segmentation=Segmentation(
            max_tokens=50,
            chunk_overlap=0,
            separator="\n\n"
        ),
        subchunk_segmentation=Segmentation(
            max_tokens=10,
            chunk_overlap=0,
            separator="。"
        )
    )
    
    result = processor.transform([doc], rule=rule)
    
    # 获取所有子文档
    child_docs = [d for d in result if isinstance(d, ChildDocument)]
    
    # 验证位置信息
    positions = [d.metadata.get("position") for d in child_docs]
    assert positions == list(range(len(positions)))

def test_metadata_inheritance():
    """测试元数据继承"""
    processor = ParentChildIndexProcessor()
    doc = Document(
        page_content="测试文档",
        metadata={
            "original_id": "test-1",
            "source": "test",
            "custom_field": "value"
        }
    )
    
    result = processor.transform([doc])
    
    # 验证所有生成的文档都继承了原始元数据
    for generated_doc in result:
        assert generated_doc.metadata.get("original_id") == "test-1"
        assert generated_doc.metadata.get("source") == "test"
        assert generated_doc.metadata.get("custom_field") == "value"

def test_chinese_english_mixed():
    """测试中英文混合文档"""
    processor = ParentChildIndexProcessor()
    doc = Document(
        page_content="这是中文。This is English.\n\n混合段落 Mixed paragraph。",
        metadata={}
    )
    
    result = processor.transform([doc])
    assert len(result) > 0
    # 验证分割结果包含完整的中英文
    for generated_doc in result:
        content = generated_doc.page_content
        assert "这是中文" in content or "This is English" in content or "混合段落" in content

def test_preview_with_parent_only():
    """测试仅使用父文档切割的预览功能"""
    processor = ParentChildIndexProcessor()
    
    # 创建一个长文档测试用例，使用明确的分隔符
    doc = Document(
        page_content="第一部分\n这是第一段内容。\n这是很长的一段话，确保能够被正确分割。\n\n"
                    "第二部分\n这是第二段内容。\n为了确保分割，这里加入更多的文本内容。\n\n"
                    "第三部分\n这是第三段内容。\n再次添加一些额外的文字来保证长度。",
        metadata={}
    )
    
    # 配置规则仅使用父文档切割，不使用子文档切割
    rule = ProcessingRule(
        segmentation=Segmentation(
            max_tokens=50,  # 使用更小的值强制分割
            chunk_overlap=5,
            separator="\n"  # 使用单个换行符作为分隔符
        ),
        subchunk_segmentation=None  # 不使用子文档切割
    )
    
    # 处理文档
    result = processor.transform([doc], rule=rule)
    
    # 验证生成了父文档
    parent_docs = [d for d in result if d.metadata.get("is_parent")]
    assert len(parent_docs) > 1, "应该生成多个父文档"
    
    # 验证每个父文档的内容
    for parent in parent_docs:
        # 确认是父文档
        assert parent.metadata["is_parent"]
        assert "doc_id" in parent.metadata
        # 验证没有子文档
        assert "child_ids" not in parent.metadata
        # 确保父文档包含完整的段落
        content = parent.page_content
        assert content.strip()
        # 验证文档内容的完整性
        assert any([
            "章" in content,  # 包含章节标题
            content.endswith("。"),  # 以句号结尾
            content.count("。") >= 1  # 至少包含一个完整句子
        ]), f"父文档内容不完整: {content}"