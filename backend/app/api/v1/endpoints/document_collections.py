from typing import List, Optional
import logging
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from pydantic import BaseModel

from ....rag.models import Document
from ....rag.parent_child_processor import ParentChildIndexProcessor, ProcessingRule, Segmentation
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

class DocumentPreviewResponse(BaseModel):
    """文档预览响应"""
    parentContent: str
    childrenContent: List[str]

class SplitterParamsResponse(BaseModel):
    """切割参数响应"""
    chunk_size: int 
    chunk_overlap: int
    min_chunk_size: int = 50
    split_by_paragraph: bool = True
    paragraph_separator: str = "\\n\\n"
    split_by_sentence: bool = True

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

@router.get("/{document_id}/preview/{segment_id}", response_model=DocumentPreviewResponse)
async def get_document_preview(
    document_id: str,
    segment_id: int,
    collection_service: DocumentCollectionService = Depends()
) -> DocumentPreviewResponse:
    """获取文档切片预览"""
    try:
        logger.info(f"开始处理文档预览请求 - document_id: {document_id}, segment_id: {segment_id}")

        # 获取文档
        document = await collection_service.get_document(document_id)
        if not document:
            logger.warning(f"文档未找到 - document_id: {document_id}")
            raise HTTPException(status_code=404, detail="Document not found")
            
        logger.info(f"成功获取文档 - document_id: {document_id}")
            
        # 初始化处理器
        processor = ParentChildIndexProcessor()
        
        # 设置处理规则
        rule = ProcessingRule(
            segmentation=Segmentation(
                max_tokens=512,  # 父文档块大小
                chunk_overlap=50,
                separator="\n\n"
            ),
            subchunk_segmentation=Segmentation(
                max_tokens=256,  # 子文档块大小
                chunk_overlap=25,
                separator="\n"
            )
        )
        logger.info("初始化处理器和规则完成")
        
        # 处理文档
        logger.info("开始处理文档...")
        processed_docs = processor.transform([Document(**document.dict())], rule=rule)
        logger.info(f"文档处理完成，生成了 {len(processed_docs)} 个文档片段")
        
        if not processed_docs or segment_id >= len(processed_docs):
            logger.warning(f"未找到指定的文档片段 - segment_id: {segment_id}")
            raise HTTPException(status_code=404, detail="Segment not found")
            
        # 获取父文档和子文档
        parent_doc = processed_docs[segment_id]
        child_docs = [
            doc for doc in processed_docs
            if doc.metadata.get("parent_id") == parent_doc.metadata.get("doc_id")
        ]
        
        logger.info(f"成功获取父文档和 {len(child_docs)} 个子文档")
        
        return DocumentPreviewResponse(
            parentContent=parent_doc.page_content,
            childrenContent=[doc.page_content for doc in child_docs]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}/splitter-params", response_model=SplitterParamsResponse)
async def get_document_splitter_params(
    document_id: str,
    collection_service: DocumentCollectionService = Depends()
) -> SplitterParamsResponse:
    """获取文档切割参数"""
    try:
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
        
    except Exception as e:
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