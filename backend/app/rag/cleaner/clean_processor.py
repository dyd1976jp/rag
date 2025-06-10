"""文本清理处理器模块"""

import re
import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class CleanLevel(str, Enum):
    """清理级别"""
    BASIC = "basic"  # 只处理无效字符和控制字符
    NORMAL = "normal"  # 基本清理 + 空白字符规范化
    FULL = "full"  # 完整清理，包括标点符号规范化

class CleanProcessor:
    """文本清理处理器"""
    
    @classmethod
    def clean(cls, text: str, level: CleanLevel = CleanLevel.FULL, process_rule: Optional[Dict[str, Any]] = None) -> str:
        """清理文本内容
        
        Args:
            text: 要清理的文本
            level: 清理级别
            process_rule: 处理规则
        """
        if not text:
            return ""
            
        # 1. 移除无效字符和控制字符
        text = cls._remove_invalid_chars(text)
        
        if level == CleanLevel.BASIC:
            return text.strip()
            
        # 2. 规范化空白字符和换行符
        text = cls._normalize_whitespace(text)
        
        if level == CleanLevel.NORMAL:
            return text.strip()
            
        # 3. 处理每一行
        text = cls._process_lines(text)
        
        # 4. 规范化标点符号
        text = cls._normalize_punctuation(text)
        
        return text.strip()
    
    @classmethod
    def clean_basic(cls, text: str) -> str:
        """只进行基本的清理（移除无效字符和控制字符）"""
        return cls.clean(text, level=CleanLevel.BASIC)
    
    @classmethod
    def clean_normal(cls, text: str) -> str:
        """进行普通级别的清理（包括空白字符规范化）"""
        return cls.clean(text, level=CleanLevel.NORMAL)
    
    @classmethod
    def _remove_invalid_chars(cls, text: str) -> str:
        """移除无效字符和控制字符"""
        # 移除HTML标记
        text = re.sub(r"<\|", "<", text)
        text = re.sub(r"\|>", ">", text)
        
        # 移除控制字符
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F\xEF\xBF\xBE]", "", text)
        
        # 移除特殊Unicode字符
        text = re.sub("\ufffe", "", text)  # Unicode U+FFFE
        
        # 移除其他特殊字符，保留中文、英文、数字和基本标点
        text = re.sub(r'[^\w\s\u4e00-\u9fff.,?!，。？！:：;；""''()（）\-]', '', text)
        
        return text
    
    @classmethod
    def _normalize_whitespace(cls, text: str) -> str:
        """规范化空白字符和换行符"""
        # 处理连续的换行符
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 处理各种空白字符
        text = re.sub(r'[\t\f\r\x20\u00a0\u1680\u180e\u2000-\u200a\u202f\u205f\u3000]{2,}', ' ', text)
        
        return text
    
    @classmethod
    def _process_lines(cls, text: str) -> str:
        """处理文本行"""
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
        
        return '\n'.join(lines)
    
    @classmethod
    def _normalize_punctuation(cls, text: str) -> str:
        """规范化标点符号"""
        # 统一省略号
        text = text.replace('...', '…')
        text = text.replace('。。。', '…')
        
        # 统一破折号
        text = text.replace('――', '—')
        text = text.replace('--', '—')
        
        # 统一引号
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r"['']", "'", text)
        
        # 移除重复的标点符号
        text = re.sub(r'([。，！？；：、])\1+', r'\1', text)
        
        return text 