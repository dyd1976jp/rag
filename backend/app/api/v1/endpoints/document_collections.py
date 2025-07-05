from typing import List, Optional, Dict, Any
import logging
import time
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from pydantic import BaseModel

from ....rag.models import Document
from ....rag.parent_child_processor import ParentChildIndexProcessor, ProcessingRule, Segmentation
from ....rag.document_splitter import ParentChildDocumentSplitter, Rule, SplitMode
from ....rag.document_processor import DocumentProcessor
from ....services.document_collection_service import DocumentCollectionService
from ....models.document_collection import (
    DocumentCollection,
    DocumentCollectionCreate,
    DocumentCollectionUpdate,
    DocumentCollectionResponse,
    DocumentCollectionListResponse
)
from ....api.deps import get_current_user
from ....models.user import User

router = APIRouter()

class CollectionResponse(BaseModel):
    """统一的文档集响应格式"""
    success: bool
    message: str
    data: Optional[dict] = None

class DocumentSegmentPreviewResponse(BaseModel):
    """文档段落预览响应 - 用于查看特定段落的父子关系"""
    success: bool
    message: str
    segment_info: Dict[str, Any]  # 段落基本信息
    parent_content: str           # 父段落内容
    children_content: List[str]   # 子段落内容列表
    metadata: Optional[Dict[str, Any]] = None  # 额外的元数据信息

class SplitterParamsResponse(BaseModel):
    """切割参数响应"""
    chunk_size: int 
    chunk_overlap: int
    min_chunk_size: int = 50
    split_by_paragraph: bool = True
    paragraph_separator: str = "\\n\\n"
    split_by_sentence: bool = True

class CompleteDocumentPreviewResponse(BaseModel):
    """完整文档预览响应 - 显示所有父子块的层级结构"""
    success: bool
    message: str
    preview_mode: bool
    doc_id: str
    total_segments: int
    parent_segments: int
    child_segments: int
    segments: List[Dict[str, Any]]  # 父子层级结构的段落数组

