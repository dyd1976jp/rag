#!/usr/bin/env python3
"""
父子分块独立编号机制演示脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, '/Users/tei/go/RAG-chat/backend')

from app.rag.document_splitter import ParentChildDocumentSplitter, Rule, SplitMode
from app.rag.models import Document

def demo_basic_numbering():
    """演示基本的编号机制"""
    print("=== 基本编号机制演示 ===")
    
    # 创建示例文档
    content = """第一章：人工智能概述
人工智能（Artificial Intelligence，AI）是计算机科学的一个分支。
它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。

第二章：机器学习基础
机器学习是人工智能的一个重要分支。
它是一种通过算法使计算机系统能够自动学习和改进的方法。
机器学习算法通过训练数据来构建数学模型，以便对新数据进行预测或决策。
常见的机器学习类型包括监督学习、无监督学习和强化学习。

第三章：深度学习
深度学习是机器学习的一个子集。
它基于人工神经网络，特别是深层神经网络。
深度学习在图像识别、语音识别、自然语言处理等领域取得了突破性进展。"""
    
    doc = Document(
        page_content=content,
        source="ai_textbook.txt",
        metadata={"title": "人工智能教程", "author": "示例作者"}
    )
    
    # 创建分割规则
    rule = Rule(
        mode=SplitMode.PARENT_CHILD,
        max_tokens=150,  # 父块大小
        chunk_overlap=20,
        fixed_separator="\n\n",
        subchunk_max_tokens=80,  # 子块大小
        subchunk_overlap=10,
        subchunk_separator="\n"
    )
    
    # 执行分割
    splitter = ParentChildDocumentSplitter()
    segments = splitter.split_documents([doc], rule)
    
    # 显示结果
    parent_segments = [s for s in segments if s.metadata.get("type") == "parent"]
    child_segments = [s for s in segments if s.metadata.get("type") == "child"]
    
    print(f"文档分割结果：")
    print(f"- 父块数量: {len(parent_segments)}")
    print(f"- 子块数量: {len(child_segments)}")
    print()
    
    for parent in parent_segments:
        parent_number = parent.metadata.get("parent_number")
        print(f"📄 父块 {parent_number}:")
        print(f"   内容: {parent.page_content[:60]}...")
        print(f"   长度: {len(parent.page_content)} 字符")
        
        # 找到对应的子块
        parent_id = parent.metadata.get("id")
        related_children = [c for c in child_segments if c.metadata.get("parent_id") == parent_id]
        related_children.sort(key=lambda x: x.metadata.get("child_number", 0))
        
        if related_children:
            print(f"   📝 子块 ({len(related_children)} 个):")
            for child in related_children:
                child_number = child.metadata.get("child_number")
                combined_number = child.metadata.get("combined_number")
                print(f"      {combined_number}: {child.page_content[:40]}...")
        else:
            print(f"   📝 无子块（内容较短）")
        print()

def demo_numbering_consistency():
    """演示编号一致性验证"""
    print("=== 编号一致性验证演示 ===")
    
    # 创建多段落文档
    content = """段落一内容比较短。

段落二内容比较长，需要分割成多个子块。
这是段落二的第二行内容，也比较长。
这是段落二的第三行内容。
这是段落二的第四行内容。

段落三内容中等长度。
这是段落三的第二行。

