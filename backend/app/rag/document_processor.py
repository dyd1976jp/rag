import re
import os
import logging
import string
import unicodedata
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import hashlib
from ..core.paths import (
    CACHE_DIR,
    RAW_DATA_DIR
)
from .models import Document  # 使用正确的 Pydantic Document 类

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    文档处理器，提供文档处理功能
    """
    def __init__(self):
        """初始化文档处理器"""
        self.max_content_length = int(os.environ.get("DOC_MAX_CONTENT_LENGTH", "100000"))
        self.min_content_length = int(os.environ.get("DOC_MIN_CONTENT_LENGTH", "10"))
        self.cache_enabled = os.environ.get("DOC_CACHE_ENABLED", "true").lower() == "true"
        self.use_cache = self.cache_enabled  # 为了向后兼容，添加这个别名
        self.cache_dir = os.environ.get("DOC_CACHE_DIR", "data/cache")

        # 初始化停用词和标点符号翻译器
        self.stop_words = set(['的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'])
        self.punctuation_translator = str.maketrans('', '', string.punctuation + '，。！？；：""''（）【】《》')

        # 创建缓存目录
        if self.cache_enabled:
            os.makedirs(self.cache_dir, exist_ok=True)

        logger.info(f"初始化文档处理器: 最大内容长度={self.max_content_length}, 最小内容长度={self.min_content_length}, 缓存启用={self.cache_enabled}")
        
    def process_document(self, document: Document) -> Document:
        """处理文档
        
        Args:
            document: 待处理的文档
            
        Returns:
            处理后的文档
        """
        # 检查文档内容长度
        if len(document.page_content.strip()) > self.max_content_length:
            logger.warning(f"文档内容超过最大长度限制: {len(document.page_content)} > {self.max_content_length}")
            document.page_content = document.page_content[:self.max_content_length]
            
        return document
    
    def validate_document(self, document: Document) -> bool:
        """
        验证文档是否有效
        
        Args:
            document: 要验证的文档
            
        Returns:
            文档是否有效
        """
        # 检查内容是否为空
        if not document or not document.page_content or len(document.page_content.strip()) == 0:
            logger.warning("文档内容为空")
            return False
            
        # 检查内容是否过短
        if len(document.page_content.strip()) < self.min_content_length:
            logger.warning(f"文档内容过短: {len(document.page_content.strip())} 字符")
            return False
            
        # 检查必要的元数据
        required_metadata = ["doc_id", "document_id"]
        for field in required_metadata:
            if field not in document.metadata:
                logger.warning(f"文档缺少必要的元数据字段: {field}")
                return False
                
        return True
        
    def clean_document(self, document: Document) -> Document:
        """
        清洗文档，去除无用信息，保持文档格式

        Args:
            document: 要清洗的文档

        Returns:
            清洗后的文档
        """
        # 尝试从缓存获取清洗结果
        if self.use_cache:
            cache_key = self._get_cache_key(document)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                logger.info(f"从缓存获取清洗结果: {cache_key}")
                return cached_result

        # 获取原始内容
        content = document.page_content

        # 规范化Unicode字符（使用NFC而不是NFKC，避免改变标点符号）
        content = unicodedata.normalize('NFC', content)

        # 删除控制字符，但保留换行符和制表符
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)

        # 规范化空白字符，但保持换行符结构
        # 将多个连续空格替换为单个空格，但保留换行符
        content = re.sub(r'[ \t]+', ' ', content)  # 只处理空格和制表符

        # 清理多余的空行（超过2个连续换行符的情况）
        content = re.sub(r'\n{3,}', '\n\n', content)

        # 清理行首行尾的空格
        lines = content.split('\n')
        lines = [line.strip() for line in lines]
        content = '\n'.join(lines)

        # 截断过长的内容
        if len(content) > self.max_content_length:
            logger.info(f"文档内容过长，截断为 {self.max_content_length} 字符")
            content = content[:self.max_content_length]

        # 创建新的Document对象
        cleaned_doc = Document(
            page_content=content.strip(),
            metadata=document.metadata.copy()
        )

        # 添加清洗时间到元数据
        cleaned_doc.metadata["cleaned_at"] = datetime.now().isoformat()

        # 缓存清洗结果
        if self.use_cache:
            self._save_to_cache(cache_key, cleaned_doc)

        return cleaned_doc
        
    def extract_keywords(self, document: Document, max_keywords: int = 10) -> List[str]:
        """
        从文档中提取关键词
        
        Args:
            document: 文档
            max_keywords: 最大关键词数量
            
        Returns:
            关键词列表
        """
        # 获取文档内容
        content = document.page_content.lower()
        
        # 移除标点符号
        content = content.translate(self.punctuation_translator)
        
        # 分词
        words = content.split()
        
        # 过滤停用词
        words = [word for word in words if word not in self.stop_words and len(word) > 1]
        
        # 统计词频
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
            
        # 按词频排序并截取前N个
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:max_keywords]
        
        return [keyword for keyword, _ in keywords]
    
    def _get_cache_key(self, document: Document) -> str:
        """生成缓存键"""
        # 使用内容和文档ID的哈希值作为缓存键
        content_hash = hashlib.md5(document.page_content.encode('utf-8')).hexdigest()
        doc_id = document.metadata.get("doc_id", "unknown")
        return f"{doc_id}_{content_hash}"
    
    def _get_cache_path(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")
    
    def _get_from_cache(self, cache_key: str) -> Optional[Document]:
        """从缓存获取文档"""
        try:
            cache_path = self._get_cache_path(cache_key)
            if os.path.exists(cache_path):
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return Document(
                        page_content=data['page_content'],
                        metadata=data['metadata']
                    )
            return None
        except Exception as e:
            logger.warning(f"从缓存获取文档失败: {str(e)}")
            return None
    
    def _save_to_cache(self, cache_key: str, document: Document) -> bool:
        """保存文档到缓存"""
        try:
            cache_path = self._get_cache_path(cache_key)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'page_content': document.page_content,
                    'metadata': document.metadata
                }, f, ensure_ascii=False)
            return True
        except Exception as e:
            logger.warning(f"保存文档到缓存失败: {str(e)}")
            return False 