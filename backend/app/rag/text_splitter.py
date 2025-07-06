import re
import hashlib
from abc import ABC, abstractmethod
from typing import List, Optional, Iterable, Callable, Any, Dict
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
    """固定分隔符的递归文本分割器 - 增强版

    支持智能分割策略：
    - 内容类型自适应分割
    - 语义边界保持
    - 质量控制和优化
    - 多级分隔符策略
    - 支持强制分割模式
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        fixed_separator: str = "\n\n",
        separators: Optional[List[str]] = None,
        keep_separator: bool = True,
        length_function: Optional[Callable[[List[str]], List[int]]] = None,
        # 新增智能分割参数
        enable_smart_splitting: bool = True,
        content_type: Optional[str] = None,
        preserve_semantic_boundaries: bool = True,
        min_chunk_size: int = 50,
        max_chunk_size_ratio: float = 1.5,
        quality_threshold: float = 0.8,
        enable_content_analysis: bool = True,
        # 新增：强制分割参数
        force_split_on_separator: bool = False  # 是否强制按分隔符分割，不考虑chunk_size
    ):
        """初始化增强分割器

        Args:
            chunk_size: 目标块大小
            chunk_overlap: 块重叠大小
            fixed_separator: 固定分隔符
            separators: 递归分隔符列表
            keep_separator: 是否保留分隔符
            length_function: 长度计算函数
            enable_smart_splitting: 启用智能分割
            content_type: 内容类型 (academic, news, dialogue, code, legal)
            preserve_semantic_boundaries: 保持语义边界
            min_chunk_size: 最小块大小
            max_chunk_size_ratio: 最大块大小比例
            quality_threshold: 质量阈值
            enable_content_analysis: 启用内容分析
        """
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            keep_separator=keep_separator,
            length_function=length_function
        )
        self._fixed_separator = fixed_separator

        # 智能分割配置
        self._enable_smart_splitting = enable_smart_splitting
        self._content_type = content_type
        self._preserve_semantic_boundaries = preserve_semantic_boundaries
        self._min_chunk_size = min_chunk_size
        self._max_chunk_size = int(chunk_size * max_chunk_size_ratio)
        self._quality_threshold = quality_threshold
        self._enable_content_analysis = enable_content_analysis
        
        # 强制分割配置
        self._force_split_on_separator = force_split_on_separator

        # 内容分析缓存
        self._content_analysis_cache = {}

        # 根据内容类型优化分隔符
        if self._enable_smart_splitting and self._content_type:
            self._separators = self._get_optimized_separators(self._content_type)
        elif not self._separators:
            self._separators = self._get_default_separators()

    def _get_default_separators(self) -> List[str]:
        """获取默认分隔符列表"""
        return ["\n\n", "\n", "。", "！", "？", ". ", "! ", "? ", "；", "; ", "，", ", ", " ", ""]

    def _get_optimized_separators(self, content_type: str) -> List[str]:
        """根据内容类型获取优化的分隔符列表

        Args:
            content_type: 内容类型

        Returns:
            List[str]: 优化的分隔符列表
        """
        separator_configs = {
            "academic": ["\n\n\n", "\n\n", "。", ". ", "；", "; ", "：", ": ", "\n", "，", ", ", " ", ""],
            "news": ["\n\n", "\n", "。", ". ", "！", "! ", "？", "? ", "，", ", ", " ", ""],
            "dialogue": ["\n\n", "\n", "？", "? ", "！", "! ", "。", ". ", "，", ", ", " ", ""],
            "code": ["\n\n", "\n", "{", "}", "(", ")", ";", ":", " ", ""],
            "legal": ["\n\n", "。", ". ", "；", "; ", "：", ": ", "（", "）", "(", ")", "\n", " ", ""]
        }
        return separator_configs.get(content_type, self._get_default_separators())

    def _analyze_content(self, text: str) -> Dict[str, Any]:
        """分析文本内容特征

        Args:
            text: 待分析文本

        Returns:
            Dict[str, Any]: 内容分析结果
        """
        if not self._enable_content_analysis:
            return {}

        # 使用文本哈希作为缓存键
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self._content_analysis_cache:
            return self._content_analysis_cache[text_hash]

        analysis = {
            "length": len(text),
            "line_count": text.count('\n') + 1,
            "paragraph_count": len([p for p in text.split('\n\n') if p.strip()]),
            "sentence_count": len(re.findall(r'[。！？.!?]+', text)),
            "avg_line_length": len(text) / (text.count('\n') + 1),
            "has_code_patterns": bool(re.search(r'[{}();]', text)),
            "has_dialogue_patterns": bool(re.search(r'[""''「」]', text)),
            "chinese_ratio": len(re.findall(r'[\u4e00-\u9fff]', text)) / len(text) if text else 0,
            "whitespace_ratio": len(re.findall(r'\s', text)) / len(text) if text else 0
        }

        # 缓存结果
        self._content_analysis_cache[text_hash] = analysis
        return analysis

    def _detect_content_type(self, text: str) -> str:
        """自动检测内容类型

        Args:
            text: 待检测文本

        Returns:
            str: 检测到的内容类型
        """
        analysis = self._analyze_content(text)

        # 代码检测
        if analysis.get("has_code_patterns", False) and analysis.get("whitespace_ratio", 0) > 0.3:
            return "code"

        # 对话检测
        if analysis.get("has_dialogue_patterns", False):
            return "dialogue"

        # 学术文档检测（长段落，复杂句式）
        if (analysis.get("avg_line_length", 0) > 100 and
            analysis.get("sentence_count", 0) / analysis.get("paragraph_count", 1) > 3):
            return "academic"

        # 法律文档检测（长句，特定标点）
        if (analysis.get("avg_line_length", 0) > 80 and
            "；" in text and "：" in text):
            return "legal"

        # 默认为新闻类型
        return "news"

    def _optimize_chunk_boundaries(self, chunks: List[str]) -> List[str]:
        """优化块边界，保持语义完整性

        Args:
            chunks: 原始块列表

        Returns:
            List[str]: 优化后的块列表
        """
        if not self._preserve_semantic_boundaries or len(chunks) <= 1:
            return chunks

        optimized_chunks = []
        current_chunk = ""

        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            # 检查是否应该与前一个块合并
            should_merge = False

            if current_chunk:
                # 检查语义连续性
                if self._should_merge_chunks(current_chunk, chunk):
                    should_merge = True

                # 检查大小限制
                merged_size = len(current_chunk) + len(chunk) + len(self._fixed_separator)
                if merged_size > self._max_chunk_size:
                    should_merge = False

            if should_merge:
                current_chunk += self._fixed_separator + chunk
            else:
                if current_chunk:
                    optimized_chunks.append(current_chunk)
                current_chunk = chunk

        # 添加最后一个块
        if current_chunk:
            optimized_chunks.append(current_chunk)

        return optimized_chunks

    def _should_merge_chunks(self, chunk1: str, chunk2: str) -> bool:
        """判断两个块是否应该合并

        Args:
            chunk1: 第一个块
            chunk2: 第二个块

        Returns:
            bool: 是否应该合并
        """
        # 检查块大小
        if len(chunk1) < self._min_chunk_size or len(chunk2) < self._min_chunk_size:
            return True

        # 检查语义连续性指标
        chunk1_end = chunk1.strip()[-50:] if len(chunk1) > 50 else chunk1.strip()
        chunk2_start = chunk2.strip()[:50] if len(chunk2) > 50 else chunk2.strip()

        # 检查是否以不完整的句子结尾
        incomplete_endings = ["，", ",", "；", ";", "：", ":", "、", "和", "或", "及", "与"]
        if any(chunk1_end.endswith(ending) for ending in incomplete_endings):
            return True

        # 检查是否以连接词开头
        connecting_starts = ["但是", "然而", "因此", "所以", "而且", "并且", "同时", "另外"]
        if any(chunk2_start.startswith(start) for start in connecting_starts):
            return True

        return False

    def _calculate_quality_score(self, chunks: List[str]) -> float:
        """计算分割质量分数

        Args:
            chunks: 分割后的块列表

        Returns:
            float: 质量分数 (0-1)
        """
        if not chunks:
            return 0.0

        scores = []

        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            # 长度分数
            length_score = 1.0
            if len(chunk) < self._min_chunk_size:
                length_score = len(chunk) / self._min_chunk_size
            elif len(chunk) > self._max_chunk_size:
                length_score = self._max_chunk_size / len(chunk)

            # 完整性分数
            completeness_score = 1.0
            if not chunk.endswith(("。", ".", "!", "！", "?", "？", "\n")):
                completeness_score = 0.8

            # 内容密度分数
            non_whitespace_ratio = len(chunk.replace(" ", "").replace("\n", "")) / len(chunk)
            density_score = min(non_whitespace_ratio * 1.2, 1.0)

            # 综合分数
            chunk_score = (length_score * 0.4 + completeness_score * 0.3 + density_score * 0.3)
            scores.append(chunk_score)

        return sum(scores) / len(scores) if scores else 0.0

    def _try_fixed_separator_split(self, text: str) -> List[str]:
        """尝试使用固定分隔符分割

        Args:
            text: 待分割文本

        Returns:
            List[str]: 分割结果，如果效果不好返回空列表
        """
        if self._fixed_separator not in text:
            return []

        # 使用固定分隔符分割
        chunks = text.split(self._fixed_separator)
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]

        # 检查分割效果
        if len(chunks) <= 1:
            return []

        # 如果启用了强制分割，直接返回分割结果
        if self._force_split_on_separator:
            logger.debug(f"强制分割模式：直接返回{len(chunks)}个分割结果")
            return chunks

        # 检查是否有过大的块需要进一步分割
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > self._max_chunk_size:
                # 递归分割过大的块
                sub_chunks = self._split_text(chunk, self._separators)
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk)

        return final_chunks

    def _apply_quality_control(self, chunks: List[str]) -> List[str]:
        """应用质量控制

        Args:
            chunks: 原始块列表

        Returns:
            List[str]: 质量控制后的块列表
        """
        if not chunks:
            return chunks

        controlled_chunks = []

        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            # 过滤过小的块
            if len(chunk) < self._min_chunk_size:
                # 特殊处理：如果只有一个块且是原始文本，保留它（用于父子分割场景）
                if len(chunks) == 1:
                    logger.debug(f"保留唯一的短块（父子分割场景）: {chunk[:30]}...")
                    controlled_chunks.append(chunk)
                    continue

                # 尝试与前一个块合并
                if (controlled_chunks and
                    len(controlled_chunks[-1]) + len(chunk) + 1 <= self._max_chunk_size):
                    controlled_chunks[-1] += " " + chunk
                    continue
                # 如果无法合并且块太小，跳过
                elif len(chunk) < self._min_chunk_size // 2:
                    logger.debug(f"跳过过小的块: {chunk[:30]}...")
                    continue

            # 截断过大的块
            if len(chunk) > self._max_chunk_size:
                logger.debug(f"截断过大的块: {len(chunk)} -> {self._max_chunk_size}")
                chunk = chunk[:self._max_chunk_size].rsplit(' ', 1)[0] + "..."

            controlled_chunks.append(chunk)

        return controlled_chunks

    @classmethod
    def from_encoder(
        cls,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        fixed_separator: str = "\n\n",
        separators: Optional[List[str]] = None,
        keep_separator: bool = True,
        length_function: Optional[Callable[[List[str]], List[int]]] = None,
        # 新增智能分割参数
        enable_smart_splitting: bool = True,
        content_type: Optional[str] = None,
        preserve_semantic_boundaries: bool = True,
        min_chunk_size: int = 50,
        max_chunk_size_ratio: float = 1.5,
        quality_threshold: float = 0.8,
        enable_content_analysis: bool = True,
        force_split_on_separator: bool = False,
        **kwargs: Any
    ):
        """从编码器创建增强的固定分隔符分割器

        Args:
            chunk_size: 目标块大小
            chunk_overlap: 块重叠大小
            fixed_separator: 固定分隔符
            separators: 递归分隔符列表
            keep_separator: 是否保留分隔符
            length_function: 长度计算函数
            enable_smart_splitting: 启用智能分割
            content_type: 内容类型
            preserve_semantic_boundaries: 保持语义边界
            min_chunk_size: 最小块大小
            max_chunk_size_ratio: 最大块大小比例
            quality_threshold: 质量阈值
            enable_content_analysis: 启用内容分析
            **kwargs: 其他参数

        Returns:
            FixedRecursiveCharacterTextSplitter: 分割器实例
        """
        return cls(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            fixed_separator=fixed_separator,
            separators=separators,
            keep_separator=keep_separator,
            length_function=length_function or (lambda x: [len(text) for text in x] if x else [0]),
            enable_smart_splitting=enable_smart_splitting,
            content_type=content_type,
            preserve_semantic_boundaries=preserve_semantic_boundaries,
            min_chunk_size=min_chunk_size,
            max_chunk_size_ratio=max_chunk_size_ratio,
            quality_threshold=quality_threshold,
            enable_content_analysis=enable_content_analysis,
            force_split_on_separator=force_split_on_separator,
            **kwargs
        )
        
    def split_text(self, text: str) -> List[str]:
        """智能分割文本

        Args:
            text: 待分割的文本

        Returns:
            List[str]: 分割后的文本块列表
        """
        logger.debug(f"开始智能分割文本，长度: {len(text)}, 固定分隔符: '{self._fixed_separator}'")

        if not text or not text.strip():
            return []

        # 智能分割流程
        if self._enable_smart_splitting:
            return self._smart_split_text(text)
        else:
            return self._basic_split_text(text)

    def _smart_split_text(self, text: str) -> List[str]:
        """智能分割文本的核心方法

        Args:
            text: 待分割文本

        Returns:
            List[str]: 分割后的文本块
        """
        # 如果启用了强制分割模式，优先使用第一个存在的分隔符进行强制分割
        if self._force_split_on_separator:
            for separator in self._separators:
                if separator in text:
                    logger.debug(f"强制分割模式：使用分隔符 '{separator}'")
                    return self._force_split_by_separator(text, separator)
        
        # 1. 内容分析
        if not self._content_type:
            detected_type = self._detect_content_type(text)
            logger.debug(f"自动检测内容类型: {detected_type}")
            # 临时使用检测到的类型优化分隔符
            temp_separators = self._get_optimized_separators(detected_type)
        else:
            temp_separators = self._separators

        # 2. 尝试固定分隔符分割
        chunks = self._try_fixed_separator_split(text)

        # 3. 如果固定分隔符效果不好，使用递归分割
        if not chunks or len(chunks) == 1:
            logger.debug("固定分隔符分割效果不佳，使用递归分割")
            chunks = self._split_text(text, temp_separators)

        # 4. 优化块边界（仅在非固定分隔符模式下进行）
        # 如果使用固定分隔符成功分割，保持原始分割结果
        if self._preserve_semantic_boundaries and len(chunks) <= 1:
            chunks = self._optimize_chunk_boundaries(chunks)

        # 5. 质量控制（仅在非固定分隔符模式下进行）
        # 如果使用固定分隔符成功分割，保持原始分割结果
        if len(chunks) <= 1:
            chunks = self._apply_quality_control(chunks)

        # 6. 计算质量分数
        quality_score = self._calculate_quality_score(chunks)
        logger.debug(f"分割质量分数: {quality_score:.3f}")

        if quality_score < self._quality_threshold:
            logger.warning(f"分割质量较低 ({quality_score:.3f} < {self._quality_threshold})，可能需要调整参数")

        logger.debug(f"智能分割完成，生成 {len(chunks)} 个块")
        return chunks

    def _basic_split_text(self, text: str) -> List[str]:
        """基础分割方法（原有逻辑）

        Args:
            text: 待分割文本

        Returns:
            List[str]: 分割后的文本块
        """
        # 首先尝试使用固定分隔符分割
        if self._fixed_separator and self._fixed_separator in text:
            chunks = text.split(self._fixed_separator)
            logger.debug(f"使用固定分隔符 '{self._fixed_separator}' 分割文本，得到 {len(chunks)} 个原始块")

            # 清理空块
            cleaned_chunks = []
            for chunk in chunks:
                chunk = chunk.strip()
                if chunk:
                    cleaned_chunks.append(chunk)

            logger.debug(f"清理后得到 {len(cleaned_chunks)} 个有效块")

            # 如果启用强制分割，直接返回清理后的块
            if self._force_split_on_separator and len(cleaned_chunks) > 1:
                logger.debug(f"强制分割模式：直接返回 {len(cleaned_chunks)} 个块")
                return cleaned_chunks

            # 如果分割成功且有多个块，返回分割结果
            if len(cleaned_chunks) > 1:
                final_chunks = []
                for i, chunk in enumerate(cleaned_chunks):
                    # 如果单个块太大，进行递归分割
                    if len(chunk) > self._chunk_size:
                        logger.debug(f"块 {i+1} 长度 {len(chunk)} 超过限制 {self._chunk_size}，进行递归分割")
                        sub_chunks = self._split_text(chunk, self._separators)
                        final_chunks.extend(sub_chunks)
                    else:
                        logger.debug(f"添加块 {i+1}，长度: {len(chunk)}")
                        final_chunks.append(chunk)

                logger.debug(f"固定分隔符分割最终生成 {len(final_chunks)} 个块")
                return final_chunks
            else:
                logger.debug(f"固定分隔符分割只得到 {len(cleaned_chunks)} 个块，使用递归分割")
        else:
            logger.debug("固定分隔符不存在于文本中，使用递归分割")

        # 使用递归分割作为后备方案
        logger.debug("使用递归分割")
        return self._split_text(text, self._separators)
        
    def _force_split_by_separator(self, text: str, separator: str) -> List[str]:
        """强制按分隔符分割，不考虑chunk_size限制
        
        Args:
            text: 待分割文本
            separator: 分隔符
            
        Returns:
            List[str]: 分割后的文本块
        """
        if separator not in text:
            return [text]
            
        chunks = text.split(separator)
        # 清理空块，但保留所有非空块
        cleaned_chunks = []
        for chunk in chunks:
            chunk = chunk.strip()
            if chunk:
                cleaned_chunks.append(chunk)
        
        logger.debug(f"强制分割模式：按 '{separator}' 分割得到 {len(cleaned_chunks)} 个块")
        return cleaned_chunks if cleaned_chunks else [text]