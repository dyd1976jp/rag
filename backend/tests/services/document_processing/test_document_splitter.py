"""
测试文档分割功能的脚本
"""

import os
import sys
import logging
import unittest
from pathlib import Path
from typing import List
from datetime import datetime
import json

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# 创建专用目录"split_results"用于存放分割结果文件
split_results_dir = Path(__file__).parent / "split_results"
os.makedirs(split_results_dir, exist_ok=True)

# 创建日志目录
log_dir = Path(__file__).parent / "logs"
os.makedirs(log_dir, exist_ok=True)

# 配置日志
log_file = log_dir / "test_document_splitter.log"
if log_file.exists():
    log_file.unlink()  # 删除已存在的日志文件

# 创建日志处理器
file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='w')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# 配置根日志记录器
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# 获取模块日志记录器
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from app.rag.document_splitter import DocumentSplitter, ParentChildDocumentSplitter, Rule, SplitMode
from app.rag.models import Document
from app.rag.models import DocumentSegment, ChildChunk
from app.rag.database import MongoDBManager
from app.rag.vector_store import MilvusVectorStore
from app.rag.embedding_model import EmbeddingModel

def save_segments_to_json(segments: List[DocumentSegment], source_file: str, split_mode: str) -> Path:
    """保存分割结果到JSON文件"""
    # 创建输出文件名
    output_filename = f"{Path(source_file).stem}_{split_mode}_segments.json"
    output_path = split_results_dir / output_filename
    
    # 准备结果数据
    results = {
        "source_file": source_file,
        "split_mode": split_mode,
        "metadata": {
            "total_segments": len(segments),
            "processed_at": datetime.now().isoformat()
        }
    }
    
    # 如果是父子分割模式，使用嵌套结构
    if split_mode == "parent_child":
        # 只保存父文档，子文档会通过父文档的 children 字段包含
        parent_segments = [s for s in segments if s.metadata["type"] == "parent"]
        # 使用 to_dict() 方法，它会自动处理 embedding 字段
        results["segments"] = [segment.to_dict() for segment in parent_segments]
        
        # 添加统计信息
        parent_lengths = [len(s.page_content) for s in parent_segments]
        child_lengths = [
            len(c.page_content) 
            for p in parent_segments 
            for c in (p.children or [])
        ]
        
        results["metadata"]["stats"] = {
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
        }
    else:
        # 对于其他分割模式，使用普通的平铺结构
        # 使用 to_dict() 方法，它会自动处理 embedding 字段
        results["segments"] = [segment.to_dict() for segment in segments]
        
        # 添加统计信息
        segment_lengths = [len(s.page_content) for s in segments]
        results["metadata"]["stats"] = {
            "min_length": min(segment_lengths) if segment_lengths else 0,
            "max_length": max(segment_lengths) if segment_lengths else 0,
            "avg_length": sum(segment_lengths) / len(segment_lengths) if segment_lengths else 0,
            "total_segments": len(segment_lengths)
        }
    
    # 写入JSON文件
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print(f"{split_mode} 分割结果已保存到: {output_path}")
    return output_path

