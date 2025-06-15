"""PDF文档提取器实现"""

from collections.abc import Iterator
from typing import Optional, cast
import io
import logging

import pypdfium2

from .extractor_base import BaseExtractor
from ..models import Document
from ..cleaner.clean_processor import CleanProcessor

logger = logging.getLogger(__name__)

class PdfExtractor(BaseExtractor):
    """PDF文档提取器
    
    使用pypdfium2提取PDF文本内容
    
    Args:
        file_path: PDF文件路径
        file_cache_key: 可选的缓存键
    """
    
    def __init__(self, file_path: str, file_cache_key: Optional[str] = None):
        self._file_path = file_path
        self._file_cache_key = file_cache_key
        
    def extract(self) -> list[Document]:
        """提取PDF文档内容"""
        try:
            logger.info(f"开始提取PDF文档: {self._file_path}")
            
            # 打开PDF文件
            pdf_document = pypdfium2.PdfDocument(self._file_path)
            documents = []
            
            try:
                # 逐页提取文本
                for page_number, page in enumerate(pdf_document):
                    text_page = page.get_textpage()
                    content = text_page.get_text_range()
                    text_page.close()
                    page.close()
                    
                    # 清理文本
                    content = CleanProcessor.clean(content)
                    
                    if content.strip():
                        # 创建文档对象
                        doc = Document(
                            page_content=content,
                            metadata={
                                "source": self._file_path,
                                "page": page_number + 1  # 页码从1开始
                            }
                        )
                        documents.append(doc)
                        
            finally:
                pdf_document.close()
                
            logger.info(f"PDF文档提取完成: {self._file_path}, 共{len(documents)}页")
            return documents
            
        except Exception as e:
            logger.error(f"PDF文档提取失败: {str(e)}")
            raise 