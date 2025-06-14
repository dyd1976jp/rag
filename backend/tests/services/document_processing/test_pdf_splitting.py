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
from enum import Enum

import pypdfium2
import numpy as np
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    Language,
    TextSplitter
)
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
import faiss

class SplitMode(str, Enum):
    """分割模式"""
    PARAGRAPH = "paragraph"  # 段落分割
    QA = "qa"  # 问答分割
    PARENT_CHILD = "parent_child"  # 父子分割

class Rule:
    """分割规则"""
    def __init__(
        self,
        mode: SplitMode,
        max_tokens: int = 1000,
        chunk_overlap: int = 200,
        fixed_separator: str = "\n\n",
        separators: Optional[List[str]] = None,
        clean_text: bool = True,
        keep_separator: bool = True,
        remove_empty_lines: bool = True,
        normalize_whitespace: bool = True,
        min_content_length: int = 10,  # 添加最小内容长度参数
        # 子文档相关参数
        subchunk_max_tokens: Optional[int] = None,
        subchunk_overlap: Optional[int] = None,
        subchunk_separator: Optional[str] = None
    ):
        self.mode = mode
        self.max_tokens = max_tokens
        self.chunk_overlap = chunk_overlap
        self.fixed_separator = fixed_separator
        self.separators = separators or ["\n\n", "。", "！", "？", ". ", " ", ""]
        self.clean_text = clean_text
        self.keep_separator = keep_separator
        self.remove_empty_lines = remove_empty_lines
        self.normalize_whitespace = normalize_whitespace
        self.min_content_length = min_content_length  # 添加最小内容长度属性
        # 子文档参数
        self.subchunk_max_tokens = subchunk_max_tokens
        self.subchunk_overlap = subchunk_overlap
        self.subchunk_separator = subchunk_separator

class FixedRecursiveCharacterTextSplitter(TextSplitter):
    """固定分隔符递归文本分割器"""
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        length_function: Optional[Callable[[str], int]] = None,
        fixed_separator: str = "\n\n",
        separators: Optional[List[str]] = None,
        keep_separator: bool = True,
        **kwargs: Any
    ):
        """初始化分割器
        
        Args:
            chunk_size: 块大小
            chunk_overlap: 重叠大小
            length_function: 长度计算函数
            fixed_separator: 固定分隔符
            separators: 分隔符列表
            keep_separator: 是否保留分隔符
        """
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=length_function or len,
            keep_separator=keep_separator,
            **kwargs
        )
        self._fixed_separator = fixed_separator
        self._separators = separators or ["\n\n", "。", "！", "？", ". ", " ", ""]
        
    def split_text(self, text: str) -> List[str]:
        """分割文本"""
        # 1. 使用固定分隔符进行初始分割
        if self._fixed_separator:
            chunks = text.split(self._fixed_separator)
        else:
            chunks = [text]
            
        # 2. 处理每个分块
        final_chunks = []
        chunks_lengths = [self._length_function(chunk) for chunk in chunks]  # 修复：为每个chunk计算长度
        
        for chunk, chunk_length in zip(chunks, chunks_lengths):
            if chunk_length > self._chunk_size:
                # 对超长块进行递归分割
                final_chunks.extend(self._recursive_split(chunk))
            else:
                final_chunks.append(chunk)
                
        return final_chunks
        
    def _recursive_split(self, text: str) -> List[str]:
        """递归分割文本"""
        # 1. 选择合适的分隔符
        separator = self._separators[-1]
        new_separators = []
        
        for i, _s in enumerate(self._separators):
            if _s == "":
                separator = _s
                break
            if _s in text:
                separator = _s
                new_separators = self._separators[i + 1:]
                break
                
        # 2. 使用选定的分隔符分割
        if separator:
            if separator == " ":
                splits = text.split()
            else:
                splits = text.split(separator)
        else:
            splits = list(text)
            
        # 3. 过滤空白文本
        splits = [s for s in splits if s.strip()]
        
        # 4. 处理分割结果
        final_chunks = []
        _good_splits = []
        _good_splits_lengths = []
        
        _separator = "" if not self._keep_separator else separator
        split_lengths = [self._length_function(split) for split in splits]  # 修复：为每个split计算长度
        
        if separator != "":
            # 处理有分隔符的情况
            for split, split_len in zip(splits, split_lengths):
                if split_len < self._chunk_size:
                    _good_splits.append(split)
                    _good_splits_lengths.append(split_len)
                else:
                    # 处理已收集的分片
                    if _good_splits:
                        merged = self._merge_splits(_good_splits, _separator, _good_splits_lengths)
                        final_chunks.extend(merged)
                        _good_splits = []
                        _good_splits_lengths = []
                        
                    # 处理当前超长分片
                    if not new_separators:
                        final_chunks.append(split)
                    else:
                        # 递归处理
                        sub_chunks = self._recursive_split(split)
                        final_chunks.extend(sub_chunks)
                        
            # 处理最后的分片
            if _good_splits:
                merged = self._merge_splits(_good_splits, _separator, _good_splits_lengths)
                final_chunks.extend(merged)
                
        else:
            # 处理无分隔符的情况
            current_chunk = ""
            current_length = 0
            overlap_chunk = ""
            overlap_length = 0
            
            for split, split_len in zip(splits, split_lengths):
                # 检查是否可以添加到当前块
                if current_length + split_len <= self._chunk_size - self._chunk_overlap:
                    current_chunk += split
                    current_length += split_len
                elif current_length + split_len <= self._chunk_size:
                    # 可以添加但需要开始重叠部分
                    current_chunk += split
                    current_length += split_len
                    overlap_chunk += split
                    overlap_length += split_len
                else:
                    # 需要创建新块
                    final_chunks.append(current_chunk)
                    current_chunk = overlap_chunk + split
                    current_length = split_len + overlap_length
                    overlap_chunk = ""
                    overlap_length = 0
                    
            # 添加最后一个块
            if current_chunk:
                final_chunks.append(current_chunk)
                
        return final_chunks
        
    def _merge_splits(
        self,
        splits: List[str],
        separator: str,
        lengths: List[int]
    ) -> List[str]:
        """合并分片
        
        Args:
            splits: 待合并的分片列表
            separator: 分隔符
            lengths: 分片长度列表
            
        Returns:
            合并后的分片列表
        """
        # 1. 初始化结果列表
        merged_chunks = []
        current_chunk = []
        current_length = 0
        
        # 2. 处理每个分片
        for split, length in zip(splits, lengths):
            # 检查是否需要创建新块
            if current_length + length > self._chunk_size:
                if current_chunk:
                    # 合并当前块
                    merged_chunks.append(separator.join(current_chunk))
                    # 开始新块，使用重叠
                    overlap_start = max(0, len(current_chunk) - self._chunk_overlap)
                    current_chunk = current_chunk[overlap_start:]
                    current_length = sum(lengths[max(0, len(splits) - self._chunk_overlap):])
            
            # 添加当前分片
            current_chunk.append(split)
            current_length += length
        
        # 3. 添加最后一个块
        if current_chunk:
            merged_chunks.append(separator.join(current_chunk))
            
        return merged_chunks

