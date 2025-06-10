import re
from abc import ABC, abstractmethod
from typing import List, Optional, Iterable, Callable, Any
import copy
from .models import Document
import logging

logger = logging.getLogger(__name__)

class TextSplitter(ABC):
    """文本分割器基类"""
    
    def __init__(
        self,
        chunk_size: int = 4000,
        chunk_overlap: int = 200,
        length_function: Optional[Callable[[List[str]], List[int]]] = None,
        keep_separator: bool = False,
        add_start_index: bool = False
    ):
        """初始化分割器
        
        Args:
            chunk_size: 每个块的最大字符数
            chunk_overlap: 块之间的重叠字符数
            length_function: 计算文本长度的函数
            keep_separator: 是否保留分隔符
            add_start_index: 是否添加起始索引
        """
        if chunk_overlap > chunk_size:
            raise ValueError(f"重叠大小({chunk_overlap})大于块大小({chunk_size})")
            
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._length_function = length_function or (lambda x: [len(text) for text in x] if x else [0])
        self._keep_separator = keep_separator
        self._add_start_index = add_start_index
        
    def split_documents(self, documents: Iterable[Document]) -> List[Document]:
        """切割文档列表"""
        texts, metadatas = [], []
        for doc in documents:
            texts.append(doc.page_content)
            metadatas.append(doc.metadata or {})
        return self.create_documents(texts, metadatas=metadatas)
        
    def create_documents(self, texts: List[str], metadatas: Optional[List[dict]] = None) -> List[Document]:
        """从文本创建文档"""
        _metadatas = metadatas or [{}] * len(texts)
        documents = []
        for i, text in enumerate(texts):
            for chunk in self.split_text(text):
                metadata = copy.deepcopy(_metadatas[i])
                new_doc = Document(page_content=chunk, metadata=metadata)
                documents.append(new_doc)
        return documents
        
    @abstractmethod
    def split_text(self, text: str) -> List[str]:
        """分割文本，需要由子类实现"""
        pass

class RecursiveCharacterTextSplitter(TextSplitter):
    """递归字符文本分割器"""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
        keep_separator: bool = True,
        length_function: Optional[Callable[[List[str]], List[int]]] = None
    ):
        """初始化分割器"""
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=length_function,
            keep_separator=keep_separator
        )
        self._separators = separators or ["\n\n", "\n", "。", "！", "？", ". ", " ", ""]
        
    def split_text(self, text: str) -> List[str]:
        """分割文本"""
        try:
            logger.debug(f"开始分割文本，长度: {len(text)}")
            return self._split_text(text, self._separators)
        except Exception as e:
            logger.error(f"分割文本时出错: {str(e)}")
            raise
        
    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """递归分割文本"""
        try:
            final_chunks = []
            separator = separators[-1]
            new_separators = []
            
            # 找到第一个存在于文本中的分隔符
            for i, _s in enumerate(separators):
                if _s == "":
                    separator = _s
                    break
                if _s in text:
                    separator = _s
                    new_separators = separators[i + 1:]
                    break
                    
            logger.debug(f"使用分隔符: '{separator}'")
            
            # 使用找到的分隔符进行分割
            if separator:
                if separator == " ":
                    splits = text.split()
                else:
                    splits = text.split(separator)
            else:
                splits = list(text)
                
            splits = [s for s in splits if s.strip()]
            logger.debug(f"分割得到 {len(splits)} 个部分")
            
            _good_splits = []
            _good_splits_lengths = []  # 缓存分割部分的长度
            _separator = "" if not self._keep_separator else separator
            
            if not splits:
                logger.warning("分割后没有有效的文本部分")
                return []
                
            s_lens = self._length_function(splits)
            logger.debug(f"各部分长度: {s_lens}")
            
            for s, s_len in zip(splits, s_lens):
                if s_len < self._chunk_size:
                    _good_splits.append(s)
                    _good_splits_lengths.append(s_len)
                else:
                    if _good_splits:
                        merged_text = self._merge_splits(_good_splits, _separator, _good_splits_lengths)
                        final_chunks.extend(merged_text)
                        _good_splits = []
                        _good_splits_lengths = []
                    if not new_separators:
                        final_chunks.append(s)
                    else:
                        other_info = self._split_text(s, new_separators)
                        final_chunks.extend(other_info)
                        
            if _good_splits:
                merged_text = self._merge_splits(_good_splits, _separator, _good_splits_lengths)
                final_chunks.extend(merged_text)
                
            logger.debug(f"最终生成 {len(final_chunks)} 个块")
            return final_chunks
            
        except Exception as e:
            logger.error(f"递归分割文本时出错: {str(e)}")
            raise
        
    def _merge_splits(self, splits: List[str], separator: str, lengths: List[int]) -> List[str]:
        """合并分割部分"""
        try:
            if not splits:
                logger.warning("没有要合并的文本部分")
                return []
                
            if not separator:
                logger.debug("没有分隔符")
                separator_len = 0
            else:
                try:
                    separator_len = self._length_function([separator])[0]
                    logger.debug(f"分隔符长度: {separator_len}")
                except (IndexError, ValueError) as e:
                    logger.warning(f"计算分隔符长度时出错: {str(e)}")
                    separator_len = 0
            
            docs = []
            current_doc = []
            total = 0
            
            for split, length in zip(splits, lengths):
                if total + length + (separator_len if current_doc else 0) > self._chunk_size:
                    if total > self._chunk_size:
                        logger.warning(f"创建了一个大小为{total}的块，超过了指定的大小{self._chunk_size}")
                    if current_doc:
                        doc = separator.join(current_doc)
                        if doc:
                            docs.append(doc)
                        # 保持重叠
                        while total > self._chunk_overlap or (
                            total + length + (separator_len if current_doc else 0) > self._chunk_size and total > 0
                        ):
                            if not current_doc:
                                break
                            try:
                                first_len = self._length_function([current_doc[0]])[0]
                            except (IndexError, ValueError) as e:
                                logger.warning(f"计算第一个文档长度时出错: {str(e)}")
                                first_len = 0
                            total -= first_len + (separator_len if len(current_doc) > 1 else 0)
                            current_doc = current_doc[1:]
                current_doc.append(split)
                total += length + (separator_len if current_doc else 0)
                
            if current_doc:
                doc = separator.join(current_doc)
                if doc:
                    docs.append(doc)
                    
            logger.debug(f"合并后生成 {len(docs)} 个文档")
            return docs
            
        except Exception as e:
            logger.error(f"合并分割部分时出错: {str(e)}")
            raise

