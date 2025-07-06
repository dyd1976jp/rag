"""
RAG服务模块，提供对RAG功能的封装
"""
import logging
import os
import uuid
import time
from typing import List, Dict, Any, Optional
from app.rag import (
    retrieval_service, 
    document_processor, 
    document_splitter, 
    pdf_processor,
    embedding_model
)
from app.rag.document_processor import Document
from app.rag.hierarchical_processor import hierarchical_processor
from app.rag.hierarchical_retriever import hierarchical_retriever
from app.rag.models import HierarchicalSplittingConfig
from app.db.connections.mongodb import mongodb_manager
from datetime import datetime, timezone
from ..core.paths import (
    UPLOADS_DIR,
    VECTORS_DIR,
    CACHE_DIR,
    RESULTS_DIR
)

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.collection_name = os.environ.get("RAG_COLLECTION_NAME", "documents")
        self.upload_dir = str(UPLOADS_DIR)
        self.vectors_dir = str(VECTORS_DIR)
        self.cache_dir = str(CACHE_DIR)
        self.results_dir = str(RESULTS_DIR)
        # 批处理大小
        self.batch_size = int(os.environ.get("RAG_BATCH_SIZE", "50"))

        # 索引相关配置
        self.vector_collection_name = os.environ.get("RAG_VECTOR_COLLECTION", "rag_documents")
        
        # 层次化处理配置
        self.enable_hierarchical_processing = os.environ.get("ENABLE_HIERARCHICAL_RAG", "true").lower() == "true"
        self.hierarchical_config = HierarchicalSplittingConfig(
            parent_mode=os.environ.get("HIERARCHICAL_PARENT_MODE", "paragraph"),
            parent_chunk_size=int(os.environ.get("HIERARCHICAL_PARENT_CHUNK_SIZE", "1000")),
            child_chunk_size=int(os.environ.get("HIERARCHICAL_CHILD_CHUNK_SIZE", "300")),
            index_child_chunks_only=os.environ.get("HIERARCHICAL_INDEX_CHILD_ONLY", "true").lower() == "true"
        )

        # 确保上传目录存在
        os.makedirs(self.upload_dir, exist_ok=True)

        # 初始化时创建必要的MongoDB索引
        # 注意：这里不直接调用异步方法，而是在应用启动时调用setup_indexes方法

        logger.info(f"初始化RAG服务: 文档集合={self.collection_name}, 向量集合={self.vector_collection_name}")
        logger.info(f"批处理配置: 批次大小={self.batch_size}")
        logger.info(f"层次化处理: enabled={self.enable_hierarchical_processing}, config={self.hierarchical_config.dict()}")

    def _get_rag_components(self):
        """动态获取RAG组件，确保获取最新的初始化状态"""
        from app.rag import (
            retrieval_service,
            document_processor,
            document_splitter,
            pdf_processor,
            embedding_model
        )
        return {
            'retrieval_service': retrieval_service,
            'document_processor': document_processor,
            'document_splitter': document_splitter,
            'pdf_processor': pdf_processor,
            'embedding_model': embedding_model
        }
    
    async def _get_database(self):
        """获取数据库连接"""
        return await mongodb_manager.get_async_database()

    async def _ensure_mongodb_connection(self) -> bool:
        """确保MongoDB连接可用"""
        try:
            db = await self._get_database()
            # 测试连接
            await db.command('ping')
            return True
        except Exception as e:
            logger.error(f"MongoDB连接检查失败: {str(e)}")
            return False

    async def setup_indexes(self):
        """应用启动时调用此方法来设置索引"""
        await self._setup_mongodb_indexes()
    
    async def _setup_mongodb_indexes(self):
        """创建必要的MongoDB索引"""
        try:
            # 获取数据库连接
            db = await self._get_database()

            # 确保文档集合存在并创建索引
            await db[self.collection_name].create_index("id", unique=True)
            await db[self.collection_name].create_index("user_id")
            await db[self.collection_name].create_index("document_id")
            await db[self.collection_name].create_index("file_name")
            await db[self.collection_name].create_index("status")

            # 层次化存储的索引
            if self.enable_hierarchical_processing:
                # 父段落索引
                await db["document_segments"].create_index("id", unique=True)
                await db["document_segments"].create_index([
                    ("document_id", 1),
                    ("position", 1)
                ])
                await db["document_segments"].create_index("dataset_id")
                await db["document_segments"].create_index("hit_count")

                # 子块索引
                await db["child_chunks"].create_index("id", unique=True)
                await db["child_chunks"].create_index([
                    ("segment_id", 1),
                    ("position", 1)
                ])
                await db["child_chunks"].create_index([
                    ("index_node_id", 1),
                    ("dataset_id", 1)
                ])
                await db["child_chunks"].create_index("document_id")

                logger.info("层次化存储MongoDB索引创建成功")

            logger.info(f"MongoDB索引创建成功: 集合={self.collection_name}")
        except Exception as e:
            logger.error(f"创建MongoDB索引失败: {str(e)}")
    
    async def process_document(
        self, 
        file_path: str, 
        file_name: str, 
        user_id: str,
        chunk_size: int = None,
        chunk_overlap: int = None,
        split_by_paragraph: bool = None,
        split_by_sentence: bool = None
    ) -> Dict[str, Any]:
        """
        处理文档并存储到向量数据库
        
        Args:
            file_path: 文件路径
            file_name: 文件名
            user_id: 用户ID
            chunk_size: 文档分块大小
            chunk_overlap: 分块重叠大小
            split_by_paragraph: 是否按段落分割
            split_by_sentence: 是否按句子分割
            
        Returns:
            处理结果
        """
        try:
            start_time = datetime.now()

            # 检查RAG服务是否可用
            if not self._check_rag_available():
                return {
                    "success": False,
                    "message": "RAG服务不可用，请确保Milvus和嵌入模型服务已启动"
                }

            # 获取RAG组件
            components = self._get_rag_components()
            retrieval_service = components['retrieval_service']
            document_processor = components['document_processor']
            document_splitter = components['document_splitter']
            pdf_processor = components['pdf_processor']
            embedding_model = components['embedding_model']

            # 调试信息：检查组件是否正确获取
            logger.info(f"RAG组件获取结果:")
            logger.info(f"- retrieval_service: {retrieval_service is not None}")
            logger.info(f"- document_processor: {document_processor is not None}")
            logger.info(f"- document_splitter: {document_splitter is not None}")
            logger.info(f"- pdf_processor: {pdf_processor is not None}")
            logger.info(f"- embedding_model: {embedding_model is not None}")

            if embedding_model is None:
                logger.error("embedding_model 为 None，无法继续处理")
                return {
                    "success": False,
                    "message": "嵌入模型未正确初始化，请检查RAG服务配置"
                }

            # 获取文件大小和限制配置
            file_size = os.path.getsize(file_path)
            max_file_size = int(os.environ.get("MAX_FILE_SIZE", "104857600"))  # 默认100MB
            
            # 检查文件大小是否超过限制
            if file_size > max_file_size:
                logger.warning(f"文件大小({file_size}字节)超过限制({max_file_size}字节)")
                return {
                    "success": False,
                    "message": f"文件大小({file_size/1024/1024:.2f}MB)超过限制({max_file_size/1024/1024:.2f}MB)"
                }
                
            # 获取处理超时设置（默认30分钟）
            processing_timeout = int(os.environ.get("PROCESSING_TIMEOUT", "1800"))  # 默认30分钟
            
            # 生成文档ID和数据集ID
            doc_id = str(uuid.uuid4())
            dataset_id = user_id  # 使用用户ID作为数据集ID
            
            # 准备元数据
            metadata = {
                "doc_id": doc_id,
                "document_id": doc_id,
                "dataset_id": dataset_id,
                "file_name": file_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": user_id,
                "file_size": file_size
            }
            
            # 记录切割参数到元数据
            if chunk_size is not None:
                metadata["chunk_size"] = chunk_size
            if chunk_overlap is not None:
                metadata["chunk_overlap"] = chunk_overlap
            if split_by_paragraph is not None:
                metadata["split_by_paragraph"] = split_by_paragraph
            if split_by_sentence is not None:
                metadata["split_by_sentence"] = split_by_sentence
            
            # 记录文档处理状态为"processing"
            doc_info = {
                "id": doc_id,
                "file_name": file_name,
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc),
                "status": "processing",
                "file_size": file_size,
                "processing_details": {
                    "start_time": datetime.now(timezone.utc),
                    "timeout": processing_timeout
                }
            }
            
            # 添加切割参数到文档信息
            if chunk_size is not None:
                doc_info["chunk_size"] = chunk_size
            if chunk_overlap is not None:
                doc_info["chunk_overlap"] = chunk_overlap
            if split_by_paragraph is not None:
                doc_info["split_by_paragraph"] = split_by_paragraph
            if split_by_sentence is not None:
                doc_info["split_by_sentence"] = split_by_sentence
            
            # 检查MongoDB连接
            if not await self._ensure_mongodb_connection():
                return {
                    "success": False,
                    "message": "数据库连接失败，无法处理文档"
                }

            await mongodb.db[self.collection_name].insert_one(doc_info)
            
            # 根据文件类型处理文档
            if file_name.lower().endswith('.pdf'):
                document = pdf_processor.process_pdf(file_path, metadata)
            else:
                # 处理文本文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                document = Document(page_content=content, metadata=metadata)
                
            # 验证和清洗文档
            if not document_processor.validate_document(document):
                # 更新状态为失败
                await mongodb.db[self.collection_name].update_one(
                    {"id": doc_id},
                    {"$set": {
                        "status": "failed", 
                        "error": "文档验证失败，请检查格式和内容",
                        "processing_details": {
                            "end_time": datetime.now(timezone.utc)
                        }
                    }}
                )
                
                return {
                    "success": False,
                    "message": "文档验证失败，请检查格式和内容"
                }
                
            cleaned_document = document_processor.clean_document(document)
            
            # 分割文档
            try:
                logger.info(f"开始分割文档，文档ID: {doc_id}, 文档大小: {len(cleaned_document.page_content)} 字符")
                logger.debug(f"文档内容前100字符预览: {cleaned_document.page_content[:100]}...")
                
                # 创建临时文档分割器并应用自定义参数
                temp_splitter = None
                if any(param is not None for param in [chunk_size, chunk_overlap, split_by_paragraph, split_by_sentence]):
                    temp_splitter = document_splitter.__class__()  # 创建同类型的新实例
                    
                    # 复制原始分割器的默认配置
                    temp_splitter.chunk_size = document_splitter.chunk_size
                    temp_splitter.chunk_overlap = document_splitter.chunk_overlap
                    temp_splitter.split_by_paragraph = document_splitter.split_by_paragraph
                    temp_splitter.split_by_sentence = document_splitter.split_by_sentence
                    
                    # 应用自定义参数
                    if chunk_size is not None:
                        temp_splitter.chunk_size = chunk_size
                    if chunk_overlap is not None:
                        temp_splitter.chunk_overlap = chunk_overlap
                    if split_by_paragraph is not None:
                        temp_splitter.split_by_paragraph = split_by_paragraph
                    if split_by_sentence is not None:
                        temp_splitter.split_by_sentence = split_by_sentence
                    
                    logger.info(f"使用自定义分割参数: chunk_size={temp_splitter.chunk_size}, chunk_overlap={temp_splitter.chunk_overlap}, "
                                f"split_by_paragraph={temp_splitter.split_by_paragraph}, split_by_sentence={temp_splitter.split_by_sentence}")
                    
                    logger.debug("开始执行文档切割")
                    segments = temp_splitter.split_document(cleaned_document)
                    logger.debug(f"分割完成，第一个段落预览: {segments[0].page_content[:100] if segments else '无段落'}...")
                else:
                    # 使用默认分割器
                    logger.info("使用默认分割器参数")
                    segments = document_splitter.split_document(cleaned_document)
                    logger.debug(f"使用默认分割器，第一个段落预览: {segments[0].page_content[:100] if segments else '无段落'}...")
                
                logger.info(f"文档分割完成，生成了 {len(segments) if segments else 0} 个段落")
                if segments:
                    total_chars = sum(len(seg.page_content) for seg in segments)
                    avg_length = total_chars / len(segments)
                    logger.info(f"段落统计信息 - 总字符数: {total_chars}, 平均段落长度: {avg_length:.2f}")
                
                # 检查是否超过最大段落数限制
                max_segments = int(os.environ.get("MAX_SEGMENTS", "100000"))
                if segments and len(segments) > max_segments:
                    logger.warning(f"段落数量({len(segments)})超过限制({max_segments})，将截断处理")
                    segments = segments[:max_segments]
            except Exception as split_error:
                logger.error(f"文档分割失败: {str(split_error)}")
                # 更新状态为失败
                await mongodb.db[self.collection_name].update_one(
                    {"id": doc_id},
                    {"$set": {
                        "status": "failed", 
                        "error": f"文档分割失败: {str(split_error)}",
                        "processing_details": {
                            "end_time": datetime.now(timezone.utc)
                        }
                    }}
                )
                return {
                    "success": False,
                    "message": f"文档分割失败: {str(split_error)}"
                }
            
            if not segments:
                # 更新状态为失败
                await mongodb.db[self.collection_name].update_one(
                    {"id": doc_id},
                    {"$set": {
                        "status": "failed", 
                        "error": "文档分割后未产生有效内容，请检查文档",
                        "processing_details": {
                            "end_time": datetime.now(timezone.utc)
                        }
                    }}
                )
                
                return {
                    "success": False,
                    "message": "文档分割后未产生有效内容，请检查文档"
                }
            
            # 获取嵌入向量维度并确保集合存在
            try:
                logger.info("获取嵌入向量维度")
                dimension = embedding_model.get_dimension()
                logger.info(f"嵌入向量维度: {dimension}")
                
                logger.info(f"创建向量集合: {self.vector_collection_name}")
                retrieval_service.vector_store.create_collection(self.vector_collection_name, dimension)
                logger.info(f"向量集合创建或确认成功: {self.vector_collection_name}")
            except Exception as vector_error:
                logger.error(f"创建向量集合失败: {str(vector_error)}")
                # 更新状态为失败
                await mongodb.db[self.collection_name].update_one(
                    {"id": doc_id},
                    {"$set": {
                        "status": "failed", 
                        "error": f"创建向量集合失败: {str(vector_error)}",
                        "processing_details": {
                            "end_time": datetime.now(timezone.utc)
                        }
                    }}
                )
                return {
                    "success": False,
                    "message": f"创建向量集合失败: {str(vector_error)}"
                }
            
            # 改进：使用批量处理模式
            total_segments = len(segments)
            logger.info(f"文档分割完成，共有{total_segments}个段落需要处理")
            
            # 更新处理状态
            await mongodb.db[self.collection_name].update_one(
                {"id": doc_id},
                {"$set": {
                    "segments_count": total_segments,
                    "processing_details.segments_generated": True,
                    "processing_details.segments_count": total_segments
                }}
            )
            
            # 批量处理段落，添加超时检查
            processing_start_time = time.time()
            processed_batches = set()  # 用于跟踪已处理的批次
            
            for i in range(0, total_segments, self.batch_size):
                # 生成当前批次的唯一标识
                batch_id = f"{doc_id}_{i}"
                
                # 检查批次是否已处理，避免重复处理
                if batch_id in processed_batches:
                    logger.warning(f"批次 {i//self.batch_size + 1} (起始索引 {i}) 已处理，跳过")
                    continue
                
                # 检查是否超时
                current_time = time.time()
                elapsed = current_time - processing_start_time
                if elapsed > processing_timeout:
                    logger.warning(f"文档处理超时，已处理 {i} 个段落，耗时 {elapsed:.2f} 秒，超过限制 {processing_timeout} 秒")
                    
                    # 更新状态为部分完成
                    await mongodb.db[self.collection_name].update_one(
                        {"id": doc_id},
                        {"$set": {
                            "status": "partial_complete",
                            "warning": f"处理超时，只完成了 {i}/{total_segments} 个段落",
                            "processing_details": {
                                "end_time": datetime.now(timezone.utc),
                                "timeout": True,
                                "processed_segments": i,
                                "processed_batches": len(processed_batches)
                            }
                        }}
                    )
                    
                    return {
                        "success": True,
                        "warning": f"处理超时，只完成了 {i}/{total_segments} 个段落",
                        "message": "文档部分处理完成",
                        "document_id": doc_id,
                        "segments_count": i
                    }
                
                try:
                    # 计算当前批次的实际范围
                    end_idx = min(i + self.batch_size, total_segments)
                    batch_segments = segments[i:end_idx]
                    batch_size = len(batch_segments)
                    
                    logger.info(f"处理批次 {i//self.batch_size + 1}，包含 {batch_size} 个段落，批次ID: {batch_id}")
                    
                    # 收集所有段落内容
                    logger.info(f"收集段落内容，批次ID: {batch_id}")
                    segment_contents = [segment.page_content for segment in batch_segments]
                    
                    # 批量生成嵌入向量
                    logger.info(f"开始生成嵌入向量，批次大小: {batch_size}，批次ID: {batch_id}")
                    start_embed_time = time.time()
                    embeddings = embedding_model.embed_documents(segment_contents)
                    embed_time = time.time() - start_embed_time
                    logger.info(f"嵌入向量生成完成，耗时: {embed_time:.2f}秒，批次ID: {batch_id}")
                    
                    if len(embeddings) != batch_size:
                        logger.warning(f"嵌入向量数量({len(embeddings)})与段落数量({batch_size})不匹配，批次ID: {batch_id}")
                    
                    # 批量插入向量存储
                    logger.info(f"开始插入向量存储，批次大小: {batch_size}，批次ID: {batch_id}")
                    start_insert_time = time.time()
                    retrieval_service.vector_store.insert(batch_segments, embeddings)
                    insert_time = time.time() - start_insert_time
                    logger.info(f"向量存储插入完成，耗时: {insert_time:.2f}秒，批次ID: {batch_id}")
                    
                    # 标记批次为已处理
                    processed_batches.add(batch_id)
                    
                    # 更新处理进度
                    # 使用已处理的段落数量计算进度，而不是索引位置
                    processed_count = end_idx
                    progress = min(99, int(processed_count * 100 / total_segments))  # 最多显示99%，留1%给最终完成
                    
                    # 记录详细的处理信息 - 使用正确的MongoDB嵌套对象格式
                    processing_details = {
                        "processing_details": {
                            "progress": progress,
                            "processed_segments": processed_count,
                            "elapsed_time": time.time() - processing_start_time,
                            "last_batch_id": batch_id,
                            "processed_batches": len(processed_batches),
                            "last_updated": datetime.now(timezone.utc).isoformat()
                        }
                    }
                    
                    await mongodb.db[self.collection_name].update_one(
                        {"id": doc_id},
                        {"$set": processing_details}
                    )
                    
                    logger.info(f"批次 {i//self.batch_size + 1} 处理完成，进度: {progress}%，批次ID: {batch_id}")
                    
                except Exception as batch_error:
                    logger.error(f"处理批次 {i//self.batch_size + 1} 失败: {str(batch_error)}，批次ID: {batch_id}")
                    # 更新状态为失败
                    await mongodb.db[self.collection_name].update_one(
                        {"id": doc_id},
                        {"$set": {
                            "status": "failed", 
                            "error": f"处理批次 {i//self.batch_size + 1} 失败: {str(batch_error)}",
                            "processing_details": {
                                "end_time": datetime.now(timezone.utc),
                                "failed_batch_id": batch_id
                            }
                        }}
                    )
                    return {
                        "success": False,
                        "message": f"处理批次 {i//self.batch_size + 1} 失败: {str(batch_error)}"
                    }
            
            # 处理完成，更新文档信息
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 更新MongoDB文档状态为"ready"
            await mongodb.db[self.collection_name].update_one(
                {"id": doc_id},
                {"$set": {
                    "segments_count": total_segments,
                    "status": "ready",
                    "processing_time": processing_time,
                    "processing_details": {
                        "end_time": datetime.now(timezone.utc),
                        "progress": 100,
                        "processing_time": processing_time
                    }
                }}
            )
            
            return {
                "success": True,
                "doc_id": doc_id,
                "segments_count": len(segments),
                "processing_time": processing_time,
                "message": "文档处理和向量化成功"
            }
            
        except Exception as e:
            logger.error(f"处理文档失败: {str(e)}")
            
            # 如果文档ID已经生成，更新状态为失败
            if 'doc_id' in locals():
                try:
                    await mongodb.db[self.collection_name].update_one(
                        {"id": doc_id},
                        {"$set": {
                            "status": "failed", 
                            "error": str(e),
                            "processing_details": {
                                "end_time": datetime.now(timezone.utc)
                            }
                        }}
                    )
                except Exception as update_error:
                    logger.error(f"更新文档状态失败: {str(update_error)}")
            
            return {
                "success": False,
                "message": f"处理文档失败: {str(e)}"
            }

    async def process_document_hierarchical(
        self, 
        file_path: str, 
        file_name: str, 
        user_id: str,
        config: Optional[HierarchicalSplittingConfig] = None
    ) -> Dict[str, Any]:
        """
        使用层次化架构处理文档
        
        Args:
            file_path: 文件路径
            file_name: 文件名
            user_id: 用户ID
            config: 层次化分割配置
            
        Returns:
            处理结果
        """
        try:
            start_time = datetime.now()
            
            # 检查RAG服务是否可用
            if not self._check_rag_available():
                return {
                    "success": False,
                    "message": "RAG服务不可用，请确保Milvus和嵌入模型服务已启动"
                }
            
            # 使用提供的配置或默认配置
            processing_config = config or self.hierarchical_config
            
            # 生成文档ID
            doc_id = str(uuid.uuid4())
            dataset_id = user_id
            
            logger.info(f"开始层次化处理文档: {doc_id}, 文件: {file_name}")
            
            # 获取文件大小和限制配置
            file_size = os.path.getsize(file_path)
            max_file_size = int(os.environ.get("MAX_FILE_SIZE", "104857600"))  # 默认100MB
            
            if file_size > max_file_size:
                return {
                    "success": False,
                    "message": f"文件大小({file_size/1024/1024:.2f}MB)超过限制({max_file_size/1024/1024:.2f}MB)"
                }
            
            # 检查MongoDB连接
            if not await self._ensure_mongodb_connection():
                return {
                    "success": False,
                    "message": "数据库连接失败，无法处理文档"
                }
            
            # 记录文档基本信息
            doc_info = {
                "id": doc_id,
                "file_name": file_name,
                "user_id": user_id,
                "dataset_id": dataset_id,
                "created_at": datetime.now(timezone.utc),
                "status": "processing",
                "file_size": file_size,
                "processing_method": "hierarchical",
                "hierarchical_config": processing_config.dict()
            }
            
            db = await self._get_database()
            await db[self.collection_name].insert_one(doc_info)
            
            # 加载和预处理文档
            components = self._get_rag_components()
            pdf_processor = components['pdf_processor']
            document_processor = components['document_processor']
            
            # 根据文件类型处理文档
            if file_name.lower().endswith('.pdf'):
                document = pdf_processor.process_pdf(file_path, {
                    "doc_id": doc_id,
                    "document_id": doc_id,  # Required by validate_document
                    "file_name": file_name,
                    "created_by": user_id,
                    "dataset_id": dataset_id
                })
            else:
                # 处理文本文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                document = Document(
                    page_content=content,
                    doc_id=doc_id,  # Set the doc_id attribute directly
                    metadata={
                        "doc_id": doc_id,
                        "document_id": doc_id,  # Required by validate_document
                        "file_name": file_name,
                        "created_by": user_id,
                        "dataset_id": dataset_id
                    }
                )
            
            # 验证和清洗文档
            if not document_processor.validate_document(document):
                db = await self._get_database()
                await db[self.collection_name].update_one(
                    {"id": doc_id},
                    {"$set": {"status": "failed", "error": "文档验证失败"}}
                )
                return {
                    "success": False,
                    "message": "文档验证失败，请检查格式和内容"
                }
            
            cleaned_document = document_processor.clean_document(document)
            
            # 使用层次化处理器处理文档
            hierarchical_processor.config = processing_config
            hierarchy_result = await hierarchical_processor.process_document_with_hierarchy(
                cleaned_document, dataset_id, doc_id
            )
            
            if not hierarchy_result["success"]:
                db = await self._get_database()
                await db[self.collection_name].update_one(
                    {"id": doc_id},
                    {"$set": {"status": "failed", "error": hierarchy_result.get("error", "层次化处理失败")}}
                )
                return hierarchy_result
            
            # 获取子块用于向量索引
            logger.info(f"尝试获取文档层次结构，doc_id: {doc_id}")
            hierarchy_info = await hierarchical_processor.get_document_hierarchy(doc_id)
            if not hierarchy_info:
                logger.error(f"无法获取文档 {doc_id} 的层次结构")
                # 检查数据库中是否存在相关数据
                db = await self._get_database()
                segments_count = await db["document_segments"].count_documents({"document_id": doc_id})
                chunks_count = await db["child_chunks"].count_documents({"document_id": doc_id})
                logger.error(f"数据库检查 - 父段落数量: {segments_count}, 子块数量: {chunks_count}")

                await db[self.collection_name].update_one(
                    {"id": doc_id},
                    {"$set": {"status": "failed", "error": f"无法获取层次结构 - 父段落: {segments_count}, 子块: {chunks_count}"}}
                )
                return {
                    "success": False,
                    "message": f"无法获取层次结构 - 父段落: {segments_count}, 子块: {chunks_count}"
                }
            else:
                logger.info(f"成功获取层次结构: {hierarchy_info['total_segments']} 个父段落, {hierarchy_info['total_chunks']} 个子块")
            
            # 如果配置为仅索引子块，则只处理子块
            if processing_config.index_child_chunks_only:
                # 获取所有子块
                all_child_chunks = []
                for chunks in hierarchy_info["child_chunks_by_segment"].values():
                    for chunk_doc in chunks:
                        # 转换为HierarchicalChildChunk对象
                        from app.rag.models import HierarchicalChildChunk
                        chunk = HierarchicalChildChunk(**chunk_doc)
                        all_child_chunks.append(chunk)
                
                # 转换为Document对象用于向量索引
                index_documents = hierarchical_processor.get_child_chunks_for_vector_indexing(all_child_chunks)
                
                # 向量化和索引
                await self._index_documents_to_vector_store(index_documents, doc_id)
            
            # 更新文档状态
            processing_time = (datetime.now() - start_time).total_seconds()
            db = await self._get_database()
            await db[self.collection_name].update_one(
                {"id": doc_id},
                {"$set": {
                    "status": "ready",
                    "segments_count": hierarchy_result["parent_segments_count"],
                    "chunks_count": hierarchy_result["child_chunks_count"],
                    "processing_time": processing_time,
                    "processing_details": {
                        "end_time": datetime.now(timezone.utc),
                        "hierarchical_processing": True,
                        "config": processing_config.dict()
                    }
                }}
            )
            
            return {
                "success": True,
                "doc_id": doc_id,
                "parent_segments_count": hierarchy_result["parent_segments_count"],
                "child_chunks_count": hierarchy_result["child_chunks_count"],
                "processing_time": processing_time,
                "message": "层次化文档处理成功"
            }
            
        except Exception as e:
            logger.error(f"层次化处理文档失败: {str(e)}", exc_info=True)
            
            # 更新状态为失败
            if 'doc_id' in locals():
                try:
                    db = await self._get_database()
                    await db[self.collection_name].update_one(
                        {"id": doc_id},
                        {"$set": {"status": "failed", "error": str(e)}}
                    )
                except Exception as update_error:
                    logger.error(f"更新文档状态失败: {str(update_error)}")
            
            return {
                "success": False,
                "message": f"层次化处理文档失败: {str(e)}"
            }

    async def _index_documents_to_vector_store(
        self, 
        documents: List[Document], 
        doc_id: str
    ) -> None:
        """将文档索引到向量存储"""
        try:
            components = self._get_rag_components()
            retrieval_service = components['retrieval_service']
            embedding_model = components['embedding_model']
            
            # 确保向量集合存在
            dimension = embedding_model.get_dimension()
            retrieval_service.vector_store.create_collection(self.vector_collection_name, dimension)
            
            # 批量处理文档
            batch_size = self.batch_size
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i + batch_size]
                
                # 生成嵌入向量
                contents = [doc.page_content for doc in batch_docs]
                embeddings = embedding_model.embed_documents(contents)
                
                # 插入向量存储
                retrieval_service.vector_store.insert(batch_docs, embeddings)
                
                logger.info(f"已索引批次 {i//batch_size + 1}, 文档数: {len(batch_docs)}")
            
            logger.info(f"文档 {doc_id} 的向量索引完成，总计 {len(documents)} 个文档")
            
        except Exception as e:
            logger.error(f"向量索引失败: {str(e)}", exc_info=True)
            raise

    async def search_documents_hierarchical(
        self,
        query: str,
        user_id: str,
        top_k: int = 3,
        search_all: bool = False,
        score_threshold: float = 0.0,
        enable_parent_context: bool = True
    ) -> Dict[str, Any]:
        """
        使用层次化架构搜索文档
        
        Args:
            query: 查询文本
            user_id: 用户ID (作为数据集ID)
            top_k: 返回结果数量
            search_all: 是否搜索所有用户的文档
            score_threshold: 分数阈值
            enable_parent_context: 是否启用父段落上下文
            
        Returns:
            搜索结果
        """
        try:
            # 检查RAG服务是否可用
            if not self._check_rag_available():
                return {
                    "success": False,
                    "message": "RAG服务不可用，请确保Milvus和嵌入模型服务已启动",
                    "results": []
                }
            
            start_time = datetime.now()
            
            # 初始化层次化检索器
            components = self._get_rag_components()
            hierarchical_retriever.vector_store = components['retrieval_service'].vector_store
            hierarchical_retriever.embedding_model = components['embedding_model']
            
            # 执行层次化检索
            results = await hierarchical_retriever.retrieve_with_parent_context(
                query=query,
                dataset_id=None if search_all else user_id,
                top_k=top_k,
                score_threshold=score_threshold,
                enable_parent_context=enable_parent_context
            )
            
            search_time = (datetime.now() - start_time).total_seconds()
            
            # 转换为API友好格式
            formatted_results = []
            for result in results:
                child_chunk = result.get("child_chunk")
                parent_segment = result.get("parent_segment")
                
                formatted_result = {
                    "content": child_chunk.get("content", "") if child_chunk else "",
                    "score": result.get("combined_score", 0.0),
                    "metadata": {
                        "chunk_id": child_chunk.get("id") if child_chunk else None,
                        "chunk_position": child_chunk.get("position", 0) if child_chunk else 0,
                        "chunk_word_count": child_chunk.get("word_count", 0) if child_chunk else 0
                    }
                }
                
                # 添加父段落信息
                if parent_segment and enable_parent_context:
                    formatted_result["parent_context"] = {
                        "segment_id": parent_segment.get("id"),
                        "content": parent_segment.get("content", ""),
                        "position": parent_segment.get("position", 0),
                        "word_count": parent_segment.get("word_count", 0),
                        "child_count": parent_segment.get("child_count", 0)
                    }
                    
                    # 如果有多个相关子块，添加其他子块信息
                    if "child_chunks" in result:
                        child_chunks = result["child_chunks"]
                        if len(child_chunks) > 1:
                            formatted_result["related_chunks"] = [
                                {
                                    "id": chunk.get("id"),
                                    "content": chunk.get("content", "")[:100] + "...",  # 截取前100字符
                                    "position": chunk.get("position", 0),
                                    "score": chunk.get("score", 0.0)
                                }
                                for chunk in child_chunks[1:]  # 排除第一个（主要结果）
                            ]
                
                formatted_results.append(formatted_result)
            
            return {
                "success": True,
                "message": f"找到 {len(formatted_results)} 个相关结果",
                "results": formatted_results,
                "search_time": search_time,
                "query": query,
                "hierarchical_search": True,
                "enable_parent_context": enable_parent_context
            }
            
        except Exception as e:
            logger.error(f"层次化搜索失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"层次化搜索失败: {str(e)}",
                "results": []
            }
    
    async def search_documents(
        self,
        query: str,
        user_id: str,
        top_k: int = 3,
        search_all: bool = False,
        include_parent: bool = False,
        collection_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        搜索相关文档
        
        Args:
            query: 查询文本
            user_id: 用户ID (作为数据集ID)
            top_k: 返回结果数量
            search_all: 是否搜索所有用户的文档，默认为False（只搜索当前用户的文档）
            include_parent: 是否包含父文档
            
        Returns:
            搜索结果
        """
        try:
            # 检查RAG服务是否可用
            if not self._check_rag_available():
                return {
                    "success": False,
                    "message": "RAG服务不可用，请确保Milvus和嵌入模型服务已启动",
                    "results": []
                }
            
            start_time = datetime.now()

            # 获取RAG组件
            components = self._get_rag_components()
            retrieval_service = components['retrieval_service']
            embedding_model = components['embedding_model']

            # 确保向量存储集合已初始化
            try:
                if retrieval_service.vector_store.collection is None:
                    logger.info("搜索前发现向量存储集合未初始化，正在初始化...")
                    dimension = embedding_model.get_dimension()
                    retrieval_service.vector_store.create_collection(self.vector_collection_name, dimension)
                    logger.info(f"向量存储集合 {self.vector_collection_name} 初始化完成")
            except Exception as e:
                logger.error(f"初始化向量存储集合失败: {str(e)}")
                return {
                    "success": False,
                    "message": f"初始化向量存储失败: {str(e)}",
                    "results": []
                }
            
            # 使用检索服务搜索文档
            if include_parent:
                # 使用父子文档检索功能
                results_with_parent = retrieval_service.retrieve_with_parent(
                    query=query,
                    dataset_id=None if search_all else user_id,  # 如果search_all为True，则不限制dataset_id
                    top_k=top_k,
                    use_cache=True
                )
                
                # 记录搜索性能指标
                search_time = (datetime.now() - start_time).total_seconds()
                
                # 转换结果为API友好格式
                formatted_results = []
                for result in results_with_parent:
                    child_doc = result.get("child_document")
                    parent_doc = result.get("parent_document")
                    score = result.get("score", 0.0)
                    
                    formatted_result = {
                        "content": child_doc.page_content,
                        "metadata": {
                            "doc_id": child_doc.metadata.get("doc_id"),
                            "document_id": child_doc.metadata.get("document_id"),
                            "file_name": child_doc.metadata.get("file_name"),
                            "position": child_doc.metadata.get("position"),
                            "score": score
                        }
                    }
                    
                    # 如果有父文档，添加父文档信息
                    if parent_doc:
                        formatted_result["parent"] = {
                            "content": parent_doc.page_content,
                            "metadata": {
                                "doc_id": parent_doc.metadata.get("doc_id"),
                                "document_id": parent_doc.metadata.get("document_id"),
                                "file_name": parent_doc.metadata.get("file_name")
                            }
                        }
                    
                    formatted_results.append(formatted_result)
            else:
                # 使用标准检索功能
                results = retrieval_service.retrieve(
                    query=query,
                    dataset_id=None if search_all else user_id,  # 如果search_all为True，则不限制dataset_id
                    top_k=top_k,
                    use_cache=True
                )
                
                # 记录搜索性能指标
                search_time = (datetime.now() - start_time).total_seconds()
                
                # 转换结果为API友好格式
                formatted_results = []
                for doc in results:
                    formatted_results.append({
                        "content": doc.page_content,
                        "metadata": {
                            "doc_id": doc.metadata.get("doc_id"),
                            "document_id": doc.metadata.get("document_id"),
                            "file_name": doc.metadata.get("file_name"),
                            "position": doc.metadata.get("position"),
                            "score": doc.metadata.get("score")
                        }
                    })
                
            return {
                "success": True,
                "message": f"找到 {len(formatted_results)} 个相关结果",
                "results": formatted_results,
                "search_time": search_time,
                "query": query,
                "include_parent": include_parent
            }
            
        except Exception as e:
            logger.error(f"搜索文档失败: {str(e)}")
            return {
                "success": False,
                "message": f"搜索文档失败: {str(e)}",
                "results": []
            }
    
    async def get_user_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有文档"""
        try:
            # 使用索引查询，按创建时间降序排序
            cursor = mongodb.db[self.collection_name].find(
                {"user_id": user_id}
            ).sort("created_at", -1)  # -1 表示降序
            
            documents = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                
                # 确保所有必需字段都存在
                if "id" not in doc:
                    doc["id"] = str(doc["_id"])  # 使用_id作为备用
                
                if "file_name" not in doc:
                    doc["file_name"] = "未知文件"
                
                if "user_id" not in doc:
                    doc["user_id"] = user_id
                
                if "segments_count" not in doc:
                    doc["segments_count"] = 0
                
                if "created_at" not in doc:
                    doc["created_at"] = datetime.now(timezone.utc)
                elif isinstance(doc.get("created_at"), str):
                    doc["created_at"] = datetime.fromisoformat(doc["created_at"].replace('Z', '+00:00'))
                
                if "status" not in doc:
                    doc["status"] = "ready"  # 默认状态为ready
                
                documents.append(doc)
            return documents
        except Exception as e:
            logger.error(f"获取用户文档失败: {str(e)}")
            return []
    
    async def get_document_by_id(self, doc_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """获取文档详情"""
        try:
            # 构建查询条件
            query = {"id": doc_id}
            if user_id:
                query["user_id"] = user_id

            doc = await mongodb.db[self.collection_name].find_one(query)
            if doc:
                doc["_id"] = str(doc["_id"])
                if isinstance(doc.get("created_at"), datetime):
                    doc["created_at"] = doc["created_at"].isoformat()

                # 获取向量存储统计信息
                try:
                    vector_stats = retrieval_service.vector_store.get_stats()
                    doc["vector_stats"] = {
                        "total_vectors": vector_stats.get("row_count", 0),
                        "index_type": vector_stats.get("index_info", {}).get("index_type", "未知")
                    }
                except Exception as stats_error:
                    logger.warning(f"获取向量统计信息失败: {str(stats_error)}")

                return doc
            return None
        except Exception as e:
            logger.error(f"获取文档详情失败: {str(e)}")
            return None

    async def get_document_segments(self, doc_id: str) -> List[Document]:
        """获取文档的所有段落"""
        try:
            # 检查RAG服务是否可用
            if not self._check_rag_available():
                logger.warning("RAG服务不可用，无法获取文档段落")
                return []

            # 获取RAG组件
            components = self._get_rag_components()
            retrieval_service = components['retrieval_service']

            # 从向量存储中获取文档的所有段落
            segments = retrieval_service.vector_store.get_documents_by_doc_id(doc_id)

            # 按段落索引排序
            segments.sort(key=lambda x: x.metadata.get("index", 0))

            logger.info(f"获取文档 {doc_id} 的 {len(segments)} 个段落")
            return segments

        except Exception as e:
            logger.error(f"获取文档段落失败: {str(e)}")
            return []
    
    async def delete_document(self, doc_id: str, user_id: str, is_admin: bool = False) -> Dict[str, Any]:
        """
        删除文档
        
        Args:
            doc_id: 文档ID
            user_id: 用户ID
            is_admin: 是否为管理员，管理员可以删除任何文档
        
        Returns:
            操作结果
        """
        try:
            # 检查RAG服务是否可用
            if not self._check_rag_available():
                logger.error(f"删除文档失败: RAG服务不可用，用户ID: {user_id}, 文档ID: {doc_id}")
                return {
                    "success": False,
                    "message": "RAG服务不可用，请确保Milvus和嵌入模型服务已启动",
                    "error_code": "RAG_SERVICE_UNAVAILABLE"
                }
                
            # 查询文档
            query = {"id": doc_id}
            if not is_admin:
                # 非管理员需要验证文档所有权
                query["user_id"] = user_id
            
            doc = await mongodb.db[self.collection_name].find_one(query)
            
            if not doc:
                # 检查文档是否存在（不考虑所有权）
                doc_exists = await mongodb.db[self.collection_name].find_one({"id": doc_id})
                if doc_exists:
                    logger.warning(f"用户 {user_id} 尝试删除不属于自己的文档: {doc_id}")
                    return {
                        "success": False,
                        "message": "您没有权限删除此文档",
                        "error_code": "PERMISSION_DENIED"
                    }
                else:
                    logger.warning(f"尝试删除不存在的文档: {doc_id}, 用户ID: {user_id}")
                    return {
                        "success": False,
                        "message": "文档不存在",
                        "error_code": "DOCUMENT_NOT_FOUND"
                    }
            
            # 记录文档信息用于日志
            doc_owner = doc.get("user_id", "未知")
            doc_name = doc.get("file_name", "未知文件")
            
            # 从MongoDB删除文档记录
            delete_result = await mongodb.db[self.collection_name].delete_one({"id": doc_id})
            
            if not delete_result.deleted_count:
                logger.error(f"MongoDB删除文档失败: {doc_id}, 用户ID: {user_id}")
                return {
                    "success": False,
                    "message": "删除文档记录失败",
                    "error_code": "DB_DELETE_FAILED"
                }
            
            # 从向量存储中删除文档片段
            try:
                # 尝试直接使用文档ID删除所有相关段落
                logger.info(f"尝试使用document_id={doc_id}从向量存储中删除段落")
                filter_expr = f'metadata["document_id"] == "{doc_id}"'
                
                # 首先获取匹配的记录数量
                collection = retrieval_service.vector_store.collection
                if collection:
                    # 获取匹配记录的ID
                    expr_results = collection.query(
                        expr=filter_expr,
                        output_fields=["id"]
                    )
                    
                    segment_ids = [item["id"] for item in expr_results]
                    
                    if segment_ids:
                        logger.info(f"找到 {len(segment_ids)} 个关联段落，正在删除...")
                        retrieval_service.vector_store.delete(segment_ids)
                        logger.info(f"成功删除 {len(segment_ids)} 个段落")
                    else:
                        logger.warning(f"未找到与文档ID {doc_id} 关联的段落")
                else:
                    logger.warning("向量存储集合未初始化，无法删除段落")
            except Exception as vector_error:
                error_msg = str(vector_error)
                logger.error(f"从向量存储中删除段落时出错: {error_msg}, 文档ID: {doc_id}")
                # 继续执行，即使向量删除失败也返回成功（但记录警告）
                return {
                    "success": True,
                    "message": "文档已删除，但清理向量数据时出现问题",
                    "warning": f"清理向量数据时出错: {error_msg}",
                    "deleted_document": bool(delete_result.deleted_count),
                    "deleted_segments": 0,
                    "error_code": "VECTOR_DELETE_FAILED"
                }
            
            # 记录详细的操作日志
            operation_type = "管理员删除" if is_admin else "用户删除"
            logger.info(f"{operation_type}文档成功: ID={doc_id}, 名称={doc_name}, 所有者={doc_owner}, 操作者={user_id}, 删除段落数={len(segment_ids) if 'segment_ids' in locals() else 0}")
            
            return {
                "success": True,
                "message": "文档已成功删除",
                "deleted_segments": len(segment_ids) if 'segment_ids' in locals() else 0,
                "deleted_document": bool(delete_result.deleted_count),
                "document_name": doc_name
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"删除文档失败: {error_msg}, 文档ID: {doc_id}, 用户ID: {user_id}", exc_info=True)
            return {
                "success": False,
                "message": f"删除文档失败: {error_msg}",
                "error_code": "UNKNOWN_ERROR"
            }
    
    def _try_init_retrieval_service(self) -> bool:
        """尝试延迟初始化检索服务"""
        try:
            import app.rag as rag_module
            from app.db.connections.mongodb import mongodb_manager
            from app.rag.retrieval_service import RetrievalService
            from app.rag.constants import RETRIEVAL_CONFIG
            from app.db.document_store import DocumentStore
            
            # 检查MongoDB连接是否可用
            if mongodb_manager._async_db is not None:
                vector_store = rag_module.vector_store
                embedding_model = rag_module.embedding_model
                cache_service = rag_module.cache_service
                
                if vector_store is not None and embedding_model is not None:
                    document_store = DocumentStore(mongodb_manager._async_db)
                    
                    retrieval_service = RetrievalService(
                        vector_store=vector_store,
                        document_store=document_store,
                        embedding_model=embedding_model,
                        retrieval_config=RETRIEVAL_CONFIG,
                        cache_service=cache_service
                    )
                    
                    # 更新全局变量
                    rag_module.retrieval_service = retrieval_service
                    logger.info("延迟初始化检索服务成功")
                    return True
                else:
                    logger.error("向量存储或嵌入模型不可用，无法初始化检索服务")
                    return False
            else:
                logger.error("MongoDB连接不可用，无法初始化检索服务")
                return False
        except Exception as e:
            logger.error(f"延迟初始化检索服务失败: {str(e)}")
            return False

    def _check_rag_available(self) -> bool:
        """检查RAG服务是否可用"""
        # 动态获取RAG组件，确保获取最新的初始化状态
        components = self._get_rag_components()
        retrieval_service = components['retrieval_service']
        document_processor = components['document_processor']
        document_splitter = components['document_splitter']
        embedding_model = components['embedding_model']

        # 如果检索服务不可用，尝试延迟初始化
        if retrieval_service is None:
            logger.info("检索服务不可用，尝试延迟初始化...")
            if self._try_init_retrieval_service():
                # 重新获取组件状态
                components = self._get_rag_components()
                retrieval_service = components['retrieval_service']

        # 调试信息
        logger.info(f"RAG组件状态检查:")
        logger.info(f"- retrieval_service: {retrieval_service is not None}")
        logger.info(f"- document_processor: {document_processor is not None}")
        logger.info(f"- document_splitter: {document_splitter is not None}")
        logger.info(f"- embedding_model: {embedding_model is not None}")

        # 检查基本组件是否存在
        if not (retrieval_service is not None and
                document_processor is not None and
                document_splitter is not None and
                embedding_model is not None):
            logger.error("RAG基本组件不可用")
            return False

        # 检查嵌入模型API是否可用
        if not embedding_model.check_api_availability():
            logger.warning("嵌入模型API不可用，但允许继续使用默认配置")
            # 不直接返回False，而是继续检查其他组件

        # 检查向量存储是否可用
        try:
            # 获取向量维度（现在有默认值，不会失败）
            dimension = embedding_model.get_dimension()

            if retrieval_service is not None and retrieval_service.vector_store.collection is None:
                # 尝试初始化集合
                retrieval_service.vector_store.create_collection(self.vector_collection_name, dimension)
                logger.info(f"向量存储集合 {self.vector_collection_name} 初始化完成")

            # 测试向量存储连接（使用更轻量的测试）
            if retrieval_service is not None:
                try:
                    # 简单的连接测试，不进行实际搜索
                    retrieval_service.vector_store._check_connection()
                    logger.info("向量存储连接测试成功")
                except AttributeError:
                    # 如果没有_check_connection方法，使用搜索测试
                    test_vector = [0.0] * dimension
                    retrieval_service.vector_store.search_by_vector(test_vector, top_k=1)
                    logger.info("向量存储搜索测试成功")

            return True
        except Exception as e:
            logger.error(f"检查向量存储可用性失败: {str(e)}")
            return False

    async def save_processed_document(
        self,
        doc_id: str,
        file_name: str,
        user_id: str,
        segments: List[Document],
        dataset_id: Optional[str] = None,
        original_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        保存处理后的文档段落到向量存储

        Args:
            doc_id: 文档ID
            file_name: 文件名
            user_id: 用户ID
            segments: 文档段落列表
            dataset_id: 数据集ID
            original_content: 原始文档内容

        Returns:
            处理结果
        """
        try:
            # 检查RAG服务是否可用
            if not self._check_rag_available():
                return {
                    "success": False,
                    "message": "RAG服务不可用，请确保Milvus和嵌入模型服务已启动"
                }

            # 检查MongoDB连接
            if not await self._ensure_mongodb_connection():
                return {
                    "success": False,
                    "message": "数据库连接失败，无法保存文档"
                }

            # 获取RAG组件
            components = self._get_rag_components()
            retrieval_service = components['retrieval_service']
            embedding_model = components['embedding_model']

            # 从segments中重建原始内容（如果没有提供original_content）
            if original_content is None and segments:
                # 尝试从segments的metadata中获取原始内容
                # 或者合并所有parent segments的内容
                parent_segments = [seg for seg in segments if seg.metadata.get("type") == "parent"]
                if parent_segments:
                    original_content = "\n\n".join([seg.page_content for seg in parent_segments])
                else:
                    # 如果没有parent segments，使用所有segments
                    original_content = "\n\n".join([seg.page_content for seg in segments])

            # 保存文档信息到MongoDB
            doc_info = {
                "id": doc_id,
                "file_name": file_name,
                "filename": file_name,  # 添加filename字段以保持兼容性
                "user_id": user_id,
                "dataset_id": dataset_id or user_id,  # 如果没有指定dataset_id，使用user_id
                "content": original_content or "",  # 添加原始文档内容
                "metadata": {
                    "segments_count": len(segments),
                    "content_length": len(original_content) if original_content else 0,
                    "processing_method": "rag_service"
                },
                "segments_count": len(segments),
                "status": "processing",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }

            logger.info(f"准备保存文档到MongoDB: doc_id={doc_id}, collection={self.collection_name}")

            # 先删除可能存在的旧文档
            await mongodb.db[self.collection_name].delete_one({"id": doc_id})
            logger.info(f"已删除可能存在的旧文档: {doc_id}")

            # 插入新文档
            insert_result = await mongodb.db[self.collection_name].insert_one(doc_info)
            logger.info(f"文档插入成功: doc_id={doc_id}, mongodb_id={insert_result.inserted_id}")
            
            # 获取嵌入向量维度并确保集合存在
            try:
                logger.info("获取嵌入向量维度")
                dimension = embedding_model.get_dimension()
                logger.info(f"嵌入向量维度: {dimension}")
                
                logger.info(f"创建向量集合: {self.vector_collection_name}")
                retrieval_service.vector_store.create_collection(self.vector_collection_name, dimension)
                logger.info(f"向量集合创建或确认成功: {self.vector_collection_name}")
            except Exception as vector_error:
                logger.error(f"创建向量集合失败: {str(vector_error)}")
                # 更新状态为失败
                await mongodb.db[self.collection_name].update_one(
                    {"id": doc_id},
                    {"$set": {
                        "status": "failed", 
                        "error": f"创建向量集合失败: {str(vector_error)}",
                        "processing_details": {
                            "end_time": datetime.now(timezone.utc)
                        }
                    }}
                )
                return {
                    "success": False,
                    "message": f"创建向量集合失败: {str(vector_error)}"
                }
            
            # 批量处理所有段落
            batch_result = await retrieval_service.process_and_index_documents_batch(
                documents=segments,
                collection_name=self.vector_collection_name
            )
            
            if not batch_result["success"]:
                # 更新状态为失败
                await mongodb.db[self.collection_name].update_one(
                    {"id": doc_id},
                    {"$set": {
                        "status": "failed", 
                        "error": batch_result.get("message", "向量存储处理失败"),
                        "processing_details": {
                            "end_time": datetime.now(timezone.utc)
                        }
                    }}
                )
                return batch_result
            
            # 更新文档状态为ready
            await mongodb.db[self.collection_name].update_one(
                {"id": doc_id},
                {"$set": {
                    "status": "ready",
                    "processing_details": {
                        "end_time": datetime.now(timezone.utc),
                        "segments_processed": len(segments),
                        "processing_time": batch_result.get("processing_time", 0)
                    }
                }}
            )
            
            return {
                "success": True,
                "message": "文档处理和索引成功",
                "doc_id": doc_id,
                "segments_count": len(segments),
                "processing_time": batch_result.get("processing_time", 0)
            }
            
        except Exception as e:
            logger.error(f"保存处理文档失败: {str(e)}")
            
            # 更新状态为失败
            try:
                await mongodb.db[self.collection_name].update_one(
                    {"id": doc_id},
                    {"$set": {
                        "status": "failed", 
                        "error": str(e),
                        "processing_details": {
                            "end_time": datetime.now(timezone.utc)
                        }
                    }}
                )
            except Exception as update_error:
                logger.error(f"更新文档状态失败: {str(update_error)}")
            
            return {
                "success": False,
                "message": f"保存处理文档失败: {str(e)}"
            }

# 创建全局RAG服务实例
rag_service = RAGService() 