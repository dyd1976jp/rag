"""
测试不同分割参数的效果并保存结果
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from app.rag.document_splitter import DocumentSplitter, HierarchicalDocumentSplitter
from app.rag.models import Document

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('splitting_test.log')
    ]
)
logger = logging.getLogger(__name__)

def create_test_document() -> Document:
    """创建测试文档"""
    test_text = """
第一章：文档分割测试

1.1 简介
这是一个用于测试文档分割功能的示例文本。它包含多个章节、段落和句子。
这样的结构可以帮助我们测试不同的分割参数效果。

1.2 主要内容
本测试文档包含了多种文本结构：
- 章节标题
- 段落
- 列表项
- 短句和长句的组合

1.3 技术细节
在这一部分，我们添加一些较长的技术描述。
文档分割是RAG（检索增强生成）系统中的关键步骤。
好的分割策略可以提高检索的准确性和生成的质量。
我们需要考虑以下几个关键因素：
1. 分块大小
2. 重叠长度
3. 分隔符选择
4. 语义完整性

第二章：测试场景

2.1 基本场景
这里我们测试基本的分割功能。
包括使用默认参数的情况。

2.2 特殊场景
这部分包含一些特殊的文本结构：

表格示例：
| 参数 | 说明 |
| --- | --- |
| chunk_size | 分块大小 |
| overlap | 重叠长度 |

代码示例：
```python
def split_text(text):
    return text.split('\n\n')
```

2.3 边界情况
这里测试一些边界情况：
- 非常短的段落
- 特别长的段落，包含大量的连续文本，没有明显的分隔符或者自然断句点，这种情况下分割器应该如何处理呢？
- 包含特殊字符的文本 @#$%^&*
- 多语言混合文本 Hello 你好 こんにちは

第三章：总结

3.1 测试要点
- 分割的准确性
- 保持语义完整性
- 处理特殊情况的能力

