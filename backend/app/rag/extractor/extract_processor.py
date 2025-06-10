"""文档提取处理器"""

import os
import logging
from typing import List, Optional, Union
from enum import Enum

from ..models import Document
from .pdf_extractor import PdfExtractor
from .unstructured_pdf_extractor import UnstructuredPDFExtractor

logger = logging.getLogger(__name__)

class ExtractMode(str, Enum):
    """提取模式"""
    BASIC = "basic"  # 基础模式，使用pypdfium2
    UNSTRUCTURED = "unstructured"  # 使用unstructured

class ExtractProcessor:
    """文档提取处理器"""
    
    # Unstructured API配置
    UNSTRUCTURED_API_URL = os.getenv("UNSTRUCTURED_API_URL", "")
    UNSTRUCTURED_API_KEY = os.getenv("UNSTRUCTURED_API_KEY", "")
    
    @classmethod
    def extract_pdf(
        cls,
        file_path: str,
        mode: str = ExtractMode.BASIC,
        cache_key: Optional[str] = None
    ) -> List[Document]:
        """提取PDF文档
        
        Args:
            file_path: PDF文件路径
            mode: 提取模式，默认使用basic模式
            cache_key: 缓存键
            
        Returns:
            List[Document]: 文档列表
        """
        try:
            logger.info(f"开始提取PDF文档: {file_path}, 模式: {mode}")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"PDF文件不存在: {file_path}")
                
            # 使用基础提取器
            extractor = PdfExtractor(
                file_path=file_path,
                file_cache_key=cache_key
            )
                
            # 提取文档
            documents = extractor.extract()
            
            logger.info(f"PDF文档提取完成: {file_path}, 生成了 {len(documents)} 个文档片段")
            return documents
            
        except Exception as e:
            logger.error(f"PDF文档提取失败: {str(e)}")
            raise 