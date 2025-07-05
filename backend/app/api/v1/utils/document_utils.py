"""
文档处理工具模块

提供文档上传和处理的通用工具函数，用于减少API端点文件的复杂度。
"""

import os
import logging
import shutil
import time
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


def format_unified_response(segments: List, cleaned_document: Document, doc_id: str = None, preview_mode: bool = True) -> Dict[str, Any]:
    """
    统一的文档切割响应格式化函数

    此函数用于统一预览模式和保存模式的API响应格式，确保用户体验的一致性。
    无论是预览还是保存，都返回相同格式的详细切割结果。

    Args:
        segments: 分割后的段落列表
        cleaned_document: 清洗后的文档
        doc_id: 文档ID
        preview_mode: 是否为预览模式

    Returns:
        Dict: 统一格式的响应数据，包含完整的文档切割详情
    """
    # 如果没有提供doc_id，生成一个临时ID
    if not doc_id:
        import uuid
        doc_id = f"preview_{uuid.uuid4()}" if preview_mode else str(uuid.uuid4())

    # 处理空段落的情况
    if not segments:
        return {
            "success": True,
            "message": "文档切割预览生成成功" if preview_mode else "文档切割处理成功",
            "preview_mode": preview_mode,
            "doc_id": doc_id,
            "total_segments": 0,
            "parent_segments": 0,
            "child_segments": 0,
            "parentContent": cleaned_document.page_content,
            "childrenContent": [],
            "segments": [],
            "document_overview": {
                "title": cleaned_document.metadata.get("title", "未命名文档"),
                "total_length": len(cleaned_document.page_content),
                "total_segments": 0,
                "parent_segments": 0,
                "child_segments": 0
            }
        }

    # 构建层级结构
    parent_segments = {}  # 存储父段落，按parent_id索引
    child_segments = {}   # 存储子段落，按parent_id分组
    children_content = []
    parent_counter = 0    # 父块连续ID计数器

    # 分析段落层级关系
    for segment in segments:
        segment_type = segment.metadata.get("type", "parent")
        parent_id = segment.metadata.get("parent_id")

        if segment_type == "parent" or parent_id is None:
            # 这是父段落
            # 获取段落ID，优先使用id属性，如果没有则使用doc_id，最后使用计数器
            segment_id = getattr(segment, 'id', None) or getattr(segment, 'doc_id', None) or segment.metadata.get("doc_id", str(parent_counter))

            parent_segments[segment_id] = {
                "id": parent_counter,  # 使用连续的ID
                "original_id": segment_id,  # 保留原始ID用于查找
                "content": segment.page_content,
                "start": segment.metadata.get("chunk_start", 0),
                "end": segment.metadata.get("chunk_end", len(segment.page_content)),
                "length": len(segment.page_content),
                "type": "parent",
                "children": []
            }

            # 处理父文档的子文档（如果存在）
            if hasattr(segment, 'children') and segment.children:
                child_segments[segment_id] = []
                for child_doc in segment.children:
                    child_segments[segment_id].append({
                        "id": len(children_content),  # 子段落的全局ID
                        "content": child_doc.page_content,
                        "start": 0,  # 子文档的起始位置
                        "end": len(child_doc.page_content),
                        "length": len(child_doc.page_content),
                        "type": "child",
                        "parent_id": segment_id
                    })
                    # 添加到全局子内容列表
                    children_content.append(child_doc.page_content)

            parent_counter += 1
        elif segment_type == "child" and parent_id is not None:
            # 这是独立的子段落（通过parent_id关联到父段落）
            if parent_id not in child_segments:
                child_segments[parent_id] = []

            child_segments[parent_id].append({
                "id": len(children_content),  # 子段落的全局ID
                "content": segment.page_content,
                "start": segment.metadata.get("chunk_start", 0),
                "end": segment.metadata.get("chunk_end", len(segment.page_content)),
                "length": len(segment.page_content),
                "type": "child",
                "parent_id": parent_id
            })
            # 添加到全局子内容列表
            children_content.append(segment.page_content)

    # 将子段落关联到父段落
    result_segments = []
    for original_parent_id, parent_info in parent_segments.items():
        # 添加子段落到父段落
        if original_parent_id in child_segments:
            parent_info["children"] = child_segments[original_parent_id]

        result_segments.append(parent_info)

    # 按ID排序以保持正确顺序
    result_segments.sort(key=lambda x: x["id"])

    # 构建统一的响应格式
    response = {
        "success": True,
        "message": "文档切割预览生成成功" if preview_mode else "文档切割处理成功",
        "preview_mode": preview_mode,
        "doc_id": doc_id,
        # 统计信息
        "total_segments": len(segments),
        "parent_segments": len(result_segments),
        "child_segments": len(children_content),
        # 详细内容 - 确保字段名与前端期望一致
        "parentContent": cleaned_document.page_content,  # 保持原有格式：完整文档内容
        "childrenContent": children_content,  # 所有子块内容列表
        "segments": result_segments,  # 层级结构的段落数组
        # 保留原有的document_overview结构以保持向后兼容
        "document_overview": {
            "title": cleaned_document.metadata.get("title", "未命名文档"),
            "total_length": len(cleaned_document.page_content),
            "total_segments": len(segments),
            "parent_segments": len(result_segments),
            "child_segments": len(children_content)
        }
    }

    return response


