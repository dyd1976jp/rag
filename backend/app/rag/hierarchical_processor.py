"""
层次化文档处理器

基于Dify的父子分块架构实现，提供高效的文档分割和存储功能
"""

import logging
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from .models import (
    Document, 
    HierarchicalDocumentSegment, 
    HierarchicalChildChunk,
    HierarchicalSplittingConfig,
    ParentChildRelationship
)
from .text_splitter import FixedRecursiveCharacterTextSplitter
from ..db.connections.mongodb import mongodb_manager

logger = logging.getLogger(__name__)


class HierarchicalDocumentProcessor:
    """层次化文档处理器
    
    实现Dify风格的父子分块处理，支持灵活的分割策略和数据库存储
    """
    
    def __init__(self, config: Optional[HierarchicalSplittingConfig] = None):
        """初始化处理器
        
        Args:
            config: 层次化分割配置
        """
        self.config = config or HierarchicalSplittingConfig()
        
        # 初始化父段落分割器
        self.parent_splitter = FixedRecursiveCharacterTextSplitter(
            chunk_size=self.config.parent_chunk_size,
            chunk_overlap=self.config.parent_chunk_overlap,
            separators=self.config.parent_separators,
            keep_separator=True
        )
        
        # 初始化子块分割器 - 启用强制分割模式确保按分隔符分割
        self.child_splitter = FixedRecursiveCharacterTextSplitter(
            chunk_size=self.config.child_chunk_size,
            chunk_overlap=self.config.child_chunk_overlap,
            separators=self.config.child_separators,
            keep_separator=True,
            force_split_on_separator=True  # 强制按分隔符分割
        )
        
        logger.info(f"层次化文档处理器初始化完成，配置: {self.config.dict()}")
    
    def update_config(self, config: HierarchicalSplittingConfig):
        """更新配置并重新初始化分割器
        
        Args:
            config: 新的层次化分割配置
        """
        self.config = config
        
        # 重新初始化父段落分割器
        self.parent_splitter = FixedRecursiveCharacterTextSplitter(
            chunk_size=self.config.parent_chunk_size,
            chunk_overlap=self.config.parent_chunk_overlap,
            separators=self.config.parent_separators,
            keep_separator=True
        )
        
        # 重新初始化子块分割器 - 启用强制分割模式确保按分隔符分割
        self.child_splitter = FixedRecursiveCharacterTextSplitter(
            chunk_size=self.config.child_chunk_size,
            chunk_overlap=self.config.child_chunk_overlap,
            separators=self.config.child_separators,
            keep_separator=True,
            force_split_on_separator=True  # 强制按分隔符分割
        )
        
        logger.info(f"层次化文档处理器配置已更新: {self.config.dict()}")
    
    async def process_document_with_hierarchy(
        self,
        document: Document,
        dataset_id: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """处理文档并创建父子层次结构

        Args:
            document: 待处理的文档
            dataset_id: 数据集ID，如果不提供则使用文档元数据中的用户ID
            document_id: 文档ID，如果不提供则使用文档对象中的doc_id或生成新的

        Returns:
            Dict[str, Any]: 处理结果，包含父段落和子块统计信息
        """
        try:
            start_time = datetime.now()
            
            # 获取数据集ID
            if not dataset_id:
                dataset_id = document.metadata.get("created_by", "default")

            # 使用传入的document_id，如果没有则使用文档对象中的doc_id，最后才生成新的
            if not document_id:
                document_id = document.doc_id or str(uuid.uuid4())
            
            logger.info(f"开始处理文档: {document_id}, 内容长度: {len(document.page_content)}")
            
            # 1. 根据模式创建父段落
            if self.config.parent_mode == "full_doc":
                parent_segments = self._create_full_doc_segment(document, document_id, dataset_id)
            else:  # paragraph mode
                parent_segments = self._create_parent_segments(document, document_id, dataset_id)
            
            logger.info(f"创建了 {len(parent_segments)} 个父段落")
            
            # 2. 为每个父段落创建子块
            all_child_chunks = []
            segment_chunk_mapping = {}
            
            for segment in parent_segments:
                child_chunks = self._create_child_chunks(segment)
                
                # 过滤太小的子块
                valid_chunks = []
                for chunk in child_chunks:
                    if len(chunk.content) >= self.config.min_child_chunk_size:
                        valid_chunks.append(chunk)
                    else:
                        logger.debug(f"过滤掉过小的子块: {len(chunk.content)} < {self.config.min_child_chunk_size}")
                
                # 限制每个父段落的子块数量
                if len(valid_chunks) > self.config.max_children_per_parent:
                    logger.warning(f"父段落 {segment.id} 的子块数量 ({len(valid_chunks)}) 超过限制 ({self.config.max_children_per_parent})，将截断")
                    valid_chunks = valid_chunks[:self.config.max_children_per_parent]
                
                all_child_chunks.extend(valid_chunks)
                segment_chunk_mapping[segment.id] = valid_chunks
                
                # 更新父段落的子块数量
                segment.child_count = len(valid_chunks)
            
            logger.info(f"总共创建了 {len(all_child_chunks)} 个子块")
            
            # 3. 批量保存到数据库
            logger.info(f"准备保存层次结构到数据库，document_id: {document_id}")
            await self._save_hierarchy_to_db(parent_segments, all_child_chunks)

            # 验证保存是否成功
            db = await mongodb_manager.get_async_database()
            saved_segments_count = await db["document_segments"].count_documents({"document_id": document_id})
            saved_chunks_count = await db["child_chunks"].count_documents({"document_id": document_id})
            logger.info(f"保存验证 - 父段落: {saved_segments_count}, 子块: {saved_chunks_count}")

            processing_time = (datetime.now() - start_time).total_seconds()

            result = {
                "success": True,
                "document_id": document_id,
                "parent_segments_count": len(parent_segments),
                "child_chunks_count": len(all_child_chunks),
                "processing_time": processing_time,
                "config": self.config.dict()
            }

            logger.info(f"文档处理完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"处理文档失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id if 'document_id' in locals() else None
            }
    
    def _create_full_doc_segment(
        self, 
        document: Document, 
        document_id: str, 
        dataset_id: str
    ) -> List[HierarchicalDocumentSegment]:
        """创建全文档作为单一父段落 - 应用Dify的 10,000 token 限制
        
        Args:
            document: 源文档
            document_id: 文档ID
            dataset_id: 数据集ID
            
        Returns:
            List[HierarchicalDocumentSegment]: 包含单个父段落的列表
        """
        logger.debug("使用全文档模式创建父段落（应用Dify 10,000 token限制）")
        
        # 应用Dify的 10,000 token 限制
        content = document.page_content
        max_tokens = 10000
        
        # 简单的token估算（中文字符数 + 英文单词数）
        chinese_chars = len([c for c in content if '\u4e00' <= c <= '\u9fff'])
        english_words = len(content.replace('中文', ' ').split())
        estimated_tokens = chinese_chars + english_words
        
        if estimated_tokens > max_tokens:
            logger.warning(f"文档内容超过{max_tokens} tokens（估算{estimated_tokens}），将截断到前{max_tokens} tokens")
            # 简单截断策略：按比例截断
            truncate_ratio = max_tokens / estimated_tokens
            truncate_length = int(len(content) * truncate_ratio)
            content = content[:truncate_length]
            # 在句子边界处截断
            if not content.endswith(('。', '.', '!', '?', '！', '？')):
                last_sentence_end = max(
                    content.rfind('。'),
                    content.rfind('.'),
                    content.rfind('!'),
                    content.rfind('?'),
                    content.rfind('！'),
                    content.rfind('？')
                )
                if last_sentence_end > 0:
                    content = content[:last_sentence_end + 1]
        
        segment = HierarchicalDocumentSegment(
            document_id=document_id,
            dataset_id=dataset_id,
            content=content,
            position=0,
            metadata={
                **document.metadata,
                "segment_type": "full_doc",
                "original_doc_id": document.doc_id,
                "is_truncated": estimated_tokens > max_tokens,
                "original_tokens": estimated_tokens,
                "final_tokens": max_tokens if estimated_tokens > max_tokens else estimated_tokens
            }
        )
        
        return [segment]
    
    def _create_parent_segments(
        self, 
        document: Document, 
        document_id: str, 
        dataset_id: str
    ) -> List[HierarchicalDocumentSegment]:
        """创建段落级父段落
        
        Args:
            document: 源文档
            document_id: 文档ID
            dataset_id: 数据集ID
            
        Returns:
            List[HierarchicalDocumentSegment]: 父段落列表
        """
        logger.debug("使用段落模式创建父段落")
        
        # 使用父段落分割器分割文档
        parent_texts = self.parent_splitter.split_text(document.page_content)
        
        segments = []
        for i, text in enumerate(parent_texts):
            # 对于小文档，进一步降低最小段落大小要求
            min_size = self.config.min_parent_chunk_size
            if len(document.page_content) < 1000:  # 中小文档（少于1000字符）
                min_size = 10  # 非常宽松的最小长度，确保所有有意义的段落都被保留
                logger.debug(f"小文档检测，降低最小段落大小为: {min_size}")
            
            # 过滤太小的段落（只过滤空白或极短内容）
            if len(text.strip()) < min_size:
                logger.debug(f"跳过过小的父段落: {len(text.strip())} < {min_size}")
                continue
                
            segment = HierarchicalDocumentSegment(
                document_id=document_id,
                dataset_id=dataset_id,
                content=text,
                position=i,
                metadata={
                    **document.metadata,
                    "segment_type": "paragraph",
                    "original_doc_id": document.doc_id,
                    "segment_index": i
                }
            )
            segments.append(segment)
        
        logger.debug(f"创建了 {len(segments)} 个有效父段落")
        return segments
    
    def _create_child_chunks(
        self, 
        parent_segment: HierarchicalDocumentSegment
    ) -> List[HierarchicalChildChunk]:
        """为父段落创建子块
        
        Args:
            parent_segment: 父段落
            
        Returns:
            List[HierarchicalChildChunk]: 子块列表
        """
        logger.debug(f"为父段落 {parent_segment.id} 创建子块")
        
        # 使用子块分割器分割父段落
        child_texts = self.child_splitter.split_text(parent_segment.content)
        
        chunks = []
        for i, text in enumerate(child_texts):
            chunk = HierarchicalChildChunk(
                segment_id=parent_segment.id,
                document_id=parent_segment.document_id,
                dataset_id=parent_segment.dataset_id,
                content=text,
                position=i,
                metadata={
                    **parent_segment.metadata,
                    "chunk_type": "child",
                    "parent_segment_id": parent_segment.id,
                    "chunk_index": i
                }
            )
            chunks.append(chunk)
        
        logger.debug(f"为父段落 {parent_segment.id} 创建了 {len(chunks)} 个子块")
        return chunks
    
    async def _save_hierarchy_to_db(
        self, 
        segments: List[HierarchicalDocumentSegment], 
        chunks: List[HierarchicalChildChunk]
    ) -> None:
        """保存层次结构到数据库
        
        Args:
            segments: 父段落列表
            chunks: 子块列表
        """
        try:
            logger.info(f"开始保存层次结构到数据库: {len(segments)} 个父段落, {len(chunks)} 个子块")

            # 获取数据库连接
            db = await mongodb_manager.get_async_database()

            # 保存父段落
            if segments:
                segment_docs = [segment.to_dict() for segment in segments]
                await db["document_segments"].insert_many(segment_docs)
                logger.info(f"保存了 {len(segment_docs)} 个父段落到 document_segments 集合")

            # 保存子块元数据
            if chunks:
                chunk_docs = [chunk.to_dict() for chunk in chunks]
                await db["child_chunks"].insert_many(chunk_docs)
                logger.info(f"保存了 {len(chunk_docs)} 个子块到 child_chunks 集合")

            logger.info("层次结构保存完成")
            
        except Exception as e:
            logger.error(f"保存层次结构到数据库失败: {str(e)}", exc_info=True)
            raise
    
    async def get_document_hierarchy(
        self, 
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取文档的层次结构
        
        Args:
            document_id: 文档ID
            
        Returns:
            Optional[Dict[str, Any]]: 层次结构信息，如果不存在返回None
        """
        try:
            # 获取数据库连接
            db = await mongodb_manager.get_async_database()

            # 获取父段落
            segments_cursor = db["document_segments"].find(
                {"document_id": document_id}
            ).sort("position", 1)

            segments = []
            async for seg_doc in segments_cursor:
                segments.append(seg_doc)

            if not segments:
                logger.warning(f"未找到文档 {document_id} 的父段落")
                return None

            # 获取子块
            chunks_cursor = db["child_chunks"].find(
                {"document_id": document_id}
            ).sort([("segment_id", 1), ("position", 1)])
            
            chunks_by_segment = {}
            async for chunk_doc in chunks_cursor:
                segment_id = chunk_doc["segment_id"]
                if segment_id not in chunks_by_segment:
                    chunks_by_segment[segment_id] = []
                chunks_by_segment[segment_id].append(chunk_doc)
            
            # 组装层次结构
            hierarchy = {
                "document_id": document_id,
                "parent_segments": segments,
                "child_chunks_by_segment": chunks_by_segment,
                "total_segments": len(segments),
                "total_chunks": sum(len(chunks) for chunks in chunks_by_segment.values())
            }
            
            logger.info(f"获取文档 {document_id} 的层次结构: {hierarchy['total_segments']} 个父段落, {hierarchy['total_chunks']} 个子块")
            return hierarchy
            
        except Exception as e:
            logger.error(f"获取文档层次结构失败: {str(e)}", exc_info=True)
            return None
    
    async def delete_document_hierarchy(
        self, 
        document_id: str
    ) -> Dict[str, Any]:
        """删除文档的层次结构
        
        Args:
            document_id: 文档ID
            
        Returns:
            Dict[str, Any]: 删除结果
        """
        try:
            logger.info(f"开始删除文档 {document_id} 的层次结构")

            # 获取数据库连接
            db = await mongodb_manager.get_async_database()

            # 删除子块
            chunk_result = await db["child_chunks"].delete_many(
                {"document_id": document_id}
            )

            # 删除父段落
            segment_result = await db["document_segments"].delete_many(
                {"document_id": document_id}
            )
            
            result = {
                "success": True,
                "document_id": document_id,
                "deleted_segments": segment_result.deleted_count,
                "deleted_chunks": chunk_result.deleted_count
            }
            
            logger.info(f"删除完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"删除文档层次结构失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id
            }
    
    def get_child_chunks_for_vector_indexing(
        self, 
        chunks: List[HierarchicalChildChunk]
    ) -> List[Document]:
        """将子块转换为适合向量索引的Document对象
        
        Args:
            chunks: 子块列表
            
        Returns:
            List[Document]: 转换后的Document对象列表
        """
        documents = []
        
        for chunk in chunks:
            # 创建Document对象，用于向量索引
            doc = Document(
                page_content=chunk.content,
                metadata=chunk.metadata,
                doc_id=chunk.index_node_id  # 使用index_node_id作为向量存储的主键
            )
            documents.append(doc)
        
        logger.debug(f"转换了 {len(documents)} 个子块为Document对象")
        return documents


# 全局实例
hierarchical_processor = HierarchicalDocumentProcessor()