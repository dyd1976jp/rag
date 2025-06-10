"""基础提取器接口"""

from abc import ABC, abstractmethod
from typing import List
from ..models import Document

class BaseExtractor(ABC):
    """文档提取器基类"""
    
    @abstractmethod
    def extract(self) -> List[Document]:
        """提取文档内容
        
        Returns:
            List[Document]: 提取的文档列表
        """
        pass 