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
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile, Form, Path
from fastapi.responses import JSONResponse

from app.dependencies import (
    get_current_user,
    get_rag_service,
    get_llm_service,
    get_rag_pipeline,
    get_parent_child_processor
)
from app.api.v1.utils import (
    SUPPORTED_EXTENSIONS,
    validate_file_type,
    save_uploaded_file,
    process_document_by_type,
    create_split_rule,
    format_unified_response,
    #format_enhanced_preview_response,
    cleanup_temp_file,
    log_document_info,
    log_split_statistics
)
from app.api.v1.utils.document_utils import (
    format_enhanced_preview_response
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
    DocumentSlicePreviewResponse
)
from app.rag.processor_factory import ProcessorType, ProcessorConfig
from app.rag.index_processor import BaseIndexProcessor, ExtractSetting, ProcessRule, ParentMode, PreviewModeManager
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.rag.interfaces import IRagPipeline
from app.models.user import User
import app.rag as rag
from app.rag.models import Document
from app.rag.document_splitter import ParentChildDocumentSplitter, Rule, SplitMode

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

# 注意：DocumentSplitRequest 和 DocumentSplitPreviewResponse 模型已被删除
# 请使用 /documents/upload 端点并设置 preview_only=true 进行文档预览

# 注意：preview_document_split 端点已被删除
# 请使用 /documents/upload 端点并设置 preview_only=true 进行文档预览

def _decode_separator(separator: str) -> str:
    """
    解码分隔符字符串，将转义字符转换为实际字符

    Args:
        separator: 可能包含转义字符的分隔符字符串

    Returns:
        str: 解码后的分隔符字符串
    """
    # 处理常见的转义字符
    separator = separator.replace('\\n', '\n')
    separator = separator.replace('\\t', '\t')
    separator = separator.replace('\\r', '\r')
    return separator


async def _process_document_with_index_processor(
    file_path: str,
    file_name: str,
    doc_id: str,
    dataset_id: str,
    metadata: dict,
    processor_type: str,
    parent_mode: str,
    parent_chunk_size: int,
    parent_chunk_overlap: int,
    parent_separator: str,
    child_chunk_size: int,
    child_chunk_overlap: int,
    child_separator: str,
    preview_only: bool,
    current_user,
    index_processor: BaseIndexProcessor,
    rag_service
) -> dict:
    """
    使用IndexProcessor处理文档的新实现

    Args:
        file_path: 文件路径
        file_name: 文件名
        doc_id: 文档ID
        dataset_id: 数据集ID
        metadata: 元数据
        processor_type: 处理器类型
        parent_mode: 父文档模式
        parent_chunk_size: 父块大小
        parent_chunk_overlap: 父块重叠
        parent_separator: 父块分隔符
        child_chunk_size: 子块大小
        child_chunk_overlap: 子块重叠
        child_separator: 子块分隔符
        preview_only: 是否仅预览
        current_user: 当前用户
        index_processor: 索引处理器实例
        rag_service: RAG服务实例

    Returns:
        dict: 处理结果
    """
    try:
        logger.info(f"开始使用IndexProcessor处理文档: {file_name}")

        # 1. 文档提取阶段
        logger.info("步骤1: 文档提取")
        extract_setting = ExtractSetting(
            file_path=file_path,
            extract_mode="basic",
            cache_key=f"{doc_id}_extract"
        )

        documents = index_processor.extract(extract_setting)
        logger.info(f"文档提取完成，提取到 {len(documents)} 个文档")

        if not documents:
            return _create_error_response(
                "文档提取失败，未能提取到有效内容",
                status_code=400,
                preview_mode=preview_only
            )

        # 2. 文档转换阶段（父子结构）
        logger.info("步骤2: 文档转换为父子结构")

        # 创建处理规则
        parent_mode_enum = ParentMode.PARAGRAPH if parent_mode == "paragraph" else ParentMode.FULL_DOC
        process_rule = ProcessRule(
            mode="automatic",
            parent_mode=parent_mode_enum,
            rules={
                "segmentation": {
                    "separator": parent_separator,
                    "max_tokens": parent_chunk_size,
                    "chunk_overlap": parent_chunk_overlap
                },
                "subchunk_segmentation": {
                    "separator": child_separator,
                    "max_tokens": child_chunk_size,
                    "chunk_overlap": child_chunk_overlap
                }
            }
        )

        transformed_documents = index_processor.transform(
            documents,
            process_rule=process_rule.__dict__,
            preview=preview_only
        )
        logger.info(f"文档转换完成，生成 {len(transformed_documents)} 个段落")

        # 3. 预览模式或存储模式
        if preview_only:
            logger.info("预览模式：返回切割结果")
            # 清理临时文件
            cleanup_temp_file(file_path)

            # 使用增强的预览响应格式化函数
            processing_stats = {
                "processor_type": "IndexProcessor",
                "processing_time": time.time() - start_time if 'start_time' in locals() else None,
                "optimization_level": "enhanced"
            }

            response = format_enhanced_preview_response(
                transformed_documents,
                documents[0] if documents else None,
                doc_id,
                processing_stats
            )
            response["message"] = "文档切割预览生成成功（使用IndexProcessor增强模式）"
            return response

        else:
            logger.info("存储模式：保存到向量数据库")

            # 4. 文档加载阶段
            index_processor.load(transformed_documents)
            logger.info("文档已加载到向量存储")

            # 5. 保存到MongoDB
            result = await rag_service.save_processed_document(
                doc_id=doc_id,
                file_name=file_name,
                user_id=str(current_user.id),
                segments=transformed_documents,
                dataset_id=dataset_id,
                original_content=documents[0].page_content if documents else None
            )

            # 清理临时文件
            cleanup_temp_file(file_path)

            if not result["success"]:
                return _create_error_response(
                    result.get('message', '文档处理失败'),
                    status_code=400,
                    preview_mode=False
                )

            # 使用统一的响应格式化函数
            response = format_unified_response(
                transformed_documents,
                documents[0] if documents else None,
                doc_id,
                preview_mode=False
            )
            response["doc_id"] = doc_id
            response["message"] = "文档上传成功（使用IndexProcessor）"
            return response

    except Exception as e:
        logger.error(f"IndexProcessor处理文档失败: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")

        # 确保临时文件被删除
        try:
            cleanup_temp_file(file_path)
        except:
            pass

        return _create_error_response(
            f"处理文档失败: {str(e)}",
            status_code=500,
            preview_mode=preview_only
        )


