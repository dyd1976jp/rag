"""
MongoDB数据库管理模块
"""

import os
import logging
from typing import List, Optional, Dict, Any
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from .models import DocumentSegment, ChildChunk, Document
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class MongoDBManager:
    """MongoDB数据库管理器"""
    
    def __init__(self, db: Database):
        self.db = db
        self.segments_collection = db["segments"]
        self.chunks_collection = db["chunks"]
        self.documents_collection = db["documents"]
        
        # 连接到MongoDB
        try:
            self.client = MongoClient(os.environ.get("MONGODB_URI", "mongodb://localhost:27017"))
            self.db = self.client[os.environ.get("MONGODB_DB", "rag_chat")]
            
            # 获取集合
            self.segments_collection: Collection = self.db.document_segments
            self.chunks_collection: Collection = self.db.child_chunks
            
            # 创建索引
            self._create_indexes()
            
            logger.info(f"MongoDB连接成功: {os.environ.get('MONGODB_URI', 'mongodb://localhost:27017')}")
        except Exception as e:
            logger.error(f"MongoDB连接失败: {str(e)}")
            raise
    
    def _create_indexes(self):
        """创建必要的索引"""
        try:
            # 删除旧的唯一索引
            self.segments_collection.drop_index("index_node_id_1")
        except:
            pass
            
        # 重新创建非唯一索引
        self.segments_collection.create_index("index_node_id", unique=False)
        self.segments_collection.create_index("index_node_hash")
        
        # 子块索引
        self.chunks_collection.create_index("segment_id")
        self.chunks_collection.create_index([("metadata.chunk_id", 1)], unique=True)
    
    def save_document_segment(self, segment: DocumentSegment) -> bool:
        """保存文档段落"""
        try:
            # 转换为字典
            segment_dict = {
                "_id": segment.id,
                "page_content": segment.page_content,
                "metadata": segment.metadata,
                "index_node_hash": segment.index_node_hash,
                "child_ids": segment.child_ids,
                "group_id": segment.group_id
            }
            
            # 使用upsert模式保存
            result = self.segments_collection.update_one(
                {"_id": segment.id},
                {"$set": segment_dict},
                upsert=True
            )
            
            return result.acknowledged
        except Exception as e:
            logger.error(f"保存文档段落失败: {str(e)}")
            return False
    
    def save_child_chunk(self, chunk: ChildChunk) -> bool:
        """保存子块"""
        try:
            # 转换为字典
            chunk_dict = {
                "_id": chunk.metadata.get("chunk_id", str(uuid.uuid4())),
                "segment_id": chunk.segment_id,
                "page_content": chunk.page_content,
                "metadata": chunk.metadata,
                "start_pos": chunk.start_pos,
                "end_pos": chunk.end_pos,
                "group_id": chunk.group_id
            }
            
            # 使用upsert模式保存
            result = self.chunks_collection.update_one(
                {"_id": chunk.metadata.get("chunk_id", str(uuid.uuid4()))},
                {"$set": chunk_dict},
                upsert=True
            )
            
            return result.acknowledged
        except Exception as e:
            logger.error(f"保存子块失败: {str(e)}")
            return False
    
    def get_document_segment(self, segment_id: str) -> Optional[DocumentSegment]:
        """获取文档段落"""
        try:
            doc = self.segments_collection.find_one({"_id": segment_id})
            if doc:
                return DocumentSegment(
                    id=doc["_id"],
                    page_content=doc["page_content"],
                    metadata=doc["metadata"],
                    index_node_hash=doc.get("index_node_hash"),
                    child_ids=doc.get("child_ids"),
                    group_id=doc.get("group_id")
                )
            return None
        except Exception as e:
            logger.error(f"获取文档段落失败: {str(e)}")
            return None
    
    def get_child_chunks(self, segment_id: str) -> List[ChildChunk]:
        """获取指定段落的所有子块"""
        try:
            chunks = self.chunks_collection.find({"segment_id": segment_id})
            return [
                ChildChunk(
                    segment_id=chunk["segment_id"],
                    page_content=chunk["page_content"],
                    metadata=chunk["metadata"],
                    start_pos=chunk["start_pos"],
                    end_pos=chunk["end_pos"],
                    group_id=chunk.get("group_id")
                )
                for chunk in chunks
            ]
        except Exception as e:
            logger.error(f"获取子块失败: {str(e)}")
            return []
    
    def delete_document_segment(self, segment_id: str) -> bool:
        """删除文档段落"""
        try:
            result = self.segments_collection.delete_one({"_id": segment_id})
            return result.acknowledged
        except Exception as e:
            logger.error(f"删除文档段落失败: {str(e)}")
            return False
    
    def delete_child_chunks(self, segment_id: str) -> bool:
        """删除指定段落的所有子块"""
        try:
            result = self.chunks_collection.delete_many({"segment_id": segment_id})
            return result.acknowledged
        except Exception as e:
            logger.error(f"删除子块失败: {str(e)}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        try:
            self.client.close()
            logger.info("MongoDB连接已关闭")
        except Exception as e:
            logger.error(f"关闭MongoDB连接失败: {str(e)}")
    
    def save_document(self, document: Document) -> str:
        """保存文档到MongoDB"""
        try:
            # 生成唯一的文档ID
            doc_id = document.doc_id
            
            # 准备文档数据
            doc_dict = {
                "_id": doc_id,
                "page_content": document.page_content,
                "metadata": document.metadata,
                "doc_hash": document.doc_hash,
                "vector": document.vector,
                "sparse_vector": document.sparse_vector,
                "group_id": document.group_id
            }
            
            # 如果文档有子文档，保存子文档ID
            if hasattr(document, 'children') and document.children:
                doc_dict["child_ids"] = [
                    str(uuid.uuid4())  # 为每个子文档生成唯一ID
                    for child in document.children
                ]
            
            # 保存到MongoDB
            result = self.documents_collection.insert_one(doc_dict)
            
            if result.inserted_id:
                logger.info(f"文档保存成功: {result.inserted_id}")
                return str(result.inserted_id)
            else:
                logger.error("文档保存失败")
                return None
                
        except Exception as e:
            logger.error(f"保存文档失败: {str(e)}")
            raise

    def insert_segments(self, segments: List[DocumentSegment]) -> List[str]:
        """插入文档段落"""
        segment_dicts = []
        for segment in segments:
            segment_dict = {
                "_id": segment.id,
                "page_content": segment.page_content,
                "metadata": segment.metadata,
                "index_node_hash": segment.index_node_hash,
                "child_ids": segment.child_ids,
                "group_id": segment.group_id
            }
            segment_dicts.append(segment_dict)
            
        if segment_dicts:
            self.segments_collection.insert_many(segment_dicts)
            
        return [s["_id"] for s in segment_dicts]
        
    def insert_chunks(self, chunks: List[ChildChunk]) -> List[str]:
        """插入子块"""
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = {
                "_id": chunk.metadata.get("chunk_id", str(uuid.uuid4())),
                "segment_id": chunk.segment_id,
                "page_content": chunk.page_content,
                "metadata": chunk.metadata,
                "start_pos": chunk.start_pos,
                "end_pos": chunk.end_pos,
                "group_id": chunk.group_id
            }
            chunk_dicts.append(chunk_dict)
            
        if chunk_dicts:
            self.chunks_collection.insert_many(chunk_dicts)
            
        return [c["_id"] for c in chunk_dicts]
        
    def get_segment_by_id(self, segment_id: str) -> Optional[DocumentSegment]:
        """根据ID获取段落"""
        doc = self.segments_collection.find_one({"_id": segment_id})
        if not doc:
            return None
            
        return DocumentSegment(
            id=doc["_id"],
            page_content=doc["page_content"],
            metadata=doc["metadata"],
            index_node_hash=doc.get("index_node_hash"),
            child_ids=doc.get("child_ids"),
            group_id=doc.get("group_id")
        )
        
    def get_chunk_by_id(self, chunk_id: str) -> Optional[ChildChunk]:
        """根据ID获取子块"""
        chunk = self.chunks_collection.find_one({"_id": chunk_id})
        if not chunk:
            return None
            
        return ChildChunk(
            segment_id=chunk["segment_id"],
            page_content=chunk["page_content"],
            metadata=chunk["metadata"],
            start_pos=chunk["start_pos"],
            end_pos=chunk["end_pos"],
            group_id=chunk.get("group_id")
        )
        
    def get_chunks_by_segment_id(self, segment_id: str) -> List[ChildChunk]:
        """根据段落ID获取所有子块"""
        chunks = self.chunks_collection.find({"segment_id": segment_id})
        return [
            ChildChunk(
                segment_id=chunk["segment_id"],
                page_content=chunk["page_content"],
                metadata=chunk["metadata"],
                start_pos=chunk["start_pos"],
                end_pos=chunk["end_pos"],
                group_id=chunk.get("group_id")
            )
            for chunk in chunks
        ]
        
    def insert_document(self, document: Document) -> str:
        """插入原始文档"""
        doc_dict = {
            "_id": document.doc_id,
            "page_content": document.page_content,
            "metadata": document.metadata,
            "doc_hash": document.doc_hash,
            "vector": document.vector,
            "sparse_vector": document.sparse_vector,
            "group_id": document.group_id
        }
        
        self.documents_collection.insert_one(doc_dict)
        return doc_dict["_id"]
        
    def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        """根据ID获取原始文档"""
        doc = self.documents_collection.find_one({"_id": doc_id})
        if not doc:
            return None
            
        return Document(
            doc_id=doc["_id"],
            page_content=doc["page_content"],
            metadata=doc["metadata"],
            doc_hash=doc.get("doc_hash"),
            vector=doc.get("vector"),
            sparse_vector=doc.get("sparse_vector"),
            group_id=doc.get("group_id")
        ) 