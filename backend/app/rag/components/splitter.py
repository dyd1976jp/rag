"""
文本分割器组件

实现智能文本分割功能，支持多种分割策略。
实现ITextSplitter接口，提供统一的文本分割功能。
"""

import re
import uuid
import logging
from typing import List, Dict, Any, Optional

from app.rag.interfaces import BaseTextSplitter, Document, DocumentChunk
from app.core.config import settings

logger = logging.getLogger(__name__)

class TextSplitter(BaseTextSplitter):
    """文本分割器实现"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None,
        keep_separator: bool = True
    ):
        """
        初始化文本分割器
        
        Args:
            chunk_size: 块大小（字符数）
            chunk_overlap: 块重叠大小
            separators: 分割符列表
            keep_separator: 是否保留分割符
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.keep_separator = keep_separator
        
        # 默认分割符，按优先级排序
        self.separators = separators or [
            "\n\n",  # 段落分割
            "\n",    # 行分割
            "。",    # 中文句号
            ".",     # 英文句号
            "！",    # 中文感叹号
            "!",     # 英文感叹号
            "？",    # 中文问号
            "?",     # 英文问号
            "；",    # 中文分号
            ";",     # 英文分号
            " ",     # 空格
            ""       # 字符级分割
        ]
    
    async def split_document(self, document: Document) -> List[DocumentChunk]:
        """
        分割文档为块
        
        Args:
            document: 要分割的文档
            
        Returns:
            List[DocumentChunk]: 分割后的文档块列表
        """
        if not document.content:
            return []
        
        # 预处理文本
        text = self._preprocess_text(document.content)
        
        # 执行分割
        chunks = self._split_text(text)
        
        # 创建文档块对象
        document_chunks = []
        for i, chunk_text in enumerate(chunks):
            if chunk_text.strip():  # 跳过空块
                chunk = DocumentChunk(
                    content=chunk_text.strip(),
                    metadata={
                        **document.metadata,
                        "chunk_index": i,
                        "chunk_id": str(uuid.uuid4()),
                        "parent_doc_id": document.doc_id,
                        "chunk_size": len(chunk_text),
                        "total_chunks": len(chunks)
                    },
                    chunk_id=str(uuid.uuid4()),
                    parent_id=document.doc_id
                )
                document_chunks.append(chunk)
        
        logger.info(f"文档分割完成: {len(document_chunks)} 个块")
        return document_chunks
    
    def configure(self, **kwargs) -> None:
        """
        配置分割器参数
        
        Args:
            **kwargs: 配置参数
        """
        if 'chunk_size' in kwargs:
            self.chunk_size = kwargs['chunk_size']
        if 'chunk_overlap' in kwargs:
            self.chunk_overlap = kwargs['chunk_overlap']
        if 'separators' in kwargs:
            self.separators = kwargs['separators']
        if 'keep_separator' in kwargs:
            self.keep_separator = kwargs['keep_separator']
    
    def _preprocess_text(self, text: str) -> str:
        """
        预处理文本
        
        Args:
            text: 原始文本
            
        Returns:
            str: 预处理后的文本
        """
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        # 标准化换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 移除多余的换行符
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    def _split_text(self, text: str) -> List[str]:
        """
        递归分割文本
        
        Args:
            text: 要分割的文本
            
        Returns:
            List[str]: 分割后的文本块列表
        """
        return self._split_text_recursive(text, self.separators)
    
    def _split_text_recursive(self, text: str, separators: List[str]) -> List[str]:
        """
        递归分割文本
        
        Args:
            text: 要分割的文本
            separators: 分割符列表
            
        Returns:
            List[str]: 分割后的文本块列表
        """
        final_chunks = []
        
        # 选择分割符
        separator = separators[0] if separators else ""
        new_separators = separators[1:] if len(separators) > 1 else []
        
        # 分割文本
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)
        
        # 处理分割结果
        good_splits = []
        for split in splits:
            if len(split) < self.chunk_size:
                good_splits.append(split)
            else:
                if good_splits:
                    merged_text = self._merge_splits(good_splits, separator)
                    final_chunks.extend(merged_text)
                    good_splits = []
                
                # 继续递归分割
                if new_separators:
                    other_info = self._split_text_recursive(split, new_separators)
                    final_chunks.extend(other_info)
                else:
                    final_chunks.append(split)
        
        if good_splits:
            merged_text = self._merge_splits(good_splits, separator)
            final_chunks.extend(merged_text)
        
        return final_chunks
    
    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        """
        合并分割结果
        
        Args:
            splits: 分割结果列表
            separator: 分割符
            
        Returns:
            List[str]: 合并后的文本块列表
        """
        separator_len = len(separator)
        docs = []
        current_doc = []
        total = 0
        
        for split in splits:
            split_len = len(split)
            
            if total + split_len + (separator_len if current_doc else 0) > self.chunk_size:
                if current_doc:
                    doc = self._join_docs(current_doc, separator)
                    if doc:
                        docs.append(doc)
                    
                    # 处理重叠
                    while (total > self.chunk_overlap or 
                           (total + split_len + separator_len > self.chunk_size and total > 0)):
                        total -= len(current_doc[0]) + separator_len
                        current_doc = current_doc[1:]
            
            current_doc.append(split)
            total += split_len + (separator_len if len(current_doc) > 1 else 0)
        
        doc = self._join_docs(current_doc, separator)
        if doc:
            docs.append(doc)
        
        return docs
    
    def _join_docs(self, docs: List[str], separator: str) -> str:
        """
        连接文档片段
        
        Args:
            docs: 文档片段列表
            separator: 分割符
            
        Returns:
            str: 连接后的文档
        """
        text = separator.join(docs).strip()
        return text if text else None
    
    def get_chunk_info(self) -> Dict[str, Any]:
        """获取分割器配置信息"""
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "separators": self.separators,
            "keep_separator": self.keep_separator
        }
