"""
RAG API端点模块

本模块提供RAG相关的API端点，包括：
1. 文档上传和处理
2. 文档分割预览
3. 文档搜索和检索
4. RAG聊天功能

注意：本文件较长，建议考虑拆分为多个子模块。
"""

import os
import logging
import shutil
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form, Path, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.api.v1.utils import (
    SUPPORTED_EXTENSIONS,
    validate_file_type,
    save_uploaded_file,
    process_document_by_type,
    create_split_rule,
    format_preview_response,
    cleanup_temp_file,
    log_document_info,
    log_split_statistics
)
from app.schemas.rag import (
    DocumentUploadResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentListResponse,
    DeleteDocumentResponse,
    RAGChatRequest,
    RAGChatResponse,
    RAGStatusResponse,
    DocumentResponse,
    DocumentSlicePreviewRequest,
    DocumentSlicePreviewResponse
)
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.models.user import User
import app.rag as rag
from app.rag.models import Document
from app.rag.extractor.extract_processor import ExtractProcessor, ExtractMode
from app.rag.document_splitter import ParentChildDocumentSplitter, Rule, SplitMode

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()
llm_service = LLMService()
rag_service = RAGService()

# 定义文档切割预览请求模型（用于纯文本内容预览）
class DocumentSplitRequest(BaseModel):
    content: str = Field(..., description="要分割的文本内容", min_length=1)
    parent_chunk_size: int = Field(1024, description="父块分段最大长度", gt=0)
    parent_chunk_overlap: int = Field(200, description="父块重叠长度", ge=0)
    parent_separator: str = Field("\n\n", description="父块分段标识符")
    child_chunk_size: int = Field(512, description="子块分段最大长度", gt=0)
    child_chunk_overlap: int = Field(50, description="子块重叠长度", ge=0)
    child_separator: str = Field("\n", description="子块分段标识符")

# 定义文档切割预览响应模型
class DocumentSplitPreviewResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    segments: Optional[List[Dict[str, Any]]] = None
    total_segments: Optional[int] = None
    parentContent: Optional[str] = None
    childrenContent: Optional[List[str]] = None

@router.post("/documents/preview-split", response_model=DocumentSplitPreviewResponse)
async def preview_document_split(
    request: DocumentSplitRequest,
    current_user: User = Depends(get_current_user)
):
    """
    预览纯文本内容的分割结果

    此端点仅用于预览纯文本内容的分割效果。

    **重要提示：**
    - 如果需要上传文件并预览分割结果，请使用 `POST /documents/upload` 端点，并设置 `preview_only=true`
    - 此端点只接受JSON格式的请求体，不支持文件上传
    - 适用于已有文本内容的分割预览场景

    Args:
        request: 包含文本内容和分割参数的请求体
        current_user: 当前用户信息

    Returns:
        DocumentSplitPreviewResponse: 分割预览结果
    """
    try:
        logger.info(f"=== 开始纯文本分割预览 ===")
        logger.info(f"用户: {current_user.email}")
        logger.info(f"文本长度: {len(request.content)} 字符")
        logger.info(f"分割参数: parent_size={request.parent_chunk_size}, child_size={request.child_chunk_size}")

        # 验证文本内容
        if not request.content.strip():
            raise HTTPException(status_code=400, detail="文本内容不能为空")

        # 创建文档对象
        document = Document(
            page_content=request.content,
            metadata={
                "source": "direct_input",
                "doc_id": str(uuid.uuid4()),
                "document_id": str(uuid.uuid4()),
                "user_id": str(current_user.id)
            }
        )

        logger.info(f"创建文档对象完成")

        # 清洗文档内容
        logger.info(f"清洗文档内容")
        cleaned_document = rag.document_processor.clean_document(document)

        # 创建分割器和规则
        splitter = ParentChildDocumentSplitter()
        rule = Rule(
            mode=SplitMode.PARENT_CHILD,
            max_tokens=request.parent_chunk_size,
            chunk_overlap=request.parent_chunk_overlap,
            fixed_separator=request.parent_separator,
            subchunk_max_tokens=request.child_chunk_size,
            subchunk_overlap=request.child_chunk_overlap,
            subchunk_separator=request.child_separator,
            clean_text=True,
            keep_separator=True
        )

        logger.info(f"开始执行分割")
        segments = splitter.split_documents([cleaned_document], rule)
        logger.info(f"分割完成，生成 {len(segments) if segments else 0} 个段落")

        if not segments:
            return DocumentSplitPreviewResponse(
                success=False,
                message="文档分割后未产生有效内容"
            )

        # 格式化预览结果
        result_segments = []
        children_content = []

        for i, segment in enumerate(segments):
            segment_data = {
                "id": i,
                "content": segment.page_content,
                "start": segment.metadata.get("chunk_start", 0),
                "end": segment.metadata.get("chunk_end", len(segment.page_content)),
                "length": len(segment.page_content),
                "type": segment.metadata.get("type", "unknown")
            }
            result_segments.append(segment_data)

            # 收集子段落内容
            if segment.metadata.get("type") == "child":
                children_content.append(segment.page_content)

        logger.info(f"预览结果格式化完成，返回 {len(result_segments)} 个段落")

        return DocumentSplitPreviewResponse(
            success=True,
            message="文本分割预览成功",
            segments=result_segments,
            total_segments=len(result_segments),
            parentContent=cleaned_document.page_content,
            childrenContent=children_content
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"纯文本分割预览失败: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")

        return DocumentSplitPreviewResponse(
            success=False,
            message=f"文本分割预览失败: {str(e)}"
        )

