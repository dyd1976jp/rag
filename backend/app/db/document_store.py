import logging
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.rag.models import Document, DocumentSegment, ChildChunk

logger = logging.getLogger(__name__)

class DocumentStore:
    """文档存储服务"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.segments_collection = db["document_segments"]
        self.chunks_collection = db["child_chunks"]
        
    async def store_segment(self, segment: DocumentSegment) -> str:
        """存储父块"""
        try:
            result = await self.segments_collection.insert_one(segment.dict())
            logger.info(f"存储父块成功: {segment.index_node_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"存储父块失败: {e}")
            raise
            
    async def store_chunks(self, chunks: List[ChildChunk]) -> List[str]:
        """存储子块"""
        try:
            if not chunks:
                return []
                
            # 批量插入子块
            chunk_dicts = [chunk.dict() for chunk in chunks]
            result = await self.chunks_collection.insert_many(chunk_dicts)
            
            logger.info(f"存储 {len(chunks)} 个子块成功")
            return [str(id) for id in result.inserted_ids]
            
        except Exception as e:
            logger.error(f"存储子块失败: {e}")
            raise
            
    async def get_segment(self, segment_id: str) -> Optional[DocumentSegment]:
        """获取父块"""
        try:
            doc = await self.segments_collection.find_one({"index_node_id": segment_id})
            if doc:
                return DocumentSegment(**doc)
            return None
        except Exception as e:
            logger.error(f"获取父块失败: {e}")
            raise
            
    async def get_chunks_by_segment(self, segment_id: str) -> List[ChildChunk]:
        """获取父块的所有子块"""
        try:
            cursor = self.chunks_collection.find({"segment_id": segment_id})
            chunks = []
            async for doc in cursor:
                chunks.append(ChildChunk(**doc))
            return chunks
        except Exception as e:
            logger.error(f"获取子块失败: {e}")
            raise
            
    async def delete_segment(self, segment_id: str):
        """删除父块及其子块"""
        try:
            # 删除父块
            await self.segments_collection.delete_one({"index_node_id": segment_id})
            # 删除子块
            await self.chunks_collection.delete_many({"segment_id": segment_id})
            logger.info(f"删除父块 {segment_id} 及其子块成功")
        except Exception as e:
            logger.error(f"删除父块及子块失败: {e}")
            raise
            
    async def update_segment(self, segment: DocumentSegment):
        """更新父块"""
        try:
            await self.segments_collection.update_one(
                {"index_node_id": segment.index_node_id},
                {"$set": segment.dict()}
            )
            logger.info(f"更新父块成功: {segment.index_node_id}")
        except Exception as e:
            logger.error(f"更新父块失败: {e}")
            raise 