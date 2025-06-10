"""
文档分割器模块
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
import json
import hashlib
import uuid
from enum import Enum

from .models import Document, DocumentSegment, ChildDocument
from .text_splitter import EnhanceRecursiveCharacterTextSplitter, FixedRecursiveCharacterTextSplitter
from .cleaner.clean_processor import CleanProcessor, CleanLevel

logger = logging.getLogger(__name__)

class SplitMode(str, Enum):
    """分割模式"""
    PARAGRAPH = "paragraph"  # 段落模式
    QA = "qa"  # 问答模式
    PARENT_CHILD = "parent_child"  # 父子模式

class Rule:
    """分割规则"""
    def __init__(
        self,
        mode: SplitMode = SplitMode.PARAGRAPH,
        max_tokens: int = 1024,  # 默认父块最大长度
        chunk_overlap: int = 200,  # 默认父块重叠
        fixed_separator: str = "\n\n",  # 默认父块分隔符
        subchunk_max_tokens: int = 512,  # 默认子块最大长度
        subchunk_overlap: int = 50,  # 默认子块重叠
        subchunk_separator: str = "\n",  # 默认子块分隔符
        min_content_length: int = 50,  # 默认最小内容长度
        clean_text: bool = True,
        keep_separator: bool = False,
        remove_empty_lines: bool = True,
        normalize_whitespace: bool = True
    ):
        self.mode = mode
        self.max_tokens = max_tokens
        self.chunk_overlap = chunk_overlap
        self.fixed_separator = fixed_separator
        self.subchunk_max_tokens = subchunk_max_tokens
        self.subchunk_overlap = subchunk_overlap
        self.subchunk_separator = subchunk_separator
        self.min_content_length = min_content_length
        self.clean_text = clean_text
        self.keep_separator = keep_separator
        self.remove_empty_lines = remove_empty_lines
        self.normalize_whitespace = normalize_whitespace

class DocumentSplitter:
    """文档分割器基类"""
    def __init__(
        self,
        chunk_size: int = 1024,  # 默认块大小
        chunk_overlap: int = 200,  # 默认重叠
        fixed_separator: str = "\n\n",  # 默认分隔符
        keep_separator: bool = True,
        add_start_index: bool = True
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.fixed_separator = fixed_separator
        self.keep_separator = keep_separator
        self.add_start_index = add_start_index
        
        # 创建文本分割器
        self.text_splitter = FixedRecursiveCharacterTextSplitter.from_encoder(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            fixed_separator=self.fixed_separator,
            separators=["\n\n", "\n", "。", "！", "？", ". ", " ", ""],
            keep_separator=self.keep_separator,
            length_function=lambda x: [len(text) for text in x]
        )
        
        logger.info(f"初始化文档分割器: 分块大小={self.chunk_size}, 重叠={self.chunk_overlap}")
        
    def _is_title(self, text: str) -> bool:
        """判断是否为标题"""
        # 标题模式
        title_patterns = [
            r"^第[一二三四五六七八九十百千万]+[章节篇]",  # 中文数字章节
            r"^[0-9]+\.[0-9]+(\.[0-9]+)?",  # 数字编号（如1.2, 1.2.3）
            r"^[一二三四五六七八九十][、.]",  # 中文数字编号
            r"^[A-Z]\.",  # 字母编号
            r"^[（(][一二三四五六七八九十][)）]",  # 带括号的中文数字
            r"^[（(][0-9]+[)）]",  # 带括号的数字
            r"^[【\[].+[】\]]$",  # 方括号包围
            r"^《.+》$",  # 书名号包围
            r"^目\s*录$",  # 目录
            r"^前\s*言$",  # 前言
            r"^概\s*述$",  # 概述
            r"^简\s*介$",  # 简介
            r"^说\s*明$",  # 说明
            r"^注\s*意$",  # 注意
            r"^警\s*告$",  # 警告
        ]
        return any(re.match(pattern, text.strip()) for pattern in title_patterns)

    def _is_list_item(self, text: str) -> bool:
        """判断是否为列表项"""
        # 列表项模式
        list_patterns = [
            r"^[•·○●◆▪-]",  # 常见列表符号
            r"^[0-9]+\.",  # 数字编号
            r"^[a-zA-Z]\.",  # 字母编号
            r"^\([0-9]+\)",  # 带括号的数字
            r"^\([a-zA-Z]\)",  # 带括号的字母
            r"^[①②③④⑤⑥⑦⑧⑨⑩]",  # 圆圈数字
            r"^[㈠㈡㈢㈣㈤㈥㈦㈧㈨㈩]",  # 括号数字
            r"^[⒈⒉⒊⒋⒌⒍⒎⒏⒐⒑]",  # 带点数字
        ]
        return any(re.match(pattern, text.strip()) for pattern in list_patterns)
        
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """智能分割段落"""
        # 1. 首先按双换行分割
        paragraphs = []
        
        # 预处理：规范化换行符
        text = text.replace('\r\n', '\n')
        text = re.sub(r'\n{3,}', '\n\n', text)  # 将多个换行符压缩为两个
        
        # 按双换行符分割
        raw_paragraphs = text.split("\n\n")
        
        current_paragraph = []
        
        for para in raw_paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # 处理单换行的情况
            lines = para.split("\n")
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                    
                # 如果是标题，作为独立段落
                if self._is_title(line):
                    # 保存之前的段落
                    if current_paragraph:
                        paragraphs.append("\n".join(current_paragraph))
                        current_paragraph = []
                    # 添加标题作为独立段落
                    paragraphs.append(line)
                    continue
                
                # 如果是列表项
                if self._is_list_item(line):
                    # 如果前一行不是列表项，开始新段落
                    if i > 0 and not self._is_list_item(lines[i-1].strip()):
                        if current_paragraph:
                            paragraphs.append("\n".join(current_paragraph))
                            current_paragraph = []
                    current_paragraph.append(line)
                    continue
                
                # 如果当前行以标点符号结尾，说明是一个完整句子
                if line[-1] in "。！？.!?":
                    current_paragraph.append(line)
                    # 如果下一行是新主题（首字有特殊标记或缩进），保存当前段落
                    if i < len(lines) - 1:
                        next_line = lines[i+1].strip()
                        if (next_line and 
                            (self._is_new_topic(next_line) or 
                             self._is_title(next_line) or 
                             self._is_list_item(next_line))):
                            if current_paragraph:
                                paragraphs.append("\n".join(current_paragraph))
                                current_paragraph = []
                else:
                    current_paragraph.append(line)
        
        # 保存最后一个段落
        if current_paragraph:
            paragraphs.append("\n".join(current_paragraph))
        
        return paragraphs
        
    def _is_new_topic(self, text: str) -> bool:
        """判断是否是新主题的开始"""
        # 1. 检查是否以特殊字符开头
        special_starts = ["第", "一、", "二、", "三、", "1.", "2.", "3.", "注：", "注意：", "提示：", "警告："]
        for start in special_starts:
            if text.startswith(start):
                return True
                
        # 2. 检查是否以括号开头
        if text.startswith(("（", "(", "【", "[", "《")):
            return True
            
        # 3. 检查是否以数字编号开头
        if re.match(r"^\d+[.、]", text):
            return True
            
        return False
        
    def split_documents(self, documents: List[Document], rule: Optional[Rule] = None) -> List[DocumentSegment]:
        """分割文档"""
        if not rule:
            rule = Rule()
            
        all_segments = []
        
        for doc in documents:
            # 1. 首先按段落分割
            paragraphs = self._split_into_paragraphs(doc.page_content)
            
            # 2. 处理每个段落
            for i, para in enumerate(paragraphs):
                # 创建父文档
                parent_id = str(uuid.uuid4())
                parent_segment = DocumentSegment(
                    id=parent_id,
                    page_content=para,
                    metadata={
                        "source": doc.source,
                        "type": "parent",
                        "index": i + 1,
                        "original_doc_id": doc.doc_id
                    }
                )
                all_segments.append(parent_segment)
                
                # 如果段落较长，创建子文档
                if len(para) > rule.subchunk_max_tokens:
                    child_splitter = FixedRecursiveCharacterTextSplitter(
                        chunk_size=rule.subchunk_max_tokens,
                        chunk_overlap=rule.subchunk_overlap,
                        fixed_separator=rule.subchunk_separator
                    )
                    child_texts = child_splitter.split_text(para)
                    
                    for j, child_text in enumerate(child_texts):
                        child_id = str(uuid.uuid4())
                        child_segment = DocumentSegment(
                            id=child_id,
                            page_content=child_text,
                            metadata={
                                "source": doc.source,
                                "type": "child",
                                "parent_id": parent_id,
                                "index": j + 1,
                                "original_doc_id": doc.doc_id
                            }
                        )
                        all_segments.append(child_segment)
        
        return all_segments

class QADocumentSplitter(DocumentSplitter):
    """问答文档分割器"""
    def split_documents(self, documents: List[Document], rule: Optional[Rule] = None) -> List[DocumentSegment]:
        """分割问答文档"""
        if not rule:
            rule = Rule(mode=SplitMode.QA)
            
        all_segments = []
        
        for doc in documents:
            # 使用正则表达式匹配问答对
            qa_pattern = r"Q\d+:\s*(.*?)\s*A\d+:\s*([\s\S]*?)(?=Q\d+:|$)"
            matches = re.findall(qa_pattern, doc.page_content, re.UNICODE)
            
            for i, (question, answer) in enumerate(matches):
                if not question.strip() or not answer.strip():
                    continue
                    
                # 创建问答片段
                qa_id = str(uuid.uuid4())
                qa_segment = DocumentSegment(
                    id=qa_id,
                    page_content=f"问：{question.strip()}\n答：{answer.strip()}",
                    metadata={
                        "source": doc.source,
                        "type": "qa",
                        "index": i + 1,
                        "question": question.strip(),
                        "answer": answer.strip(),
                        "original_doc_id": doc.doc_id
                    }
                )
                all_segments.append(qa_segment)
        
        return all_segments

class ParentChildDocumentSplitter(DocumentSplitter):
    """父子文档分割器"""
    def split_documents(self, documents: List[Document], rule: Optional[Rule] = None) -> List[DocumentSegment]:
        """分割父子文档"""
        if not rule:
            rule = Rule(mode=SplitMode.PARENT_CHILD)
            
        all_segments = []
        
        for doc in documents:
            # 1. 对原始文档进行完整清理
            doc.page_content = CleanProcessor.clean(doc.page_content, level=CleanLevel.FULL)
            if not doc.page_content:
                continue
                
            # 2. 创建父文档分词器
            parent_splitter = FixedRecursiveCharacterTextSplitter.from_encoder(
                chunk_size=rule.max_tokens,
                chunk_overlap=rule.chunk_overlap,
                fixed_separator="\n\n",  # 固定使用双换行作为主分隔符
                separators=["\n\n", "。", ". ", " ", ""],  # 递归分隔符
                keep_separator=rule.keep_separator,
                length_function=lambda x: [len(text) for text in x]
            )
            
            # 3. 分割父文档
            parent_nodes = parent_splitter.split_text(doc.page_content)
            
            # 4. 处理每个父节点
            for i, parent_content in enumerate(parent_nodes):
                parent_content = parent_content.strip()
                if not parent_content:
                    continue
                    
                # 创建父文档
                parent_id = str(uuid.uuid4())
                parent_hash = hashlib.sha256(parent_content.encode()).hexdigest()
                
                parent_segment = DocumentSegment(
                    id=parent_id,
                    page_content=parent_content,
                    metadata={
                        "source": doc.source,
                        "type": "parent",
                        "index": i + 1,
                        "original_doc_id": doc.doc_id,
                        "doc_hash": parent_hash
                    }
                )
                
                # 5. 创建子文档分词器
                if rule.subchunk_max_tokens > 0:
                    child_splitter = FixedRecursiveCharacterTextSplitter.from_encoder(
                        chunk_size=rule.subchunk_max_tokens,
                        chunk_overlap=rule.subchunk_overlap,
                        fixed_separator="\n",  # 固定使用单换行作为主分隔符
                        separators=["\n", " ", ""],  # 递归分隔符
                        keep_separator=rule.keep_separator,
                        length_function=lambda x: [len(text) for text in x]
                    )
                    
                    # 6. 分割子文档
                    child_nodes = child_splitter.split_text(parent_content)
                    
                    # 7. 处理每个子节点
                    for j, child_content in enumerate(child_nodes):
                        child_content = child_content.strip()
                        if not child_content or len(child_content) < rule.min_content_length:
                            continue
                            
                        # 创建子文档
                        child_id = str(uuid.uuid4())
                        child_hash = hashlib.sha256(child_content.encode()).hexdigest()
                        
                        child_segment = DocumentSegment(
                            id=child_id,
                            page_content=child_content,
                            metadata={
                                "source": doc.source,
                                "type": "child",
                                "parent_id": parent_id,
                                "index": j + 1,
                                "original_doc_id": doc.doc_id,
                                "doc_hash": child_hash
                            }
                        )
                        all_segments.append(child_segment)
                
                # 添加父文档
                all_segments.append(parent_segment)
        
        return all_segments 