@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    parent_chunk_size: int = Form(1024),
    parent_chunk_overlap: int = Form(200),
    parent_separator: str = Form("\n\n"),
    child_chunk_size: int = Form(512),
    child_chunk_overlap: int = Form(50),
    child_separator: str = Form("\n"),
    preview_only: bool = Form(False),
    current_user: User = Depends(get_current_user)
):
    """
    上传文档进行RAG处理，支持PDF、TXT和Markdown文件
    
    参数:
        file: 要上传的文件
        parent_chunk_size: 父块分段最大长度，默认1024
        parent_chunk_overlap: 父块重叠长度，默认200
        parent_separator: 父块分段标识符，默认"\n\n"
        child_chunk_size: 子块分段最大长度，默认512
        child_chunk_overlap: 子块重叠长度，默认50
        child_separator: 子块分段标识符，默认"\n"
        preview_only: 是否仅预览文档切割结果，不进行向量存储
    """
    logger.info(f"===== 文档上传请求开始 =====")
    logger.info(f"上传参数: 文件名={file.filename}, parent_chunk_size={parent_chunk_size}, parent_chunk_overlap={parent_chunk_overlap}, "
               f"parent_separator={parent_separator}, child_chunk_size={child_chunk_size}, child_chunk_overlap={child_chunk_overlap}, child_separator={child_separator}, preview_only={preview_only}")
    logger.info(f"preview_only参数类型: {type(preview_only)}, 值: {preview_only}")
    
    # 验证文件类型
    is_supported, file_ext = validate_file_type(file.filename)
    logger.info(f"文件扩展名: {file_ext}")

    if not is_supported:
        logger.warning(f"不支持的文件类型: {file_ext}")
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": f"不支持的文件类型: {file_ext}，支持的类型: {', '.join(SUPPORTED_EXTENSIONS)}"
            }
        )

    # 保存上传的文件
    try:
        file_path = save_uploaded_file(file)
        logger.info(f"用户 {current_user.email} 上传文件 {file.filename}")

        # 生成文档ID和数据集ID
        doc_id = str(uuid.uuid4())
        dataset_id = str(current_user.id)  # 使用用户ID作为数据集ID
        logger.info(f"生成文档ID: {doc_id}, 数据集ID: {dataset_id}")

        # 准备元数据
        metadata = {
            "doc_id": doc_id,
            "document_id": doc_id,
            "dataset_id": dataset_id,
            "file_name": file.filename,
            "preview": preview_only,
            "created_by": str(current_user.id)
        }
        
        # 根据文件类型处理文档
        document = process_document_by_type(file_path, file.filename, metadata)
        
        # 清洗文档
        logger.info(f"清洗文档内容")
        cleaned_document = rag.document_processor.clean_document(document)
        
        # 创建父子文档分割器
        splitter = ParentChildDocumentSplitter()
        
        # 创建分割规则
        rule = create_split_rule(
            parent_chunk_size, parent_chunk_overlap, parent_separator,
            child_chunk_size, child_chunk_overlap, child_separator
        )
        
        # 执行分割
        segments = splitter.split_documents([cleaned_document], rule)
        logger.info(f"文档分割完成，生成了 {len(segments) if segments else 0} 个段落")
        
        # 记录文档信息
        log_document_info(doc_id, file.filename, cleaned_document)

        # 如果是预览模式，返回格式化的预览结果
        if preview_only:
            logger.info(f"预览模式处理完成")
            return format_preview_response(segments, cleaned_document)

        # 正常处理模式：准备返回的段落数据
        result_segments = []
        logger.info(f"\n=== 段落分割结果 ===")

        for i, segment in enumerate(segments):
            # 确保每个段落都有正确的起始和结束位置
            start_pos = segment.metadata.get("chunk_start")
            if start_pos is None:
                start_pos = 0

            end_pos = segment.metadata.get("chunk_end")
            if end_pos is None:
                end_pos = start_pos + len(segment.page_content)

            segment_data = {
                "id": i,
                "content": segment.page_content,
                "start": start_pos,
                "end": end_pos,
                "length": len(segment.page_content)
            }
            result_segments.append(segment_data)

            # 打印每个段落的详细信息
            logger.info(f"\n段落 {i + 1}:")
            logger.info(f"  内容: {segment.page_content}")
            logger.info(f"  长度: {len(segment.page_content)} 字符")
            logger.info(f"  起始位置: {start_pos}")
            logger.info(f"  结束位置: {end_pos}")
            logger.info(f"  元数据: {segment.metadata}")

        # 记录分割统计信息
        log_split_statistics(segments)
        
        # 正常处理模式：保存到数据库和向量存储
        logger.info(f"正常上传模式：开始保存文档")
        result = await rag_service.save_processed_document(
            doc_id=doc_id,
            file_name=file.filename,
            user_id=str(current_user.id),
            segments=segments,
            dataset_id=dataset_id
        )
        
        # 清理临时文件
        cleanup_temp_file(file_path)
        
        if not result["success"]:
            logger.error(f"文档处理失败: {result.get('message', '未知错误')}")
            return JSONResponse(
                status_code=400,
                content=result
            )
            
        logger.info(f"文档处理成功，文档ID: {doc_id}")
        return {
            "success": True,
            "message": "文档上传成功",
            "doc_id": doc_id,
            "segments_count": len(segments)
        }
        
    except Exception as e:
        logger.error(f"处理文档失败: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        
        # 确保临时文件被删除
        cleanup_temp_file(file_path)
            
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"处理文档失败: {str(e)}"
            }
        )

