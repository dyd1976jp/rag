"""测试PDF文档分割功能"""

import os
import unittest
from pathlib import Path
import logging
import io
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
import gc
import torch
import numpy as np
import faiss

from app.rag.models import Document, DocumentSegment
from app.rag.document_splitter import Rule, SplitMode, DocumentSplitter, QADocumentSplitter, ParentChildDocumentSplitter
from app.rag.pdf_processor import PDFProcessor
from app.rag.text_splitter import FixedRecursiveCharacterTextSplitter
from app.core.embedding import LMStudioEmbeddings

class TestPDFSplitting(unittest.TestCase):
    def setUp(self):
        """测试前的准备工作"""
        self.test_dir = Path(__file__).parent
        self.split_results_dir = self.test_dir / "split_results"
        os.makedirs(self.split_results_dir, exist_ok=True)
        
        # 设置默认环境变量
        os.environ["CHUNK_SIZE"] = "100"
        os.environ["CHUNK_OVERLAP"] = "20"
        os.environ["SPLIT_BY_PARAGRAPH"] = "true"
        
        # 创建必要的目录
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = self.test_dir / "results"
        self.vectors_dir = self.test_dir / "vectors"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.vectors_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建测试用的处理器
        self.pdf_processor = PDFProcessor()
        self.embedding_model = LMStudioEmbeddings()
        
        # 创建文档分割器
        self.paragraph_splitter = DocumentSplitter()
        self.qa_splitter = QADocumentSplitter()
        self.parent_child_splitter = ParentChildDocumentSplitter()
        
        # 使用data/uploads目录下的PDF文件
        project_root = Path(__file__).parent.parent.parent.parent.parent
        self.test_pdf = str(project_root / "data" / "uploads" / "初赛训练数据集.pdf")
        if not os.path.exists(self.test_pdf):
            raise FileNotFoundError(f"测试文件不存在: {self.test_pdf}")
        
        print(f"使用测试文件: {self.test_pdf}")

    def save_result_to_json(self, document: Document, source_file: str):
        """将处理结果保存为JSON文件"""
        # 创建输出文件名
        output_filename = f"{Path(source_file).stem}_result.json"
        output_path = self.output_dir / output_filename
        
        # 准备JSON数据
        result = {
            "source_file": source_file,
            "document": document.model_dump()  # 使用 pydantic 的 model_dump() 方法
        }
        
        # 写入JSON文件
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        print(f"处理结果已保存到: {output_path}")
        return output_path
        
    def save_segments_to_json(self, segments: List[DocumentSegment], source_file: str, split_mode: str):
        """保存分割结果到JSON文件"""
        # 创建输出文件名
        output_filename = f"{Path(source_file).stem}_{split_mode}_segments.json"
        output_path = self.vectors_dir / output_filename
        
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
            # 创建父块字典，用于快速查找
            parent_dict = {}
            for segment in segments:
                if segment.metadata["type"] == "parent":
                    parent_dict[segment.id] = {
                        "id": segment.id,
                        "content": segment.page_content,
                        "metadata": segment.metadata,
                        "children": []
                    }
                    
            # 将子块添加到对应的父块中
            for segment in segments:
                if segment.metadata["type"] == "child":
                    parent_id = segment.metadata["parent_id"]
                    if parent_id in parent_dict:
                        parent_dict[parent_id]["children"].append({
                            "id": segment.id,
                            "content": segment.page_content,
                            "metadata": segment.metadata
                        })
                        
            results["segments"] = list(parent_dict.values())
        else:
            # 对于其他模式，直接保存片段列表
            results["segments"] = [
                {
                    "id": segment.id,
                    "content": segment.page_content,
                    "metadata": segment.metadata
                }
                for segment in segments
            ]
            
        # 写入JSON文件
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        print(f"分割结果已保存到: {output_path}")
        return output_path

    def test_parent_child_splitting(self):
        """测试父子分割"""
        # 1. 处理PDF文件
        document = Document(
            page_content="",
            metadata={"source": self.test_pdf},
            source=self.test_pdf
        )
        document = self.pdf_processor.process_pdf(self.test_pdf, document)
        self.assertIsNotNone(document)
        self.assertTrue(len(document.page_content) > 0)
        
        # 保存原始文档
        self.save_result_to_json(document, self.test_pdf)
        
        # 2. 创建分割规则
        rule = Rule(
            mode=SplitMode.PARENT_CHILD,
            max_tokens=1024,  # 父块大小
            chunk_overlap=200,  # 父块重叠
            fixed_separator="\n\n",  # 父块分隔符
            subchunk_max_tokens=512,  # 子块大小
            subchunk_overlap=50,  # 子块重叠
            subchunk_separator="\n",  # 子块分隔符
            clean_text=True,
            keep_separator=True
        )
        
        # 3. 执行父子分割
        segments = self.parent_child_splitter.split_documents([document], rule)
        self.assertTrue(len(segments) > 0)
        
        # 4. 生成向量嵌入
        for segment in segments:
            embedding = self.embedding_model.embed_documents([segment.page_content])[0]
            segment.embedding = embedding
            
            # 验证向量
            self.assertIsNotNone(segment.embedding)
            self.assertTrue(len(segment.embedding) > 0)
            
            # 验证元数据
            self.assertIn("type", segment.metadata)
            if segment.metadata["type"] == "parent":
                self.assertNotIn("parent_id", segment.metadata)
            else:
                self.assertIn("parent_id", segment.metadata)
        
        # 5. 保存结果
        self.save_segments_to_json(segments, self.test_pdf, "parent_child")
        
        # 6. 构建FAISS索引
        dimension = len(segments[0].embedding)  # 使用向量长度而不是 shape
        index = faiss.IndexFlatL2(dimension)
        vectors = np.array([segment.embedding for segment in segments])  # 转换为 numpy 数组
        index.add(vectors)
        
        # 验证索引
        self.assertEqual(index.ntotal, len(segments))

    def test_parent_child_splitting_without_vectors(self):
        """测试不带向量的父子分割"""
        # 1. 处理PDF文件
        document = Document(
            page_content="",
            metadata={"source": self.test_pdf},
            source=self.test_pdf
        )
        document = self.pdf_processor.process_pdf(self.test_pdf, document)
        self.assertIsNotNone(document)
        self.assertTrue(len(document.page_content) > 0)
        
        # 2. 创建分割规则
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
        
        # 3. 执行父子分割
        segments = self.parent_child_splitter.split_documents([document], rule)
        self.assertTrue(len(segments) > 0)
        
        # 4. 验证结果
        parent_segments = [s for s in segments if s.metadata["type"] == "parent"]
        child_segments = [s for s in segments if s.metadata["type"] == "child"]
        
        self.assertTrue(len(parent_segments) > 0)
        self.assertTrue(len(child_segments) > 0)
        
        # 验证父子关系
        for child in child_segments:
            parent_id = child.metadata["parent_id"]
            parent = next((p for p in parent_segments if p.id == parent_id), None)
            self.assertIsNotNone(parent)
        
        # 5. 保存结果
        self.save_segments_to_json(segments, self.test_pdf, "parent_child_no_vectors")

if __name__ == "__main__":
    unittest.main() 