class Document:
    """简化版的文档类"""
    def __init__(self, page_content: str, metadata: dict = None):
        self.page_content = page_content
        self.metadata = metadata or {}
        
    def to_dict(self) -> dict:
        """将文档对象转换为字典"""
        return {
            "content": self.page_content,
            "metadata": self.metadata,
            "stats": {
                "content_length": len(self.page_content),
                "extracted_at": datetime.now().isoformat()
            }
        }

class DocumentSegment:
    """文档片段类"""
    def __init__(self, content: str, metadata: dict = None):
        self.id = metadata.get("id") if metadata else None
        self.content = content
        self.metadata = metadata or {}
        self.embedding = None
        
    def to_dict(self) -> dict:
        """将文档片段对象转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "embedding": self.embedding.tolist() if self.embedding is not None else None,
            "stats": {
                "content_length": len(self.content),
                "extracted_at": datetime.now().isoformat()
            }
        }

class DocumentSplitter:
    """文档分割器基类"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def clean_text(self, text: str, rule: Rule) -> str:
        """清理文本
        
        Args:
            text: 待清理的文本
            rule: 分割规则
            
        Returns:
            清理后的文本
        """
        if not rule.clean_text:
            return text
            
        # 1. 移除多余的空白字符
        if rule.normalize_whitespace:
            text = " ".join(text.split())
            
        # 2. 移除空行
        if rule.remove_empty_lines:
            lines = text.splitlines()
            lines = [line.strip() for line in lines if line.strip()]
            text = "\n".join(lines)
            
        return text
        
    def create_text_splitter(self, rule: Rule) -> TextSplitter:
        """创建文本分割器"""
        return FixedRecursiveCharacterTextSplitter(
            chunk_size=rule.max_tokens,
            chunk_overlap=rule.chunk_overlap,
            fixed_separator=rule.fixed_separator,
            separators=rule.separators,
            keep_separator=rule.keep_separator
        )
        
    def split_documents(self, documents: List[Document], rule: Rule) -> List[DocumentSegment]:
        """分割文档
        
        Args:
            documents: 待分割的文档列表
            rule: 分割规则
            
        Returns:
            文档片段列表
        """
        try:
            self.logger.info(f"开始使用 {rule.mode} 模式分割文档")
            
            text_splitter = self.create_text_splitter(rule)
            segments = []
            
            for doc in documents:
                # 1. 清理文本
                cleaned_text = self.clean_text(doc.page_content, rule)
                
                # 2. 分割文本
                texts = text_splitter.split_text(cleaned_text)
                
                # 3. 创建文档片段
                for i, text in enumerate(texts):
                    # 跳过过短的文本
                    if len(text.strip()) < rule.min_content_length:
                        continue
                        
                    # 创建片段
                    segment = DocumentSegment(
                        content=text,
                        metadata={
                            "id": f"{doc.metadata.get('source', 'unknown')}_{i}",
                            "source": doc.metadata.get("source"),
                            "page": doc.metadata.get("page", 1),
                            "chunk_index": i,
                            "total_chunks": len(texts),
                            "type": "segment",
                            "created_at": datetime.now().isoformat()
                        }
                    )
                    segments.append(segment)
                    
            self.logger.info(f"文档分割完成，生成了 {len(segments)} 个片段")
            return segments
            
        except Exception as e:
            self.logger.error(f"文档分割失败: {str(e)}")
            raise
            
    def save_segments(self, segments: List[DocumentSegment], output_dir: str):
        """保存文档片段
        
        Args:
            segments: 文档片段列表
            output_dir: 输出目录
        """
        try:
            # 1. 创建输出目录
            os.makedirs(output_dir, exist_ok=True)
            
            # 2. 准备输出数据
            output_data = {
                "segments": [segment.to_dict() for segment in segments],
                "metadata": {
                    "total_segments": len(segments),
                    "created_at": datetime.now().isoformat()
                }
            }
            
            # 3. 保存JSON文件
            output_file = os.path.join(output_dir, f"segments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"文档片段已保存到: {output_file}")
            
        except Exception as e:
            self.logger.error(f"保存文档片段失败: {str(e)}")
            raise

class QADocumentSplitter(DocumentSplitter):
    """问答文档分割器"""
    def split_documents(self, documents: List[Document], rule: Rule) -> List[DocumentSegment]:
        """分割文档为问答对"""
        try:
            self.logger.info("开始问答分割")
            
            segments = []
            for doc in documents:
                # 查找所有问题和答案
                qa_pairs = self._extract_qa_pairs(doc.page_content)
                
                # 创建文档片段
                for i, (question, answer) in enumerate(qa_pairs):
                    segment = DocumentSegment(
                        content=f"问题：{question}\n答案：{answer}",
                        metadata={
                            "id": f"{doc.metadata.get('source', 'unknown')}_qa_{i}",
                            "source": doc.metadata.get("source"),
                            "qa_index": i,
                            "total_qa_pairs": len(qa_pairs),
                            "type": "qa",
                            "question": question,
                            "answer": answer
                        }
                    )
                    segments.append(segment)
                    
            self.logger.info(f"问答分割完成，生成了 {len(segments)} 个问答对")
            return segments
            
        except Exception as e:
            self.logger.error(f"问答分割失败: {str(e)}")
            raise
            
    def _extract_qa_pairs(self, text: str) -> List[tuple]:
        """从文本中提取问答对"""
        # 这里使用简单的规则来识别问答对
        # 可以根据实际需求修改识别规则
        qa_pairs = []
        lines = text.split("\n")
        current_question = None
        current_answer = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 识别问题（以问号结尾的句子）
            if line.endswith("？") or line.endswith("?"):
                if current_question and current_answer:
                    qa_pairs.append((current_question, "\n".join(current_answer)))
                current_question = line
                current_answer = []
            elif current_question:
                current_answer.append(line)
                
        # 添加最后一个问答对
        if current_question and current_answer:
            qa_pairs.append((current_question, "\n".join(current_answer)))
            
        return qa_pairs

class ParentChildDocumentSplitter(DocumentSplitter):
    """父子文档分割器"""
    def __init__(self, embedding_model=None):
        """初始化分割器
        
        Args:
            embedding_model: 向量化模型,如果为None则不进行向量化
        """
        super().__init__()
        self.embedding_model = embedding_model
        
    def split_documents(self, documents: List[Document], rule: Rule) -> List[DocumentSegment]:
        """分割文档为父子结构
        
        Args:
            documents: 待分割的文档列表
            rule: 分割规则
            
        Returns:
            文档片段列表
        """
        try:
            self.logger.info("开始父子分割")
            
            # 创建父文档分割器
            parent_splitter = self.create_text_splitter(Rule(
                mode=SplitMode.PARAGRAPH,
                max_tokens=rule.max_tokens,
                chunk_overlap=rule.chunk_overlap,
                fixed_separator=rule.fixed_separator,
                separators=rule.separators,
                keep_separator=rule.keep_separator
            ))
            
            segments = []
            for doc in documents:
                # 1. 清理文本
                cleaned_text = self.clean_text(doc.page_content, rule)
                
                # 2. 分割父文档
                parent_texts = parent_splitter.split_text(cleaned_text)
                
                # 3. 处理每个父文档
                for i, parent_text in enumerate(parent_texts):
                    if len(parent_text.strip()) < rule.min_content_length:
                        continue
                        
                    # 创建父文档片段
                    parent_segment = DocumentSegment(
                        content=parent_text,
                        metadata={
                            "id": f"{doc.metadata.get('source', 'unknown')}_parent_{i}",
                            "source": doc.metadata.get("source"),
                            "page": doc.metadata.get("page", 1),
                            "chunk_index": i,
                            "total_chunks": len(parent_texts),
                            "type": "parent",
                            "created_at": datetime.now().isoformat()
                        }
                    )
                    
                    # 4. 生成父文档向量
                    if self.embedding_model:
                        try:
                            parent_segment.embedding = np.array(
                                self.embedding_model.embed_documents([parent_text])[0]
                            )
                        except Exception as e:
                            self.logger.error(f"生成父文档向量失败: {str(e)}")
                            
                    segments.append(parent_segment)
                    
                    # 5. 分割子文档
                    child_texts = self._split_into_children(
                        parent_text=parent_text,
                        rule=rule
                    )
                    
                    # 6. 创建子文档片段
                    for j, child_text in enumerate(child_texts):
                        if len(child_text.strip()) < rule.min_content_length:
                            continue
                            
                        child_segment = DocumentSegment(
                            content=child_text,
                            metadata={
                                "id": f"{doc.metadata.get('source', 'unknown')}_parent_{i}_child_{j}",
                                "source": doc.metadata.get("source"),
                                "page": doc.metadata.get("page", 1),
                                "parent_id": parent_segment.id,
                                "chunk_index": j,
                                "total_chunks": len(child_texts),
                                "type": "child",
                                "created_at": datetime.now().isoformat()
                            }
                        )
                        
                        # 7. 生成子文档向量
                        if self.embedding_model:
                            try:
                                child_segment.embedding = np.array(
                                    self.embedding_model.embed_documents([child_text])[0]
                                )
                            except Exception as e:
                                self.logger.error(f"生成子文档向量失败: {str(e)}")
                                
                        segments.append(child_segment)
                        
            self.logger.info(f"父子分割完成，生成了 {len(segments)} 个片段")
            return segments
            
        except Exception as e:
            self.logger.error(f"父子分割失败: {str(e)}")
            raise
            
    def _split_into_children(self, parent_text: str, rule: Rule) -> List[str]:
        """将父文档分割为子文档
        
        Args:
            parent_text: 父文档文本
            rule: 分割规则
            
        Returns:
            子文档文本列表
        """
        # 1. 创建子文档分割器
        child_splitter = self.create_text_splitter(Rule(
            mode=SplitMode.PARAGRAPH,
            max_tokens=rule.max_tokens // 2,  # 子文档长度为父文档的一半
            chunk_overlap=rule.chunk_overlap // 2,  # 子文档重叠为父文档的一半
            fixed_separator=rule.fixed_separator,
            separators=rule.separators,
            keep_separator=rule.keep_separator
        ))
        
        # 2. 分割子文档
        child_texts = child_splitter.split_text(parent_text)
        
        return child_texts
        
    def save_segments_with_vectors(self, segments: List[DocumentSegment], output_dir: str):
        """保存带向量的文档片段
        
        Args:
            segments: 文档片段列表
            output_dir: 输出目录
        """
        try:
            # 1. 创建输出目录
            os.makedirs(output_dir, exist_ok=True)
            
            # 2. 准备输出数据
            parent_dict = {}
            
            # 3. 处理所有父块
            for segment in segments:
                if segment.metadata["type"] == "parent":
                    parent_dict[segment.id] = {
                        "id": segment.id,
                        "content": segment.content,
                        "metadata": segment.metadata,
                        "embedding": segment.embedding.tolist() if segment.embedding is not None else None,
                        "children": []
                    }
            
            # 4. 将子块添加到对应的父块中
            for segment in segments:
                if segment.metadata["type"] == "child":
                    parent_id = segment.metadata["parent_id"]
                    if parent_id in parent_dict:
                        parent_dict[parent_id]["children"].append({
                            "id": segment.id,
                            "content": segment.content,
                            "metadata": segment.metadata,
                            "embedding": segment.embedding.tolist() if segment.embedding is not None else None
                        })
            
            # 5. 准备最终输出
            output_data = {
                "segments": list(parent_dict.values()),
                "metadata": {
                    "total_segments": len(segments),
                    "total_parents": len(parent_dict),
                    "total_children": sum(len(p["children"]) for p in parent_dict.values()),
                    "created_at": datetime.now().isoformat()
                }
            }
            
            # 6. 添加统计信息
            parent_lengths = [len(s["content"]) for s in output_data["segments"]]
            child_lengths = [len(c["content"]) for p in output_data["segments"] for c in p["children"]]
            
            output_data["metadata"]["stats"] = {
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
            
            # 7. 保存JSON文件
            output_file = os.path.join(output_dir, f"segments_with_vectors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"带向量的文档片段已保存到: {output_file}")
            
            # 8. 构建FAISS索引
            if any(s.embedding is not None for s in segments):
                self._build_and_save_index(segments, output_dir)
            
        except Exception as e:
            self.logger.error(f"保存带向量的文档片段失败: {str(e)}")
            raise
            
    def _build_and_save_index(self, segments: List[DocumentSegment], output_dir: str):
        """构建并保存FAISS索引
        
        Args:
            segments: 文档片段列表
            output_dir: 输出目录
        """
        try:
            # 1. 分别为父文档和子文档构建索引
            parent_segments = [s for s in segments if s.metadata["type"] == "parent" and s.embedding is not None]
            child_segments = [s for s in segments if s.metadata["type"] == "child" and s.embedding is not None]
            
            # 2. 构建父文档索引
            if parent_segments:
                parent_vectors = np.vstack([s.embedding for s in parent_segments])
                parent_index = faiss.IndexFlatL2(parent_vectors.shape[1])
                parent_index.add(parent_vectors)
                
                # 保存父文档索引
                parent_index_path = os.path.join(output_dir, "parent_index.faiss")
                faiss.write_index(parent_index, parent_index_path)
                self.logger.info(f"父文档索引已保存到: {parent_index_path}")
                
                # 保存父文档ID映射
                parent_id_map = {i: s.id for i, s in enumerate(parent_segments)}
                parent_id_map_path = os.path.join(output_dir, "parent_id_map.json")
                with open(parent_id_map_path, "w", encoding="utf-8") as f:
                    json.dump(parent_id_map, f, ensure_ascii=False, indent=2)
            
            # 3. 构建子文档索引
            if child_segments:
                child_vectors = np.vstack([s.embedding for s in child_segments])
                child_index = faiss.IndexFlatL2(child_vectors.shape[1])
                child_index.add(child_vectors)
                
                # 保存子文档索引
                child_index_path = os.path.join(output_dir, "child_index.faiss")
                faiss.write_index(child_index, child_index_path)
                self.logger.info(f"子文档索引已保存到: {child_index_path}")
                
                # 保存子文档ID映射
                child_id_map = {i: s.id for i, s in enumerate(child_segments)}
                child_id_map_path = os.path.join(output_dir, "child_id_map.json")
                with open(child_id_map_path, "w", encoding="utf-8") as f:
                    json.dump(child_id_map, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            self.logger.error(f"构建和保存索引失败: {str(e)}")
            raise

class PDFProcessor:
    """PDF文档处理器"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def process_pdf(self, pdf_file_path: str, metadata: dict = None) -> Document:
        """处理PDF文件并返回文档对象"""
        try:
            self.logger.info(f"开始处理PDF文件: {pdf_file_path}")
            text = self._extract_text_from_pdf(pdf_file_path)
            
            # 创建文档对象
            document = Document(
                page_content=text,
                metadata=metadata or {}
            )
            
            self.logger.info(f"PDF处理完成: {pdf_file_path}, 文本长度: {len(text)}")
            return document
        except Exception as e:
            self.logger.error(f"PDF处理失败: {str(e)}")
            raise
            
    def process_pdf_bytes(self, pdf_bytes: bytes, metadata: dict = None) -> Document:
        """处理PDF字节数据并返回文档对象"""
        try:
            self.logger.info("开始处理PDF字节数据")
            text = self._extract_text_from_pdf_bytes(pdf_bytes)
            
            # 创建文档对象
            document = Document(
                page_content=text,
                metadata=metadata or {}
            )
            
            self.logger.info(f"PDF字节数据处理完成, 文本长度: {len(text)}")
            return document
        except Exception as e:
            self.logger.error(f"PDF字节数据处理失败: {str(e)}")
            raise
    
    def _extract_text_from_pdf(self, pdf_file_path: str) -> str:
        """从PDF文件中提取文本"""
        try:
            # 使用pypdfium2打开PDF文件
            pdf_document = pypdfium2.PdfDocument(pdf_file_path)
            text_parts = []
            
            try:
                # 逐页提取文本
                for page_num, page in enumerate(pdf_document, 1):
                    text_page = page.get_textpage()
                    content = text_page.get_text_range()
                    text_page.close()
                    page.close()
                    
                    # 清理文本
                    content = self._clean_text(content)
                    if content.strip():
                        # 添加页码信息
                        text_parts.append(f"[Page {page_num}]\n{content}")
            finally:
                pdf_document.close()
                
            # 使用双换行符连接页面文本
            return "\n\n".join(text_parts)
            
        except Exception as e:
            self.logger.error(f"提取PDF文本失败: {str(e)}")
            raise
            
    def _extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """从PDF字节数据中提取文本"""
        try:
            # 将字节数据转换为文件对象
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_document = pypdfium2.PdfDocument(pdf_file, autoclose=True)
            text_parts = []
            
            try:
                # 逐页提取文本
                for page_num, page in enumerate(pdf_document, 1):
                    text_page = page.get_textpage()
                    content = text_page.get_text_range()
                    text_page.close()
                    page.close()
                    
                    # 清理文本
                    content = self._clean_text(content)
                    if content.strip():
                        # 添加页码信息
                        text_parts.append(f"[Page {page_num}]\n{content}")
            finally:
                pdf_document.close()
                
            # 使用双换行符连接页面文本
            return "\n\n".join(text_parts)
            
        except Exception as e:
            self.logger.error(f"提取PDF字节数据文本失败: {str(e)}")
            raise
            
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""
        # 基本的文本清理
        text = text.strip()
        # 移除多余的空白字符
        text = " ".join(text.split())
        return text

class RAGProcessor:
    """RAG处理器，用于文档分割和向量化"""
    def __init__(self, 
                 chunk_size: int = 500,
                 chunk_overlap: int = 50,
                 model_name: str = "BAAI/bge-small-zh",
                 device: str = None):
        self.logger = logging.getLogger(__name__)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
        )
        
        # 自动检测设备
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.logger.info(f"使用设备: {device}")
        
        try:
            self.embedding_model = HuggingFaceBgeEmbeddings(
                model_name=model_name,
                model_kwargs={'device': device},
                encode_kwargs={'normalize_embeddings': True}
            )
            self.logger.info(f"成功加载嵌入模型: {model_name}")
        except Exception as e:
            self.logger.error(f"加载嵌入模型失败: {str(e)}")
            raise
        
    def process_document(self, document: Document) -> List[DocumentSegment]:
        """处理文档，返回文档片段列表"""
        try:
            self.logger.info("开始处理文档")
            
            # 分割文本
            self.logger.info("开始文本分割")
            texts = self.text_splitter.split_text(document.page_content)
            self.logger.info(f"文本分割完成，生成了 {len(texts)} 个文本片段")
            
            # 创建文档片段
            segments = []
            for i, text in enumerate(texts):
                segment = DocumentSegment(
                    content=text,
                    metadata={
                        **document.metadata,
                        "chunk_index": i,
                        "total_chunks": len(texts)
                    }
                )
                segments.append(segment)
            
            # 生成向量嵌入
            self.logger.info("开始生成向量嵌入")
            try:
                # 批量处理以减少内存使用
                batch_size = 32
                for i in range(0, len(segments), batch_size):
                    batch = segments[i:i + batch_size]
                    batch_texts = [segment.page_content for segment in batch]
                    
                    # 生成向量
                    embeddings = self.embedding_model.embed_documents(batch_texts)
                    
                    # 将向量添加到文档片段中
                    for segment, embedding in zip(batch, embeddings):
                        segment.embedding = np.array(embedding)
                    
                    # 清理内存
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    
                    self.logger.info(f"完成批次 {i//batch_size + 1}/{(len(segments)-1)//batch_size + 1}")
                
            except Exception as e:
                self.logger.error(f"生成向量嵌入失败: {str(e)}")
                raise
            
            self.logger.info(f"文档处理完成，生成了 {len(segments)} 个文档片段")
            return segments
            
        except Exception as e:
            self.logger.error(f"文档处理失败: {str(e)}")
            raise
            
    def build_index(self, segments: List[DocumentSegment]) -> Any:
        """构建FAISS索引"""
        try:
            self.logger.info("开始构建FAISS索引")
            
            if not segments:
                raise ValueError("没有文档片段可以构建索引")
                
            # 获取向量维度
            dimension = segments[0].embedding.shape[0]
            self.logger.info(f"向量维度: {dimension}")
            
            # 创建FAISS索引
            index = faiss.IndexFlatL2(dimension)
            
            # 添加向量到索引
            vectors = np.vstack([segment.embedding for segment in segments])
            index.add(vectors)
            
            self.logger.info(f"FAISS索引构建完成，包含 {len(segments)} 个向量")
            return index
            
        except Exception as e:
            self.logger.error(f"构建索引失败: {str(e)}")
            raise

class TestPDFSplitting(unittest.TestCase):
    def setUp(self):
        """测试前准备"""
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('pdf_splitting_test.log')
            ]
        )
        
        # 使用项目根目录下的data目录
        project_root = Path(__file__).parent.parent.parent.parent.parent
        self.test_dir = project_root / "data" / "uploads"
        self.output_dir = project_root / "data" / "results"
        self.vectors_dir = project_root / "data" / "vectors"
        
        # 创建必要的目录
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.vectors_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建测试用的处理器
        self.pdf_processor = PDFProcessor()
        self.rag_processor = RAGProcessor(
            chunk_size=500,
            chunk_overlap=50,
            device="cpu"  # 强制使用CPU以避免潜在的CUDA问题
        )
        
        # 创建文档分割器
        self.paragraph_splitter = DocumentSplitter()
        self.qa_splitter = QADocumentSplitter()
        self.parent_child_splitter = ParentChildDocumentSplitter()
        
        # 获取目录中的PDF文件
        self.pdf_files = [f for f in self.test_dir.glob("*.pdf")]
        if not self.pdf_files:
            raise ValueError(f"测试目录中没有找到PDF文件: {self.test_dir}")
        
        # 使用第一个PDF文件作为测试文件
        self.test_pdf = str(self.pdf_files[0])
        print(f"使用测试文件: {self.test_pdf}")

    def save_result_to_json(self, document: Document, source_file: str):
        """将处理结果保存为JSON文件"""
        # 创建输出文件名
        output_filename = f"{Path(source_file).stem}_result.json"
        output_path = self.output_dir / output_filename
        
        # 准备JSON数据
        result = {
            "source_file": source_file,
            "document": document.to_dict()
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
            # 先处理所有父块
            for segment in segments:
                if segment.metadata["type"] == "parent":
                    parent_dict[segment.id] = {
                        "id": segment.id,
                        "content": segment.content,
                        "metadata": segment.metadata,
                        "embedding": segment.embedding.tolist() if segment.embedding is not None else None,
                        "children": []
                    }
            
            # 将子块添加到对应的父块中
            for segment in segments:
                if segment.metadata["type"] == "child":
                    parent_id = segment.metadata["parent_id"]
                    if parent_id in parent_dict:
                        parent_dict[parent_id]["children"].append({
                            "id": segment.id,
                            "content": segment.content,
                            "metadata": segment.metadata,
                            "embedding": segment.embedding.tolist() if segment.embedding is not None else None
                        })
            
            # 使用父块列表作为segments
            results["segments"] = list(parent_dict.values())
            
            # 添加统计信息
            parent_lengths = [len(s["content"]) for s in results["segments"]]
            child_lengths = [len(c["content"]) for p in results["segments"] for c in p["children"]]
            
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
            results["segments"] = [segment.to_dict() for segment in segments]
            
            # 添加统计信息
            segment_lengths = [len(s.content) for s in segments]
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

    def test_paragraph_splitting(self):
        """测试段落分割"""
        # 首先处理PDF文件
        metadata = {
            "source": os.path.basename(self.test_pdf),
            "processed_at": datetime.now().isoformat()
        }
        document = self.pdf_processor.process_pdf(self.test_pdf, metadata)
        
        # 创建分割规则
        rule = Rule(
            mode=SplitMode.PARAGRAPH,
            max_tokens=500,
            chunk_overlap=50,
            fixed_separator="\n\n"
        )
        
        # 进行段落分割
        segments = self.paragraph_splitter.split_documents([document], rule)
        
        # 验证分割结果
        self.assertIsNotNone(segments)
        self.assertTrue(len(segments) > 0)
        for segment in segments:
            self.assertIsNotNone(segment.content)
            self.assertTrue(len(segment.content) > 0)
            self.assertEqual(segment.metadata["source"], os.path.basename(self.test_pdf))
            
        # 保存分割结果
        output_path = self.save_segments_to_json(segments, self.test_pdf, "paragraph")
        self.assertTrue(os.path.exists(output_path))

    def test_qa_splitting(self):
        """测试问答分割"""
        # 首先处理PDF文件
        metadata = {
            "source": os.path.basename(self.test_pdf),
            "processed_at": datetime.now().isoformat()
        }
        document = self.pdf_processor.process_pdf(self.test_pdf, metadata)
        
        # 创建分割规则
        rule = Rule(
            mode=SplitMode.QA,
            max_tokens=1000,
            chunk_overlap=0  # 问答模式不需要重叠
        )
        
        # 进行问答分割
        segments = self.qa_splitter.split_documents([document], rule)
        
        # 验证分割结果
        self.assertIsNotNone(segments)
        for segment in segments:
            self.assertIsNotNone(segment.page_content)
            self.assertTrue(len(segment.page_content) > 0)
            self.assertEqual(segment.metadata["source"], os.path.basename(self.test_pdf))
            self.assertEqual(segment.metadata["type"], "qa")
            self.assertIn("question", segment.metadata)
            self.assertIn("answer", segment.metadata)
            
        # 保存分割结果
        output_path = self.save_segments_to_json(segments, self.test_pdf, "qa")
        self.assertTrue(os.path.exists(output_path))

    def test_parent_child_splitting(self):
        """测试父子分割"""
        # 首先处理PDF文件
        metadata = {
            "source": os.path.basename(self.test_pdf),
            "processed_at": datetime.now().isoformat()
        }
        document = self.pdf_processor.process_pdf(self.test_pdf, metadata)
        
        # 创建分割规则
        rule = Rule(
            mode=SplitMode.PARENT_CHILD,
            max_tokens=1024,  # 父块最大长度
            chunk_overlap=200,  # 父块重叠
            fixed_separator="\n\n",  # 父块分隔符
            separators=["\n\n", "。", "！", "？", ". ", " ", ""],  # 分隔符列表
            clean_text=True,  # 启用文本清理
            keep_separator=True,
            remove_empty_lines=True,
            normalize_whitespace=True,
            subchunk_max_tokens=1024,  # 增加子块最大长度
            subchunk_overlap=100,  # 增加子块重叠
            subchunk_separator="\n"  # 子块分隔符
        )
        
        # 进行父子分割
        segments = self.parent_child_splitter.split_documents([document], rule)
        
        # 验证分割结果
        self.assertIsNotNone(segments)
        self.assertTrue(len(segments) > 0)
        
        # 分别验证父文档和子文档
        parent_segments = [s for s in segments if s.metadata["type"] == "parent"]
        child_segments = [s for s in segments if s.metadata["type"] == "child"]
        
        self.assertTrue(len(parent_segments) > 0)
        self.assertTrue(len(child_segments) > 0)
        
        for parent in parent_segments:
            self.assertIsNotNone(parent.content)
            self.assertTrue(len(parent.content) > 0)
            self.assertEqual(parent.metadata["source"], os.path.basename(self.test_pdf))
            
        for child in child_segments:
            self.assertIsNotNone(child.content)
            self.assertTrue(len(child.content) > 0)
            self.assertEqual(child.metadata["source"], os.path.basename(self.test_pdf))
            self.assertIn("parent_id", child.metadata)
            
        # 保存分割结果
        output_path = self.save_segments_to_json(segments, self.test_pdf, "parent_child")
        self.assertTrue(os.path.exists(output_path))

    def test_fixed_recursive_splitter(self):
        """测试固定分隔符递归分割器"""
        # 1. 准备测试数据
        text = """
        第一段落。这是一个很长的段落，包含了很多句子。
        这是第一段的第二句话。这是第一段的第三句话。
        
        第二段落！这是另一个段落。它也包含多个句子。
        这是第二段的第二句话。这是第二段的第三句话。
        
        第三段落？这是最后一个段落。它同样包含多个句子。
        这是第三段的第二句话。这是第三段的最后一句话。
        """
        
        # 2. 创建分割器
        rule = Rule(
            mode=SplitMode.PARAGRAPH,
            max_tokens=100,
            chunk_overlap=20,
            fixed_separator="\n\n",
            separators=["\n\n", "。", "！", "？", " ", ""],
            clean_text=True,
            keep_separator=True,
            remove_empty_lines=True,
            normalize_whitespace=True
        )
        
        # 3. 创建文本分割器并执行分割
        splitter = DocumentSplitter()
        text_splitter = splitter.create_text_splitter(rule)
        chunks = text_splitter.split_text(text)
        
        # 4. 验证结果
        self.assertTrue(len(chunks) > 0)
        for chunk in chunks:
            self.assertTrue(len(chunk.strip()) > 0)
            
    def test_document_splitting(self):
        """测试文档分割"""
        # 1. 准备测试数据
        text = """
        第一段落。这是一个很长的段落，包含了很多句子。
        这是第一段的第二句话。这是第一段的第三句话。
        
        第二段落！这是另一个段落。它也包含多个句子。
        这是第二段的第二句话。这是第二段的第三句话。
        
        第三段落？这是最后一个段落。它同样包含多个句子。
        这是第三段的第二句话。这是第三段的最后一句话。
        """
        
        # 2. 创建分割器
        rule = Rule(
            mode=SplitMode.PARAGRAPH,
            max_tokens=100,
            chunk_overlap=20,
            fixed_separator="\n\n",
            separators=["\n\n", "。", "！", "？", " ", ""],
            clean_text=True,
            keep_separator=True,
            remove_empty_lines=True,
            normalize_whitespace=True
        )
        
        splitter = DocumentSplitter()
        
        # 3. 执行分割
        doc = Document(page_content=text, metadata={"source": "test.txt"})
        segments = splitter.split_documents([doc], rule)
        
        # 4. 验证结果
        self.assertTrue(len(segments) > 0)
        for segment in segments:
            # 验证内容不为空
            self.assertTrue(len(segment.content.strip()) > 0)
            # 验证元数据
            self.assertIn("source", segment.metadata)
            self.assertIn("page", segment.metadata)
            self.assertIn("chunk_index", segment.metadata)
            self.assertIn("created_at", segment.metadata)

    def test_parent_child_splitting_without_vectors(self):
        """测试父子分割并保存为JSON（不包含向量数据）"""
        # 1. 首先处理PDF文件
        metadata = {
            "source": os.path.basename(self.test_pdf),
            "processed_at": datetime.now().isoformat()
        }
        document = self.pdf_processor.process_pdf(self.test_pdf, metadata)
        
        # 2. 创建优化后的分割规则
        rule = Rule(
            mode=SplitMode.PARENT_CHILD,
            max_tokens=1024,  # 减小父块最大长度
            chunk_overlap=50,  # 减小重叠
            fixed_separator="\n\n",  # 父块分隔符
            separators=["\n\n", "。", "！", "？", ". ", " ", ""],  # 分隔符列表
            clean_text=True,  # 启用文本清理
            keep_separator=True,
            remove_empty_lines=True,
            normalize_whitespace=True,
            subchunk_max_tokens=256,  # 减小子块最大长度
            subchunk_overlap=20,  # 减小子块重叠
            subchunk_separator="\n"  # 子块分隔符
        )
        
        # 3. 进行父子分割
        segments = self.parent_child_splitter.split_documents([document], rule)
        
        # 4. 过滤和清理段落
        filtered_segments = []
        for segment in segments:
            content = segment.content.strip()
            # 跳过空白的内容
            if not content:
                continue
            # 跳过只包含特殊字符的内容
            if not any(c.isalnum() for c in content):
                continue
            # 更新segment的content
            segment.content = content
            filtered_segments.append(segment)
            
        segments = filtered_segments
        
        # 5. 准备输出数据
        output_data = {
            "source_file": self.test_pdf,
            "split_mode": "parent_child",
            "metadata": {
                "total_segments": len(segments),
                "processed_at": datetime.now().isoformat()
            },
            "segments": []
        }
        
        # 6. 处理父子结构
        parent_dict = {}
        
        # 先处理所有父块
        for segment in segments:
            if segment.metadata["type"] == "parent":
                # 只保留必要的元数据
                essential_metadata = {
                    "id": segment.metadata["id"],
                    "source": segment.metadata["source"],
                    "page": segment.metadata["page"],
                    "type": "parent",
                    "chunk_index": segment.metadata["chunk_index"]
                }
                
                parent_dict[segment.id] = {
                    "id": segment.id,
                    "content": segment.content,
                    "metadata": essential_metadata,
                    "children": []
                }
        
        # 将子块添加到对应的父块中
        for segment in segments:
            if segment.metadata["type"] == "child":
                parent_id = segment.metadata["parent_id"]
                if parent_id in parent_dict:
                    # 只保留必要的元数据
                    essential_metadata = {
                        "id": segment.metadata["id"],
                        "parent_id": parent_id,
                        "type": "child",
                        "chunk_index": segment.metadata["chunk_index"]
                    }
                    
                    parent_dict[parent_id]["children"].append({
                        "id": segment.id,
                        "content": segment.content,
                        "metadata": essential_metadata
                    })
        
        # 7. 添加统计信息
        parent_lengths = [len(s["content"]) for s in parent_dict.values()]
        child_lengths = [
            len(c["content"]) 
            for p in parent_dict.values() 
            for c in p["children"]
        ]
        
        output_data["metadata"]["stats"] = {
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
        
        # 8. 将父块列表添加到输出数据中
        output_data["segments"] = list(parent_dict.values())
        
        # 9. 保存到JSON文件
        output_filename = f"{Path(self.test_pdf).stem}_parent_child_no_vectors.json"
        output_path = self.vectors_dir / output_filename
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
            
        print(f"父子分割结果（无向量数据）已保存到: {output_path}")
        
        # 10. 验证结果
        self.assertTrue(os.path.exists(output_path))
        # 验证父文档和子文档的数量
        parent_segments = [s for s in segments if s.metadata["type"] == "parent"]
        child_segments = [s for s in segments if s.metadata["type"] == "child"]
        self.assertEqual(len(parent_dict), len(parent_segments))
        total_children = sum(len(p["children"]) for p in parent_dict.values())
        self.assertEqual(total_children, len(child_segments))
        
        # 11. 打印文件大小信息
        file_size = os.path.getsize(output_path) / (1024 * 1024)  # 转换为MB
        print(f"输出文件大小: {file_size:.2f}MB")
        print(f"父块数量: {len(parent_segments)}")
        print(f"子块数量: {len(child_segments)}")
        
        # 12. 验证文件大小是否合理
        max_expected_size = 50 * 1024 * 1024  # 50MB
        self.assertLess(os.path.getsize(output_path), max_expected_size, 
                       "输出文件大小超过预期的50MB限制")

class TestDocumentSplitting(unittest.TestCase):
    """测试文档分割功能"""
    
    def setUp(self):
        """测试准备"""
        # 使用项目根目录下的data目录
        project_root = Path(__file__).parent.parent.parent.parent.parent
        self.test_dir = project_root / "data" / "test_data"
        os.makedirs(self.test_dir, exist_ok=True)
        
    def tearDown(self):
        """测试清理"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            
    def test_fixed_recursive_splitter(self):
        """测试固定分隔符递归分割器"""
        # 1. 准备测试数据
        text = """
        第一段落。这是一个很长的段落，包含了很多句子。
        这是第一段的第二句话。这是第一段的第三句话。
        
        第二段落！这是另一个段落。它也包含多个句子。
        这是第二段的第二句话。这是第二段的第三句话。
        
        第三段落？这是最后一个段落。它同样包含多个句子。
        这是第三段的第二句话。这是第三段的最后一句话。
        """
        
        # 2. 创建分割器
        rule = Rule(
            mode=SplitMode.PARAGRAPH,
            max_tokens=100,
            chunk_overlap=20,
            fixed_separator="\n\n",
            separators=["\n\n", "。", "！", "？", " ", ""],
            min_content_length=10,
            clean_text=True,
            keep_separator=True,
            remove_empty_lines=True,
            normalize_whitespace=True
        )
        
        splitter = DocumentSplitter()
        
        # 3. 执行分割
        doc = Document(page_content=text, metadata={"source": "test.txt"})
        segments = splitter.split_documents([doc], rule)
        
        # 4. 验证结果
        self.assertTrue(len(segments) > 0)
        for segment in segments:
            # 验证内容长度
            self.assertGreaterEqual(len(segment.content.strip()), rule.min_content_length)
            # 验证元数据
            self.assertIn("source", segment.metadata)
            self.assertIn("page", segment.metadata)
            self.assertIn("chunk_index", segment.metadata)
            self.assertIn("created_at", segment.metadata)
            
    def test_save_segments(self):
        """测试保存文档片段"""
        # 1. 准备测试数据
        segments = [
            DocumentSegment(
                content="测试内容1",
                metadata={
                    "id": "test_1",
                    "source": "test.txt",
                    "page": 1,
                    "chunk_index": 0,
                    "total_chunks": 2,
                    "type": "segment",
                    "created_at": datetime.now().isoformat()
                }
            ),
            DocumentSegment(
                content="测试内容2",
                metadata={
                    "id": "test_2",
                    "source": "test.txt",
                    "page": 1,
                    "chunk_index": 1,
                    "total_chunks": 2,
                    "type": "segment",
                    "created_at": datetime.now().isoformat()
                }
            )
        ]
        
        # 2. 保存片段
        output_dir = os.path.join(self.test_dir, "segments")
        splitter = DocumentSplitter()
        splitter.save_segments(segments, output_dir)
        
        # 3. 验证结果
        json_files = [f for f in os.listdir(output_dir) if f.endswith(".json")]
        self.assertEqual(len(json_files), 1)
        
        # 4. 验证JSON内容
        json_path = os.path.join(output_dir, json_files[0])
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        self.assertIn("segments", data)
        self.assertIn("metadata", data)
        self.assertEqual(len(data["segments"]), 2)
        self.assertEqual(data["metadata"]["total_segments"], 2)
        
if __name__ == "__main__":
    unittest.main() 