@router.post("/documents/batch-upload", response_model=DocumentUploadResponse)
async def batch_upload_documents(
    files: List[UploadFile] = File(...),
    parent_chunk_size: int = Form(1024),
    parent_chunk_overlap: int = Form(200),
    parent_separator: str = Form("\n\n"),
    child_chunk_size: int = Form(512),
    child_chunk_overlap: int = Form(50),
    child_separator: str = Form("\n"),
    current_user: User = Depends(get_current_user)
):
    """批量上传文档
    
    参数:
        files: 文件列表
        parent_chunk_size: 父块分段最大长度，默认1024
        parent_chunk_overlap: 父块重叠长度，默认200
        parent_separator: 父块分段标识符，默认"\n\n"
        child_chunk_size: 子块分段最大长度，默认512
        child_chunk_overlap: 子块重叠长度，默认50
        child_separator: 子块分段标识符，默认"\n"
    """
    if not files:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "未提供任何文件"
            }
        )
    
    logger.info(f"用户 {current_user.email} 批量上传 {len(files)} 个文件, 参数: parent_chunk_size={parent_chunk_size}, parent_chunk_overlap={parent_chunk_overlap}, parent_separator={parent_separator}, child_chunk_size={child_chunk_size}, child_chunk_overlap={child_chunk_overlap}, child_separator={child_separator}")
    
    # 保存文件到临时位置
    upload_dir = "data/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # 记录临时文件路径以便后续清理
    temp_file_paths = []
    
    # 支持的文件类型
    supported_extensions = ['.txt', '.pdf', '.md']
    
    try:
        # 处理所有文档并准备批量插入
        all_segments = []
        total_documents = 0
        
        for file in files:
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            # 跳过不支持的文件类型
            if file_ext not in supported_extensions:
                logger.warning(f"跳过不支持的文件类型: {file.filename}")
                continue
                
            # 保存文件
            file_path = os.path.join(upload_dir, file.filename)
            temp_file_paths.append(file_path)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # 生成文档ID和数据集ID
            doc_id = str(uuid.uuid4())
            dataset_id = str(current_user.id)  # 使用用户ID作为数据集ID
            
            # 准备元数据
            metadata = {
                "doc_id": doc_id,
                "document_id": doc_id,
                "dataset_id": dataset_id,
                "file_name": file.filename,
                "created_by": str(current_user.id)
            }
            
            # 根据文件类型处理文档
            if file_ext.lower() == '.pdf':
                logger.info(f"处理PDF文件: {file.filename}")
                document = rag.pdf_processor.process_pdf(file_path, metadata)
            else:
                # 处理文本文件
                logger.info(f"处理文本文件: {file.filename}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                document = Document(page_content=content, metadata=metadata)
            
            # 验证和清洗文档
            if not rag.document_processor.validate_document(document):
                logger.warning(f"文档验证失败，跳过: {file.filename}")
                continue
                
            cleaned_document = rag.document_processor.clean_document(document)
            
            # 创建父子文档分割器
            splitter = ParentChildDocumentSplitter()
            
            # 创建分割规则
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
            
            # 执行分割
            segments = splitter.split_documents([cleaned_document], rule)
            
            if not segments:
                logger.warning(f"文档分割后未产生有效内容，跳过: {file.filename}")
                continue
            
            # 添加到批处理列表
            all_segments.extend(segments)
            total_documents += 1
            
            # 保存文档信息到MongoDB
            doc_info = {
                "id": doc_id,
                "file_name": file.filename,
                "user_id": str(current_user.id),
                "segments_count": len(segments),
                "status": "processing"
            }
            
            await rag_service.mongodb.db[rag_service.collection_name].insert_one(doc_info)
        
        # 清理临时文件
        for file_path in temp_file_paths:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        if not all_segments:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "所有文档处理后未产生有效内容"
                }
            )
        
        # 批量处理所有段落
        from app.rag import retrieval_service
        batch_result = await retrieval_service.process_and_index_documents_batch(
            documents=all_segments,
            collection_name="rag_documents"
        )
        
        if not batch_result["success"]:
            return JSONResponse(
                status_code=500,
                content=batch_result
            )
        
        # 更新所有文档状态为ready
        for file in files:
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext in supported_extensions:
                await rag_service.mongodb.db[rag_service.collection_name].update_many(
                    {"file_name": file.filename, "user_id": str(current_user.id), "status": "processing"},
                    {"$set": {"status": "ready"}}
                )
        
        return {
            "success": True,
            "message": f"成功处理和索引 {total_documents} 个文档，共 {len(all_segments)} 个段落",
            "segments_count": len(all_segments),
            "doc_id": batch_result.get("doc_ids", [None])[0] if batch_result.get("doc_ids") else None,
            "processing_time": batch_result.get("processing_time", 0)
        }
        
    except Exception as e:
        logger.error(f"批量处理文档失败: {str(e)}")
        
        # 确保所有临时文件被删除
        for file_path in temp_file_paths:
            if os.path.exists(file_path):
                os.remove(file_path)
                
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"批量处理文档失败: {str(e)}"
            }
        )

