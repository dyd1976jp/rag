"""
父子文档索引处理器

基于参考项目Dify的实现，提供专门的父子文档处理架构，包括文档提取、转换、加载、清理和检索功能。
"""

import os
import uuid
import logging
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from abc import ABC, abstractmethod

from .models import Document, ChildDocument
from .extractor.extract_processor import ExtractProcessor, ExtractMode
from .cleaner.clean_processor import CleanProcessor, CleanLevel
from .document_splitter import ParentChildDocumentSplitter, Rule, SplitMode
from .vector_store import MilvusVectorStore
from .document_store import DocumentStore
from .retrieval_service import RetrievalService
from .embedding_model import EmbeddingModel
from .config import get_document_process_rule, get_embedding_model_config

logger = logging.getLogger(__name__)


class ParentMode(str, Enum):
    """父文档分割模式"""
    PARAGRAPH = "paragraph"  # 段落模式
    FULL_DOC = "full_doc"    # 全文档模式


class ExtractSetting:
    """文档提取设置"""
    
    def __init__(
        self,
        file_path: str,
        extract_mode: str = ExtractMode.BASIC,
        cache_key: Optional[str] = None,
        **kwargs
    ):
        self.file_path = file_path
        self.extract_mode = extract_mode
        self.cache_key = cache_key
        self.kwargs = kwargs