段落四内容也比较长，需要分割。
这是段落四的第二行内容。
这是段落四的第三行内容。
这是段落四的第四行内容。
这是段落四的第五行内容。"""
    
    doc = Document(
        page_content=content,
        source="multi_paragraph.txt",
        metadata={"title": "多段落文档"}
    )
    
    # 创建分割规则
    rule = Rule(
        mode=SplitMode.PARENT_CHILD,
        max_tokens=80,
        chunk_overlap=10,
        fixed_separator="\n\n",
        subchunk_max_tokens=40,
        subchunk_overlap=5,
        subchunk_separator="\n"
    )
    
    # 执行分割
    splitter = ParentChildDocumentSplitter()
    segments = splitter.split_documents([doc], rule)
    
    # 验证编号规则
    parent_segments = [s for s in segments if s.metadata.get("type") == "parent"]
    child_segments = [s for s in segments if s.metadata.get("type") == "child"]
    
    print("验证结果：")
    
    # 验证父块编号连续性
    parent_numbers = [p.metadata.get("parent_number") for p in parent_segments]
    parent_numbers.sort()
    expected_parent_numbers = list(range(1, len(parent_segments) + 1))
    
    if parent_numbers == expected_parent_numbers:
        print("✅ 父块编号连续性验证通过")
    else:
        print(f"❌ 父块编号不连续: {parent_numbers}")
    
    # 验证子块编号重置
    reset_validation_passed = True
    for parent in parent_segments:
        parent_id = parent.metadata.get("id")
        parent_number = parent.metadata.get("parent_number")
        
        related_children = [c for c in child_segments if c.metadata.get("parent_id") == parent_id]
        child_numbers = [c.metadata.get("child_number") for c in related_children]
        child_numbers.sort()
        
        if related_children:
            expected_child_numbers = list(range(1, len(related_children) + 1))
            if child_numbers != expected_child_numbers:
                print(f"❌ 父块 {parent_number} 的子块编号不正确: {child_numbers}")
                reset_validation_passed = False
    
    if reset_validation_passed:
        print("✅ 子块编号重置验证通过")
    
    # 验证组合编号格式
    format_validation_passed = True
    for child in child_segments:
        parent_number = child.metadata.get("parent_number")
        child_number = child.metadata.get("child_number")
        combined_number = child.metadata.get("combined_number")
        expected_combined = f"{parent_number}-{child_number}"
        
        if combined_number != expected_combined:
            print(f"❌ 组合编号格式错误: {combined_number}, 期望: {expected_combined}")
            format_validation_passed = False
    
    if format_validation_passed:
        print("✅ 组合编号格式验证通过")
    
    print()
    
    # 显示编号分布
    print("编号分布：")
    for parent in parent_segments:
        parent_number = parent.metadata.get("parent_number")
        parent_id = parent.metadata.get("id")
        
        related_children = [c for c in child_segments if c.metadata.get("parent_id") == parent_id]
        related_children.sort(key=lambda x: x.metadata.get("child_number", 0))
        
        if related_children:
            child_numbers = [c.metadata.get("combined_number") for c in related_children]
            print(f"父块 {parent_number} → 子块: {', '.join(child_numbers)}")
        else:
            print(f"父块 {parent_number} → 无子块")

def demo_metadata_structure():
    """演示元数据结构"""
    print("=== 元数据结构演示 ===")
    
    content = """示例段落内容，用于演示元数据结构。
这是第二行内容。
这是第三行内容。"""
    
    doc = Document(
        page_content=content,
        source="metadata_demo.txt",
        metadata={"title": "元数据演示", "category": "示例"}
    )
    
    rule = Rule(
        mode=SplitMode.PARENT_CHILD,
        max_tokens=50,
        chunk_overlap=5,
        fixed_separator="\n\n",
        subchunk_max_tokens=25,
        subchunk_overlap=2,
        subchunk_separator="\n"
    )
    
    splitter = ParentChildDocumentSplitter()
    segments = splitter.split_documents([doc], rule)
    
    # 显示元数据结构
    for segment in segments:
        segment_type = segment.metadata.get("type")
        print(f"\n{segment_type.upper()} 段落元数据:")
        
        # 显示关键元数据字段
        key_fields = [
            "type", "parent_number", "child_number", "combined_number",
            "index", "parent_id", "source"
        ]
        
        for field in key_fields:
            value = segment.metadata.get(field)
            if value is not None:
                if field == "parent_id":
                    value = f"{value[:8]}..."  # 截断显示
                print(f"  {field}: {value}")
        
        print(f"  内容: {segment.page_content[:30]}...")

if __name__ == "__main__":
    print("🚀 父子分块独立编号机制演示")
    print("=" * 50)
    
    demo_basic_numbering()
    print("\n" + "=" * 50)
    
    demo_numbering_consistency()
    print("\n" + "=" * 50)
    
    demo_metadata_structure()
    
    print("\n" + "=" * 50)
    print("✨ 演示完成！新的编号机制确保了:")
    print("   1. 父块编号独立且连续")
    print("   2. 子块编号在每个父块内重新开始")
    print("   3. 组合编号格式清晰（父块-子块）")
    print("   4. 向后兼容现有系统")
