"""PDF文档处理器"""

import logging
import io
from typing import Dict, Any
import pypdfium2
from .document_processor import Document
from .cleaner.clean_processor import CleanProcessor

class PDFProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def process_pdf(self, pdf_file_path: str, metadata: Dict[str, Any]) -> Document:
        """处理PDF文件并返回文档对象"""
        try:
            self.logger.info(f"开始处理PDF文件: {pdf_file_path}")
            text = self._extract_text_from_pdf(pdf_file_path)
            
            # 创建文档对象
            document = Document(
                page_content=text,
                metadata=metadata
            )
            
            self.logger.info(f"PDF处理完成: {pdf_file_path}, 文本长度: {len(text)}")
            return document
        except Exception as e:
            self.logger.error(f"PDF处理失败: {str(e)}")
            raise
    
    def process_pdf_bytes(self, pdf_bytes: bytes, metadata: Dict[str, Any]) -> Document:
        """处理PDF字节数据并返回文档对象"""
        try:
            self.logger.info("开始处理PDF字节数据")
            text = self._extract_text_from_pdf_bytes(pdf_bytes)
            
            # 创建文档对象
            document = Document(
                page_content=text,
                metadata=metadata
            )
            
            self.logger.info(f"PDF字节数据处理完成, 文本长度: {len(text)}")
            return document
        except Exception as e:
            self.logger.error(f"PDF字节数据处理失败: {str(e)}")
            raise
    
    def _extract_text_from_pdf(self, pdf_file_path: str) -> str:
        """从PDF文件中提取文本"""
        try:
            # 使用pypdfium2打开PDF文件
            pdf_document = pypdfium2.PdfDocument(pdf_file_path)
            text_parts = []
            
            try:
                # 逐页提取文本
                for page in pdf_document:
                    text_page = page.get_textpage()
                    content = text_page.get_text_range()
                    text_page.close()
                    page.close()
                    
                    # 清理文本
                    content = CleanProcessor.clean(content)
                    if content.strip():
                        text_parts.append(content)
            finally:
                pdf_document.close()
                
            # 使用双换行符连接页面文本
            return "\n\n".join(text_parts)
            
        except Exception as e:
            self.logger.error(f"提取PDF文本失败: {str(e)}")
            raise
            
    def _extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """从PDF字节数据中提取文本"""
        try:
            # 将字节数据转换为文件对象
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_document = pypdfium2.PdfDocument(pdf_file, autoclose=True)
            text_parts = []
            
            try:
                # 逐页提取文本
                for page in pdf_document:
                    text_page = page.get_textpage()
                    content = text_page.get_text_range()
                    text_page.close()
                    page.close()
                    
                    # 清理文本
                    content = CleanProcessor.clean(content)
                    if content.strip():
                        text_parts.append(content)
            finally:
                pdf_document.close()
                
            # 使用双换行符连接页面文本
            return "\n\n".join(text_parts)
            
        except Exception as e:
            self.logger.error(f"提取PDF字节数据文本失败: {str(e)}")
            raise

# 创建一个默认的处理器实例
_default_processor = PDFProcessor()

def process_pdf(pdf_file_path: str, metadata: Dict[str, Any] = None) -> Document:
    """
    处理PDF文件的便捷函数
    
    Args:
        pdf_file_path: PDF文件路径
        metadata: 可选的元数据
    
    Returns:
        Document: 处理后的文档对象
    """
    if metadata is None:
        metadata = {}
    return _default_processor.process_pdf(pdf_file_path, metadata)

def process_pdf_bytes(pdf_bytes: bytes, metadata: Dict[str, Any] = None) -> Document:
    """
    处理PDF字节数据的便捷函数
    
    Args:
        pdf_bytes: PDF文件的字节数据
        metadata: 可选的元数据
    
    Returns:
        Document: 处理后的文档对象
    """
    if metadata is None:
        metadata = {}
    return _default_processor.process_pdf_bytes(pdf_bytes, metadata) 