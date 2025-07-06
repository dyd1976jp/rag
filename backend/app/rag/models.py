"""
文档模型定义
"""
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field as PydanticField
from .constants import Field as ConstantField
import uuid
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

class Document(BaseModel):
    """文档基类"""
    page_content: str
    metadata: Dict[str, Any] = PydanticField(default_factory=dict)
    source: Optional[str] = None
    doc_id: Optional[str] = None
    doc_hash: Optional[str] = None
    vector: Optional[List[float]] = None
    sparse_vector: Optional[List[float]] = None
    group_id: Optional[str] = None
    children: Optional[List['ChildDocument']] = None  # 明确指定为ChildDocument类型

    def __init__(self, **data):
        super().__init__(**data)
        if not self.doc_id:
            self.doc_id = str(uuid.uuid4())
        if not self.doc_hash:
            self.doc_hash = self._generate_hash()
        if self.source and "source" not in self.metadata:
            self.metadata["source"] = self.source

    def _generate_hash(self) -> str:
        """生成文档哈希值"""
        text = self.page_content + str(sorted(self.metadata.items()))
        return hashlib.sha256(text.encode()).hexdigest()

    def add_child(self, child_document: 'ChildDocument') -> None:
        """添加子文档

        Args:
            child_document: 要添加的子文档
        """
        if self.children is None:
            self.children = []

        # 设置父子关系
        child_document.parent_id = self.doc_id
        child_document.parent_content = self.page_content
        child_document.position = len(self.children)

        # 更新子文档元数据
        child_document.metadata.update({
            "parent_id": self.doc_id,
            "parent_content": self.page_content[:200] + "..." if len(self.page_content) > 200 else self.page_content,
            "position": child_document.position,
            "is_child": True
        })

        self.children.append(child_document)

    def remove_child(self, child_id: str) -> bool:
        """移除子文档

        Args:
            child_id: 要移除的子文档ID

        Returns:
            bool: 是否成功移除
        """
        if not self.children:
            return False

        for i, child in enumerate(self.children):
            if child.doc_id == child_id:
                self.children.pop(i)
                # 重新设置剩余子文档的位置
                for j, remaining_child in enumerate(self.children[i:], start=i):
                    remaining_child.position = j
                    remaining_child.metadata["position"] = j
                return True
        return False

    def get_child_by_id(self, child_id: str) -> Optional['ChildDocument']:
        """根据ID获取子文档

        Args:
            child_id: 子文档ID

        Returns:
            Optional[ChildDocument]: 找到的子文档，如果不存在则返回None
        """
        if not self.children:
            return None

        for child in self.children:
            if child.doc_id == child_id:
                return child
        return None

    def get_children_count(self) -> int:
        """获取子文档数量

        Returns:
            int: 子文档数量
        """
        return len(self.children) if self.children else 0

    def has_children(self) -> bool:
        """检查是否有子文档

        Returns:
            bool: 是否有子文档
        """
        return self.children is not None and len(self.children) > 0

    def get_all_content(self) -> str:
        """获取包含所有子文档的完整内容

        Returns:
            str: 完整内容
        """
        content = self.page_content
        if self.children:
            child_contents = [child.page_content for child in self.children]
            content += "\n\n" + "\n\n".join(child_contents)
        return content

    def get_children_by_position_range(self, start: int, end: int) -> List['ChildDocument']:
        """根据位置范围获取子文档

        Args:
            start: 起始位置（包含）
            end: 结束位置（不包含）

        Returns:
            List[ChildDocument]: 指定范围内的子文档列表
        """
        if not self.children:
            return []

        return [child for child in self.children if start <= child.position < end]

    def get_children_by_content_length(self, min_length: int = 0, max_length: int = float('inf')) -> List['ChildDocument']:
        """根据内容长度筛选子文档

        Args:
            min_length: 最小内容长度
            max_length: 最大内容长度

        Returns:
            List[ChildDocument]: 符合长度条件的子文档列表
        """
        if not self.children:
            return []

        return [
            child for child in self.children
            if min_length <= len(child.page_content) <= max_length
        ]

    def reorder_children(self) -> None:
        """重新排序子文档位置"""
        if not self.children:
            return

        for i, child in enumerate(self.children):
            child.position = i
            child.metadata["position"] = i

    def merge_children_content(self, separator: str = "\n\n") -> str:
        """合并所有子文档内容

        Args:
            separator: 子文档间的分隔符

        Returns:
            str: 合并后的内容
        """
        if not self.children:
            return self.page_content

        child_contents = [child.page_content for child in self.children]
        return self.page_content + separator + separator.join(child_contents)

    def get_document_statistics(self) -> Dict[str, Any]:
        """获取文档统计信息

        Returns:
            Dict[str, Any]: 包含各种统计信息的字典
        """
        stats = {
            "doc_id": self.doc_id,
            "parent_content_length": len(self.page_content),
            "children_count": self.get_children_count(),
            "has_children": self.has_children(),
            "total_content_length": len(self.get_all_content())
        }

        if self.children:
            child_lengths = [len(child.page_content) for child in self.children]
            stats.update({
                "min_child_length": min(child_lengths),
                "max_child_length": max(child_lengths),
                "avg_child_length": sum(child_lengths) / len(child_lengths),
                "total_children_length": sum(child_lengths)
            })

        return stats

    def to_point_struct(self) -> Dict[str, Any]:
        """转换为向量存储的数据结构"""
        return {
            ConstantField.PRIMARY_KEY.value: self.doc_id,
            ConstantField.VECTOR.value: self.vector,
            ConstantField.CONTENT_KEY.value: self.page_content,
            ConstantField.METADATA_KEY.value: {
                **self.metadata,
                "has_children": self.has_children(),
                "children_count": self.get_children_count()
            },
            ConstantField.GROUP_KEY.value: self.group_id or "",
            ConstantField.SPARSE_VECTOR.value: self.sparse_vector or self.vector
        }

