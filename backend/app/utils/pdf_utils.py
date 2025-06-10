import os
import logging
from typing import Optional
import fitz  # PyMuPDF
from ..rag.cleaner.clean_processor import CleanProcessor

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path: str) -> str:
    """从PDF文件中提取文本内容"""
    try:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
            
        # 打开PDF文件
        doc = fitz.open(pdf_path)
        
        # 提取所有页面的文本
        text_content = []
        for page in doc:
            # 提取当前页面的文本
            text = page.get_text()
            if text.strip():
                text_content.append(text)
        
        # 关闭PDF文件
        doc.close()
        
        # 合并所有文本，使用双换行符分隔不同页面
        full_text = "\n\n".join(text_content)
        
        # 使用CleanProcessor清理文本
        cleaned_text = CleanProcessor.clean(full_text)
        
        return cleaned_text
        
    except Exception as e:
        logger.error(f"PDF文本提取失败: {str(e)}")
        raise

def clean_pdf_text(text: str) -> str:
    """清理从PDF提取的文本"""
    if not text:
        return ""
        
    # 1. 移除无效字符和控制字符
    text = re.sub(r"<\|", "<", text)
    text = re.sub(r"\|>", ">", text)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F\xEF\xBF\xBE]", "", text)
    text = re.sub("\ufffe", "", text)  # Unicode U+FFFE
    
    # 2. 规范化空白字符和换行符
    # 处理连续的换行符
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 处理各种空白字符
    text = re.sub(r'[\t\f\r\x20\u00a0\u1680\u180e\u2000-\u200a\u202f\u205f\u3000]{2,}', ' ', text)
    
    # 3. 处理每一行
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        # 跳过空行
        if not line:
            continue
        # 处理行尾的连字符
        if line.endswith('-'):
            line = line[:-1]
        # 处理行首的项目符号
        line = re.sub(r'^[\s•·○●◆▪-]+', '', line)
        lines.append(line)
    
    # 4. 合并行
    text = '\n'.join(lines)
    
    # 5. 规范化标点符号
    text = text.replace('...', '…')
    text = text.replace('。。。', '…')
    text = text.replace('――', '—')
    text = text.replace('--', '—')
    text = re.sub(r'["""]', '"', text)
    text = re.sub(r"['']", "'", text)
    
    # 6. 移除重复的标点符号
    text = re.sub(r'([。，！？；：、])\1+', r'\1', text)
    
    return text.strip() 