@router.post("/documents/search", response_model=DocumentSearchResponse)
async def search_documents(
    request: DocumentSearchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    搜索用户的文档
    """
    logger.info(f"用户 {current_user.email} 搜索文档: {request.query}, 搜索所有用户: {request.search_all}, 包含父文档: {request.include_parent}")
    
    # 如果没有指定文档集，但搜索参数限制了特定文档集时，返回错误
    if request.collection_id and not request.search_all:
        logger.info(f"用户在指定文档集中搜索: {request.collection_id}")
    
    result = await rag_service.search_documents(
        query=request.query,
        user_id=str(current_user.id),
        top_k=request.top_k,
        search_all=request.search_all,
        include_parent=request.include_parent,
        collection_id=request.collection_id
    )
    
    return result

@router.get("/documents", response_model=DocumentListResponse)
async def get_documents(
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的所有文档
    """
    logger.info(f"用户 {current_user.email} 获取文档列表")
    
    documents = await rag_service.get_user_documents(str(current_user.id))
    
    return {"documents": documents}


@router.delete("/documents/{doc_id}", response_model=DeleteDocumentResponse)
async def delete_document(
    doc_id: str = Path(...),
    current_user: User = Depends(get_current_user)
):
    """
    删除文档
    
    普通用户只能删除自己的文档，管理员可以删除任何文档
    """
    # 检查用户是否为管理员
    is_admin = getattr(current_user, "is_admin", False)
    user_email = getattr(current_user, "email", "未知")
    
    logger.info(f"用户 {user_email} ({current_user.id}) 请求删除文档: {doc_id}, 管理员权限: {is_admin}")
    
    result = await rag_service.delete_document(
        doc_id=doc_id,
        user_id=str(current_user.id),
        is_admin=is_admin
    )
    
    if not result["success"]:
        # 根据错误代码返回不同的状态码
        status_code = 400
        if result.get("error_code") == "PERMISSION_DENIED":
            status_code = 403
        elif result.get("error_code") == "DOCUMENT_NOT_FOUND":
            status_code = 404
        elif result.get("error_code") == "RAG_SERVICE_UNAVAILABLE":
            status_code = 503
            
        # 记录错误日志
        logger.error(f"删除文档失败: {result['message']}, 错误代码: {result.get('error_code', '未知')}")
        return JSONResponse(
            status_code=status_code,
            content=result
        )
    
    # 如果有警告，记录但仍然返回成功    
    if "warning" in result:
        logger.warning(f"删除文档警告: {result['warning']}")
        
    # 返回成功结果
    document_name = result.get("document_name", "未知文档")
    logger.info(f"成功删除文档 {doc_id} ({document_name}), 删除了 {result.get('deleted_segments', 0)} 个段落")
    return result

@router.post("/chat", response_model=RAGChatResponse)
async def rag_chat(
    request: RAGChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    RAG聊天
    """
    logger.info(f"用户 {current_user.email} 发送RAG聊天: {request.query}")
    
    # 获取默认LLM模型
    llm = await llm_service.get_default_llm()
    if not llm:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "未找到可用的LLM模型",
                "response": "",
                "sources": [],
                "conversation_id": request.conversation_id or ""
            }
        )
    
    # 生成对话ID
    conversation_id = request.conversation_id or f"conv_{current_user.id}_{llm.id}"
    
    # 如果启用RAG，则获取相关文档
    sources = []
    context = ""
    
    if request.enable_rag:
        search_result = await rag_service.search_documents(
            query=request.query,
            user_id=str(current_user.id),
            top_k=request.top_k,
            search_all=True,
            include_parent=True,  # 聊天时默认使用父子文档模式以提供更多上下文
            collection_id=request.collection_id if hasattr(request, 'collection_id') else None  # 支持文档集过滤
        )
        
        if search_result["success"] and search_result["results"]:
            # 提取上下文和来源
            for result in search_result["results"]:
                content = result["content"]
                
                # 如果有父文档，添加到上下文
                if "parent" in result and result["parent"]:
                    parent_content = result["parent"]["content"]
                    # 只添加父文档的相关部分，可能需要做更智能的裁剪
                    max_parent_length = 1000  # 限制父文档内容长度，避免上下文过长
                    if len(parent_content) > max_parent_length:
                        parent_content = parent_content[:max_parent_length] + "..."
                    
                    context += f"\n\n文档片段的更多上下文:\n{parent_content}\n\n具体相关内容:\n{content}"
                    
                    # 添加来源信息
                    sources.append({
                        "content": content,
                        "file_name": result["metadata"].get("file_name", "未知文件"),
                        "score": result["metadata"].get("score", 0.0),
                        "has_context": True
                    })
                else:
                    context += f"\n\n{content}"
                    sources.append({
                        "content": content,
                        "file_name": result["metadata"].get("file_name", "未知文件"),
                        "score": result["metadata"].get("score", 0.0)
                    })
    
    # 构建带有RAG上下文的提示
    prompt = ""
    if context:
        prompt = f"""
以下是与用户问题相关的信息：
{context}

根据上述信息，请回答用户的问题: {request.query}
"""
    else:
        prompt = request.query
    
    # 调用LLM获取响应
    try:
        llm_result = await llm_service._test_local_llm(llm, prompt)
        
        if "error" in llm_result:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": llm_result["error"],
                    "response": "",
                    "sources": sources,
                    "conversation_id": conversation_id
                }
            )
            
        # 解析不同格式的LLM响应
        response = ""
        if "response" in llm_result:
            # 直接使用response字段
            response = llm_result.get("response", "")
        elif "choices" in llm_result and len(llm_result["choices"]) > 0:
            # OpenAI/LM Studio格式
            message = llm_result["choices"][0].get("message", {})
            response = message.get("content", "")
        else:
            # 尝试其他可能的格式
            logger.warning(f"无法解析LLM响应格式: {str(llm_result)[:200]}")
            response = str(llm_result)
        
        return {
            "success": True,
            "message": "查询成功",
            "response": response,
            "sources": sources,
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        logger.error(f"LLM调用失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"LLM调用失败: {str(e)}",
                "response": "",
                "sources": sources,
                "conversation_id": conversation_id
            }
        )

@router.get("/status", response_model=RAGStatusResponse)
async def check_rag_status(current_user: User = Depends(get_current_user)):
    """
    检查RAG服务状态
    """
    try:
        # 检查各组件状态
        status = {
            "vector_store_available": rag.vector_store is not None,
            "embedding_model_available": rag.embedding_model is not None,
            "retrieval_service_available": rag_service is not None
        }
        
        # 整体可用性判断
        available = all(status.values())
        
        # 构建详细信息
        details = []
        if not status["vector_store_available"]:
            details.append("向量存储不可用")
        if not status["embedding_model_available"]:
            details.append("嵌入模型不可用")
        if not status["retrieval_service_available"]:
            details.append("检索服务不可用")
            
        # 构建响应消息
        message = "RAG服务正常" if available else "RAG服务不可用: " + ", ".join(details)
        
        # 构建服务器信息
        server_info = {}
        if rag.vector_store:
            server_info["milvus"] = {
                "host": rag.vector_store.host,
                "port": rag.vector_store.port
            }
        
        return {
            "available": available,
            "message": message,
            "status": status,
            "server_info": server_info
        }
    except Exception as e:
        logger.error(f"检查RAG状态失败: {str(e)}")
        return {
            "available": False,
            "message": f"检查RAG状态失败: {str(e)}",
            "status": {
                "vector_store_available": False,
                "embedding_model_available": False,
                "retrieval_service_available": False
            },
            "server_info": {}
        }

@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str = Path(..., description="文档ID"),
    current_user: User = Depends(get_current_user)
):
    """获取单个文档信息"""
    try:
        document = await rag_service.get_document_by_id(doc_id)
        if not document:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "文档不存在"
                }
            )
        return {
            "success": True,
            "document": document
        }
    except Exception as e:
        logger.error(f"获取文档失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"获取文档失败: {str(e)}"
            }
        )

@router.get("/collections/documents/{document_id}/slices/{slice_index}/preview", response_model=DocumentSlicePreviewResponse)
async def preview_document_slice(
    document_id: str = Path(..., description="文档ID"),
    slice_index: int = Path(..., description="切割索引位置"),
    current_user: User = Depends(get_current_user)
):
    """
    获取文档切片的预览内容，包括父级内容和子切片内容
    """
    try:
        logger.info(f"===== 开始预览文档切片 =====")
        logger.info(f"用户: {current_user.email}")
        logger.info(f"文档ID: {document_id}")
        logger.info(f"切片索引: {slice_index}")
        
        # 从数据库获取文档
        document = await rag_service.get_document_by_id(document_id)
        if not document:
            logger.error(f"文档不存在: {document_id}")
            return DocumentSlicePreviewResponse(
                success=False,
                message="文档不存在"
            )
        
        logger.info(f"成功获取文档信息:")
        logger.info(f"- 文件名: {document.metadata.get('file_name', '未知')}")
        logger.info(f"- 文档内容长度: {len(document.page_content)} 字符")
        logger.info(f"- 文档内容预览: {document.page_content[:200]}...")
        
        # 获取文档的所有切片
        segments = await rag_service.get_document_segments(document_id)
        if not segments:
            logger.error(f"文档没有切片: {document_id}")
            return DocumentSlicePreviewResponse(
                success=False,
                message="文档没有切片"
            )
        
        if slice_index >= len(segments):
            logger.error(f"切片索引无效: {slice_index}, 总切片数: {len(segments)}")
            return DocumentSlicePreviewResponse(
                success=False,
                message=f"切片索引无效，总切片数: {len(segments)}"
            )
        
        logger.info(f"成功获取文档切片:")
        logger.info(f"- 总切片数: {len(segments)}")
        
        # 获取当前切片
        current_segment = segments[slice_index]
        logger.info(f"\n=== 当前切片信息 ===")
        logger.info(f"- 切片ID: {current_segment.metadata.get('doc_id', '未知')}")
        logger.info(f"- 切片内容长度: {len(current_segment.page_content)} 字符")
        logger.info(f"- 切片内容预览: {current_segment.page_content[:200]}...")
        logger.info(f"- 切片元数据: {current_segment.metadata}")
        
        # 获取父级内容（原始文档内容）
        parent_content = document.page_content
        logger.info(f"\n=== 父级内容信息 ===")
        logger.info(f"- 内容长度: {len(parent_content)} 字符")
        logger.info(f"- 内容预览: {parent_content[:200]}...")
        
        # 获取子切片内容（当前切片的子切片）
        children_content = []
        if current_segment:
            # 如果当前切片存在，获取其子切片
            child_segments = await rag_service.get_segment_children(current_segment.metadata.get("doc_id"))
            if child_segments:
                children_content = [segment.page_content for segment in child_segments]
                logger.info(f"\n=== 子切片信息 ===")
                logger.info(f"- 子切片数量: {len(children_content)}")
                for i, content in enumerate(children_content):
                    logger.info(f"\n子切片 {i + 1}:")
                    logger.info(f"- 内容长度: {len(content)} 字符")
                    logger.info(f"- 内容预览: {content[:200]}...")
            else:
                logger.info("没有找到子切片")
        
        # 准备返回结果
        result_segments = []
        for i, segment in enumerate(segments):
            result_segments.append({
                "id": i,
                "content": segment.page_content,
                "start": segment.metadata.get("chunk_start", 0),
                "end": segment.metadata.get("chunk_end", len(segment.page_content)),
                "length": len(segment.page_content)
            })
        
        logger.info(f"\n=== 返回结果统计 ===")
        logger.info(f"- 总段落数: {len(result_segments)}")
        logger.info(f"- 父级内容长度: {len(parent_content)} 字符")
        logger.info(f"- 子切片数量: {len(children_content)}")
        logger.info("===== 预览文档切片完成 =====\n")
        
        return DocumentSlicePreviewResponse(
            success=True,
            message="获取切片预览成功",
            segments=result_segments,
            total_segments=len(segments),
            parentContent=parent_content,
            childrenContent=children_content
        )
        
    except Exception as e:
        logger.error(f"预览文档切片失败: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return DocumentSlicePreviewResponse(
            success=False,
            message=f"预览文档切片失败: {str(e)}"
        )