@router.get("/", response_model=CollectionResponse)
async def get_collections(
    current_user: User = Depends(get_current_user),
    collection_service: DocumentCollectionService = Depends()
) -> CollectionResponse:
    """获取用户的所有文档集"""
    try:
        collections = await collection_service.get_user_collections(str(current_user.id))
        return CollectionResponse(
            success=True,
            message="获取文档集列表成功",
            data={"collections": [c.dict() for c in collections]}
        )
    except Exception as e:
        logger.error(f"获取文档集列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=CollectionResponse)
async def create_collection(
    data: DocumentCollectionCreate,
    current_user: User = Depends(get_current_user),
    collection_service: DocumentCollectionService = Depends()
) -> CollectionResponse:
    """创建文档集"""
    try:
        result = await collection_service.create_collection(str(current_user.id), data)
        if result:
            return CollectionResponse(
                success=True,
                message="文档集创建成功",
                data=result.dict()
            )
        else:
            return CollectionResponse(
                success=False,
                message="文档集创建失败",
                data=None
            )
    except Exception as e:
        logger.error(f"创建文档集失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}/preview/{segment_id}", response_model=DocumentSegmentPreviewResponse)
async def get_document_segment_preview(
    document_id: str,
    segment_id: int,
    current_user: User = Depends(get_current_user),
    collection_service: DocumentCollectionService = Depends()
) -> DocumentSegmentPreviewResponse:
    """获取文档切片预览"""
    try:
        logger.info(f"开始处理文档预览请求 - document_id: {document_id}, segment_id: {segment_id}")

        # 检查是否为预览模式的文档ID
        if document_id.startswith("preview_"):
            logger.info(f"处理预览模式文档: {document_id}")

            # 从预览缓存获取数据
            from app.services.preview_cache_service import preview_cache_service
            preview_data = preview_cache_service.get_preview_data(document_id)

            if not preview_data:
                logger.error(f"预览文档不存在或已过期: {document_id}")
                raise HTTPException(status_code=404, detail="Preview document not found or expired")

            # 获取预览缓存中的段落数据
            segments = preview_data.get("segments", [])

            # 分离父块和子块
            parent_segments = [seg for seg in segments if seg.get("type") == "parent"]
            child_segments = [seg for seg in segments if seg.get("type") == "child"]

            logger.info(f"预览缓存数据统计: 总段落={len(segments)}, 父块={len(parent_segments)}, 子块={len(child_segments)}")

            # segment_id 应该对应父块的索引
            if not parent_segments or segment_id >= len(parent_segments):
                logger.warning(f"未找到指定的父块 - segment_id: {segment_id}, 父块总数: {len(parent_segments)}")
                raise HTTPException(status_code=404, detail="Parent segment not found")

            # 获取指定的父块
            target_parent = parent_segments[segment_id]
            parent_content = target_parent.get("page_content", "")
            parent_id = target_parent.get("metadata", {}).get("id", str(segment_id))

            logger.info(f"目标父块: segment_id={segment_id}, parent_id={parent_id}, 内容长度={len(parent_content)}")

            # 构建子文档内容列表
            children_content = []
            if parent_id:
                for segment in child_segments:
                    if segment.get("metadata", {}).get("parent_id") == parent_id:
                        children_content.append(segment.get("page_content", ""))

            logger.info(f"找到 {len(children_content)} 个子块")

            logger.info(f"成功从预览缓存获取段落: segment_id={segment_id}, 父块内容长度={len(parent_content)}, 子块数量={len(children_content)}")

        else:
            # 从数据库获取文档
            document_dict = await collection_service.get_document(document_id)
            if not document_dict:
                logger.warning(f"文档未找到 - document_id: {document_id}")
                raise HTTPException(status_code=404, detail="Document not found")

            # 从字典构建Document对象
            document = Document(
                page_content=document_dict.get("content", ""),
                metadata=document_dict.get("metadata", {})
            )
            logger.info(f"成功从数据库获取文档: {document_id}")

            # 使用与预览相同的切割器和参数
            # 使用默认参数（与预览模式保持一致）
            parent_chunk_size = 512
            parent_chunk_overlap = 50
            parent_separator = "\n\n"
            child_chunk_size = 256
            child_chunk_overlap = 25
            child_separator = "\n"

            # 清洗文档内容
            document_processor = DocumentProcessor()
            cleaned_document = document_processor.clean_document(document)

            # 创建分割器和规则（与预览模式相同）
            splitter = ParentChildDocumentSplitter()
            rule = Rule(
                mode=SplitMode.PARENT_CHILD,
                max_tokens=parent_chunk_size,
                chunk_overlap=parent_chunk_overlap,
                fixed_separator=parent_separator,
                subchunk_max_tokens=child_chunk_size,
                subchunk_overlap=child_chunk_overlap,
                subchunk_separator=child_separator,
                clean_text=True,
                keep_separator=True
            )

            logger.info("初始化分割器和规则完成")

            # 执行分割
            logger.info("开始分割文档...")
            processed_docs = splitter.split_documents([cleaned_document], rule)
            logger.info(f"文档分割完成，生成了 {len(processed_docs)} 个段落")

            # 分离父块和子块（与预览模式相同的逻辑）
            parent_segments = []
            child_segments = {}

            for segment in processed_docs:
                segment_type = segment.metadata.get("type", "unknown")
                parent_id = segment.metadata.get("parent_id")

                if segment_type == "parent":
                    parent_segments.append(segment)
                elif segment_type == "child" and parent_id:
                    if parent_id not in child_segments:
                        child_segments[parent_id] = []
                    child_segments[parent_id].append(segment)

            logger.info(f"分离结果: 父块={len(parent_segments)}, 子块组={len(child_segments)}")

            # 检查segment_id是否有效
            if not parent_segments or segment_id >= len(parent_segments):
                logger.warning(f"未找到指定的父块 - segment_id: {segment_id}, 父块总数: {len(parent_segments)}")
                raise HTTPException(status_code=404, detail="Parent segment not found")

            # 获取指定的父块
            parent_segment = parent_segments[segment_id]
            parent_content = parent_segment.page_content

            # 获取对应的子块
            parent_id = parent_segment.metadata.get("id", str(segment_id))
            children_content = []
            if parent_id in child_segments:
                children_content = [child.page_content for child in child_segments[parent_id]]

            logger.info(f"成功获取父块和 {len(children_content)} 个子块")

        return DocumentSegmentPreviewResponse(
            success=True,
            message="文档段落预览获取成功",
            segment_info={
                "segment_id": segment_id,
                "parent_id": parent_id,
                "segment_type": "parent",
                "children_count": len(children_content)
            },
            parent_content=parent_content,
            children_content=children_content,
            metadata={
                "document_id": document_id,
                "is_preview_mode": document_id.startswith("preview_"),
                "processing_timestamp": time.time()
            }
        )

    except HTTPException:
        # 重新抛出HTTP异常，保持原有的状态码
        raise
    except Exception as e:
        logger.error(f"文档预览处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}/splitter-params", response_model=SplitterParamsResponse)
async def get_document_splitter_params(
    document_id: str,
    collection_service: DocumentCollectionService = Depends()
) -> SplitterParamsResponse:
    """获取文档切割参数"""
    try:
        # 检查是否为预览模式的文档ID
        if document_id.startswith("preview_"):
            logger.info(f"处理预览模式文档的切割参数请求: {document_id}")

            # 从预览缓存获取数据和切割参数
            from app.services.preview_cache_service import preview_cache_service
            preview_data = preview_cache_service.get_preview_data(document_id)

            if not preview_data:
                logger.error(f"预览文档不存在或已过期: {document_id}")
                raise HTTPException(status_code=404, detail="Preview document not found or expired")

            # 从缓存中获取实际使用的切割参数
            split_params = preview_data.get("split_params", {})
            logger.info(f"从缓存获取到切割参数: {split_params}")

            return SplitterParamsResponse(
                chunk_size=split_params.get("parent_chunk_size", 512),
                chunk_overlap=split_params.get("parent_chunk_overlap", 50),
                min_chunk_size=50,
                split_by_paragraph=True,
                paragraph_separator=split_params.get("parent_separator", "\\n\\n"),
                split_by_sentence=True
            )

        # 处理正常的文档ID
        document = await collection_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # 返回默认参数
        # 注意：这里可以根据实际需求从数据库或配置中获取参数
        return SplitterParamsResponse(
            chunk_size=512,
            chunk_overlap=50,
            min_chunk_size=50,
            split_by_paragraph=True,
            paragraph_separator="\\n\\n",
            split_by_sentence=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档切割参数失败: {document_id}, 错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: str,
    data: DocumentCollectionUpdate,
    current_user: User = Depends(get_current_user),
    collection_service: DocumentCollectionService = Depends()
) -> CollectionResponse:
    """更新文档集"""
    try:
        result = await collection_service.update_collection(collection_id, str(current_user.id), data)
        if result:
            return CollectionResponse(
                success=True,
                message="文档集更新成功",
                data=result.dict()
            )
        return CollectionResponse(
            success=False,
            message="文档集更新失败",
            data=None
        )
    except Exception as e:
        logger.error(f"更新文档集失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{collection_id}", response_model=CollectionResponse)
async def delete_collection(
    collection_id: str,
    current_user: User = Depends(get_current_user),
    collection_service: DocumentCollectionService = Depends()
) -> CollectionResponse:
    """删除文档集"""
    try:
        result = await collection_service.delete_collection(collection_id, str(current_user.id))
        if result:
            return CollectionResponse(
                success=True,
                message="文档集删除成功"
            )
        return CollectionResponse(
            success=False,
            message="文档集删除失败"
        )
    except Exception as e:
        logger.error(f"删除文档集失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection_detail(
    collection_id: str,
    current_user: User = Depends(get_current_user),
    collection_service: DocumentCollectionService = Depends()
) -> CollectionResponse:
    """获取文档集详情"""
    try:
        collection = await collection_service.get_collection_by_id(collection_id, str(current_user.id))
        if collection:
            return CollectionResponse(
                success=True,
                message="获取文档集详情成功",
                data=collection.dict()
            )
        return CollectionResponse(
            success=False,
            message="文档集不存在",
            data=None
        )
    except Exception as e:
        logger.error(f"获取文档集详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{collection_id}/documents/{document_id}", response_model=CollectionResponse)
async def add_document_to_collection(
    collection_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    collection_service: DocumentCollectionService = Depends()
) -> CollectionResponse:
    """将文档添加到文档集"""
    try:
        result = await collection_service.add_document_to_collection(collection_id, document_id, str(current_user.id))
        if result:
            return CollectionResponse(
                success=True,
                message="文档添加成功"
            )
        return CollectionResponse(
            success=False,
            message="文档添加失败"
        )
    except Exception as e:
        logger.error(f"添加文档到文档集失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{collection_id}/documents/{document_id}", response_model=CollectionResponse)
async def remove_document_from_collection(
    collection_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    collection_service: DocumentCollectionService = Depends()
) -> CollectionResponse:
    """从文档集中移除文档"""
    try:
        result = await collection_service.remove_document_from_collection(collection_id, document_id, str(current_user.id))
        if result:
            return CollectionResponse(
                success=True,
                message="文档移除成功"
            )
        return CollectionResponse(
            success=False,
            message="文档移除失败"
        )
    except Exception as e:
        logger.error(f"从文档集中移除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}/complete-preview", response_model=CompleteDocumentPreviewResponse)
async def get_complete_document_preview(
    document_id: str,
    current_user: User = Depends(get_current_user),
    collection_service: DocumentCollectionService = Depends()
) -> CompleteDocumentPreviewResponse:
    """获取完整文档预览 - 显示所有父子块的层级结构"""
    try:
        logger.info(f"开始处理完整文档预览请求 - document_id: {document_id}")

        # 检查是否为预览模式的文档ID
        if document_id.startswith("preview_"):
            logger.info(f"处理预览模式文档: {document_id}")

            # 从预览缓存获取数据
            from app.services.preview_cache_service import preview_cache_service
            preview_data = preview_cache_service.get_preview_data(document_id)

            if not preview_data:
                logger.error(f"预览文档不存在或已过期: {document_id}")
                raise HTTPException(status_code=404, detail="Preview document not found or expired")

            # 获取预览缓存中的段落数据
            segments = preview_data.get("segments", [])
            
            # 分离父块和子块
            parent_segments = [seg for seg in segments if seg.get("type") == "parent"]
            child_segments = [seg for seg in segments if seg.get("type") == "child"]

            logger.info(f"预览缓存数据统计: 总段落={len(segments)}, 父块={len(parent_segments)}, 子块={len(child_segments)}")

            # 构建层级结构
            hierarchical_segments = []
            child_segments_by_parent = {}
            
            # 按父块ID分组子块
            for child in child_segments:
                parent_id = child.get("metadata", {}).get("parent_id")
                if parent_id:
                    if parent_id not in child_segments_by_parent:
                        child_segments_by_parent[parent_id] = []
                    child_segments_by_parent[parent_id].append(child)

            # 构建层级结构
            for parent in parent_segments:
                parent_id = parent.get("metadata", {}).get("id", str(len(hierarchical_segments)))
                
                parent_segment = {
                    "type": "parent",
                    "id": parent_id,
                    "content": parent.get("page_content", ""),
                    "metadata": parent.get("metadata", {}),
                    "children": []
                }
                
                # 添加子块
                if parent_id in child_segments_by_parent:
                    for child in child_segments_by_parent[parent_id]:
                        child_segment = {
                            "type": "child",
                            "id": child.get("metadata", {}).get("id", ""),
                            "content": child.get("page_content", ""),
                            "metadata": child.get("metadata", {}),
                            "parent_id": parent_id
                        }
                        parent_segment["children"].append(child_segment)
                
                hierarchical_segments.append(parent_segment)

            logger.info(f"构建层级结构完成: {len(hierarchical_segments)} 个父块")

        else:
            # 从数据库获取文档
            document_dict = await collection_service.get_document(document_id)
            if not document_dict:
                logger.warning(f"文档未找到 - document_id: {document_id}")
                raise HTTPException(status_code=404, detail="Document not found")

            # 从字典构建Document对象
            document = Document(
                page_content=document_dict.get("content", ""),
                metadata=document_dict.get("metadata", {})
            )
            logger.info(f"成功从数据库获取文档: {document_id}")

            # 使用与预览相同的切割器和参数
            parent_chunk_size = 512
            parent_chunk_overlap = 50
            parent_separator = "\\n\\n"
            child_chunk_size = 256
            child_chunk_overlap = 25
            child_separator = "\\n"

            # 清洗文档内容
            document_processor = DocumentProcessor()
            cleaned_document = document_processor.clean_document(document)

            # 创建分割器和规则
            splitter = ParentChildDocumentSplitter()
            rule = Rule(
                mode=SplitMode.PARENT_CHILD,
                max_tokens=parent_chunk_size,
                chunk_overlap=parent_chunk_overlap,
                fixed_separator=parent_separator,
                subchunk_max_tokens=child_chunk_size,
                subchunk_overlap=child_chunk_overlap,
                subchunk_separator=child_separator,
                clean_text=True,
                keep_separator=True
            )

            logger.info("开始分割文档...")
            processed_docs = splitter.split_documents([cleaned_document], rule)
            logger.info(f"文档分割完成，生成了 {len(processed_docs)} 个段落")

            # 构建层级结构
            parent_segments = []
            child_segments_by_parent = {}

            for segment in processed_docs:
                segment_type = segment.metadata.get("type", "unknown")
                parent_id = segment.metadata.get("parent_id")

                if segment_type == "parent":
                    parent_segments.append(segment)
                elif segment_type == "child" and parent_id:
                    if parent_id not in child_segments_by_parent:
                        child_segments_by_parent[parent_id] = []
                    child_segments_by_parent[parent_id].append(segment)

            hierarchical_segments = []
            for parent in parent_segments:
                parent_id = parent.metadata.get("id", str(len(hierarchical_segments)))
                
                parent_segment = {
                    "type": "parent",
                    "id": parent_id,
                    "content": parent.page_content,
                    "metadata": parent.metadata,
                    "children": []
                }
                
                # 添加子块
                if parent_id in child_segments_by_parent:
                    for child in child_segments_by_parent[parent_id]:
                        child_segment = {
                            "type": "child",
                            "id": child.metadata.get("id", ""),
                            "content": child.page_content,
                            "metadata": child.metadata,
                            "parent_id": parent_id
                        }
                        parent_segment["children"].append(child_segment)
                
                hierarchical_segments.append(parent_segment)

            logger.info(f"构建层级结构完成: {len(hierarchical_segments)} 个父块")

        # 计算统计信息
        total_segments = len(hierarchical_segments)
        parent_segments_count = len(hierarchical_segments)
        child_segments_count = sum(len(parent["children"]) for parent in hierarchical_segments)

        return CompleteDocumentPreviewResponse(
            success=True,
            message="获取完整文档预览成功",
            preview_mode=document_id.startswith("preview_"),
            doc_id=document_id,
            total_segments=total_segments + child_segments_count,
            parent_segments=parent_segments_count,
            child_segments=child_segments_count,
            segments=hierarchical_segments
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取完整文档预览失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{collection_id}/documents", response_model=CollectionResponse)
async def get_collection_documents(
    collection_id: str,
    current_user: User = Depends(get_current_user),
    collection_service: DocumentCollectionService = Depends()
) -> CollectionResponse:
    """获取文档集中的所有文档"""
    try:
        documents = await collection_service.get_collection_documents(collection_id, str(current_user.id))
        return CollectionResponse(
            success=True,
            message="获取文档列表成功",
            data={"documents": documents}
        )
    except Exception as e:
        logger.error(f"获取文档集文档列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# @router.get("/{document_id}/chunks", response_model=CollectionResponse)
# async def get_document_chunks(
#     document_id: str,
#     current_user: User = Depends(get_current_user),
#     collection_service: DocumentCollectionService = Depends()
# ):
#     """获取单个文档的所有分块信息"""
#     try:
#         # 假设 collection_service 有一个方法可以获取文档的所有分块
#         # 这个方法需要去向量数据库中查询
#         chunks = await collection_service.get_document_chunks(document_id, str(current_user.id))
        
#         if chunks is None:
#             raise HTTPException(status_code=404, detail="Document or chunks not found")

#  结构
#         return CollectionResponse(
#             success=True,
#             message="获取文档分块成功",
#             data={"segments": chunks}
#         )
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"获取文档分块失败: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))