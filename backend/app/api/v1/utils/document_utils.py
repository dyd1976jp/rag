"""
文档处理工具模块

提供文档上传和处理的通用工具函数，用于减少API端点文件的复杂度。
"""

import os
import logging
import shutil
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import HTTPException
from app.rag.models import Document
from app.rag.document_splitter import ParentChildDocumentSplitter, Rule, SplitMode
import app.rag as rag

logger = logging.getLogger(__name__)

# 支持的文件类型
SUPPORTED_EXTENSIONS = ['.txt', '.pdf', '.md']


def validate_file_type(filename: str) -> tuple[bool, str]:
    """
    验证文件类型是否支持
    
    Args:
        filename: 文件名
        
    Returns:
        tuple: (是否支持, 文件扩展名)
    """
    file_ext = os.path.splitext(filename)[1].lower()
    is_supported = file_ext in SUPPORTED_EXTENSIONS
    return is_supported, file_ext


def save_uploaded_file(file, upload_dir: str = "data/uploads") -> str:
    """
    保存上传的文件到临时位置，支持中文文件名

    Args:
        file: 上传的文件对象
        upload_dir: 上传目录

    Returns:
        str: 保存的文件路径
    """
    try:
        os.makedirs(upload_dir, exist_ok=True)

        # 安全处理文件名，避免编码问题
        filename = file.filename
        if not filename:
            filename = f"upload_{uuid.uuid4().hex[:8]}.tmp"

        # 确保文件名是有效的UTF-8字符串
        try:
            filename.encode('utf-8')
        except UnicodeEncodeError:
            # 如果文件名包含无法编码的字符，生成一个安全的文件名
            file_ext = os.path.splitext(filename)[1] if '.' in filename else ''
            filename = f"upload_{uuid.uuid4().hex[:8]}{file_ext}"
            logger.warning(f"文件名包含无法编码的字符，已重命名为: {filename}")

        file_path = os.path.join(upload_dir, filename)

        # 如果文件已存在，添加时间戳避免冲突
        if os.path.exists(file_path):
            name, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}{ext}"
            file_path = os.path.join(upload_dir, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"文件已保存到临时位置: {file_path}")
        return file_path

    except Exception as e:
        logger.error(f"保存上传文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")


def process_document_by_type(file_path: str, filename: str, metadata: Dict[str, Any]) -> Document:
    """
    根据文件类型处理文档
    
    Args:
        file_path: 文件路径
        filename: 文件名
        metadata: 元数据
        
    Returns:
        Document: 处理后的文档对象
    """
    file_ext = os.path.splitext(filename)[1].lower()
    
    if file_ext == '.pdf':
        logger.info(f"处理PDF文件: {filename}")
        return rag.pdf_processor.process_pdf(file_path, metadata)
    else:
        # 处理文本文件
        logger.info(f"处理文本文件: {filename}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Document(page_content=content, metadata=metadata)


def create_split_rule(
    parent_chunk_size: int = 1024,
    parent_chunk_overlap: int = 200,
    parent_separator: str = "\n\n",
    child_chunk_size: int = 512,
    child_chunk_overlap: int = 50,
    child_separator: str = "\n"
) -> Rule:
    """
    创建文档分割规则
    
    Args:
        parent_chunk_size: 父块分段最大长度
        parent_chunk_overlap: 父块重叠长度
        parent_separator: 父块分段标识符
        child_chunk_size: 子块分段最大长度
        child_chunk_overlap: 子块重叠长度
        child_separator: 子块分段标识符
        
    Returns:
        Rule: 分割规则对象
    """
    return Rule(
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


def format_preview_response(segments: List, cleaned_document: Document, doc_id: str = None) -> Dict[str, Any]:
    """
    格式化预览响应数据

    Args:
        segments: 分割后的段落列表
        cleaned_document: 清洗后的文档
        doc_id: 文档ID，用于预览模式的子块查询

    Returns:
        Dict: 格式化的响应数据
    """
    if not segments:
        return {
            "success": False,
            "message": "文档分割后未产生有效内容"
        }

    # 如果没有提供doc_id，生成一个临时ID用于预览
    if not doc_id:
        import uuid
        doc_id = f"preview_{uuid.uuid4()}"
    # 如果已经提供了doc_id，直接使用（调用方已经确保格式正确）

    # 使用与API方式一致的平铺结构格式化
    result_segments = []
    children_content = []

    # 直接处理所有段落，保持与API方式一致的平铺结构
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

    return {
        "success": True,
        "preview_mode": True,  # 添加预览模式标识
        "doc_id": doc_id,  # 添加doc_id到响应中
        "segments": result_segments,
        "total_segments": len(result_segments),
        "parentContent": cleaned_document.page_content,
        "childrenContent": children_content
    }


def cleanup_temp_file(file_path: str) -> None:
    """
    清理临时文件
    
    Args:
        file_path: 文件路径
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"临时文件已删除: {file_path}")
    except Exception as e:
        logger.warning(f"删除临时文件失败: {file_path}, 错误: {e}")


def log_document_info(doc_id: str, filename: str, cleaned_document: Document) -> None:
    """
    记录文档信息日志
    
    Args:
        doc_id: 文档ID
        filename: 文件名
        cleaned_document: 清洗后的文档
    """
    logger.info(f"\n=== 原始文档信息 ===")
    logger.info(f"文件名: {filename}")
    logger.info(f"文档ID: {doc_id}")
    logger.info(f"文档内容前100字符: {cleaned_document.page_content[:100]}")
    logger.info(f"总字符数: {len(cleaned_document.page_content)}")


def log_split_statistics(segments: List) -> None:
    """
    记录分割统计信息
    
    Args:
        segments: 分割后的段落列表
    """
    logger.info(f"\n=== 分割统计 ===")
    logger.info(f"总段落数: {len(segments)}")
    
    if segments:
        segment_lengths = [len(s.page_content) for s in segments]
        avg_length = sum(segment_lengths) / len(segment_lengths)
        logger.info(f"平均段落长度: {avg_length:.2f} 字符")
        logger.info(f"最短段落长度: {min(segment_lengths)} 字符")
        logger.info(f"最长段落长度: {max(segment_lengths)} 字符")
