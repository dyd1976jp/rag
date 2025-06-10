"""
测试文档分割功能的脚本
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from app.rag.models import Document, DocumentSegment
from app.rag.document_splitter import (
    DocumentSplitter,
    QADocumentSplitter,
    ParentChildDocumentSplitter,
    Rule,
    SplitMode
)
from app.rag.extractor.extract_processor import ExtractProcessor, ExtractMode

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pdf_splitting_test.log')
    ]
)
logger = logging.getLogger(__name__)

def load_pdf_content(pdf_path: str) -> Document:
    """加载PDF文件内容"""
    try:
        logger.info(f"正在加载PDF文件: {pdf_path}")
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
            
        # 使用ExtractProcessor提取PDF文本
        documents = ExtractProcessor.extract_pdf(
            file_path=pdf_path,
            mode=ExtractMode.UNSTRUCTURED
        )
        
        # 合并所有文档内容
        text_content = "\n\n".join([doc.page_content for doc in documents])
        
        # 创建文档对象
        document = Document(
            page_content=text_content,
            source=os.path.basename(pdf_path)
        )
        
        logger.info(f"PDF加载完成，文本长度: {len(document.page_content)} 字符")
        return document
        
    except Exception as e:
        logger.error(f"加载PDF文件失败: {str(e)}")
        raise

def test_paragraph_splitting(document: Document, output_dir: str = "output") -> List[DocumentSegment]:
    """测试段落分割"""
    try:
        logger.info("\n=== 开始测试段落分割 ===")
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建分割器和规则
        splitter = DocumentSplitter()
        rule = Rule(
            mode=SplitMode.PARAGRAPH,
            max_tokens=500,
            chunk_overlap=50,
            fixed_separator="\n\n"
        )
        
        # 分割文档
        segments = splitter.split_documents([document], rule)
        
        # 准备结果
        results = []
        for segment in segments:
            segment_data = {
                "id": segment.id,
                "page_content": segment.page_content,
                "metadata": segment.metadata,
                "length": len(segment.page_content)
            }
            results.append(segment_data)
            
        # 保存结果
        output_file = os.path.join(output_dir, "paragraph_splitting_result.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        logger.info(f"段落分割完成，共生成 {len(segments)} 个片段")
        logger.info(f"结果已保存至: {output_file}")
        
        return segments
        
    except Exception as e:
        logger.error(f"段落分割测试失败: {str(e)}")
        raise

def test_qa_splitting(document: Document, output_dir: str = "output") -> List[DocumentSegment]:
    """测试问答分割"""
    try:
        logger.info("\n=== 开始测试问答分割 ===")
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建分割器和规则
        splitter = QADocumentSplitter()
        rule = Rule(
            mode=SplitMode.QA,
            max_tokens=1000,
            chunk_overlap=0  # 问答模式不需要重叠
        )
        
        # 分割文档
        segments = splitter.split_documents([document], rule)
        
        # 准备结果
        results = []
        for segment in segments:
            segment_data = {
                "id": segment.id,
                "page_content": segment.page_content,
                "metadata": segment.metadata,
                "length": len(segment.page_content)
            }
            results.append(segment_data)
            
        # 保存结果
        output_file = os.path.join(output_dir, "qa_splitting_result.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        logger.info(f"问答分割完成，共生成 {len(segments)} 个问答对")
        logger.info(f"结果已保存至: {output_file}")
        
        return segments
        
    except Exception as e:
        logger.error(f"问答分割测试失败: {str(e)}")
        raise

def test_parent_child_splitting(document: Document, output_dir: str = "output") -> List[DocumentSegment]:
    """测试父子分割"""
    try:
        logger.info("\n=== 开始测试父子分割 ===")
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建分割器和规则
        splitter = ParentChildDocumentSplitter()
        rule = Rule(
            mode=SplitMode.PARENT_CHILD,
            max_tokens=1024,  # 父块最大长度
            chunk_overlap=200,  # 父块重叠
            fixed_separator="\n\n",  # 父块分隔符
            subchunk_max_tokens=512,  # 子块最大长度
            subchunk_overlap=50,  # 子块重叠
            subchunk_separator="\n",  # 子块分隔符
            min_content_length=50,  # 最小内容长度
            clean_text=True,
            keep_separator=True,
            remove_empty_lines=True,
            normalize_whitespace=True
        )
        
        # 分割文档
        segments = splitter.split_documents([document], rule)
        
        # 统计父文档和子文档
        parent_segments = [s for s in segments if s.metadata["type"] == "parent"]
        child_segments = [s for s in segments if s.metadata["type"] == "child"]
        
        # 准备结果数据
        results = {
            "summary": {
                "total_parents": len(parent_segments),
                "total_children": len(child_segments),
                "source_file": document.source,
                "text_length": len(document.page_content),
                "splitting_config": {
                    "parent_max_tokens": rule.max_tokens,
                    "parent_chunk_overlap": rule.chunk_overlap,
                    "parent_separator": rule.fixed_separator,
                    "child_max_tokens": rule.subchunk_max_tokens,
                    "child_chunk_overlap": rule.subchunk_overlap,
                    "child_separator": rule.subchunk_separator,
                    "min_content_length": rule.min_content_length
                }
            },
            "segments": []
        }
        
        # 处理每个片段
        current_parent = None
        for segment in segments:
            if segment.metadata["type"] == "parent":
                if current_parent:
                    results["segments"].append(current_parent)
                current_parent = {
                    "id": segment.id,
                    "page_content": segment.page_content,
                    "metadata": segment.metadata,
                    "length": len(segment.page_content),
                    "children": []
                }
            else:  # child
                if current_parent:
                    child_data = {
                        "id": segment.id,
                        "page_content": segment.page_content,
                        "metadata": segment.metadata,
                        "length": len(segment.page_content)
                    }
                    current_parent["children"].append(child_data)
        
        # 添加最后一个父文档
        if current_parent:
            results["segments"].append(current_parent)
            
        # 计算统计信息
        parent_lengths = [len(p["page_content"]) for p in results["segments"]]
        child_lengths = [len(c["page_content"]) for p in results["segments"] for c in p["children"]]
        
        results["summary"].update({
            "parent_stats": {
                "min_length": min(parent_lengths) if parent_lengths else 0,
                "max_length": max(parent_lengths) if parent_lengths else 0,
                "avg_length": sum(parent_lengths) / len(parent_lengths) if parent_lengths else 0,
                "total_parents": len(parent_lengths)
            },
            "child_stats": {
                "min_length": min(child_lengths) if child_lengths else 0,
                "max_length": max(child_lengths) if child_lengths else 0,
                "avg_length": sum(child_lengths) / len(child_lengths) if child_lengths else 0,
                "total_children": len(child_lengths)
            }
        })
        
        # 保存结果
        output_file = os.path.join(output_dir, "parent_child_splitting_result.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        logger.info(f"父子分割完成，结果已保存至: {output_file}")
        logger.info(f"统计信息:")
        logger.info(f"- 总父文档数: {results['summary']['total_parents']}")
        logger.info(f"- 总子文档数: {results['summary']['total_children']}")
        logger.info(f"- 父文档长度: 最小={results['summary']['parent_stats']['min_length']}, " +
                   f"最大={results['summary']['parent_stats']['max_length']}, " +
                   f"平均={results['summary']['parent_stats']['avg_length']:.2f}")
        logger.info(f"- 子文档长度: 最小={results['summary']['child_stats']['min_length']}, " +
                   f"最大={results['summary']['child_stats']['max_length']}, " +
                   f"平均={results['summary']['child_stats']['avg_length']:.2f}")
        
        return segments
        
    except Exception as e:
        logger.error(f"父子分割测试失败: {str(e)}")
        raise

def main():
    """主函数"""
    try:
        # PDF文件路径
        pdf_path = "/Users/tei/go/RAG-chat/backend/data/uploads/初赛训练数据集.pdf"
        
        # 输出目录
        output_dir = "output"
        
        # 加载PDF内容
        document = load_pdf_content(pdf_path)
        
        # 测试段落分割
        test_paragraph_splitting(document, output_dir)
        
        # 测试问答分割
        test_qa_splitting(document, output_dir)
        
        # 测试父子分割
        test_parent_child_splitting(document, output_dir)
        
        logger.info("\n=== 测试完成 ===")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