class TestDocumentSplitter(unittest.TestCase):
    """测试文档分割器"""
    
    def setUp(self):
        """测试前的准备工作"""
        self.test_dir = Path(__file__).parent
        self.split_results_dir = self.test_dir / "split_results"
        os.makedirs(self.split_results_dir, exist_ok=True)
        
    def test_text_splitting(self):
        """测试文本分割功能"""
        # 设置环境变量
        os.environ["CHUNK_SIZE"] = "100"  # 设置较小的分块大小以便于观察
        os.environ["CHUNK_OVERLAP"] = "20"  # 设置重叠大小
        os.environ["SPLIT_BY_PARAGRAPH"] = "true"  # 启用段落分割
        os.environ["SPLIT_BY_SENTENCE"] = "true"  # 启用句子分割
        
        # 创建示例文本
        test_text = """
第一段落：这是第一段文字。这里包含了一些基本信息。这是第一段的最后一句。

第二段落：这是第二段的开始。这里有一些技术细节的描述。
这是第二段的第二行。这里继续描述一些内容。

第三段落：这是最后一段。这段包含总结信息。
这是最后一段的第二行。这里是文档的结束。
        """
        
        # 创建文档对象
        doc = Document(
            page_content=test_text,
            source="test_document",
            doc_id="test_doc_id_1",
            metadata={
                "created_at": "2024-03-19"
            }
        )
        
        # 创建分割器实例
        splitter = DocumentSplitter()
        
        logger.info("开始测试文档分割...")
        logger.info(f"分割配置: chunk_size={splitter.chunk_size}, chunk_overlap={splitter.chunk_overlap}")
        logger.info(f"原始文本长度: {len(test_text)} 字符")
        
        # 执行分割
        try:
            segments = splitter.split_documents([doc])
            # 保存分割结果
            output_path = save_segments_to_json(segments, "test_document", "text")
            self.assertTrue(output_path.exists())
            
            # 打印分割结果
            logger.info(f"\n分割结果: 共生成 {len(segments)} 个片段")
            for i, segment in enumerate(segments, 1):
                logger.info(f"\n片段 {i}:")
                logger.info(f"内容: {segment.page_content}")
                logger.info(f"长度: {len(segment.page_content)} 字符")
                logger.info(f"元数据: {segment.metadata}")
                
            # 验证分割结果
            self.assertGreater(len(segments), 0, "应该生成至少一个片段")
            total_chars = sum(len(seg.page_content) for seg in segments)
            avg_length = total_chars / len(segments) if segments else 0
            
            logger.info(f"\n统计信息:")
            logger.info(f"总字符数: {total_chars}")
            logger.info(f"平均片段长度: {avg_length:.2f} 字符")
            logger.info(f"最短片段长度: {min(len(seg.page_content) for seg in segments)} 字符")
            logger.info(f"最长片段长度: {max(len(seg.page_content) for seg in segments)} 字符")
            
            # 验证每个片段
            for segment in segments:
                self.assertIsNotNone(segment.page_content)
                self.assertGreater(len(segment.page_content), 0)
                self.assertIn("source", segment.metadata)
                self.assertIn("type", segment.metadata)
            
        except Exception as e:
            logger.error(f"分割过程中出错: {str(e)}")
            raise
            
    def test_different_configurations(self):
        """测试不同的分割配置"""
        test_text = """
这是一个测试文档。它包含多个句子和段落。
这是第一段的第二句话。这是第三句话。

这是第二段。它也有多个句子。
这是一个较长的句子，包含了更多的信息和细节描述。

这是最后一段。
它很短。
        """
        
        doc = Document(page_content=test_text, source="test_config", doc_id="test_doc_id_2", metadata={})
        
        # 测试不同的配置
        configs = [
            {
                "CHUNK_SIZE": "50",
                "CHUNK_OVERLAP": "10",
                "SPLIT_BY_PARAGRAPH": "true",
                "SPLIT_BY_SENTENCE": "true"
            },
            {
                "CHUNK_SIZE": "100",
                "CHUNK_OVERLAP": "20",
                "SPLIT_BY_PARAGRAPH": "true",
                "SPLIT_BY_SENTENCE": "false"
            },
            {
                "CHUNK_SIZE": "200",
                "CHUNK_OVERLAP": "30",
                "SPLIT_BY_PARAGRAPH": "false",
                "SPLIT_BY_SENTENCE": "true"
            }
        ]
        
        for idx, config in enumerate(configs):
            logger.info(f"\n测试配置: {config}")
            # 设置环境变量
            for key, value in config.items():
                os.environ[key] = value
            splitter = DocumentSplitter()
            try:
                segments = splitter.split_documents([doc])
                # 保存分割结果
                output_path = save_segments_to_json(segments, f"test_config_{idx+1}", "config")
                self.assertTrue(output_path.exists())
                
                logger.info(f"生成片段数: {len(segments)}")
                for i, segment in enumerate(segments, 1):
                    logger.info(f"片段 {i} 长度: {len(segment.page_content)} 字符")
                    logger.info(f"内容: {segment.page_content}\n")
                    
                # 验证分割结果
                self.assertGreater(len(segments), 0, f"配置 {config} 应该生成至少一个片段")
                for segment in segments:
                    self.assertIsNotNone(segment.page_content)
                    self.assertGreater(len(segment.page_content), 0)
                    self.assertIn("source", segment.metadata)
                    self.assertIn("type", segment.metadata)
                    
            except Exception as e:
                logger.error(f"使用配置 {config} 分割时出错: {str(e)}")
                raise
                
    def test_hierarchical_splitting(self):
        """测试父子分割功能"""
        logger.debug("开始测试父子分割功能")
        
        # 创建示例文本
        test_text = """
第一章：引言
这是一个较长的文档示例。它包含多个章节和段落。
这个文档将用于测试父子分割功能。每个章节都可能被分成父块。
每个父块又可以进一步分割成更小的子块。

第二章：主要内容
这一章包含了更多的细节信息。我们将详细讨论父子分割的原理。
父块通常是较大的文本单位，比如章节或者大段落。
子块则是更小的文本单位，可能是句子或者短段落。

第三章：技术实现
在实现层面，我们使用了两级分割策略。
第一级分割会将文档分成较大的块，这些是父块。
第二级分割则会将这些父块进一步分割成更小的子块。
这种方式可以更好地保持文档的层级结构。

第四章：总结
父子分割方法提供了更灵活的文档处理方式。
它可以同时保持文档的整体结构和局部细节。
这对于后续的文档分析和处理非常有帮助。
        """
        
        logger.debug(f"测试文本长度: {len(test_text)} 字符")
        
        # 创建文档对象
        doc = Document(
            page_content=test_text,
            source="test_hierarchical",
            doc_id="test_doc_id_3",
            metadata={
                "created_at": "2024-03-19",
                "document_type": "technical"
            }
        )
        
        # 创建分割规则
        rule = Rule(
            mode=SplitMode.PARENT_CHILD,
            max_tokens=1024,  # 父块最大长度
            chunk_overlap=200,  # 父块重叠
            fixed_separator="\n\n",  # 父块分隔符
            subchunk_max_tokens=512,  # 子块最大长度
            subchunk_overlap=50,  # 子块重叠
            subchunk_separator="\n"  # 子块分隔符
        )
        
        logger.debug(f"分割规则: {rule.__dict__}")
        
        # 创建层级分割器实例
        splitter = ParentChildDocumentSplitter()
        
        logger.debug("开始执行文档分割")
        try:
            # 执行分割
            segments = splitter.split_documents([doc], rule)
            
            # 打印分割结果统计
            parent_segments = [s for s in segments if s.metadata["type"] == "parent"]
            child_segments = [s for s in segments if s.metadata["type"] == "child"]
            
            logger.debug(f"分割结果统计:")
            logger.debug(f"父文档数量: {len(parent_segments)}")
            logger.debug(f"子文档数量: {len(child_segments)}")
            
            # 打印每个父文档的信息
            for i, parent in enumerate(parent_segments, 1):
                logger.debug(f"\n父文档 {i}:")
                logger.debug(f"ID: {parent.id}")
                logger.debug(f"内容长度: {len(parent.page_content)} 字符")
                logger.debug(f"子文档数量: {len(parent.children) if parent.children else 0}")
                if parent.children:
                    for j, child in enumerate(parent.children, 1):
                        logger.debug(f"  子文档 {j}:")
                        logger.debug(f"    ID: {child.id}")
                        logger.debug(f"    内容长度: {len(child.page_content)} 字符")
                        logger.debug(f"    内容: {child.page_content[:100]}...")
                else:
                    logger.debug("  没有子文档")
            
            # 保存分割结果
            output_path = save_segments_to_json(segments, "test_hierarchical", "parent_child")
            logger.debug(f"分割结果已保存到: {output_path}")
            
            # 验证分割结果
            self.assertGreater(len(parent_segments), 0, "应该生成至少一个父文档")
            self.assertGreater(len(child_segments), 0, "应该生成至少一个子文档")
            
            # 验证父文档
            for parent in parent_segments:
                self.assertIsNotNone(parent.page_content)
                self.assertGreater(len(parent.page_content), 0)
                self.assertEqual(parent.metadata["type"], "parent")
                self.assertIsNotNone(parent.children, "父文档应该有children属性")
                
            # 验证子文档
            for child in child_segments:
                self.assertIsNotNone(child.page_content)
                self.assertGreater(len(child.page_content), 0)
                self.assertEqual(child.metadata["type"], "child")
                self.assertIn("parent_id", child.metadata)
                
            # 验证父子关系
            for parent in parent_segments:
                child_count = len([c for c in child_segments if c.metadata["parent_id"] == parent.id])
                self.assertEqual(len(parent.children), child_count, 
                               f"父文档 {parent.id} 的子文档数量不匹配")
                
        except Exception as e:
            logger.error(f"父子分割过程中出错: {str(e)}", exc_info=True)
            raise
            
        logger.debug("测试完成")

if __name__ == "__main__":
    unittest.main() 