class EnhanceRecursiveCharacterTextSplitter(RecursiveCharacterTextSplitter):
    """增强的递归字符文本分割器，支持不同的长度计算方式"""
    
    @classmethod
    def from_encoder(
        cls,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None,
        keep_separator: bool = True,
        length_function: Optional[Callable[[List[str]], List[int]]] = None,
        **kwargs: Any  # 添加额外参数支持
    ):
        """从编码器创建分割器"""
        return cls(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            keep_separator=keep_separator,
            length_function=length_function or (lambda x: [len(text) for text in x] if x else [0]),
            **kwargs  # 传递额外参数
        )

class FixedRecursiveCharacterTextSplitter(EnhanceRecursiveCharacterTextSplitter):
    """固定分隔符的递归文本分割器"""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        fixed_separator: str = "\n\n",
        separators: Optional[List[str]] = None,
        keep_separator: bool = True,
        length_function: Optional[Callable[[List[str]], List[int]]] = None
    ):
        """初始化分割器"""
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            keep_separator=keep_separator,
            length_function=length_function
        )
        self._fixed_separator = fixed_separator
        
    def split_text(self, text: str) -> List[str]:
        """分割文本"""
        # 首先使用固定分隔符分割
        if self._fixed_separator:
            chunks = text.split(self._fixed_separator)
            logger.debug(f"使用固定分隔符 '{self._fixed_separator}' 分割文本，得到 {len(chunks)} 个块")
        else:
            chunks = [text]
            logger.debug("没有固定分隔符，使用整个文本作为一个块")
            
        # 对每个块进行处理
        final_chunks = []
        chunks_lengths = self._length_function(chunks)
        logger.debug(f"块长度: {chunks_lengths}")
        
        for chunk, chunk_length in zip(chunks, chunks_lengths):
            if chunk_length > self._chunk_size:
                # 如果块太大，进行递归分割
                logger.debug(f"块长度 {chunk_length} 超过限制 {self._chunk_size}，进行递归分割")
                final_chunks.extend(self._split_text(chunk, self._separators))
            else:
                if chunk.strip():
                    logger.debug(f"添加长度为 {chunk_length} 的块")
                    final_chunks.append(chunk)
                    
        logger.debug(f"最终生成 {len(final_chunks)} 个块")
        return final_chunks