class ProcessRule:
    """处理规则"""

    def __init__(
        self,
        mode: str = "automatic",
        parent_mode: ParentMode = ParentMode.PARAGRAPH,
        rules: Optional[Dict[str, Any]] = None,
        enable_preview: bool = False,
        preview_limit: int = 10,
        enable_validation: bool = True,
        enable_optimization: bool = True,
        **kwargs
    ):
        self.mode = mode
        self.parent_mode = parent_mode
        self.rules = rules or {}
        self.enable_preview = enable_preview
        self.preview_limit = preview_limit
        self.enable_validation = enable_validation
        self.enable_optimization = enable_optimization
        self.kwargs = kwargs

        # 设置默认规则
        if not self.rules:
            self.rules = self._get_default_rules()

        # 根据父文档模式调整默认规则
        self._adjust_rules_by_parent_mode()

    def _get_default_rules(self) -> Dict[str, Any]:
        """获取默认处理规则"""
        return {
            "segmentation": {
                "separator": "\n\n",
                "max_tokens": 1024,
                "chunk_overlap": 200,
                "min_chunk_size": 100,
                "separators": ["\n\n", "\n", "。", ".", "！", "!", "？", "?", " "],
                "keep_separator": True,
                "remove_empty_chunks": True
            },
            "subchunk_segmentation": {
                "separator": "\n",
                "max_tokens": 512,
                "chunk_overlap": 50,
                "min_chunk_size": 50,
                "separators": ["\n", "。", ".", "！", "!", "？", "?", " "],
                "keep_separator": False,
                "remove_empty_chunks": True
            },
            "pre_processing_rules": [
                {"type": "remove_html", "enabled": True},
                {"type": "remove_extra_spaces", "enabled": True},
                {"type": "remove_urls", "enabled": False},
                {"type": "normalize_unicode", "enabled": True},
                {"type": "remove_control_chars", "enabled": True}
            ],
            "post_processing_rules": [
                {"type": "validate_chunks", "enabled": True},
                {"type": "optimize_chunks", "enabled": True},
                {"type": "add_metadata", "enabled": True}
            ],
            "quality_control": {
                "min_content_ratio": 0.1,  # 最小内容比例
                "max_empty_lines": 3,      # 最大空行数
                "check_encoding": True,    # 检查编码
                "validate_structure": True  # 验证结构
            }
        }

    def _adjust_rules_by_parent_mode(self) -> None:
        """根据父文档模式调整规则"""
        if self.parent_mode == ParentMode.FULL_DOC:
            # FULL_DOC模式的特殊配置
            segmentation = self.rules.get("segmentation", {})
            segmentation.update({
                "separator": "\n\n\n",  # 使用更大的分隔符
                "max_tokens": 2048,     # 更大的父文档块
                "chunk_overlap": 100,   # 较小的重叠
                "separators": ["\n\n\n", "\n\n", "第", "章", "节", "\n"]
            })

            # 子块配置保持相对较小
            subchunk_segmentation = self.rules.get("subchunk_segmentation", {})
            subchunk_segmentation.update({
                "max_tokens": 256,      # 较小的子块
                "chunk_overlap": 25     # 较小的重叠
            })
        elif self.parent_mode == ParentMode.PARAGRAPH:
            # PARAGRAPH模式的特殊配置
            segmentation = self.rules.get("segmentation", {})
            segmentation.update({
                "separator": "\n\n",
                "max_tokens": 1024,
                "chunk_overlap": 200,
                "separators": ["\n\n", "\n", "。", ".", " "]
            })

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            Dict[str, Any]: 规则字典
        """
        return {
            "mode": self.mode,
            "parent_mode": self.parent_mode.value if isinstance(self.parent_mode, ParentMode) else self.parent_mode,
            "rules": self.rules,
            "enable_preview": self.enable_preview,
            "preview_limit": self.preview_limit,
            "enable_validation": self.enable_validation,
            "enable_optimization": self.enable_optimization,
            **self.kwargs
        }

    @classmethod
    def from_dict(cls, rule_dict: Dict[str, Any]) -> 'ProcessRule':
        """从字典创建规则对象

        Args:
            rule_dict: 规则字典

        Returns:
            ProcessRule: 规则对象
        """
        parent_mode_str = rule_dict.get("parent_mode", "paragraph")
        parent_mode = ParentMode.FULL_DOC if parent_mode_str == "full_doc" else ParentMode.PARAGRAPH

        return cls(
            mode=rule_dict.get("mode", "automatic"),
            parent_mode=parent_mode,
            rules=rule_dict.get("rules", {}),
            enable_preview=rule_dict.get("enable_preview", False),
            preview_limit=rule_dict.get("preview_limit", 10),
            enable_validation=rule_dict.get("enable_validation", True),
            enable_optimization=rule_dict.get("enable_optimization", True),
            **{k: v for k, v in rule_dict.items() if k not in [
                "mode", "parent_mode", "rules", "enable_preview",
                "preview_limit", "enable_validation", "enable_optimization"
            ]}
        )

    def update_segmentation_config(
        self,
        max_tokens: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        separator: Optional[str] = None,
        separators: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """更新分割配置

        Args:
            max_tokens: 最大token数
            chunk_overlap: 重叠大小
            separator: 主分隔符
            separators: 分隔符列表
            **kwargs: 其他配置参数
        """
        segmentation = self.rules.setdefault("segmentation", {})

        if max_tokens is not None:
            segmentation["max_tokens"] = max_tokens
        if chunk_overlap is not None:
            segmentation["chunk_overlap"] = chunk_overlap
        if separator is not None:
            segmentation["separator"] = separator
        if separators is not None:
            segmentation["separators"] = separators

        # 更新其他参数
        for key, value in kwargs.items():
            segmentation[key] = value

    def update_subchunk_config(
        self,
        max_tokens: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        separator: Optional[str] = None,
        separators: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """更新子块配置

        Args:
            max_tokens: 最大token数
            chunk_overlap: 重叠大小
            separator: 主分隔符
            separators: 分隔符列表
            **kwargs: 其他配置参数
        """
        subchunk_segmentation = self.rules.setdefault("subchunk_segmentation", {})

        if max_tokens is not None:
            subchunk_segmentation["max_tokens"] = max_tokens
        if chunk_overlap is not None:
            subchunk_segmentation["chunk_overlap"] = chunk_overlap
        if separator is not None:
            subchunk_segmentation["separator"] = separator
        if separators is not None:
            subchunk_segmentation["separators"] = separators

        # 更新其他参数
        for key, value in kwargs.items():
            subchunk_segmentation[key] = value

    def enable_preprocessing_rule(self, rule_type: str, enabled: bool = True) -> None:
        """启用/禁用预处理规则

        Args:
            rule_type: 规则类型
            enabled: 是否启用
        """
        pre_processing_rules = self.rules.setdefault("pre_processing_rules", [])

        # 查找现有规则
        for rule in pre_processing_rules:
            if rule.get("type") == rule_type:
                rule["enabled"] = enabled
                return

        # 添加新规则
        pre_processing_rules.append({"type": rule_type, "enabled": enabled})

    def set_quality_control(self, **quality_params) -> None:
        """设置质量控制参数

        Args:
            **quality_params: 质量控制参数
        """
        quality_control = self.rules.setdefault("quality_control", {})
        quality_control.update(quality_params)

    def validate(self) -> List[str]:
        """验证规则配置

        Returns:
            List[str]: 验证错误列表
        """
        errors = []

        # 验证分割配置
        segmentation = self.rules.get("segmentation", {})
        if segmentation.get("max_tokens", 0) <= 0:
            errors.append("segmentation.max_tokens必须大于0")

        if segmentation.get("chunk_overlap", -1) < 0:
            errors.append("segmentation.chunk_overlap不能小于0")

        # 验证子块配置
        subchunk_segmentation = self.rules.get("subchunk_segmentation", {})
        if subchunk_segmentation.get("max_tokens", 0) <= 0:
            errors.append("subchunk_segmentation.max_tokens必须大于0")

        # 验证重叠不能大于块大小
        parent_tokens = segmentation.get("max_tokens", 1024)
        parent_overlap = segmentation.get("chunk_overlap", 200)
        if parent_overlap >= parent_tokens:
            errors.append("父文档chunk_overlap不能大于等于max_tokens")

        child_tokens = subchunk_segmentation.get("max_tokens", 512)
        child_overlap = subchunk_segmentation.get("chunk_overlap", 50)
        if child_overlap >= child_tokens:
            errors.append("子文档chunk_overlap不能大于等于max_tokens")

        # 验证预览限制
        if self.preview_limit <= 0:
            errors.append("preview_limit必须大于0")

        return errors


class PreviewModeManager:
    """预览模式管理器"""

    def __init__(self):
        self.default_limits = {
            "max_documents": 20,  # 增加默认限制以支持更多父段落
            "max_children_per_parent": 10,
            "max_total_children": 50,
            "max_content_length": 10000,
            "max_processing_time": 30  # 秒
        }

    def calculate_preview_limits(
        self,
        content_length: int,
        document_count: int,
        process_rule: ProcessRule
    ) -> Dict[str, int]:
        """计算智能预览限制

        Args:
            content_length: 内容总长度
            document_count: 文档数量
            process_rule: 处理规则

        Returns:
            Dict[str, int]: 预览限制配置
        """
        limits = self.default_limits.copy()

        # 根据内容长度调整
        if content_length < 1000:
            # 短内容：显示更多细节
            limits["max_children_per_parent"] = 15
            limits["max_total_children"] = 30
        elif content_length > 50000:
            # 长内容：限制更严格
            limits["max_documents"] = 5
            limits["max_children_per_parent"] = 5
            limits["max_total_children"] = 25

        # 根据文档数量调整
        if document_count > 5:
            limits["max_documents"] = max(3, limits["max_documents"] // 2)
            limits["max_children_per_parent"] = max(3, limits["max_children_per_parent"] // 2)

        # 根据处理规则调整
        if process_rule.parent_mode == ParentMode.FULL_DOC:
            # FULL_DOC模式通常生成较少的父文档但更多子文档
            limits["max_documents"] = min(3, limits["max_documents"])
            limits["max_children_per_parent"] = min(20, limits["max_children_per_parent"] * 2)

        # 应用用户自定义限制
        if process_rule.enable_preview and process_rule.preview_limit > 0:
            limits["max_documents"] = min(limits["max_documents"], process_rule.preview_limit)

        return limits

    def optimize_preview_content(
        self,
        documents: List[Document],
        limits: Dict[str, int]
    ) -> List[Document]:
        """优化预览内容

        Args:
            documents: 原始文档列表
            limits: 预览限制

        Returns:
            List[Document]: 优化后的文档列表
        """
        if not documents:
            return documents

        optimized_docs = []
        total_children = 0

        for i, doc in enumerate(documents):
            if i >= limits["max_documents"]:
                logger.info(f"预览模式：达到最大文档数量限制 {limits['max_documents']}")
                break

            # 复制文档以避免修改原始数据
            optimized_doc = Document(
                page_content=doc.page_content,
                metadata=doc.metadata.copy()
            )

            # 处理子文档
            if hasattr(doc, 'children') and doc.children:
                children_limit = min(
                    limits["max_children_per_parent"],
                    limits["max_total_children"] - total_children
                )

                if children_limit > 0:
                    # 智能选择子文档
                    selected_children = self._select_representative_children(
                        doc.children, children_limit
                    )
                    optimized_doc.children = selected_children
                    total_children += len(selected_children)

                    # 更新元数据
                    optimized_doc.metadata.update({
                        "preview_children_count": len(selected_children),
                        "original_children_count": len(doc.children),
                        "children_truncated": len(doc.children) > len(selected_children)
                    })
                else:
                    optimized_doc.children = []
                    optimized_doc.metadata.update({
                        "preview_children_count": 0,
                        "original_children_count": len(doc.children),
                        "children_truncated": True
                    })

            # 截断过长的内容
            if len(optimized_doc.page_content) > limits["max_content_length"]:
                truncated_content = optimized_doc.page_content[:limits["max_content_length"]]
                # 尝试在句子边界截断
                last_sentence_end = max(
                    truncated_content.rfind('。'),
                    truncated_content.rfind('.'),
                    truncated_content.rfind('！'),
                    truncated_content.rfind('!'),
                    truncated_content.rfind('？'),
                    truncated_content.rfind('?')
                )

                if last_sentence_end > limits["max_content_length"] * 0.8:
                    truncated_content = truncated_content[:last_sentence_end + 1]

                optimized_doc.page_content = truncated_content + "..."
                optimized_doc.metadata["content_truncated"] = True
                optimized_doc.metadata["original_content_length"] = len(doc.page_content)

            optimized_docs.append(optimized_doc)

            # 检查总子文档数量限制
            if total_children >= limits["max_total_children"]:
                logger.info(f"预览模式：达到最大子文档总数限制 {limits['max_total_children']}")
                break

        return optimized_docs

    def _select_representative_children(
        self,
        children: List[Document],
        limit: int
    ) -> List[Document]:
        """智能选择代表性的子文档

        Args:
            children: 子文档列表
            limit: 选择数量限制

        Returns:
            List[Document]: 选择的子文档
        """
        if len(children) <= limit:
            return children

        # 策略1: 均匀分布选择
        if limit >= 3:
            # 选择开头、中间和结尾的文档，其余均匀分布
            selected = []

            # 开头
            selected.append(children[0])

            # 中间部分均匀选择
            middle_count = limit - 2
            if middle_count > 0:
                step = (len(children) - 2) / (middle_count + 1)
                for i in range(middle_count):
                    index = int(1 + (i + 1) * step)
                    if index < len(children) - 1:
                        selected.append(children[index])

            # 结尾
            if limit > 1:
                selected.append(children[-1])

            return selected[:limit]
        else:
            # 策略2: 简单选择前几个
            return children[:limit]

    def format_preview_response(
        self,
        documents: List[Document],
        original_document: Optional[Document] = None,
        doc_id: str = "",
        processing_stats: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """格式化预览响应

        Args:
            documents: 处理后的文档列表
            original_document: 原始文档
            doc_id: 文档ID
            processing_stats: 处理统计信息

        Returns:
            Dict[str, Any]: 格式化的响应
        """
        # 统计信息
        total_segments = len(documents)
        parent_segments = len([doc for doc in documents if not hasattr(doc, 'parent_id')])
        child_segments = sum(len(getattr(doc, 'children', [])) for doc in documents)

        # 提取内容
        parent_content = original_document.page_content if original_document else ""
        children_content = []
        segments = []

        for i, doc in enumerate(documents):
            # 添加父段落信息
            segment_info = {
                "id": i,
                "type": "parent",
                "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                "metadata": doc.metadata,
                "children_count": len(getattr(doc, 'children', []))
            }
            segments.append(segment_info)

            # 添加子文档内容
            if hasattr(doc, 'children') and doc.children:
                for j, child in enumerate(doc.children):
                    children_content.append(child.page_content)
                    child_segment_info = {
                        "id": f"{i}_{j}",
                        "type": "child",
                        "parent_id": i,
                        "content": child.page_content[:100] + "..." if len(child.page_content) > 100 else child.page_content,
                        "metadata": child.metadata
                    }
                    segments.append(child_segment_info)

        # 构建响应
        response = {
            "success": True,
            "message": "预览生成成功",
            "preview_mode": True,
            "doc_id": doc_id,
            "total_segments": total_segments,
            "parent_segments": parent_segments,
            "child_segments": child_segments,
            "parentContent": parent_content,
            "childrenContent": children_content,
            "segments": segments,
            "document_overview": {
                "total_length": len(parent_content),
                "estimated_tokens": len(parent_content) // 4,  # 粗略估算
                "language": "zh" if any('\u4e00' <= char <= '\u9fff' for char in parent_content[:100]) else "en"
            },
            "preview_info": {
                "is_truncated": any(doc.metadata.get("content_truncated", False) for doc in documents),
                "children_truncated": any(doc.metadata.get("children_truncated", False) for doc in documents),
                "total_original_children": sum(doc.metadata.get("original_children_count", 0) for doc in documents)
            }
        }

        # 添加处理统计信息
        if processing_stats:
            response["processing_stats"] = processing_stats

        return response


class BaseIndexProcessor(ABC):
    """索引处理器基类"""
    
    @abstractmethod
    def extract(self, extract_setting: ExtractSetting, **kwargs) -> List[Document]:
        """提取文档"""
        pass
    
    @abstractmethod
    def transform(self, documents: List[Document], **kwargs) -> List[Document]:
        """转换文档为父子结构"""
        pass
    
    @abstractmethod
    def load(self, documents: List[Document], **kwargs) -> None:
        """加载文档到存储系统"""
        pass
    
    @abstractmethod
    def clean(self, node_ids: Optional[List[str]] = None, **kwargs) -> None:
        """清理文档"""
        pass
    
    @abstractmethod
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        score_threshold: float = 0.0,
        **kwargs
    ) -> List[Document]:
        """检索文档"""
        pass


class ParentChildIndexProcessor(BaseIndexProcessor):
    """父子文档索引处理器
    
    实现专门的父子文档处理架构，支持：
    - 文档提取和清理
    - 父子结构转换
    - 预览模式和批量处理
    - 向量存储和检索
    """
    
    def __init__(
        self,
        vector_store: Optional[MilvusVectorStore] = None,
        document_store: Optional[DocumentStore] = None,
        embedding_model: Optional[EmbeddingModel] = None,
        retrieval_service: Optional[RetrievalService] = None
    ):
        """初始化处理器
        
        Args:
            vector_store: 向量存储实例
            document_store: 文档存储实例
            embedding_model: 嵌入模型实例
            retrieval_service: 检索服务实例
        """
        self.vector_store = vector_store
        self.document_store = document_store
        self.embedding_model = embedding_model
        self.retrieval_service = retrieval_service

        # 初始化预览模式管理器
        self.preview_manager = PreviewModeManager()

        # 初始化组件
        self._init_components()
    
    def _init_components(self):
        """初始化组件"""
        try:
            # 初始化向量存储
            if not self.vector_store:
                self.vector_store = MilvusVectorStore()
            
            # 初始化文档存储
            if not self.document_store:
                self.document_store = DocumentStore()
            
            # 初始化嵌入模型
            if not self.embedding_model:
                config = get_embedding_model_config()
                self.embedding_model = EmbeddingModel(
                    model_name=config.get("model_name"),
                    api_base=config.get("api_base")
                )
            
            # 初始化检索服务
            if not self.retrieval_service:
                self.retrieval_service = RetrievalService(
                    vector_store=self.vector_store,
                    document_store=self.document_store,
                    embedding_model=self.embedding_model
                )
                
        except Exception as e:
            logger.warning(f"组件初始化失败，某些功能可能不可用: {str(e)}")

    def extract(self, extract_setting: ExtractSetting, **kwargs) -> List[Document]:
        """提取文档

        Args:
            extract_setting: 提取设置
            **kwargs: 额外参数，包括：
                - process_rule_mode: 处理规则模式
                - is_automatic: 是否自动模式

        Returns:
            List[Document]: 提取的文档列表
        """
        try:
            logger.info(f"开始提取文档: {extract_setting.file_path}")

            # 根据文件类型选择提取方法
            file_ext = os.path.splitext(extract_setting.file_path)[1].lower()

            if file_ext == '.pdf':
                # 使用ExtractProcessor提取PDF文档
                documents = ExtractProcessor.extract_pdf(
                    file_path=extract_setting.file_path,
                    mode=extract_setting.extract_mode,
                    cache_key=extract_setting.cache_key
                )
            else:
                # 处理文本文件（.txt, .md等）
                logger.info(f"处理文本文件: {extract_setting.file_path}")
                with open(extract_setting.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 创建文档对象
                document = Document(
                    page_content=content,
                    metadata={
                        "source": extract_setting.file_path,
                        "file_type": file_ext,
                        "cache_key": extract_setting.cache_key
                    }
                )
                documents = [document]

            logger.info(f"文档提取完成，共提取 {len(documents)} 个文档片段")
            return documents

        except Exception as e:
            logger.error(f"文档提取失败: {str(e)}")
            raise

    def transform(self, documents: List[Document], **kwargs) -> List[Document]:
        """转换文档为父子结构

        Args:
            documents: 要转换的文档列表
            **kwargs: 额外参数，包括：
                - process_rule: 处理规则
                - preview: 是否预览模式
                - embedding_model_instance: 嵌入模型实例

        Returns:
            List[Document]: 转换后的父子文档列表
        """
        try:
            logger.info(f"开始转换文档为父子结构，输入文档数量: {len(documents)}")

            # 获取处理规则
            process_rule_dict = kwargs.get("process_rule")
            if not process_rule_dict:
                # 使用默认规则
                process_rule_dict = {
                    "mode": "automatic",
                    "rules": get_document_process_rule()["rules"]
                }

            # 从process_rule_dict中获取parent_mode
            parent_mode_str = process_rule_dict.get("parent_mode", "paragraph")
            if isinstance(parent_mode_str, str):
                parent_mode = ParentMode.FULL_DOC if parent_mode_str == "full_doc" else ParentMode.PARAGRAPH
            else:
                parent_mode = parent_mode_str

            process_rule = ProcessRule(
                mode=process_rule_dict.get("mode", "automatic"),
                parent_mode=parent_mode,
                rules=process_rule_dict.get("rules", {})
            )

            # 验证和标准化处理规则
            process_rule = self._validate_process_rule(process_rule)

            # 是否预览模式
            preview_mode = kwargs.get("preview", False)

            logger.info(f"使用处理规则: 模式={process_rule.parent_mode.value}, 预览={preview_mode}")

            # 计算内容统计信息
            total_content_length = sum(len(doc.page_content) for doc in documents)

            # 如果是预览模式，计算智能预览限制
            preview_limits = None
            if preview_mode:
                preview_limits = self.preview_manager.calculate_preview_limits(
                    content_length=total_content_length,
                    document_count=len(documents),
                    process_rule=process_rule
                )
                logger.info(f"预览模式限制: {preview_limits}")

            all_documents = []

            if process_rule.parent_mode == ParentMode.PARAGRAPH:
                # 段落模式处理
                # 从kwargs中移除process_rule以避免参数冲突
                filtered_kwargs = {k: v for k, v in kwargs.items() if k != 'process_rule'}
                if preview_limits:
                    filtered_kwargs.update(preview_limits)
                all_documents = self._transform_paragraph_mode(
                    documents, process_rule, preview_mode, **filtered_kwargs
                )
            elif process_rule.parent_mode == ParentMode.FULL_DOC:
                # 全文档模式处理
                filtered_kwargs = {k: v for k, v in kwargs.items() if k != 'process_rule'}
                if preview_limits:
                    filtered_kwargs.update(preview_limits)
                all_documents = self._transform_full_doc_mode(
                    documents, process_rule, preview_mode, **filtered_kwargs
                )

            # 如果是预览模式，应用预览优化
            if preview_mode and preview_limits:
                all_documents = self.preview_manager.optimize_preview_content(
                    all_documents, preview_limits
                )
                logger.info(f"预览优化完成，最终文档数量: {len(all_documents)}")

            logger.info(f"文档转换完成，生成 {len(all_documents)} 个父文档")
            return all_documents

        except Exception as e:
            logger.error(f"文档转换失败: {str(e)}")
            raise

    def _transform_paragraph_mode(
        self,
        documents: List[Document],
        process_rule: ProcessRule,
        preview_mode: bool,
        **kwargs
    ) -> List[Document]:
        """段落模式转换

        Args:
            documents: 输入文档列表
            process_rule: 处理规则
            preview_mode: 是否预览模式
            **kwargs: 额外参数

        Returns:
            List[Document]: 转换后的文档列表
        """
        all_documents = []

        # 获取分割规则
        segmentation = process_rule.rules.get("segmentation", {})
        subchunk_segmentation = process_rule.rules.get("subchunk_segmentation", {})

        # 创建父文档分割规则
        parent_rule = Rule(
            mode=SplitMode.PARENT_CHILD,
            max_tokens=segmentation.get("max_tokens", 1024),
            chunk_overlap=segmentation.get("chunk_overlap", 200),
            fixed_separator=segmentation.get("separator", "\n\n"),
            subchunk_max_tokens=subchunk_segmentation.get("max_tokens", 512),
            subchunk_overlap=subchunk_segmentation.get("chunk_overlap", 50),
            subchunk_separator=subchunk_segmentation.get("separator", "\n"),
            clean_text=True,
            keep_separator=True
        )

        # 创建分割器
        splitter = ParentChildDocumentSplitter()

        # 获取预览限制
        max_documents = kwargs.get("max_documents", 10)

        for document in documents:
            if preview_mode and len(all_documents) >= max_documents:
                logger.info(f"预览模式：已达到最大文档数量限制 {max_documents}")
                break

            # 清理文档内容
            cleaned_content = CleanProcessor.clean(
                document.page_content,
                level=CleanLevel.FULL
            )
            document.page_content = cleaned_content

            # 分割文档
            segments = splitter.split_documents([document], parent_rule)

            # 处理分割结果
            for segment in segments:
                if segment.page_content.strip():
                    # 生成文档ID和哈希
                    doc_id = str(uuid.uuid4())
                    doc_hash = self._generate_text_hash(segment.page_content)

                    # 更新元数据
                    segment.metadata.update({
                        "doc_id": doc_id,
                        "doc_hash": doc_hash
                    })

                    # 处理内容格式
                    page_content = segment.page_content
                    if page_content.startswith(".") or page_content.startswith("。"):
                        page_content = page_content[1:].strip()

                    if len(page_content) > 0:
                        segment.page_content = page_content

                        # 生成子文档
                        child_documents = self._split_child_documents(
                            segment, process_rule, **kwargs
                        )
                        segment.children = child_documents

                        # 修复：确保元数据包含type字段以兼容传统处理器
                        if "type" not in segment.metadata:
                            segment.metadata["type"] = "parent"

                        all_documents.append(segment)

        return all_documents

    def _transform_full_doc_mode(
        self,
        documents: List[Document],
        process_rule: ProcessRule,
        preview_mode: bool,
        **kwargs
    ) -> List[Document]:
        """全文档模式转换

        在FULL_DOC模式下，将所有输入文档合并为一个父文档，
        然后根据子文档分割规则生成子文档。
        这种模式适合需要保持文档完整性的场景。

        Args:
            documents: 输入文档列表
            process_rule: 处理规则
            preview_mode: 是否预览模式
            **kwargs: 额外参数

        Returns:
            List[Document]: 转换后的文档列表（通常只有一个父文档）
        """
        try:
            logger.info(f"FULL_DOC模式：处理 {len(documents)} 个输入文档")

            if not documents:
                logger.warning("FULL_DOC模式：没有输入文档")
                return []

            # 1. 合并所有文档内容，保持文档间的分隔
            merged_content_parts = []
            merged_metadata = {}
            source_docs_info = []

            for i, doc in enumerate(documents):
                # 清理文档内容
                cleaned_content = self._clean_text(doc.page_content)
                if cleaned_content:
                    merged_content_parts.append(cleaned_content)

                    # 收集源文档信息
                    source_docs_info.append({
                        "index": i,
                        "doc_id": doc.doc_id,
                        "source": doc.source,
                        "length": len(cleaned_content)
                    })

                    # 合并元数据（第一个文档的元数据作为基础）
                    if i == 0:
                        merged_metadata = doc.metadata.copy()
                    else:
                        # 合并其他文档的关键元数据
                        for key in ["title", "author", "category"]:
                            if key in doc.metadata and key not in merged_metadata:
                                merged_metadata[key] = doc.metadata[key]

            if not merged_content_parts:
                logger.warning("FULL_DOC模式：所有文档内容为空")
                return []

            # 2. 创建合并后的父文档
            page_content = "\n\n".join(merged_content_parts)
            doc_id = str(uuid.uuid4())
            doc_hash = self._generate_text_hash(page_content)

            # 更新合并文档的元数据
            merged_metadata.update({
                "doc_id": doc_id,
                "doc_hash": doc_hash,
                "is_parent": True,
                "parent_mode": "full_doc",
                "source_docs_count": len(documents),
                "source_docs_info": source_docs_info,
                "total_length": len(page_content),
                "merge_timestamp": str(uuid.uuid4())  # 用作合并标识
            })

            merged_document = Document(
                page_content=page_content,
                metadata=merged_metadata,
                doc_id=doc_id,
                doc_hash=doc_hash
            )

            logger.info(f"FULL_DOC模式：创建合并文档，长度 {len(page_content)} 字符")

            # 3. 生成子文档
            child_documents = self._split_child_documents(
                merged_document, process_rule, **kwargs
            )

            # 4. 预览模式限制子文档数量
            if preview_mode:
                original_count = len(child_documents)
                max_children_per_parent = kwargs.get("max_children_per_parent", 10)
                if len(child_documents) > max_children_per_parent:
                    child_documents = child_documents[:max_children_per_parent]
                    logger.info(f"预览模式：限制子文档数量从 {original_count} 个减少到 {len(child_documents)} 个")

            # 5. 设置父子关系
            merged_document.children = child_documents

            # 6. 更新父文档元数据，包含子文档统计信息
            merged_document.metadata.update({
                "children_count": len(child_documents),
                "preview_mode": preview_mode
            })

            logger.info(f"FULL_DOC模式：生成 1 个父文档，包含 {len(child_documents)} 个子文档")
            return [merged_document]

        except Exception as e:
            logger.error(f"FULL_DOC模式转换失败: {str(e)}")
            raise

    def _split_child_documents(
        self,
        parent_document: Document,
        process_rule: ProcessRule,
        **kwargs
    ) -> List[ChildDocument]:
        """分割子文档

        根据处理规则将父文档分割为多个子文档。
        支持多种分割策略和灵活的配置选项。

        Args:
            parent_document: 父文档
            process_rule: 处理规则
            **kwargs: 额外参数

        Returns:
            List[ChildDocument]: 子文档列表
        """
        try:
            logger.info(f"开始分割子文档，父文档长度: {len(parent_document.page_content)} 字符")

            # 获取子块分割规则
            subchunk_segmentation = process_rule.rules.get("subchunk_segmentation", {})

            # 获取分割参数
            max_tokens = subchunk_segmentation.get("max_tokens", 512)
            chunk_overlap = subchunk_segmentation.get("chunk_overlap", 50)
            separator = subchunk_segmentation.get("separator", "\n")

            # 验证分割参数
            if max_tokens <= 0:
                logger.warning(f"无效的max_tokens值: {max_tokens}，使用默认值512")
                max_tokens = 512

            if chunk_overlap < 0 or chunk_overlap >= max_tokens:
                logger.warning(f"无效的chunk_overlap值: {chunk_overlap}，使用默认值50")
                chunk_overlap = 50

            # 创建分割器，支持更丰富的分隔符
            from .text_splitter import FixedRecursiveCharacterTextSplitter

            # 根据分隔符类型选择合适的递归分隔符序列
            if separator == "\n":
                # 换行符分割：使用更细粒度的分隔符序列
                separators = ["\n\n", "\n", "。", "！", "？", ". ", "! ", "? ", "；", "; ", "，", ", ", " ", ""]
            elif separator == "\n\n":
                # 段落分割：使用段落级别的分隔符序列
                separators = ["\n\n", "\n", "。", ". ", " ", ""]
            else:
                # 自定义分隔符：使用指定分隔符加上通用分隔符
                separators = [separator, "\n\n", "\n", "。", ". ", " ", ""]

            child_splitter = FixedRecursiveCharacterTextSplitter(
                chunk_size=max_tokens,
                chunk_overlap=chunk_overlap,
                separators=separators
            )

            logger.info(f"创建子文档分割器: chunk_size={max_tokens}, overlap={chunk_overlap}, separator='{separator}'")

            # 分割子文档
            child_nodes = child_splitter.split_documents([parent_document])
            child_documents = []

            # 获取预览模式限制
            preview_mode = kwargs.get("preview", False)
            max_children_per_parent = kwargs.get("max_children_per_parent", 10)

            for i, child_node in enumerate(child_nodes):
                # 预览模式下限制子文档数量
                if preview_mode and i >= max_children_per_parent:
                    logger.info(f"预览模式：达到最大子文档数量限制 {max_children_per_parent}")
                    break

                # 清理和验证子文档内容
                child_content = child_node.page_content.strip()
                if not child_content:
                    continue

                # 处理内容格式：移除开头的标点符号
                if child_content.startswith((".", "。", ",", "，", ";", "；")):
                    child_content = child_content[1:].strip()

                # 跳过过短的子文档
                min_child_length = kwargs.get("min_child_length", 10)
                if len(child_content) < min_child_length:
                    logger.debug(f"跳过过短的子文档 (长度: {len(child_content)}): {child_content[:50]}...")
                    continue

                # 生成子文档ID和哈希
                doc_id = str(uuid.uuid4())
                doc_hash = self._generate_text_hash(child_content)

                # 创建子文档
                child_document = ChildDocument(
                    page_content=child_content,
                    metadata=parent_document.metadata.copy(),
                    parent_id=parent_document.metadata.get("doc_id"),
                    parent_content=parent_document.page_content[:500] + "..." if len(parent_document.page_content) > 500 else parent_document.page_content,
                    position=len(child_documents)  # 使用实际添加的子文档数量作为位置
                )

                # 更新子文档元数据
                child_document.metadata.update({
                    "doc_id": doc_id,
                    "doc_hash": doc_hash,
                    "is_child": True,
                    "type": "child",  # 修复：添加type字段以兼容传统处理器
                    "parent_id": parent_document.metadata.get("doc_id"),
                    "position": len(child_documents),
                    "content_length": len(child_content),
                    "split_method": "recursive_character",
                    "separator_used": separator
                })

                child_documents.append(child_document)

            logger.info(f"成功生成 {len(child_documents)} 个子文档")

            # 如果没有生成任何子文档，创建一个包含完整父文档内容的子文档
            if not child_documents and parent_document.page_content.strip():
                logger.warning("未能分割出子文档，创建单个子文档包含完整内容")

                doc_id = str(uuid.uuid4())
                doc_hash = self._generate_text_hash(parent_document.page_content)

                fallback_child = ChildDocument(
                    page_content=parent_document.page_content,
                    metadata=parent_document.metadata.copy(),
                    parent_id=parent_document.metadata.get("doc_id"),
                    parent_content=parent_document.page_content,
                    position=0
                )

                fallback_child.metadata.update({
                    "doc_id": doc_id,
                    "doc_hash": doc_hash,
                    "is_child": True,
                    "type": "child",  # 修复：添加type字段以兼容传统处理器
                    "parent_id": parent_document.metadata.get("doc_id"),
                    "position": 0,
                    "content_length": len(parent_document.page_content),
                    "split_method": "fallback_full_content",
                    "is_fallback": True
                })

                child_documents.append(fallback_child)
                logger.info("创建了1个回退子文档")

            return child_documents

        except Exception as e:
            logger.error(f"分割子文档失败: {str(e)}")
            # 返回空列表而不是抛出异常，保证处理流程的稳定性
            return []

    def _validate_process_rule(self, process_rule: ProcessRule) -> ProcessRule:
        """验证和标准化处理规则

        Args:
            process_rule: 输入的处理规则

        Returns:
            ProcessRule: 验证后的处理规则
        """
        try:
            # 验证父文档模式
            if process_rule.parent_mode not in [ParentMode.PARAGRAPH, ParentMode.FULL_DOC]:
                logger.warning(f"无效的父文档模式: {process_rule.parent_mode}，使用默认值PARAGRAPH")
                process_rule.parent_mode = ParentMode.PARAGRAPH

            # 验证分割规则
            if not process_rule.rules:
                process_rule.rules = process_rule._get_default_rules()
                logger.info("使用默认处理规则")

            # 验证父文档分割参数
            segmentation = process_rule.rules.get("segmentation", {})
            if segmentation.get("max_tokens", 0) <= 0:
                segmentation["max_tokens"] = 1024
                logger.warning("父文档max_tokens无效，使用默认值1024")

            if segmentation.get("chunk_overlap", -1) < 0:
                segmentation["chunk_overlap"] = 200
                logger.warning("父文档chunk_overlap无效，使用默认值200")

            # 验证子文档分割参数
            subchunk_segmentation = process_rule.rules.get("subchunk_segmentation", {})
            if subchunk_segmentation.get("max_tokens", 0) <= 0:
                subchunk_segmentation["max_tokens"] = 512
                logger.warning("子文档max_tokens无效，使用默认值512")

            if subchunk_segmentation.get("chunk_overlap", -1) < 0:
                subchunk_segmentation["chunk_overlap"] = 50
                logger.warning("子文档chunk_overlap无效，使用默认值50")

            # 确保子文档分块大小不超过父文档分块大小
            parent_max_tokens = segmentation.get("max_tokens", 1024)
            child_max_tokens = subchunk_segmentation.get("max_tokens", 512)
            if child_max_tokens > parent_max_tokens:
                subchunk_segmentation["max_tokens"] = parent_max_tokens // 2
                logger.warning(f"子文档分块大小超过父文档，调整为 {parent_max_tokens // 2}")

            return process_rule

        except Exception as e:
            logger.error(f"验证处理规则失败: {str(e)}")
            # 返回默认规则
            return ProcessRule()

    def _generate_text_hash(self, text: str) -> str:
        """生成文本哈希值

        Args:
            text: 要生成哈希的文本

        Returns:
            str: 哈希值
        """
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def load(self, documents: List[Document], **kwargs) -> None:
        """加载文档到存储系统

        Args:
            documents: 要加载的文档列表
            **kwargs: 额外参数，包括：
                - with_keywords: 是否包含关键词
                - collection_name: 集合名称

        Raises:
            Exception: 加载失败时抛出异常
        """
        try:
            logger.info(f"开始加载 {len(documents)} 个文档到存储系统")

            with_keywords = kwargs.get("with_keywords", True)
            collection_name = kwargs.get("collection_name")

            # 设置集合名称
            if collection_name and hasattr(self.vector_store, 'set_collection'):
                self.vector_store.set_collection(collection_name)

            # 处理每个父文档
            for document in documents:
                child_documents = document.children
                if child_documents:
                    # 准备子文档数据
                    child_docs = []
                    child_vectors = []

                    for child_doc in child_documents:
                        # 转换为标准Document格式
                        formatted_child = Document(
                            page_content=child_doc.page_content,
                            metadata=child_doc.metadata,
                            doc_id=child_doc.doc_id,
                            doc_hash=child_doc.doc_hash
                        )
                        child_docs.append(formatted_child)

                        # 生成向量嵌入
                        if self.embedding_model:
                            try:
                                vector = self.embedding_model.embed_text(child_doc.page_content)
                                child_vectors.append(vector)
                            except Exception as e:
                                logger.warning(f"生成向量嵌入失败: {str(e)}")
                                # 使用零向量作为占位符
                                child_vectors.append([0.0] * 768)  # 假设768维
                        else:
                            child_vectors.append([0.0] * 768)

                    # 存储子文档到向量数据库
                    if child_docs and child_vectors:
                        self.vector_store.insert(child_docs, child_vectors)
                        logger.info(f"成功存储 {len(child_docs)} 个子文档到向量数据库")

                    # 存储父文档到文档数据库
                    if self.document_store:
                        try:
                            # 这里可以添加文档存储逻辑
                            pass
                        except Exception as e:
                            logger.warning(f"存储父文档到文档数据库失败: {str(e)}")

            logger.info("文档加载完成")

        except Exception as e:
            logger.error(f"文档加载失败: {str(e)}")
            raise

    def clean(self, node_ids: Optional[List[str]] = None, **kwargs) -> None:
        """清理文档

        Args:
            node_ids: 要清理的节点ID列表，如果为None则清理所有
            **kwargs: 额外参数，包括：
                - delete_child_chunks: 是否删除子块
                - collection_name: 集合名称

        Raises:
            Exception: 清理失败时抛出异常
        """
        try:
            logger.info(f"开始清理文档，节点ID: {node_ids}")

            delete_child_chunks = kwargs.get("delete_child_chunks", False)
            collection_name = kwargs.get("collection_name")

            # 设置集合名称
            if collection_name and hasattr(self.vector_store, 'set_collection'):
                self.vector_store.set_collection(collection_name)

            if node_ids:
                # 清理指定节点
                if self.vector_store:
                    self.vector_store.delete_by_ids(node_ids)
                    logger.info(f"成功从向量数据库删除 {len(node_ids)} 个节点")

                # 清理文档数据库中的相关记录
                if self.document_store and delete_child_chunks:
                    try:
                        # 这里可以添加文档数据库清理逻辑
                        pass
                    except Exception as e:
                        logger.warning(f"清理文档数据库失败: {str(e)}")
            else:
                # 清理所有文档
                if self.vector_store:
                    self.vector_store.delete_all()
                    logger.info("成功清理向量数据库中的所有文档")

                if self.document_store and delete_child_chunks:
                    try:
                        # 这里可以添加文档数据库清理逻辑
                        pass
                    except Exception as e:
                        logger.warning(f"清理文档数据库失败: {str(e)}")

            logger.info("文档清理完成")

        except Exception as e:
            logger.error(f"文档清理失败: {str(e)}")
            raise

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        score_threshold: float = 0.0,
        **kwargs
    ) -> List[Document]:
        """检索文档

        Args:
            query: 查询文本
            top_k: 返回结果数量
            score_threshold: 分数阈值
            **kwargs: 额外参数，包括：
                - retrieval_method: 检索方法
                - reranking_model: 重排序模型
                - collection_name: 集合名称

        Returns:
            List[Document]: 检索结果文档列表

        Raises:
            Exception: 检索失败时抛出异常
        """
        try:
            logger.info(f"开始检索文档，查询: {query[:50]}...")

            retrieval_method = kwargs.get("retrieval_method", "vector")
            reranking_model = kwargs.get("reranking_model", {})
            collection_name = kwargs.get("collection_name")

            # 设置集合名称
            if collection_name and hasattr(self.vector_store, 'set_collection'):
                self.vector_store.set_collection(collection_name)

            # 使用检索服务进行检索
            if self.retrieval_service:
                results = self.retrieval_service.search(
                    query=query,
                    top_k=top_k,
                    score_threshold=score_threshold,
                    search_type=retrieval_method
                )
            else:
                # 直接使用向量存储进行检索
                if not self.embedding_model:
                    raise ValueError("嵌入模型未初始化，无法进行向量检索")

                # 生成查询向量
                query_vector = self.embedding_model.embed_text(query)

                # 执行向量搜索
                results = self.vector_store.search(
                    query_vector=query_vector,
                    top_k=top_k,
                    score_threshold=score_threshold
                )

            # 组织检索结果
            docs = []
            for result in results:
                # 检查分数阈值
                if hasattr(result, 'score') and result.score > score_threshold:
                    # 构建文档对象
                    metadata = getattr(result, 'metadata', {})
                    metadata["score"] = getattr(result, 'score', 0.0)

                    doc = Document(
                        page_content=getattr(result, 'page_content', ''),
                        metadata=metadata
                    )
                    docs.append(doc)
                elif not hasattr(result, 'score'):
                    # 如果结果没有分数字段，直接添加
                    doc = Document(
                        page_content=getattr(result, 'page_content', ''),
                        metadata=getattr(result, 'metadata', {})
                    )
                    docs.append(doc)

            logger.info(f"检索完成，返回 {len(docs)} 个结果")
            return docs

        except Exception as e:
            logger.error(f"文档检索失败: {str(e)}")
            raise

    def batch_process(
        self,
        extract_settings: List[ExtractSetting],
        process_rule: Optional[ProcessRule] = None,
        preview_mode: bool = False,
        **kwargs
    ) -> List[Document]:
        """批量处理文档

        Args:
            extract_settings: 提取设置列表
            process_rule: 处理规则
            preview_mode: 是否预览模式
            **kwargs: 额外参数

        Returns:
            List[Document]: 处理后的文档列表
        """
        try:
            logger.info(f"开始批量处理 {len(extract_settings)} 个文档")

            all_documents = []

            for extract_setting in extract_settings:
                try:
                    # 提取文档
                    documents = self.extract(extract_setting, **kwargs)

                    # 转换文档
                    transformed_docs = self.transform(
                        documents,
                        process_rule=process_rule.__dict__ if process_rule else None,
                        preview=preview_mode,
                        **kwargs
                    )

                    all_documents.extend(transformed_docs)

                    # 预览模式限制
                    if preview_mode and len(all_documents) >= 50:
                        logger.info("预览模式：已达到批量处理文档数量限制")
                        break

                except Exception as e:
                    logger.error(f"处理文档失败 {extract_setting.file_path}: {str(e)}")
                    continue

            logger.info(f"批量处理完成，共处理 {len(all_documents)} 个文档")
            return all_documents

        except Exception as e:
            logger.error(f"批量处理失败: {str(e)}")
            raise