def format_enhanced_preview_response(
    segments: List,
    cleaned_document: Document,
    doc_id: str = None,
    processing_stats: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    增强的预览响应格式化函数

    提供更智能的预览内容优化和详细的处理统计信息
    修复：确保与传统处理器的响应格式完全一致

    Args:
        segments: 分割后的段落列表
        cleaned_document: 清洗后的文档
        doc_id: 文档ID
        processing_stats: 处理统计信息

    Returns:
        Dict: 增强的预览响应数据
    """
    # 修复：使用统一的响应格式化函数确保一致性
    response = format_unified_response(segments, cleaned_document, doc_id, preview_mode=True)

    # 添加增强的预览信息
    preview_info = {
        "is_optimized": True,
        "optimization_applied": [],
        "content_analysis": {},
        "quality_metrics": {}
    }

    # 内容分析
    total_content_length = len(cleaned_document.page_content)
    avg_segment_length = total_content_length / len(segments) if segments else 0

    preview_info["content_analysis"] = {
        "total_length": total_content_length,
        "avg_segment_length": int(avg_segment_length),
        "language_detected": "zh" if any('\u4e00' <= char <= '\u9fff' for char in cleaned_document.page_content[:100]) else "en",
        "estimated_reading_time": int(total_content_length / 500)  # 假设每分钟500字
    }

    # 质量指标
    non_empty_segments = [s for s in segments if s.page_content.strip()]
    preview_info["quality_metrics"] = {
        "segment_quality_score": len(non_empty_segments) / len(segments) if segments else 0,
        "content_density": total_content_length / len(segments) if segments else 0,
        "structure_preserved": True
    }

    # 检查是否应用了优化
    truncated_segments = sum(1 for s in segments if s.metadata.get("content_truncated", False))
    if truncated_segments > 0:
        preview_info["optimization_applied"].append("content_truncation")
        preview_info["truncated_segments"] = truncated_segments

    children_truncated = sum(1 for s in segments if s.metadata.get("children_truncated", False))
    if children_truncated > 0:
        preview_info["optimization_applied"].append("children_limitation")
        preview_info["children_truncated_segments"] = children_truncated

    # 添加处理统计信息
    if processing_stats:
        preview_info["processing_stats"] = processing_stats

    # 更新响应
    response["preview_info"] = preview_info
    response["message"] = "增强预览生成成功"

    return response


def format_preview_response(segments: List, cleaned_document: Document, doc_id: str = None) -> Dict[str, Any]:
    """
    格式化文档切割预览响应数据 - 向后兼容函数

    此函数现在调用统一的响应格式化函数，保持向后兼容性。

    Args:
        segments: 分割后的段落列表
        cleaned_document: 清洗后的文档
        doc_id: 文档ID，用于预览模式的子块查询

    Returns:
        Dict: 格式化的响应数据，包含完整文档的切割概览
    """
    return format_unified_response(segments, cleaned_document, doc_id, preview_mode=True)


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
