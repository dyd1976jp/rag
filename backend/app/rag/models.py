"""
文档模型定义
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field as PydanticField
from .constants import Field as ConstantField
import uuid
import hashlib
from dataclasses import dataclass, field

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
    children: Optional[List['Document']] = None
    
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
        
    def to_point_struct(self) -> Dict[str, Any]:
        """转换为向量存储的数据结构"""
        return {
            ConstantField.PRIMARY_KEY.value: self.doc_id,
            ConstantField.VECTOR.value: self.vector,
            ConstantField.CONTENT_KEY.value: self.page_content,
            ConstantField.METADATA_KEY.value: self.metadata,
            ConstantField.GROUP_KEY.value: self.group_id or "",
            ConstantField.SPARSE_VECTOR.value: self.sparse_vector or self.vector
        }

class DocumentSegment(BaseModel):
    """文档片段"""
    id: str
    page_content: str
    metadata: Dict[str, Any] = PydanticField(default_factory=dict)
    index_node_id: Optional[str] = None
    index_node_hash: Optional[str] = None
    child_ids: Optional[List[str]] = None
    group_id: Optional[str] = None
    children: Optional[List['DocumentSegment']] = None  # 添加子文档列表
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = str(uuid.uuid4())
        if "doc_hash" not in self.metadata:
            self.metadata["doc_hash"] = self._generate_hash()
            
    def _generate_hash(self) -> str:
        """生成片段哈希值"""
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
            "group_id": self.group_id
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
            ConstantField.GROUP_KEY.value: self.group_id or ""
        }

class ChildDocument(Document):
    """子文档"""
    parent_id: Optional[str] = None
    parent_content: Optional[str] = None
    position: Optional[int] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.parent_id and "parent_id" not in self.metadata:
            self.metadata["parent_id"] = self.parent_id
            
    def to_point_struct(self) -> Dict[str, Any]:
        """转换为向量存储的数据结构"""
        point = super().to_point_struct()
        point[ConstantField.METADATA_KEY.value].update({
            "parent_id": self.parent_id,
            "parent_content": self.parent_content,
            "position": self.position
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