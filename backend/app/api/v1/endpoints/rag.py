import os
import logging
import shutil
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form, Path, Query, Body
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from app.api.deps import get_current_user
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
from pydantic import BaseModel
from langchain_core.documents import Document
from app.rag.extractor.extract_processor import ExtractProcessor, ExtractMode

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()
llm_service = LLMService()
rag_service = RAGService()

# 定义文档切割预览请求模型
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
    file: Optional[UploadFile] = File(None),
    content: Optional[str] = Body(None),
    parent_chunk_size: int = Body(1024),
    parent_chunk_overlap: int = Body(200),
    parent_separator: str = Body("\n\n"),
    child_chunk_size: int = Body(512),
    child_chunk_overlap: int = Body(50),
    child_separator: str = Body("\n"),
    current_user: User = Depends(get_current_user)
):
    """预览文档分割结果
    
    参数:
        file: 上传的文件
        content: 文本内容
        parent_chunk_size: 父块分段最大长度，默认1024
        parent_chunk_overlap: 父块重叠长度，默认200
        parent_separator: 父块分段标识符，默认"\n\n"
        child_chunk_size: 子块分段最大长度，默认512
        child_chunk_overlap: 子块重叠长度，默认50
        child_separator: 子块分段标识符，默认"\n"
    """
    try:
        # 获取文档内容
        if file:
            content_bytes = await file.read()
            # 检查文件扩展名
            file_ext = os.path.splitext(file.filename)[1].lower()
            
            logger.info(f"处理文件: {file.filename}, 扩展名: {file_ext}")
            
            if file_ext == '.pdf':
                # 创建临时文件
                temp_file_path = f"/tmp/{file.filename}"
                with open(temp_file_path, "wb") as f:
                    f.write(content_bytes)
                
                try:
                    # 使用ExtractProcessor处理PDF
                    documents = ExtractProcessor.extract_pdf(
                        file_path=temp_file_path,
                        mode=ExtractMode.UNSTRUCTURED
                    )
                    
                    # 合并所有文档内容
                    content = "\n\n".join([doc.page_content for doc in documents])
                finally:
                    # 清理临时文件
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
            else:
                # 对于其他文件，尝试使用UTF-8解码
                try:
                    content = content_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    # 如果UTF-8解码失败，尝试使用其他编码
                    try:
                        content = content_bytes.decode('gbk')
                    except UnicodeDecodeError:
                        content = content_bytes.decode('latin1')
                        
            logger.info(f"文件内容解码完成，长度: {len(content)}")
        elif not content:
            raise HTTPException(status_code=400, detail="必须提供文件或文本内容")
            
        # 创建文档对象
        document = Document(
            page_content=content,
            metadata={
                "source": file.filename if file else "direct_input",
                "created_at": datetime.now().isoformat()
            }
        )
        
        # 创建层级文档分割器
        splitter = rag.HierarchicalDocumentSplitter(
            parent_chunk_size=parent_chunk_size,
            parent_chunk_overlap=parent_chunk_overlap,
            parent_separator=parent_separator,
            child_chunk_size=child_chunk_size,
            child_chunk_overlap=child_chunk_overlap,
            child_separator=child_separator
        )
        
        # 执行分割
        parent_docs = splitter.split_document(document)
        
        if not parent_docs:
            return DocumentSplitPreviewResponse(
                success=False,
                message="文档分割后未产生有效内容，请检查文档或调整切割参数"
            )
            
        # 准备返回结果
        result_segments = []
        parent_content = document.page_content
        children_content = []
        
        logger.info(f"分割完成，生成了 {len(parent_docs)} 个父文档")
        
        # 处理每个父文档及其子文档
        for i, parent in enumerate(parent_docs):
            # 添加父文档信息
            result_segments.append({
                "id": i,
                "content": parent.page_content,
                "start": parent_content.find(parent.page_content),
                "end": parent_content.find(parent.page_content) + len(parent.page_content),
                "length": len(parent.page_content),
                "is_parent": True,
                "doc_id": parent.metadata.get("doc_id", str(i))
            })
            
            # 处理子文档
            if parent.children:
                for child in parent.children:
                    # 添加子文档内容
                    children_content.append(child.page_content)
                    
                    # 计算子文档在父文档中的位置
                    child_start = parent.page_content.find(child.page_content)
                    if child_start != -1:
                        result_segments.append({
                            "id": len(result_segments),
                            "content": child.page_content,
                            "start": child_start,
                            "end": child_start + len(child.page_content),
                            "length": len(child.page_content),
                            "is_parent": False,
                            "parent_id": parent.metadata.get("doc_id", str(i)),
                            "doc_id": child.metadata.get("doc_id", f"{i}-{len(children_content)}")
                        })
        
        logger.info(f"处理完成，总共生成了 {len(result_segments)} 个段落")
        
        return DocumentSplitPreviewResponse(
            success=True,
            segments=result_segments,
            total_segments=len(result_segments),
            parentContent=parent_content,
            childrenContent=children_content
        )
        
    except Exception as e:
        logger.error(f"文档分割预览失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/upload", response_model=DocumentUploadResponse)
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
    
    # 支持的文件类型
    supported_extensions = ['.txt', '.pdf', '.md']
    
    # 检查文件扩展名
    file_ext = os.path.splitext(file.filename)[1].lower()
    logger.info(f"文件扩展名: {file_ext}")
    
    if file_ext not in supported_extensions:
        logger.warning(f"不支持的文件类型: {file_ext}")
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": f"不支持的文件类型: {file_ext}，支持的类型: {', '.join(supported_extensions)}"
            }
        )
    
    # 保存文件到临时位置
    upload_dir = "data/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"文件已保存到临时位置: {file_path}")
        logger.info(f"用户 {current_user.email} 上传文件 {file.filename}")

        # 生成文档ID
        doc_id = str(uuid.uuid4())
        logger.info(f"生成文档ID: {doc_id}")
        
        # 准备元数据
        metadata = {
            "doc_id": doc_id,
            "document_id": doc_id,
            "file_name": file.filename,
            "preview": preview_only
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
        
        # 清洗文档
        logger.info(f"清洗文档内容")
        cleaned_document = rag.document_processor.clean_document(document)
        
        # 创建文档分割器并应用自定义参数
        logger.info(f"创建文档分割器，参数: parent_chunk_size={parent_chunk_size}, parent_chunk_overlap={parent_chunk_overlap}, "
                   f"parent_separator={parent_separator}, child_chunk_size={child_chunk_size}, child_chunk_overlap={child_chunk_overlap}, child_separator={child_separator}")
        
        # 创建层级文档分割器
        splitter = rag.HierarchicalDocumentSplitter(
            parent_chunk_size=parent_chunk_size,
            parent_chunk_overlap=parent_chunk_overlap,
            parent_separator=parent_separator,
            child_chunk_size=child_chunk_size,
            child_chunk_overlap=child_chunk_overlap,
            child_separator=child_separator
        )
        
        # 分割文档
        segments = splitter.split_document(cleaned_document)
        logger.info(f"文档分割完成，生成了 {len(segments) if segments else 0} 个段落")
        
        # 打印原始文档信息
        logger.info(f"\n=== 原始文档信息 ===")
        logger.info(f"文件名: {file.filename}")
        logger.info(f"文档ID: {doc_id}")
        logger.info(f"文档内容前100字符: {cleaned_document.page_content[:100]}")
        logger.info(f"总字符数: {len(cleaned_document.page_content)}")

        # 准备返回的段落数据
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

        logger.info(f"\n=== 分割统计 ===")
        logger.info(f"总段落数: {len(result_segments)}")
        if result_segments:
            avg_length = sum(len(s['content']) for s in result_segments) / len(result_segments)
            logger.info(f"平均段落长度: {avg_length:.2f} 字符")
            logger.info(f"最短段落长度: {min(len(s['content']) for s in result_segments)} 字符")
            logger.info(f"最长段落长度: {max(len(s['content']) for s in result_segments)} 字符")

        # 如果是预览模式，直接返回处理结果
        if preview_only:
            logger.info(f"预览模式处理完成，返回 {len(result_segments)} 个段落")
            return {
                "success": True,
                "message": "文档预览成功",
                "preview_mode": True,
                "segments": result_segments,
                "total_segments": len(segments),
                "original_text": cleaned_document.page_content,  # 添加原始文本
                "file_name": file.filename,
                "statistics": {
                    "total_segments": len(segments),
                    "total_chars": len(cleaned_document.page_content),
                    "avg_segment_length": sum(len(s['content']) for s in result_segments) / len(result_segments) if result_segments else 0,
                    "min_segment_length": min(len(s['content']) for s in result_segments) if result_segments else 0,
                    "max_segment_length": max(len(s['content']) for s in result_segments) if result_segments else 0
                }
            }
        
        # 正常处理模式：保存到数据库和向量存储
        logger.info(f"正常上传模式：开始保存文档")
        result = await rag_service.save_processed_document(
            doc_id=doc_id,
            file_name=file.filename,
            user_id=str(current_user.id),
            segments=segments
        )
        
        # 删除临时文件
        os.remove(file_path)
        logger.info(f"临时文件已删除: {file_path}")
        
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
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"异常处理：临时文件已删除: {file_path}")
            
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
            
            # 创建层级文档分割器
            splitter = rag.HierarchicalDocumentSplitter(
                parent_chunk_size=parent_chunk_size,
                parent_chunk_overlap=parent_chunk_overlap,
                parent_separator=parent_separator,
                child_chunk_size=child_chunk_size,
                child_chunk_overlap=child_chunk_overlap,
                child_separator=child_separator
            )
            
            # 分割文档
            segments = splitter.split_document(cleaned_document)
            
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