def _create_error_response(message: str, status_code: int = 400, preview_mode: bool = False) -> JSONResponse:
    """
    创建统一的错误响应格式

    Args:
        message: 错误消息
        status_code: HTTP状态码
        preview_mode: 是否为预览模式

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "preview_mode": preview_mode,
            "doc_id": None,
            "total_segments": 0,
            "parent_segments": 0,
            "child_segments": 0,
            "parentContent": "",
            "childrenContent": [],
            "segments": [],
            "document_overview": {
                "title": "错误",
                "total_length": 0,
                "total_segments": 0,
                "parent_segments": 0,
                "child_segments": 0
            }
        }
    )


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
    processor_type: str = Form("parent_child"),  # 新增：处理器类型选择
    parent_mode: str = Form("paragraph"),        # 新增：父文档模式选择
    use_new_processor: bool = Form(False),       # 修复：默认使用传统处理器确保一致性
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service),
    index_processor: BaseIndexProcessor = Depends(get_parent_child_processor)
):
    """
    统一的文档上传和预览API接口

    此接口通过preview_only参数统一了文档预览切割和正式上传的功能：
    - preview_only=True: 仅进行文档切割预览，返回切割结果但不存储到向量数据库
    - preview_only=False: 执行完整的文档上传流程，包括切割、向量化和存储到数据库

    两种模式使用相同的文档处理逻辑和切割参数，确保预览结果与实际上传结果一致。

    支持的文件格式: PDF、TXT、Markdown

    参数:
        file: 要上传的文件
        parent_chunk_size: 父块分段最大长度，默认1024
        parent_chunk_overlap: 父块重叠长度，默认200
        parent_separator: 父块分段标识符，默认"\n\n"
        child_chunk_size: 子块分段最大长度，默认512
        child_chunk_overlap: 子块重叠长度，默认50
        child_separator: 子块分段标识符，默认"\n"
        preview_only: 是否仅预览文档切割结果，不进行向量存储

    返回:
        统一格式的响应，包含文档切割详情和处理状态
    """
    logger.info(f"===== 文档上传请求开始 =====")
    logger.info(f"用户信息: email={current_user.email}, id={current_user.id}")
    logger.info(f"文件信息: 文件名={file.filename}, 大小={file.size}字节, 内容类型={file.content_type}")
    logger.info(f"上传参数详情:")
    logger.info(f"  - parent_chunk_size: {parent_chunk_size} (类型: {type(parent_chunk_size)})")
    logger.info(f"  - parent_chunk_overlap: {parent_chunk_overlap} (类型: {type(parent_chunk_overlap)})")
    logger.info(f"  - parent_separator: {repr(parent_separator)} (类型: {type(parent_separator)})")
    logger.info(f"  - child_chunk_size: {child_chunk_size} (类型: {type(child_chunk_size)})")
    logger.info(f"  - child_chunk_overlap: {child_chunk_overlap} (类型: {type(child_chunk_overlap)})")
    logger.info(f"  - child_separator: {repr(child_separator)} (类型: {type(child_separator)})")
    logger.info(f"  - preview_only: {preview_only} (类型: {type(preview_only)})")
    logger.info(f"  - processor_type: {processor_type} (类型: {type(processor_type)})")
    logger.info(f"  - parent_mode: {parent_mode} (类型: {type(parent_mode)})")
    logger.info(f"  - use_new_processor: {use_new_processor} (类型: {type(use_new_processor)})")

    # 记录请求来源信息（如果可用）
    try:
        from fastapi import Request
        # 注意：这里需要在函数参数中添加request: Request参数才能获取
        logger.info(f"请求来源信息: 暂时无法获取（需要添加Request参数）")
    except Exception as e:
        logger.debug(f"无法获取请求来源信息: {e}")

    # 解码分隔符参数
    parent_separator = _decode_separator(parent_separator)
    child_separator = _decode_separator(child_separator)
    logger.info(f"解码后分隔符: parent_separator={repr(parent_separator)}, child_separator={repr(child_separator)}")

    # 记录处理器选择和参数，用于一致性分析
    logger.info(f"处理器配置: use_new_processor={use_new_processor}, processor_type={processor_type}, parent_mode={parent_mode}")
    logger.info(f"分割参数: parent_size={parent_chunk_size}, parent_overlap={parent_chunk_overlap}, child_size={child_chunk_size}, child_overlap={child_chunk_overlap}")

    # 验证文件类型
    is_supported, file_ext = validate_file_type(file.filename)
    logger.info(f"文件扩展名: {file_ext}")

    if not is_supported:
        logger.warning(f"不支持的文件类型: {file_ext}")
        return _create_error_response(
            f"不支持的文件类型: {file_ext}，支持的类型: {', '.join(SUPPORTED_EXTENSIONS)}",
            status_code=400,
            preview_mode=preview_only
        )

    # 保存上传的文件
    try:
        logger.info(f"开始保存上传文件: {file.filename}")
        file_path = save_uploaded_file(file)
        logger.info(f"文件保存成功: {file_path}")
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
        logger.info(f"元数据准备完成: {metadata}")

        # 检查是否使用新的IndexProcessor
        if use_new_processor:
            logger.info("使用新的IndexProcessor处理文档")
            return await _process_document_with_index_processor(
                file_path=file_path,
                file_name=file.filename,
                doc_id=doc_id,
                dataset_id=dataset_id,
                metadata=metadata,
                processor_type=processor_type,
                parent_mode=parent_mode,
                parent_chunk_size=parent_chunk_size,
                parent_chunk_overlap=parent_chunk_overlap,
                parent_separator=parent_separator,
                child_chunk_size=child_chunk_size,
                child_chunk_overlap=child_chunk_overlap,
                child_separator=child_separator,
                preview_only=preview_only,
                current_user=current_user,
                index_processor=index_processor,
                rag_service=rag_service
            )

        # 使用原有的处理逻辑（向后兼容）
        logger.info("使用原有的文档处理逻辑")

        # 根据文件类型处理文档
        logger.info(f"开始处理文档，文件类型: {os.path.splitext(file.filename)[1].lower()}")
        document = process_document_by_type(file_path, file.filename, metadata)
        logger.info(f"文档处理完成，内容长度: {len(document.page_content)}字符")

        # 清洗文档
        logger.info(f"开始清洗文档内容")
        cleaned_document = rag.document_processor.clean_document(document)
        logger.info(f"文档清洗完成，清洗后长度: {len(cleaned_document.page_content)}字符")

        # 创建父子文档分割器
        logger.info(f"创建父子文档分割器，参数: parent_size={parent_chunk_size}, parent_overlap={parent_chunk_overlap}, child_size={child_chunk_size}, child_overlap={child_chunk_overlap}")
        splitter = ParentChildDocumentSplitter()
        
        # 创建分割规则
        logger.info(f"创建分割规则，参数详情:")
        logger.info(f"  - parent_separator: {repr(parent_separator)}")
        logger.info(f"  - child_separator: {repr(child_separator)}")
        rule = create_split_rule(
            parent_chunk_size, parent_chunk_overlap, parent_separator,
            child_chunk_size, child_chunk_overlap, child_separator
        )
        logger.info(f"分割规则创建完成: {rule}")

        # 执行分割
        logger.info(f"开始执行文档分割")
        segments = splitter.split_documents([cleaned_document], rule)
        logger.info(f"文档分割完成，生成了 {len(segments) if segments else 0} 个段落")

        # 记录分割结果详情
        if segments:
            logger.info(f"分割结果详情:")
            for i, segment in enumerate(segments[:3]):  # 只记录前3个段落的详情
                logger.info(f"  段落 {i+1}: 长度={len(segment.page_content)}字符, 元数据={segment.metadata}")
            if len(segments) > 3:
                logger.info(f"  ... 还有 {len(segments) - 3} 个段落")
        
        # 记录文档信息
        log_document_info(doc_id, file.filename, cleaned_document)

        # 准备切割参数（两种模式都需要）
        split_params = {
            "parent_chunk_size": parent_chunk_size,
            "parent_chunk_overlap": parent_chunk_overlap,
            "parent_separator": parent_separator,
            "child_chunk_size": child_chunk_size,
            "child_chunk_overlap": child_chunk_overlap,
            "child_separator": child_separator
        }

        # 如果是预览模式，存储到缓存中用于后续的子块预览
        if preview_only:
            logger.info(f"预览模式处理完成")
            # 生成预览格式的doc_id
            preview_doc_id = f"preview_{doc_id}"
            # 将预览数据存储到缓存中，用于后续的子块预览
            from app.services.preview_cache_service import preview_cache_service
            preview_cache_service.store_preview_data(preview_doc_id, segments, cleaned_document, split_params)

            # 使用统一的响应格式化函数，但标记为预览模式
            response = format_unified_response(segments, cleaned_document, preview_doc_id, preview_mode=True)
            logger.info(f"预览模式响应生成完成")
            return response

        # 正常处理模式：保存到数据库和向量存储
        logger.info(f"正常上传模式：开始保存文档到数据库和向量存储")
        logger.info(f"保存参数: doc_id={doc_id}, file_name={file.filename}, user_id={current_user.id}, segments_count={len(segments)}, dataset_id={dataset_id}")
        result = await rag_service.save_processed_document(
            doc_id=doc_id,
            file_name=file.filename,
            user_id=str(current_user.id),
            segments=segments,
            dataset_id=dataset_id,
            original_content=cleaned_document.page_content if cleaned_document else None
        )
        logger.info(f"文档保存结果: success={result.get('success')}, message={result.get('message')}")

        # 清理临时文件
        cleanup_temp_file(file_path)

        if not result["success"]:
            logger.error(f"文档处理失败: {result.get('message', '未知错误')}")
            return _create_error_response(
                result.get('message', '文档处理失败'),
                status_code=400,
                preview_mode=False
            )

        logger.info(f"文档处理成功，文档ID: {doc_id}")

        # 记录分割统计信息
        log_split_statistics(segments)

        # 使用统一的响应格式化函数，标记为保存模式
        response = format_unified_response(segments, cleaned_document, doc_id, preview_mode=False)

        # 添加保存模式特有的字段
        response["doc_id"] = doc_id
        response["message"] = "文档上传成功"

        logger.info(f"保存模式响应生成完成")
        return response
        
    except Exception as e:
        logger.error(f"处理文档失败: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")

        # 确保临时文件被删除
        try:
            cleanup_temp_file(file_path)
        except:
            pass  # 忽略清理文件时的错误

        return _create_error_response(
            f"处理文档失败: {str(e)}",
            status_code=500,
            preview_mode=preview_only
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
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
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
    
    logger.info(f"用户 {current_user.email} 批量上传 {len(files)} 个文件, 参数: parent_chunk_size={parent_chunk_size}, parent_chunk_overlap={parent_chunk_overlap}, parent_separator={repr(parent_separator)}, child_chunk_size={child_chunk_size}, child_chunk_overlap={child_chunk_overlap}, child_separator={repr(child_separator)}")

    # 解码分隔符参数
    parent_separator = _decode_separator(parent_separator)
    child_separator = _decode_separator(child_separator)
    logger.info(f"解码后分隔符: parent_separator={repr(parent_separator)}, child_separator={repr(child_separator)}")

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


@router.post("/documents/upload-hierarchical", response_model=DocumentUploadResponse)
async def upload_document_hierarchical(
    file: UploadFile = File(...),
    parent_mode: str = Form("paragraph"),
    parent_chunk_size: int = Form(1000),
    parent_chunk_overlap: int = Form(100),
    child_chunk_size: int = Form(300),
    child_chunk_overlap: int = Form(50),
    parent_separators: str = Form(None),  # 新增：父块分隔符，用逗号分隔，如 "\\n\\n,\\n,。"
    child_separators: str = Form(None),   # 新增：子块分隔符，用逗号分隔，如 "\\n,。,. "
    index_child_chunks_only: bool = Form(True),
    enable_parent_context: bool = Form(True),
    content_type: str = Form(None),
    preview_only: bool = Form(False),
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    使用层次化架构上传和处理文档
    
    Args:
        file: 上传的文件
        parent_mode: 父段落模式 (paragraph/full_doc)
        parent_chunk_size: 父段落大小
        parent_chunk_overlap: 父段落重叠
        child_chunk_size: 子块大小
        child_chunk_overlap: 子块重叠
        parent_separators: 父块分隔符（用逗号分隔），如 "\\n\\n,\\n,。"，为空时使用默认值
        child_separators: 子块分隔符（用逗号分隔），如 "\\n,。,. "，为空时使用默认值
        index_child_chunks_only: 是否仅索引子块
        enable_parent_context: 是否启用父段落上下文
        content_type: 内容类型 (academic/news/dialogue/code/legal)
        preview_only: 是否仅预览
        current_user: 当前用户
        rag_service: RAG服务
    """
    
    try:
        logger.info(f"用户 {current_user.email} 开始层次化上传文档: {file.filename}")
        
        # 检查RAG服务是否启用层次化处理
        if not rag_service.enable_hierarchical_processing:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "层次化处理功能未启用，请联系管理员",
                    "error_code": "HIERARCHICAL_DISABLED"
                }
            )
        
        # 验证文件类型
        is_supported, file_ext = validate_file_type(file.filename)
        if not is_supported:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(SUPPORTED_EXTENSIONS)}",
                    "error_code": "UNSUPPORTED_FILE_TYPE"
                }
            )
        
        # 保存上传的文件
        file_path = save_uploaded_file(file)
        
        try:
            # 解析自定义分隔符
            def parse_separators(separator_string: str) -> List[str]:
                """解析分隔符字符串，处理转义字符"""
                if not separator_string or separator_string.strip() == "":
                    return None  # 返回None表示使用默认值
                
                # 按逗号分割
                separators = [s.strip() for s in separator_string.split(',')]
                
                # 处理转义字符
                processed_separators = []
                for sep in separators:
                    if sep:  # 忽略空字符串
                        # 处理常见的转义字符
                        sep = sep.replace('\\n', '\n')
                        sep = sep.replace('\\t', '\t')
                        sep = sep.replace('\\r', '\r')
                        processed_separators.append(sep)
                
                return processed_separators if processed_separators else None
            
            # 解析父块和子块分隔符
            parsed_parent_separators = parse_separators(parent_separators)
            parsed_child_separators = parse_separators(child_separators)
            
            logger.info(f"自定义分隔符解析结果:")
            logger.info(f"  parent_separators: {parent_separators} -> {parsed_parent_separators}")
            logger.info(f"  child_separators: {child_separators} -> {parsed_child_separators}")
            
            # 创建层次化配置
            from app.rag.models import HierarchicalSplittingConfig
            
            # 准备配置参数
            config_params = {
                "parent_mode": parent_mode,
                "parent_chunk_size": parent_chunk_size,
                "parent_chunk_overlap": parent_chunk_overlap,
                "child_chunk_size": child_chunk_size,
                "child_chunk_overlap": child_chunk_overlap,
                "index_child_chunks_only": index_child_chunks_only,
                "enable_parent_context": enable_parent_context,
                "content_type": content_type if content_type != "None" else None
            }
            
            # 添加自定义分隔符（如果提供）
            if parsed_parent_separators is not None:
                config_params["parent_separators"] = parsed_parent_separators
            if parsed_child_separators is not None:
                config_params["child_separators"] = parsed_child_separators
            
            hierarchical_config = HierarchicalSplittingConfig(**config_params)
            
            # 如果是预览模式
            if preview_only:
                # 处理文档并返回预览信息
                from app.rag.hierarchical_processor import hierarchical_processor
                from app.rag.document_processor import Document
                import copy
                
                # 加载文档内容
                if file.filename.lower().endswith('.pdf'):
                    components = rag_service._get_rag_components()
                    pdf_processor = components['pdf_processor']
                    document = pdf_processor.process_pdf(file_path, {})
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    document = Document(page_content=content, metadata={})
                
                # 创建临时处理器进行预览
                temp_processor = copy.deepcopy(hierarchical_processor)
                temp_processor.update_config(hierarchical_config)
                
                # 生成预览
                if hierarchical_config.parent_mode == "full_doc":
                    parent_segments = temp_processor._create_full_doc_segment(
                        document, "preview", "preview"
                    )
                else:
                    parent_segments = temp_processor._create_parent_segments(
                        document, "preview", "preview"
                    )
                
                # 为每个父段落生成子块预览
                preview_data = {
                    "document_id": "preview",
                    "file_name": file.filename,
                    "config": hierarchical_config.dict(),
                    "parent_segments": [],
                    "total_parent_segments": len(parent_segments),
                    "total_child_chunks": 0
                }
                
                for i, segment in enumerate(parent_segments[:10]):  # 预览前10个父段落
                    child_chunks = temp_processor._create_child_chunks(segment)
                    preview_data["total_child_chunks"] += len(child_chunks)
                    
                    segment_preview = {
                        "position": segment.position,
                        "content": segment.content[:500] + "..." if len(segment.content) > 500 else segment.content,
                        "word_count": segment.word_count,
                        "child_chunks": [
                            {
                                "position": chunk.position,
                                "content": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                                "word_count": chunk.word_count
                            }
                            for j, chunk in enumerate(child_chunks[:3])  # 每个父段落只预览前3个子块
                        ],
                        "child_count": len(child_chunks)
                    }
                    preview_data["parent_segments"].append(segment_preview)
                
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": "层次化文档预览生成成功",
                        "preview_only": True,
                        "data": preview_data
                    }
                )
            
            # 实际处理文档
            result = await rag_service.process_document_hierarchical(
                file_path=file_path,
                file_name=file.filename,
                user_id=current_user.id,
                config=hierarchical_config
            )
            
            if result["success"]:
                logger.info(f"层次化文档处理成功: {result}")
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": result["message"],
                        "data": {
                            "doc_id": result["doc_id"],
                            "parent_segments_count": result["parent_segments_count"],
                            "child_chunks_count": result["child_chunks_count"],
                            "processing_time": result["processing_time"],
                            "hierarchical_config": hierarchical_config.dict()
                        }
                    }
                )
            else:
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "message": result["message"],
                        "error_code": "HIERARCHICAL_PROCESSING_FAILED"
                    }
                )
        
        finally:
            # 清理临时文件
            cleanup_temp_file(file_path)
    
    except Exception as e:
        logger.error(f"层次化上传文档失败: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"层次化上传文档失败: {str(e)}",
                "error_code": "HIERARCHICAL_UPLOAD_ERROR"
            }
        )