class DocumentSegment(BaseModel):
    """文档片段"""
    id: str = PydanticField(default_factory=lambda: str(uuid.uuid4()))
    page_content: str
    metadata: Dict[str, Any] = PydanticField(default_factory=dict)
    index_node_id: Optional[str] = None
    index_node_hash: Optional[str] = None
    child_ids: Optional[List[str]] = None
    group_id: Optional[str] = None
    children: Optional[List['DocumentSegment']] = None
    embedding: Optional[List[float]] = None  # 添加 embedding 字段
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.index_node_hash:
            self.index_node_hash = self._generate_hash()
            
    def _generate_hash(self) -> str:
        """生成文档片段哈希值"""
        text = self.page_content + str(sorted(self.metadata.items()))
        return hashlib.sha256(text.encode()).hexdigest()
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，包含子文档"""
        result = {
            "id": self.id,
            "page_content": self.page_content,
            "metadata": self.metadata,
            "index_node_id": self.index_node_id,
            "index_node_hash": self.index_node_hash,
            "child_ids": self.child_ids,
            "group_id": self.group_id,
            "embedding": None  # 默认设置为 None，因为模型中没有这个字段
        }
        
        # 如果有子文档，递归转换
        if self.children:
            result["children"] = [child.to_dict() for child in self.children]
            
        return result
        
    def to_point_struct(self) -> Dict[str, Any]:
        """转换为向量存储的数据结构"""
        return {
            ConstantField.PRIMARY_KEY.value: self.id,
            ConstantField.CONTENT_KEY.value: self.page_content,
            ConstantField.METADATA_KEY.value: {
                **self.metadata,
                "index_node_hash": self.index_node_hash,
                "child_ids": self.child_ids
            },
            ConstantField.GROUP_KEY.value: self.group_id or "",
            ConstantField.VECTOR.value: self.embedding  # 添加 embedding 到输出
        }

class ChildDocument(Document):
    """子文档

    继承自Document类，添加了父子关系相关的字段和方法
    """
    parent_id: Optional[str] = None
    parent_content: Optional[str] = None
    position: Optional[int] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.parent_id and "parent_id" not in self.metadata:
            self.metadata["parent_id"] = self.parent_id

        # 确保子文档标记
        self.metadata["is_child"] = True

    def set_parent(self, parent_document: Document, position: Optional[int] = None) -> None:
        """设置父文档

        Args:
            parent_document: 父文档对象
            position: 在父文档中的位置
        """
        self.parent_id = parent_document.doc_id
        self.parent_content = parent_document.page_content
        if position is not None:
            self.position = position

        # 更新元数据
        self.metadata.update({
            "parent_id": self.parent_id,
            "parent_content": self.parent_content[:200] + "..." if len(self.parent_content) > 200 else self.parent_content,
            "position": self.position,
            "is_child": True
        })

    def get_parent_id(self) -> Optional[str]:
        """获取父文档ID

        Returns:
            Optional[str]: 父文档ID
        """
        return self.parent_id

    def get_position(self) -> Optional[int]:
        """获取在父文档中的位置

        Returns:
            Optional[int]: 位置索引
        """
        return self.position

    def is_first_child(self) -> bool:
        """检查是否是第一个子文档

        Returns:
            bool: 是否是第一个子文档
        """
        return self.position == 0

    def get_context_info(self) -> Dict[str, Any]:
        """获取上下文信息

        Returns:
            Dict[str, Any]: 包含父文档和位置信息的上下文
        """
        return {
            "parent_id": self.parent_id,
            "parent_content_preview": self.parent_content[:100] + "..." if self.parent_content and len(self.parent_content) > 100 else self.parent_content,
            "position": self.position,
            "is_child": True
        }

    def to_dict_with_parent(self) -> Dict[str, Any]:
        """转换为包含父文档信息的字典

        Returns:
            Dict[str, Any]: 包含父文档信息的字典
        """
        result = {
            "doc_id": self.doc_id,
            "page_content": self.page_content,
            "metadata": self.metadata,
            "parent_info": {
                "parent_id": self.parent_id,
                "parent_content": self.parent_content,
                "position": self.position
            }
        }
        return result

    def get_siblings(self, parent_document: Document) -> List['ChildDocument']:
        """获取同级子文档（兄弟文档）

        Args:
            parent_document: 父文档对象

        Returns:
            List[ChildDocument]: 同级子文档列表（不包括自己）
        """
        if not parent_document.children:
            return []

        return [child for child in parent_document.children if child.doc_id != self.doc_id]

    def get_previous_sibling(self, parent_document: Document) -> Optional['ChildDocument']:
        """获取前一个兄弟文档

        Args:
            parent_document: 父文档对象

        Returns:
            Optional[ChildDocument]: 前一个兄弟文档，如果不存在则返回None
        """
        if not parent_document.children or self.position is None or self.position <= 0:
            return None

        for child in parent_document.children:
            if child.position == self.position - 1:
                return child

        return None

    def get_next_sibling(self, parent_document: Document) -> Optional['ChildDocument']:
        """获取下一个兄弟文档

        Args:
            parent_document: 父文档对象

        Returns:
            Optional[ChildDocument]: 下一个兄弟文档，如果不存在则返回None
        """
        if not parent_document.children or self.position is None:
            return None

        for child in parent_document.children:
            if child.position == self.position + 1:
                return child

        return None

    def get_context_window(self, parent_document: Document, window_size: int = 1) -> Dict[str, Any]:
        """获取上下文窗口（包括前后兄弟文档）

        Args:
            parent_document: 父文档对象
            window_size: 窗口大小（前后各取多少个兄弟文档）

        Returns:
            Dict[str, Any]: 包含上下文信息的字典
        """
        if not parent_document.children or self.position is None:
            return {"current": self, "previous": [], "next": []}

        previous_siblings = []
        next_siblings = []

        # 获取前面的兄弟文档
        for i in range(max(0, self.position - window_size), self.position):
            for child in parent_document.children:
                if child.position == i:
                    previous_siblings.append(child)
                    break

        # 获取后面的兄弟文档
        for i in range(self.position + 1, min(len(parent_document.children), self.position + window_size + 1)):
            for child in parent_document.children:
                if child.position == i:
                    next_siblings.append(child)
                    break

        return {
            "current": self,
            "previous": previous_siblings,
            "next": next_siblings,
            "context_content": self._build_context_content(previous_siblings, next_siblings)
        }

    def _build_context_content(self, previous: List['ChildDocument'], next_docs: List['ChildDocument']) -> str:
        """构建上下文内容字符串

        Args:
            previous: 前面的兄弟文档
            next_docs: 后面的兄弟文档

        Returns:
            str: 上下文内容
        """
        parts = []

        # 添加前面的内容
        if previous:
            prev_content = " ".join([doc.page_content for doc in previous])
            parts.append(f"[前文] {prev_content}")

        # 添加当前内容
        parts.append(f"[当前] {self.page_content}")

        # 添加后面的内容
        if next_docs:
            next_content = " ".join([doc.page_content for doc in next_docs])
            parts.append(f"[后文] {next_content}")

        return " ".join(parts)

    def calculate_similarity_with_parent(self) -> float:
        """计算与父文档的相似度（基于内容重叠）

        Returns:
            float: 相似度分数（0-1之间）
        """
        if not self.parent_content:
            return 0.0

        # 简单的基于词汇重叠的相似度计算
        child_words = set(self.page_content.split())
        parent_words = set(self.parent_content.split())

        if not child_words or not parent_words:
            return 0.0

        intersection = child_words.intersection(parent_words)
        union = child_words.union(parent_words)

        return len(intersection) / len(union) if union else 0.0

    def to_point_struct(self) -> Dict[str, Any]:
        """转换为向量存储的数据结构"""
        point = super().to_point_struct()
        point[ConstantField.METADATA_KEY.value].update({
            "parent_id": self.parent_id,
            "parent_content": self.parent_content[:200] + "..." if self.parent_content and len(self.parent_content) > 200 else self.parent_content,
            "position": self.position,
            "is_child": True
        })
        return point

class ChildChunk(BaseModel):
    """子块模型"""
    segment_id: str
    page_content: str
    vector: Optional[List[float]] = None
    metadata: Dict[str, Any] = PydanticField(default_factory=dict)
    start_pos: int = 0
    end_pos: int = 0
    group_id: Optional[str] = None
    
    def to_point_struct(self) -> Dict[str, Any]:
        """转换为向量存储的数据结构"""
        return {
            ConstantField.PRIMARY_KEY.value: self.metadata.get("chunk_id", str(uuid.uuid4())),
            ConstantField.VECTOR.value: self.vector,
            ConstantField.CONTENT_KEY.value: self.page_content,
            ConstantField.METADATA_KEY.value: {
                **self.metadata,
                "segment_id": self.segment_id,
                "start_pos": self.start_pos,
                "end_pos": self.end_pos
            },
            ConstantField.GROUP_KEY.value: self.group_id or "",
            ConstantField.SPARSE_VECTOR.value: self.vector  # 简化处理，实际应该是不同的向量
        }


class DocumentRelationshipManager:
    """文档关系管理器

    用于管理父子文档之间的关系，提供批量操作和关系维护功能
    """

    @staticmethod
    def create_parent_child_relationship(
        parent_content: str,
        child_contents: List[str],
        parent_metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> Document:
        """创建父子文档关系

        Args:
            parent_content: 父文档内容
            child_contents: 子文档内容列表
            parent_metadata: 父文档元数据
            source: 文档来源

        Returns:
            Document: 包含子文档的父文档
        """
        # 创建父文档
        parent_doc = Document(
            page_content=parent_content,
            metadata=parent_metadata or {},
            source=source
        )

        # 创建子文档
        for i, child_content in enumerate(child_contents):
            child_doc = ChildDocument(
                page_content=child_content,
                metadata=parent_metadata.copy() if parent_metadata else {},
                source=source
            )
            parent_doc.add_child(child_doc)

        return parent_doc

    @staticmethod
    def merge_documents(documents: List[Document]) -> Document:
        """合并多个文档为一个父文档

        Args:
            documents: 要合并的文档列表

        Returns:
            Document: 合并后的父文档
        """
        if not documents:
            raise ValueError("文档列表不能为空")

        # 合并内容
        merged_content = "\n\n".join([doc.page_content for doc in documents])

        # 合并元数据
        merged_metadata = documents[0].metadata.copy()
        merged_metadata["merged_from"] = [doc.doc_id for doc in documents]
        merged_metadata["original_count"] = len(documents)

        # 创建合并文档
        merged_doc = Document(
            page_content=merged_content,
            metadata=merged_metadata,
            source=documents[0].source
        )

        # 将原文档作为子文档
        for i, doc in enumerate(documents):
            child_doc = ChildDocument(
                page_content=doc.page_content,
                metadata=doc.metadata.copy(),
                source=doc.source
            )
            merged_doc.add_child(child_doc)

        return merged_doc

    @staticmethod
    def split_document_by_separator(
        document: Document,
        separator: str = "\n\n",
        min_chunk_size: int = 100
    ) -> Document:
        """按分隔符分割文档为父子结构

        Args:
            document: 要分割的文档
            separator: 分隔符
            min_chunk_size: 最小块大小

        Returns:
            Document: 分割后的父文档
        """
        # 分割内容
        chunks = document.page_content.split(separator)

        # 过滤太小的块
        valid_chunks = [chunk.strip() for chunk in chunks if len(chunk.strip()) >= min_chunk_size]

        if not valid_chunks:
            return document

        # 创建父文档（使用原内容）
        parent_doc = Document(
            page_content=document.page_content,
            metadata=document.metadata.copy(),
            source=document.source
        )

        # 创建子文档
        for chunk in valid_chunks:
            child_doc = ChildDocument(
                page_content=chunk,
                metadata=document.metadata.copy(),
                source=document.source
            )
            parent_doc.add_child(child_doc)

        return parent_doc

    @staticmethod
    def validate_parent_child_relationship(document: Document) -> List[str]:
        """验证父子文档关系的完整性

        Args:
            document: 要验证的文档

        Returns:
            List[str]: 验证错误列表，空列表表示验证通过
        """
        errors = []

        if not document.children:
            return errors

        # 检查子文档的父ID是否正确
        for i, child in enumerate(document.children):
            if child.parent_id != document.doc_id:
                errors.append(f"子文档 {i} 的parent_id不匹配")

            if child.position != i:
                errors.append(f"子文档 {i} 的position不正确")

            if not child.metadata.get("is_child"):
                errors.append(f"子文档 {i} 缺少is_child标记")

        return errors

    @staticmethod
    def batch_create_parent_child_documents(
        documents_data: List[Dict[str, Any]]
    ) -> List[Document]:
        """批量创建父子文档

        Args:
            documents_data: 文档数据列表，每个元素包含parent_content, child_contents, metadata等

        Returns:
            List[Document]: 创建的父文档列表
        """
        parent_documents = []

        for doc_data in documents_data:
            parent_content = doc_data.get("parent_content", "")
            child_contents = doc_data.get("child_contents", [])
            metadata = doc_data.get("metadata", {})
            source = doc_data.get("source")

            if parent_content:
                parent_doc = DocumentRelationshipManager.create_parent_child_relationship(
                    parent_content=parent_content,
                    child_contents=child_contents,
                    parent_metadata=metadata,
                    source=source
                )
                parent_documents.append(parent_doc)

        return parent_documents

    @staticmethod
    def optimize_parent_child_structure(document: Document) -> Document:
        """优化父子文档结构

        Args:
            document: 要优化的文档

        Returns:
            Document: 优化后的文档
        """
        if not document.children:
            return document

        # 1. 移除空的子文档
        document.children = [child for child in document.children if child.page_content.strip()]

        # 2. 重新排序子文档
        document.reorder_children()

        # 3. 合并过短的相邻子文档
        min_length = 50  # 最小子文档长度
        merged_children = []
        i = 0

        while i < len(document.children):
            current_child = document.children[i]

            # 如果当前子文档太短，尝试与下一个合并
            if len(current_child.page_content) < min_length and i + 1 < len(document.children):
                next_child = document.children[i + 1]

                # 合并内容
                merged_content = current_child.page_content + "\n" + next_child.page_content

                # 创建新的合并子文档
                merged_child = ChildDocument(
                    page_content=merged_content,
                    metadata=current_child.metadata.copy(),
                    parent_id=current_child.parent_id,
                    parent_content=current_child.parent_content,
                    position=len(merged_children)
                )

                merged_child.metadata.update({
                    "merged_from": [current_child.doc_id, next_child.doc_id],
                    "is_merged": True
                })

                merged_children.append(merged_child)
                i += 2  # 跳过下一个子文档
            else:
                # 更新位置
                current_child.position = len(merged_children)
                current_child.metadata["position"] = len(merged_children)
                merged_children.append(current_child)
                i += 1

        document.children = merged_children
        return document

    @staticmethod
    def extract_document_hierarchy(document: Document) -> Dict[str, Any]:
        """提取文档层次结构信息

        Args:
            document: 要分析的文档

        Returns:
            Dict[str, Any]: 层次结构信息
        """
        hierarchy = {
            "parent": {
                "doc_id": document.doc_id,
                "content_length": len(document.page_content),
                "metadata": document.metadata
            },
            "children": [],
            "statistics": document.get_document_statistics()
        }

        if document.children:
            for child in document.children:
                child_info = {
                    "doc_id": child.doc_id,
                    "position": child.position,
                    "content_length": len(child.page_content),
                    "content_preview": child.page_content[:100] + "..." if len(child.page_content) > 100 else child.page_content,
                    "metadata": child.metadata
                }
                hierarchy["children"].append(child_info)

        return hierarchy

    @staticmethod
    def find_documents_by_criteria(
        documents: List[Document],
        criteria: Dict[str, Any]
    ) -> List[Document]:
        """根据条件查找文档

        Args:
            documents: 文档列表
            criteria: 查找条件

        Returns:
            List[Document]: 符合条件的文档列表
        """
        results = []

        for doc in documents:
            match = True

            # 检查内容长度条件
            if "min_content_length" in criteria:
                if len(doc.page_content) < criteria["min_content_length"]:
                    match = False

            if "max_content_length" in criteria:
                if len(doc.page_content) > criteria["max_content_length"]:
                    match = False

            # 检查子文档数量条件
            if "min_children_count" in criteria:
                if doc.get_children_count() < criteria["min_children_count"]:
                    match = False

            if "max_children_count" in criteria:
                if doc.get_children_count() > criteria["max_children_count"]:
                    match = False

            # 检查元数据条件
            if "metadata_filters" in criteria:
                for key, value in criteria["metadata_filters"].items():
                    if doc.metadata.get(key) != value:
                        match = False
                        break

            # 检查内容关键词
            if "content_keywords" in criteria:
                keywords = criteria["content_keywords"]
                if not any(keyword.lower() in doc.page_content.lower() for keyword in keywords):
                    match = False

            if match:
                results.append(doc)

        return results

    @staticmethod
    def calculate_document_similarity(doc1: Document, doc2: Document) -> float:
        """计算两个文档的相似度

        Args:
            doc1: 第一个文档
            doc2: 第二个文档

        Returns:
            float: 相似度分数（0-1之间）
        """
        # 简单的基于词汇重叠的相似度计算
        words1 = set(doc1.page_content.lower().split())
        words2 = set(doc2.page_content.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0


# ======================================================================
# 新增：层次化RAG模型 (基于Dify架构设计)
# ======================================================================

class HierarchicalDocumentSegment(BaseModel):
    """父段落模型 - 存储在MongoDB
    
    基于Dify的DocumentSegment设计，用于存储父段落信息
    """
    id: str = PydanticField(default_factory=lambda: str(uuid.uuid4()))
    document_id: str  # 所属文档ID
    dataset_id: str   # 数据集ID
    content: str      # 父段落内容
    position: int = 0 # 在文档中的位置
    
    # 元数据
    metadata: Dict[str, Any] = PydanticField(default_factory=dict)
    index_node_id: Optional[str] = None  # 如果父段落也需要索引
    index_node_hash: Optional[str] = None
    
    # 统计信息
    word_count: int = 0
    child_count: int = 0
    hit_count: int = 0  # 检索命中次数
    
    # 时间戳
    created_at: datetime = PydanticField(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = PydanticField(default_factory=lambda: datetime.now(timezone.utc))
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.index_node_hash:
            self.index_node_hash = self._generate_hash()
        self.word_count = len(self.content)
            
    def _generate_hash(self) -> str:
        """生成段落哈希值"""
        text = self.content + str(sorted(self.metadata.items()))
        return hashlib.sha256(text.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "dataset_id": self.dataset_id,
            "content": self.content,
            "position": self.position,
            "metadata": self.metadata,
            "index_node_id": self.index_node_id,
            "index_node_hash": self.index_node_hash,
            "word_count": self.word_count,
            "child_count": self.child_count,
            "hit_count": self.hit_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_point_struct(self) -> Dict[str, Any]:
        """转换为向量存储的数据结构（如果需要索引父段落）"""
        return {
            ConstantField.PRIMARY_KEY.value: self.id,
            ConstantField.CONTENT_KEY.value: self.content,
            ConstantField.METADATA_KEY.value: {
                **self.metadata,
                "document_id": self.document_id,
                "dataset_id": self.dataset_id,
                "position": self.position,
                "segment_type": "parent",
                "index_node_hash": self.index_node_hash,
                "child_count": self.child_count
            },
            ConstantField.GROUP_KEY.value: self.dataset_id
        }


class HierarchicalChildChunk(BaseModel):
    """子块模型 - 部分存储在MongoDB，向量存储在Milvus
    
    基于Dify的ChildChunk设计，用于存储子块信息
    """
    id: str = PydanticField(default_factory=lambda: str(uuid.uuid4()))
    segment_id: str   # 关联的父段落ID
    document_id: str  # 文档ID  
    dataset_id: str   # 数据集ID
    content: str      # 子块内容
    position: int = 0 # 在父段落中的位置
    
    # 向量数据库引用
    index_node_id: str = PydanticField(default_factory=lambda: str(uuid.uuid4()))
    
    # 元数据
    metadata: Dict[str, Any] = PydanticField(default_factory=dict)
    
    # 统计信息
    word_count: int = 0
    hit_count: int = 0  # 检索命中次数
    
    # 向量相关（仅在向量存储中使用）
    vector: Optional[List[float]] = None
    sparse_vector: Optional[List[float]] = None
    
    # 时间戳
    created_at: datetime = PydanticField(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = PydanticField(default_factory=lambda: datetime.now(timezone.utc))
    
    def __init__(self, **data):
        super().__init__(**data)
        self.word_count = len(self.content)
        # 确保index_node_id的唯一性
        if not self.index_node_id:
            self.index_node_id = self.id
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（MongoDB存储）"""
        return {
            "id": self.id,
            "segment_id": self.segment_id,
            "document_id": self.document_id,
            "dataset_id": self.dataset_id,
            "content": self.content,
            "position": self.position,
            "index_node_id": self.index_node_id,
            "metadata": self.metadata,
            "word_count": self.word_count,
            "hit_count": self.hit_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_point_struct(self) -> Dict[str, Any]:
        """转换为向量存储的数据结构"""
        return {
            ConstantField.PRIMARY_KEY.value: self.index_node_id,
            ConstantField.VECTOR.value: self.vector,
            ConstantField.CONTENT_KEY.value: self.content,
            ConstantField.METADATA_KEY.value: {
                **self.metadata,
                "id": self.id,
                "segment_id": self.segment_id,
                "document_id": self.document_id,
                "dataset_id": self.dataset_id,
                "position": self.position,
                "word_count": self.word_count,
                "chunk_type": "child"
            },
            ConstantField.GROUP_KEY.value: self.dataset_id,
            ConstantField.SPARSE_VECTOR.value: self.sparse_vector or self.vector
        }


class HierarchicalSplittingConfig(BaseModel):
    """层次化分割配置 - 基于Dify的父子分块实现
    
    实现Dify风格的父子分块策略：
    - 父块：提供上下文背景（段落或全文档）
    - 子块：用于精确检索（通常是句子）
    """
    parent_mode: Literal["paragraph", "full_doc"] = "paragraph"
    
    # 父段落配置 - 对齐Dify默认值
    parent_chunk_size: int = 500        # Dify默认500 tokens
    parent_chunk_overlap: int = 50      # 减少重叠
    parent_separators: List[str] = PydanticField(default_factory=lambda: ["\n\n", "\n", "。", ". "])
    
    # 子块配置 - 对齐Dify默认值 
    child_chunk_size: int = 200         # Dify默认200 tokens
    child_chunk_overlap: int = 20       # 减少重叠
    child_separators: List[str] = PydanticField(default_factory=lambda: ["\n", "。", "!", "?", "；", "; ", ". ", "! ", "? ", " "])
    
    # 索引配置
    index_child_chunks_only: bool = True  # 仅索引子块到向量数据库
    enable_parent_context: bool = True    # 启用父段落上下文
    
    # 质量控制
    min_child_chunk_size: int = 1  # 对标Dify，几乎不过滤，主要由chunk_size控制
    max_children_per_parent: int = 20
    min_parent_chunk_size: int = 200
    
    # 内容分析
    enable_content_analysis: bool = True
    content_type: Optional[str] = None  # academic, news, dialogue, code, legal


class ParentChildRelationship(BaseModel):
    """父子关系模型
    
    用于表示检索结果中的父子关系
    """
    parent_segment: HierarchicalDocumentSegment
    child_chunks: List[HierarchicalChildChunk]
    max_child_score: float = 0.0
    relevant_child_count: int = 0
    combined_score: float = 0.0
    
    def to_retrieval_result(self) -> Dict[str, Any]:
        """转换为检索结果格式"""
        return {
            "parent_segment": {
                "id": self.parent_segment.id,
                "content": self.parent_segment.content,
                "position": self.parent_segment.position,
                "word_count": self.parent_segment.word_count,
                "child_count": self.parent_segment.child_count
            },
            "child_chunks": [
                {
                    "id": chunk.id,
                    "content": chunk.content,
                    "position": chunk.position,
                    "word_count": chunk.word_count,
                    "score": chunk.metadata.get("score", 0.0)
                }
                for chunk in self.child_chunks
            ],
            "max_child_score": self.max_child_score,
            "relevant_child_count": self.relevant_child_count,
            "combined_score": self.combined_score
        }