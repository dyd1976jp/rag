"""使用unstructured的PDF提取器实现"""

import logging
from typing import List

from .extractor_base import BaseExtractor
from ..models import Document

logger = logging.getLogger(__name__)

class UnstructuredPDFExtractor(BaseExtractor):
    """使用unstructured的PDF提取器
    
    Args:
        file_path: PDF文件路径
        api_url: Unstructured API URL
        api_key: Unstructured API Key
    """
    
    def __init__(self, file_path: str, api_url: str = "", api_key: str = ""):
        """Initialize with file path."""
        self._file_path = file_path
        self._api_url = api_url
        self._api_key = api_key
        
    def extract(self) -> List[Document]:
        """提取PDF文档内容"""
        if self._api_url:
            from unstructured.partition.api import partition_via_api
            
            elements = partition_via_api(
                filename=self._file_path,
                api_url=self._api_url,
                api_key=self._api_key,
                strategy="auto"
            )
        else:
            from unstructured.partition.pdf import partition_pdf
            
            elements = partition_pdf(
                filename=self._file_path,
                strategy="auto"
            )
            
        from unstructured.chunking.title import chunk_by_title
        
        # 使用标题分块，最大字符数2000，合并小于2000字符的文本
        chunks = chunk_by_title(
            elements,
            max_characters=2000,
            combine_text_under_n_chars=2000
        )
        
        documents = []
        for chunk in chunks:
            text = chunk.text.strip()
            if text:
                documents.append(Document(
                    content=text,
                    metadata={
                        "source": self._file_path
                    }
                ))
        
        logger.info(f"成功提取PDF文件，共{len(documents)}个文档块")
        return documents 