@router.post("/documents/search-hierarchical", response_model=DocumentSearchResponse)
async def search_documents_hierarchical(
    request: DocumentSearchRequest,
    score_threshold: float = 0.0,
    enable_parent_context: bool = True,
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    使用层次化架构搜索文档
    
    Args:
        request: 搜索请求
        score_threshold: 分数阈值
        enable_parent_context: 是否启用父段落上下文
        current_user: 当前用户
        rag_service: RAG服务
    """
    try:
        logger.info(f"用户 {current_user.email} 进行层次化搜索: {request.query}")
        
        # 检查RAG服务是否启用层次化处理
        if not rag_service.enable_hierarchical_processing:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "层次化搜索功能未启用，请联系管理员",
                    "results": []
                }
            )
        
        # 执行层次化搜索
        search_result = await rag_service.search_documents_hierarchical(
            query=request.query,
            user_id=current_user.id,
            top_k=request.top_k,
            search_all=request.search_all,
            score_threshold=score_threshold,
            enable_parent_context=enable_parent_context
        )
        
        if search_result["success"]:
            return JSONResponse(
                status_code=200,
                content=search_result
            )
        else:
            return JSONResponse(
                status_code=500,
                content=search_result
            )
    
    except Exception as e:
        logger.error(f"层次化搜索失败: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"层次化搜索失败: {str(e)}",
                "results": []
            }
        )


@router.get("/documents/{doc_id}/hierarchy")
async def get_document_hierarchy(
    doc_id: str = Path(..., description="文档ID"),
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    获取文档的层次结构信息
    """
    try:
        logger.info(f"用户 {current_user.email} 获取文档层次结构: {doc_id}")
        
        # 检查文档是否存在且属于当前用户
        doc_info = await rag_service.get_document_by_id(doc_id, current_user.id)
        if not doc_info:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "文档不存在或无权访问"
                }
            )
        
        # 获取层次结构
        from app.rag.hierarchical_processor import hierarchical_processor
        hierarchy = await hierarchical_processor.get_document_hierarchy(doc_id)
        
        if hierarchy:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "data": hierarchy
                }
            )
        else:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "未找到文档的层次结构，可能该文档未使用层次化处理"
                }
            )
    
    except Exception as e:
        logger.error(f"获取文档层次结构失败: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"获取文档层次结构失败: {str(e)}"
            }
        )


