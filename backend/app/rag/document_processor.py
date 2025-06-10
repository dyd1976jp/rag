import re
import os
import logging
import string
import unicodedata
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import hashlib

logger = logging.getLogger(__name__)

class Document:
    """
    文档类，表示一个可以被处理的文本文档
    """
    def __init__(self, page_content: str, metadata: Dict[str, Any] = None):
        self.page_content = page_content
        self.metadata = metadata or {}
        
    def __str__(self) -> str:
        return f"Document(content_length={len(self.page_content)}, metadata={self.metadata})"

class DocumentProcessor:
    """
    文档处理器，提供文档处理功能
    """
    def __init__(self):
        self.stop_words = set()
        self.punctuation_translator = str.maketrans('', '', string.punctuation)
        self.min_content_length = int(os.environ.get("DOC_MIN_CONTENT_LENGTH", "10"))
        self.max_content_length = int(os.environ.get("DOC_MAX_CONTENT_LENGTH", "100000"))
        
        # 缓存配置
        self.use_cache = os.environ.get("DOC_USE_CACHE", "true").lower() == "true"
        self.cache_dir = os.environ.get("DOC_CACHE_DIR", "data/cache")
        
        # 确保缓存目录存在
        if self.use_cache:
            os.makedirs(self.cache_dir, exist_ok=True)
            
        # 加载停用词（如果有）
        self._load_stop_words()
        
        logger.info(f"初始化文档处理器: 最小内容长度={self.min_content_length}, 最大内容长度={self.max_content_length}")
        logger.info(f"缓存设置: 启用={self.use_cache}, 缓存目录={self.cache_dir}")
        
    def _load_stop_words(self):
        """加载停用词"""
        try:
            stop_words_file = os.environ.get("STOP_WORDS_FILE", "data/stop_words.txt")
            if os.path.exists(stop_words_file):
                with open(stop_words_file, 'r', encoding='utf-8') as f:
                    self.stop_words = set(line.strip() for line in f if line.strip())
                logger.info(f"加载了 {len(self.stop_words)} 个停用词")
            else:
                logger.info(f"停用词文件 {stop_words_file} 不存在，跳过加载")
        except Exception as e:
            logger.error(f"加载停用词失败: {str(e)}")
    
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
        清洗文档，去除无用信息
        
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
        
        # 规范化Unicode字符
        content = unicodedata.normalize('NFKC', content)
        
        # 替换多个连续空白字符为单个空格
        content = re.sub(r'\s+', ' ', content)
        
        # 删除控制字符
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
        
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