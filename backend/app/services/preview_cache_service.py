"""
预览缓存服务

用于管理文档预览模式下的临时数据缓存，支持子块预览功能。
"""

import json
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

import logging
logger = logging.getLogger(__name__)


class PreviewCacheService:
    """预览缓存服务类"""
    
    def __init__(self, cache_dir: str = "data/cache", ttl_hours: int = 24):
        """
        初始化预览缓存服务
        
        Args:
            cache_dir: 缓存目录
            ttl_hours: 缓存过期时间（小时）
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_hours * 3600
        
    def _get_cache_file_path(self, doc_id: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{doc_id}.json"
    
    def _is_cache_expired(self, cache_data: Dict) -> bool:
        """检查缓存是否过期"""
        if "created_at" not in cache_data:
            return True
            
        created_at = datetime.fromisoformat(cache_data["created_at"])
        return datetime.now() - created_at > timedelta(seconds=self.ttl_seconds)
    
    def store_preview_data(self, doc_id: str, segments: List, cleaned_document: Any, split_params: Dict = None) -> bool:
        """
        存储预览数据到缓存

        Args:
            doc_id: 文档ID
            segments: 分割后的段落列表
            cleaned_document: 清洗后的文档
            split_params: 切割参数字典

        Returns:
            bool: 是否存储成功
        """
        try:
            # 准备缓存数据
            cache_data = {
                "doc_id": doc_id,
                "created_at": datetime.now().isoformat(),
                "document": {
                    "page_content": cleaned_document.page_content,
                    "metadata": cleaned_document.metadata
                },
                "segments": [],
                "split_params": split_params or {}  # 存储切割参数
            }
            
            # 处理段落数据，分离父块和子块
            parent_segments = []
            child_segments = []

            for i, segment in enumerate(segments):
                segment_data = {
                    "id": i,
                    "page_content": segment.page_content,
                    "metadata": segment.metadata,
                    "type": segment.metadata.get("type", "unknown")
                }

                if segment.metadata.get("type") == "parent":
                    parent_segments.append(segment_data)
                elif segment.metadata.get("type") == "child":
                    child_segments.append(segment_data)
                else:
                    # 未知类型，默认作为父块处理
                    segment_data["type"] = "parent"
                    parent_segments.append(segment_data)

                cache_data["segments"].append(segment_data)

            # 添加父子块统计信息
            cache_data["parent_count"] = len(parent_segments)
            cache_data["child_count"] = len(child_segments)
            
            # 写入缓存文件
            cache_file = self._get_cache_file_path(doc_id)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"预览数据已缓存: {doc_id}, 段落数: {len(segments)}")
            return True
            
        except Exception as e:
            logger.error(f"存储预览数据失败: {doc_id}, 错误: {e}")
            return False
    
    def get_preview_data(self, doc_id: str) -> Optional[Dict]:
        """
        获取预览数据
        
        Args:
            doc_id: 文档ID
            
        Returns:
            Dict: 预览数据，如果不存在或过期则返回None
        """
        try:
            cache_file = self._get_cache_file_path(doc_id)
            
            if not cache_file.exists():
                logger.debug(f"预览缓存文件不存在: {doc_id}")
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 检查是否过期
            if self._is_cache_expired(cache_data):
                logger.debug(f"预览缓存已过期: {doc_id}")
                self.remove_preview_data(doc_id)
                return None
            
            logger.debug(f"获取预览缓存数据: {doc_id}")
            return cache_data
            
        except Exception as e:
            logger.error(f"获取预览数据失败: {doc_id}, 错误: {e}")
            return None
    
    def get_preview_segments(self, doc_id: str) -> Optional[List]:
        """
        获取预览文档的段落列表
        
        Args:
            doc_id: 文档ID
            
        Returns:
            List: 段落列表，如果不存在则返回None
        """
        cache_data = self.get_preview_data(doc_id)
        if cache_data:
            return cache_data.get("segments", [])
        return None

    def get_preview_split_params(self, doc_id: str) -> Optional[Dict]:
        """
        获取预览文档的切割参数

        Args:
            doc_id: 文档ID

        Returns:
            Dict: 切割参数，如果不存在则返回None
        """
        cache_data = self.get_preview_data(doc_id)
        if cache_data:
            return cache_data.get("split_params", {})
        return None

    def get_preview_segment(self, doc_id: str, segment_id: int) -> Optional[Dict]:
        """
        获取预览文档的特定段落
        
        Args:
            doc_id: 文档ID
            segment_id: 段落ID
            
        Returns:
            Dict: 段落数据，如果不存在则返回None
        """
        segments = self.get_preview_segments(doc_id)
        if segments and 0 <= segment_id < len(segments):
            return segments[segment_id]
        return None
    
    def remove_preview_data(self, doc_id: str) -> bool:
        """
        删除预览数据
        
        Args:
            doc_id: 文档ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            cache_file = self._get_cache_file_path(doc_id)
            if cache_file.exists():
                cache_file.unlink()
                logger.debug(f"预览缓存已删除: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除预览数据失败: {doc_id}, 错误: {e}")
            return False
    
    def cleanup_expired_cache(self) -> int:
        """
        清理过期的缓存文件
        
        Returns:
            int: 清理的文件数量
        """
        cleaned_count = 0
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    
                    if self._is_cache_expired(cache_data):
                        cache_file.unlink()
                        cleaned_count += 1
                        logger.debug(f"清理过期缓存: {cache_file.name}")
                        
                except Exception as e:
                    logger.warning(f"清理缓存文件失败: {cache_file}, 错误: {e}")
                    
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
            
        if cleaned_count > 0:
            logger.info(f"清理了 {cleaned_count} 个过期缓存文件")
            
        return cleaned_count


# 全局预览缓存服务实例
preview_cache_service = PreviewCacheService()