3.2 结论
通过这个测试文档，我们可以全面评估分割器的性能。
结果将帮助我们优化分割参数和策略。
    """
    
    return Document(
        page_content=test_text,
        metadata={
            "source": "test_document",
            "created_at": datetime.now().isoformat(),
            "type": "test"
        }
    )

def test_splitting_parameters(document: Document, output_dir: str = "output/splitting_tests"):
    """测试不同的分割参数组合"""
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 定义要测试的参数组合
    test_configs = [
        {
            "name": "default",
            "params": {
                "chunk_size": 512,
                "chunk_overlap": 50,
                "split_by_paragraph": True,
                "split_by_sentence": True
            }
        },
        {
            "name": "large_chunks",
            "params": {
                "chunk_size": 1024,
                "chunk_overlap": 100,
                "split_by_paragraph": True,
                "split_by_sentence": True
            }
        },
        {
            "name": "small_chunks",
            "params": {
                "chunk_size": 256,
                "chunk_overlap": 30,
                "split_by_paragraph": True,
                "split_by_sentence": True
            }
        },
        {
            "name": "paragraph_only",
            "params": {
                "chunk_size": 512,
                "chunk_overlap": 50,
                "split_by_paragraph": True,
                "split_by_sentence": False
            }
        },
        {
            "name": "sentence_only",
            "params": {
                "chunk_size": 512,
                "chunk_overlap": 50,
                "split_by_paragraph": False,
                "split_by_sentence": True
            }
        }
    ]
    
    # 测试每个配置
    results = {}
    for config in test_configs:
        logger.info(f"\n测试配置: {config['name']}")
        logger.info(f"参数: {config['params']}")
        
        # 设置环境变量
        for key, value in config["params"].items():
            os.environ[key.upper()] = str(value)
        
        # 创建分割器
        splitter = DocumentSplitter()
        
        try:
            # 执行分割
            segments = splitter.split_document(document)
            
            # 收集结果
            segments_data = []
            for i, segment in enumerate(segments):
                segment_data = {
                    "id": i,
                    "content": segment.page_content,
                    "length": len(segment.page_content),
                    "metadata": segment.metadata
                }
                segments_data.append(segment_data)
            
            # 计算统计信息
            stats = {
                "total_segments": len(segments),
                "total_chars": sum(len(seg.page_content) for seg in segments),
                "avg_length": sum(len(seg.page_content) for seg in segments) / len(segments) if segments else 0,
                "min_length": min(len(seg.page_content) for seg in segments) if segments else 0,
                "max_length": max(len(seg.page_content) for seg in segments) if segments else 0
            }
            
            results[config["name"]] = {
                "config": config["params"],
                "stats": stats,
                "segments": segments_data
            }
            
            logger.info(f"分割完成 - 段落数: {stats['total_segments']}, "
                       f"平均长度: {stats['avg_length']:.2f}, "
                       f"最短: {stats['min_length']}, "
                       f"最长: {stats['max_length']}")
            
        except Exception as e:
            logger.error(f"配置 {config['name']} 测试失败: {str(e)}")
            results[config["name"]] = {
                "config": config["params"],
                "error": str(e)
            }
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"splitting_test_results_{timestamp}.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n测试结果已保存至: {output_file}")
    return results

def test_hierarchical_splitting(document: Document, output_dir: str = "output/splitting_tests"):
    """测试层级分割的不同参数组合"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 定义要测试的层级分割参数组合
    test_configs = [
        {
            "name": "default_hierarchical",
            "params": {
                "parent_chunk_size": 1024,
                "parent_chunk_overlap": 200,
                "parent_separator": "\n\n",
                "child_chunk_size": 512,
                "child_chunk_overlap": 50,
                "child_separator": "\n"
            }
        },
        {
            "name": "large_parent_small_child",
            "params": {
                "parent_chunk_size": 2048,
                "parent_chunk_overlap": 300,
                "parent_separator": "\n\n",
                "child_chunk_size": 256,
                "child_chunk_overlap": 30,
                "child_separator": "。"
            }
        },
        {
            "name": "balanced_sizes",
            "params": {
                "parent_chunk_size": 800,
                "parent_chunk_overlap": 100,
                "parent_separator": "\n\n",
                "child_chunk_size": 400,
                "child_chunk_overlap": 50,
                "child_separator": "。"
            }
        }
    ]
    
    results = {}
    for config in test_configs:
        logger.info(f"\n测试层级分割配置: {config['name']}")
        logger.info(f"参数: {config['params']}")
        
        try:
            # 创建层级分割器
            splitter = HierarchicalDocumentSplitter(**config["params"])
            
            # 执行分割
            parent_docs = splitter.split_document(document)
            
            # 收集结果
            parent_segments = []
            total_children = 0
            
            for i, parent in enumerate(parent_docs):
                children_data = []
                if hasattr(parent, "children") and parent.children:
                    total_children += len(parent.children)
                    for j, child in enumerate(parent.children):
                        child_data = {
                            "id": j,
                            "content": child.page_content,
                            "length": len(child.page_content),
                            "metadata": child.metadata
                        }
                        children_data.append(child_data)
                
                parent_data = {
                    "id": i,
                    "content": parent.page_content,
                    "length": len(parent.page_content),
                    "metadata": parent.metadata,
                    "children": children_data
                }
                parent_segments.append(parent_data)
            
            # 计算统计信息
            stats = {
                "total_parents": len(parent_docs),
                "total_children": total_children,
                "avg_parent_length": sum(len(p.page_content) for p in parent_docs) / len(parent_docs) if parent_docs else 0,
                "avg_children_per_parent": total_children / len(parent_docs) if parent_docs else 0
            }
            
            results[config["name"]] = {
                "config": config["params"],
                "stats": stats,
                "segments": parent_segments
            }
            
            logger.info(f"分割完成 - 父段落数: {stats['total_parents']}, "
                       f"子段落数: {stats['total_children']}, "
                       f"平均父段落长度: {stats['avg_parent_length']:.2f}, "
                       f"平均每个父段落的子段落数: {stats['avg_children_per_parent']:.2f}")
            
        except Exception as e:
            logger.error(f"配置 {config['name']} 测试失败: {str(e)}")
            results[config["name"]] = {
                "config": config["params"],
                "error": str(e)
            }
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"hierarchical_splitting_test_results_{timestamp}.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n测试结果已保存至: {output_file}")
    return results

def main():
    """主函数"""
    try:
        logger.info("开始文档分割参数测试")
        
        # 创建测试文档
        test_doc = create_test_document()
        
        # 测试普通分割
        logger.info("\n=== 测试普通分割参数 ===")
        regular_results = test_splitting_parameters(test_doc)
        
        # 测试层级分割
        logger.info("\n=== 测试层级分割参数 ===")
        hierarchical_results = test_hierarchical_splitting(test_doc)
        
        logger.info("\n所有测试完成")
        
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}")
        raise

if __name__ == "__main__":
    main() 