@router.post("/documents/search", response_model=DocumentSearchResponse)
async def search_documents(
    request: DocumentSearchRequest,
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
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
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
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
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
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
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service),
    llm_service: LLMService = Depends(get_llm_service)
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
async def check_rag_status(
    current_user: User = Depends(get_current_user),
    rag_pipeline: IRagPipeline = Depends(get_rag_pipeline)
):
    """
    检查RAG服务状态
    """
    try:
        # 使用新的组件化架构检查状态
        health_status = await rag_pipeline.health_check()

        # 检查各组件状态
        status = {
            "vector_store_available": health_status.get("retriever", False),
            "embedding_model_available": health_status.get("embedder", False),
            "retrieval_service_available": health_status.get("retriever", False),
            "document_loader_available": health_status.get("loader", False),
            "text_splitter_available": health_status.get("splitter", False),
            "generator_available": health_status.get("generator", False)
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
        if not status["generator_available"]:
            details.append("答案生成器不可用")

        # 构建响应消息
        message = "RAG服务正常" if available else "RAG服务不可用: " + ", ".join(details)

        # 获取流程统计信息
        pipeline_stats = rag_pipeline.get_pipeline_stats()

        # 构建服务器信息
        server_info = {
            "pipeline_stats": pipeline_stats,
            "component_health": health_status
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
                "retrieval_service_available": False,
                "document_loader_available": False,
                "text_splitter_available": False,
                "generator_available": False
            },
            "server_info": {}
        }

