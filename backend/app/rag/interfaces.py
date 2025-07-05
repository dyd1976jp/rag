"""
RAG组件接口定义

本模块定义RAG流程中各个组件的抽象接口，确保组件的可替换性和可测试性。
使用Protocol和ABC来定义接口，支持类型检查和运行时验证。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, Protocol, runtime_checkable
from pydantic import BaseModel
from pathlib import Path

# ============================================================================
# 数据模型
# ============================================================================

class DocumentChunk(BaseModel):
    """文档块数据模型"""
    content: str
    metadata: Dict[str, Any] = {}
    chunk_id: Optional[str] = None
    parent_id: Optional[str] = None
    vector: Optional[List[float]] = None

class Document(BaseModel):
    """文档数据模型"""
    content: str
    metadata: Dict[str, Any] = {}
    doc_id: Optional[str] = None
    file_path: Optional[str] = None

class RetrievalResult(BaseModel):
    """检索结果数据模型"""
    content: str
    score: float
    metadata: Dict[str, Any] = {}
    chunk_id: Optional[str] = None

class GenerationResult(BaseModel):
    """生成结果数据模型"""
    answer: str
    sources: List[RetrievalResult] = []
    metadata: Dict[str, Any] = {}

# ============================================================================
# 组件接口定义
# ============================================================================

@runtime_checkable
class IDocumentLoader(Protocol):
    """文档加载器接口"""
    
    async def load_document(self, file_path: Union[str, Path]) -> Document:
        """
        加载文档
        
        Args:
            file_path: 文档文件路径
            
        Returns:
            Document: 加载的文档对象
        """
        ...
    
    def supports_format(self, file_extension: str) -> bool:
        """
        检查是否支持指定格式
        
        Args:
            file_extension: 文件扩展名
            
        Returns:
            bool: 是否支持该格式
        """
        ...

@runtime_checkable
class ITextSplitter(Protocol):
    """文本分割器接口"""
    
    async def split_document(self, document: Document) -> List[DocumentChunk]:
        """
        分割文档为块
        
        Args:
            document: 要分割的文档
            
        Returns:
            List[DocumentChunk]: 分割后的文档块列表
        """
        ...
    
    def configure(self, **kwargs) -> None:
        """
        配置分割器参数
        
        Args:
            **kwargs: 配置参数
        """
        ...

@runtime_checkable
class IEmbedder(Protocol):
    """向量嵌入器接口"""
    
    async def embed_text(self, text: str) -> List[float]:
        """
        对单个文本进行向量化
        
        Args:
            text: 要向量化的文本
            
        Returns:
            List[float]: 向量表示
        """
        ...
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        对多个文本进行批量向量化
        
        Args:
            texts: 要向量化的文本列表
            
        Returns:
            List[List[float]]: 向量表示列表
        """
        ...
    
    @property
    def dimension(self) -> int:
        """获取向量维度"""
        ...

@runtime_checkable
class IRetriever(Protocol):
    """文档检索器接口"""
    
    async def retrieve(
        self, 
        query: str, 
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            filters: 过滤条件
            
        Returns:
            List[RetrievalResult]: 检索结果列表
        """
        ...
    
    async def add_documents(self, chunks: List[DocumentChunk]) -> bool:
        """
        添加文档到检索索引
        
        Args:
            chunks: 要添加的文档块列表
            
        Returns:
            bool: 是否成功
        """
        ...

@runtime_checkable
class IGenerator(Protocol):
    """答案生成器接口"""
    
    async def generate(
        self,
        query: str,
        context: List[RetrievalResult],
        **kwargs
    ) -> GenerationResult:
        """
        基于查询和上下文生成答案
        
        Args:
            query: 用户查询
            context: 检索到的上下文
            **kwargs: 其他生成参数
            
        Returns:
            GenerationResult: 生成结果
        """
        ...
    
    def configure(self, **kwargs) -> None:
        """
        配置生成器参数
        
        Args:
            **kwargs: 配置参数
        """
        ...

@runtime_checkable
class IRagPipeline(Protocol):
    """RAG流程管道接口"""
    
    async def process_document(
        self,
        file_path: Union[str, Path],
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理文档的完整流程
        
        Args:
            file_path: 文档路径
            user_id: 用户ID
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        ...
    
    async def query(
        self,
        question: str,
        user_id: str,
        **kwargs
    ) -> GenerationResult:
        """
        查询的完整流程
        
        Args:
            question: 用户问题
            user_id: 用户ID
            **kwargs: 其他参数
            
        Returns:
            GenerationResult: 查询结果
        """
        ...

# ============================================================================
# 抽象基类（用于具体实现继承）
# ============================================================================

class BaseDocumentLoader(ABC):
    """文档加载器抽象基类"""
    
    @abstractmethod
    async def load_document(self, file_path: Union[str, Path]) -> Document:
        pass
    
    @abstractmethod
    def supports_format(self, file_extension: str) -> bool:
        pass

class BaseTextSplitter(ABC):
    """文本分割器抽象基类"""
    
    @abstractmethod
    async def split_document(self, document: Document) -> List[DocumentChunk]:
        pass
    
    def configure(self, **kwargs) -> None:
        """默认配置实现"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

class BaseEmbedder(ABC):
    """向量嵌入器抽象基类"""
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        pass
    
    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        pass

class BaseRetriever(ABC):
    """文档检索器抽象基类"""
    
    @abstractmethod
    async def retrieve(
        self, 
        query: str, 
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        pass
    
    @abstractmethod
    async def add_documents(self, chunks: List[DocumentChunk]) -> bool:
        pass

class BaseGenerator(ABC):
    """答案生成器抽象基类"""
    
    @abstractmethod
    async def generate(
        self,
        query: str,
        context: List[RetrievalResult],
        **kwargs
    ) -> GenerationResult:
        pass
    
    def configure(self, **kwargs) -> None:
        """默认配置实现"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

class BaseRagPipeline(ABC):
    """RAG流程管道抽象基类"""
    
    @abstractmethod
    async def process_document(
        self,
        file_path: Union[str, Path],
        user_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def query(
        self,
        question: str,
        user_id: str,
        **kwargs
    ) -> GenerationResult:
        pass