@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str = Path(..., description="文档ID"),
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
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
    current_user: User = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    获取文档切片的预览内容，包括父级内容和子切片内容
    """
    try:
        logger.info(f"===== 开始预览文档切片 =====")
        logger.info(f"用户: {current_user.email}")
        logger.info(f"文档ID: {document_id}")
        logger.info(f"切片索引: {slice_index}")
        
        # 首先尝试从预览缓存获取文档数据
        from app.services.preview_cache_service import preview_cache_service
        preview_data = None

        # 检查是否为预览模式的文档ID
        if document_id.startswith("preview_"):
            preview_data = preview_cache_service.get_preview_data(document_id)
            if not preview_data:
                logger.error(f"预览文档不存在或已过期: {document_id}")
                return DocumentSlicePreviewResponse(
                    success=False,
                    message="预览文档不存在或已过期，请重新生成预览"
                )

        # 如果不是预览模式，从数据库获取文档
        document = None
        if not preview_data:
            document = await rag_service.get_document_by_id(document_id)
            if not document:
                logger.error(f"文档不存在: {document_id}")
                return DocumentSlicePreviewResponse(
                    success=False,
                    message="文档不存在"
                )
        
        # 处理预览模式和正常模式的数据获取
        if preview_data:
            # 预览模式：从缓存数据获取信息
            file_name = preview_data["document"]["metadata"].get("file_name", "预览文档")
            document_content = preview_data["document"]["page_content"]
            segments_data = preview_data["segments"]

            logger.info(f"成功获取预览文档信息:")
            logger.info(f"- 文件名: {file_name}")
            logger.info(f"- 文档内容长度: {len(document_content)} 字符")
            logger.info(f"- 段落数量: {len(segments_data)}")

            # 转换为Document对象格式以保持兼容性
            from langchain.schema import Document
            segments = []
            for seg_data in segments_data:
                seg_doc = Document(
                    page_content=seg_data["page_content"],
                    metadata=seg_data["metadata"]
                )
                segments.append(seg_doc)

        else:
            # 正常模式：从向量存储获取真实段落
            logger.info(f"成功获取文档信息:")
            logger.info(f"- 文件名: {document.get('file_name', '未知')}")
            logger.info(f"- 文档ID: {document.get('id', '未知')}")
            logger.info(f"- 段落数量: {document.get('segments_count', 0)}")

            # 从向量存储中获取文档的真实段落
            segments = await rag_service.get_document_segments(document_id)

            if not segments:
                # 如果向量存储中没有数据，生成提示信息
                from langchain.schema import Document
                segments = [Document(
                    page_content=f"文档 '{document.get('file_name', '未知文件')}' 的段落数据未找到。可能原因：1) 文档正在处理中 2) 向量存储服务异常 3) 文档未正确上传",
                    metadata={
                        "doc_id": document_id,
                        "segment_index": 0,
                        "file_name": document.get("file_name", "未知文件"),
                        "error": "no_segments_found"
                    }
                )]
                logger.warning(f"文档 {document_id} 在向量存储中未找到段落数据")
            else:
                logger.info(f"从向量存储获取了 {len(segments)} 个真实段落")
        
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
        
        # 获取父级内容和子切片内容
        if preview_data:
            # 预览模式：从缓存数据获取
            parent_content = preview_data["document"]["page_content"]

            # 获取子切片内容：查找当前父切片对应的所有子切片
            children_content = []
            current_segment_id = current_segment.metadata.get("id")

            for seg_data in segments_data:
                seg_type = seg_data["metadata"].get("type")
                seg_parent_id = seg_data["metadata"].get("parent_id")

                if (seg_type == "child" and seg_parent_id == current_segment_id):
                    children_content.append(seg_data["page_content"])

            logger.info(f"\n=== 预览模式父级内容信息 ===")
            logger.info(f"- 内容长度: {len(parent_content)} 字符")
            logger.info(f"- 内容预览: {parent_content[:200]}...")
            logger.info(f"- 子切片数量: {len(children_content)}")

        else:
            # 正常模式：从数据库获取
            # 对于正常模式，我们需要从segments中获取内容
            if slice_index < len(segments):
                current_segment = segments[slice_index]
                parent_content = current_segment.page_content
                logger.info(f"\n=== 父级内容信息 ===")
                logger.info(f"- 内容长度: {len(parent_content)} 字符")
                logger.info(f"- 内容预览: {parent_content[:200]}...")

                # 获取子切片内容（当前切片的子切片）
                children_content = []
                if current_segment:
                    # 对于正常模式，我们简化处理，直接使用当前段落作为子内容
                    # 这是因为从向量存储获取的段落已经是处理后的最终段落
                    children_content = [current_segment.page_content]
                    logger.info(f"\n=== 子切片信息 ===")
                    logger.info(f"- 子切片数量: {len(children_content)}")
                    logger.info(f"- 内容长度: {len(children_content[0])} 字符")
                    logger.info(f"- 内容预览: {children_content[0][:200]}...")
            else:
                parent_content = ""
                children_content = []
        
        # 准备返回结果
        result_segments = []
        for i, segment in enumerate(segments):
            # 从元数据中获取段落类型，如果没有则根据是否有子段落来判断
            segment_type = segment.metadata.get("type", "parent")  # 默认为parent类型

            result_segments.append({
                "id": i,
                "content": segment.page_content,
                "start": segment.metadata.get("chunk_start", 0),
                "end": segment.metadata.get("chunk_end", len(segment.page_content)),
                "length": len(segment.page_content),
                "type": segment_type,
                "children": []  # 添加children字段以符合SegmentInfo模型
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