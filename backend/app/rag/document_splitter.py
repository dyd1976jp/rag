"""
文档分割器模块
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
import json
import hashlib
import uuid
from enum import Enum

from .models import Document, DocumentSegment, ChildDocument
from .text_splitter import EnhanceRecursiveCharacterTextSplitter, FixedRecursiveCharacterTextSplitter
from .cleaner.clean_processor import CleanProcessor, CleanLevel

logger = logging.getLogger(__name__)

class SplitMode(str, Enum):
    """分割模式"""
    PARAGRAPH = "paragraph"  # 段落模式
    QA = "qa"  # 问答模式
    PARENT_CHILD = "parent_child"  # 父子模式

class Rule:
    """分割规则"""
    def __init__(
        self,
        mode: SplitMode = SplitMode.PARAGRAPH,
        max_tokens: int = 1024,  # 默认父块最大长度
        chunk_overlap: int = 200,  # 默认父块重叠
        fixed_separator: str = "\n\n",  # 默认父块分隔符
        subchunk_max_tokens: int = 512,  # 默认子块最大长度
        subchunk_overlap: int = 50,  # 默认子块重叠
        subchunk_separator: str = "\n",  # 默认子块分隔符
        clean_text: bool = True,
        keep_separator: bool = False,
        remove_empty_lines: bool = True,
        normalize_whitespace: bool = True,
        # 新增配置选项
        min_chunk_size: int = 50,  # 最小块大小
        max_chunk_size: Optional[int] = None,  # 最大块大小限制
        separators: Optional[List[str]] = None,  # 分隔符优先级列表
        subchunk_separators: Optional[List[str]] = None,  # 子块分隔符列表
        enable_smart_splitting: bool = True,  # 启用智能分割
        preserve_structure: bool = True,  # 保持文档结构
        quality_threshold: float = 0.8,  # 质量阈值
        enable_validation: bool = True,  # 启用验证
        custom_rules: Optional[Dict[str, Any]] = None  # 自定义规则
    ):
        self.mode = mode
        self.max_tokens = max_tokens
        self.chunk_overlap = chunk_overlap
        self.fixed_separator = fixed_separator
        self.subchunk_max_tokens = subchunk_max_tokens
        self.subchunk_overlap = subchunk_overlap
        self.subchunk_separator = subchunk_separator
        self.clean_text = clean_text
        self.keep_separator = keep_separator
        self.remove_empty_lines = remove_empty_lines
        self.normalize_whitespace = normalize_whitespace

        # 新增属性
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.enable_smart_splitting = enable_smart_splitting
        self.preserve_structure = preserve_structure
        self.quality_threshold = quality_threshold
        self.enable_validation = enable_validation
        self.custom_rules = custom_rules or {}

        # 设置分隔符列表
        self.separators = separators or self._get_default_separators()
        self.subchunk_separators = subchunk_separators or self._get_default_subchunk_separators()

        # 验证配置
        if self.enable_validation:
            self._validate_config()

    def _get_default_separators(self) -> List[str]:
        """获取默认分隔符列表"""
        if self.mode == SplitMode.PARENT_CHILD:
            return [
                "\n\n\n",  # 多段落分隔
                "\n\n",    # 段落分隔
                "\n",      # 行分隔
                "。",      # 中文句号
                ".",       # 英文句号
                "！",      # 中文感叹号
                "!",       # 英文感叹号
                "？",      # 中文问号
                "?",       # 英文问号
                "；",      # 中文分号
                ";",       # 英文分号
                "，",      # 中文逗号
                ",",       # 英文逗号
                " ",       # 空格
                ""         # 字符级分割
            ]
        else:
            return [self.fixed_separator, "\n", " ", ""]

    def _get_default_subchunk_separators(self) -> List[str]:
        """获取默认子块分隔符列表"""
        return [
            "\n",      # 行分隔
            "。",      # 中文句号
            ".",       # 英文句号
            "！",      # 中文感叹号
            "!",       # 英文感叹号
            "？",      # 中文问号
            "?",       # 英文问号
            "；",      # 中文分号
            ";",       # 英文分号
            " ",       # 空格
            ""         # 字符级分割
        ]

    def _validate_config(self) -> None:
        """验证配置参数"""
        errors = []

        if self.max_tokens <= 0:
            errors.append("max_tokens必须大于0")

        if self.chunk_overlap < 0:
            errors.append("chunk_overlap不能小于0")

        if self.chunk_overlap >= self.max_tokens:
            errors.append("chunk_overlap不能大于等于max_tokens")

        if self.subchunk_max_tokens <= 0:
            errors.append("subchunk_max_tokens必须大于0")

        if self.subchunk_overlap < 0:
            errors.append("subchunk_overlap不能小于0")

        if self.subchunk_overlap >= self.subchunk_max_tokens:
            errors.append("subchunk_overlap不能大于等于subchunk_max_tokens")

        if self.min_chunk_size <= 0:
            errors.append("min_chunk_size必须大于0")

        if self.max_chunk_size and self.max_chunk_size < self.min_chunk_size:
            errors.append("max_chunk_size不能小于min_chunk_size")

        if self.quality_threshold < 0 or self.quality_threshold > 1:
            errors.append("quality_threshold必须在0-1之间")

        if errors:
            raise ValueError(f"配置验证失败: {'; '.join(errors)}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "mode": self.mode.value,
            "max_tokens": self.max_tokens,
            "chunk_overlap": self.chunk_overlap,
            "fixed_separator": self.fixed_separator,
            "subchunk_max_tokens": self.subchunk_max_tokens,
            "subchunk_overlap": self.subchunk_overlap,
            "subchunk_separator": self.subchunk_separator,
            "clean_text": self.clean_text,
            "keep_separator": self.keep_separator,
            "remove_empty_lines": self.remove_empty_lines,
            "normalize_whitespace": self.normalize_whitespace,
            "min_chunk_size": self.min_chunk_size,
            "max_chunk_size": self.max_chunk_size,
            "separators": self.separators,
            "subchunk_separators": self.subchunk_separators,
            "enable_smart_splitting": self.enable_smart_splitting,
            "preserve_structure": self.preserve_structure,
            "quality_threshold": self.quality_threshold,
            "enable_validation": self.enable_validation,
            "custom_rules": self.custom_rules
        }

    @classmethod
    def from_dict(cls, rule_dict: Dict[str, Any]) -> 'Rule':
        """从字典创建规则对象"""
        mode = SplitMode(rule_dict.get("mode", SplitMode.PARAGRAPH))
        return cls(
            mode=mode,
            max_tokens=rule_dict.get("max_tokens", 1024),
            chunk_overlap=rule_dict.get("chunk_overlap", 200),
            fixed_separator=rule_dict.get("fixed_separator", "\n\n"),
            subchunk_max_tokens=rule_dict.get("subchunk_max_tokens", 512),
            subchunk_overlap=rule_dict.get("subchunk_overlap", 50),
            subchunk_separator=rule_dict.get("subchunk_separator", "\n"),
            clean_text=rule_dict.get("clean_text", True),
            keep_separator=rule_dict.get("keep_separator", False),
            remove_empty_lines=rule_dict.get("remove_empty_lines", True),
            normalize_whitespace=rule_dict.get("normalize_whitespace", True),
            min_chunk_size=rule_dict.get("min_chunk_size", 50),
            max_chunk_size=rule_dict.get("max_chunk_size"),
            separators=rule_dict.get("separators"),
            subchunk_separators=rule_dict.get("subchunk_separators"),
            enable_smart_splitting=rule_dict.get("enable_smart_splitting", True),
            preserve_structure=rule_dict.get("preserve_structure", True),
            quality_threshold=rule_dict.get("quality_threshold", 0.8),
            enable_validation=rule_dict.get("enable_validation", True),
            custom_rules=rule_dict.get("custom_rules", {})
        )

    def copy(self) -> 'Rule':
        """创建规则副本"""
        return Rule.from_dict(self.to_dict())

    def update_for_mode(self, mode: SplitMode) -> 'Rule':
        """根据模式更新规则配置

        Args:
            mode: 新的分割模式

        Returns:
            Rule: 更新后的规则副本
        """
        new_rule = self.copy()
        new_rule.mode = mode

        if mode == SplitMode.PARENT_CHILD:
            # 父子模式的优化配置
            new_rule.max_tokens = max(1024, new_rule.max_tokens)
            new_rule.subchunk_max_tokens = min(512, new_rule.max_tokens // 2)
            new_rule.separators = new_rule._get_default_separators()
            new_rule.enable_smart_splitting = True
            new_rule.preserve_structure = True
        elif mode == SplitMode.PARAGRAPH:
            # 段落模式的优化配置
            new_rule.fixed_separator = "\n\n"
            new_rule.separators = ["\n\n", "\n", "。", ".", " ", ""]
            new_rule.preserve_structure = True
        elif mode == SplitMode.QA:
            # 问答模式的优化配置
            new_rule.separators = ["？", "?", "。", ".", "\n", " ", ""]
            new_rule.enable_smart_splitting = True

        return new_rule

    def optimize_for_content_type(self, content_type: str) -> 'Rule':
        """根据内容类型优化规则

        Args:
            content_type: 内容类型 (academic, news, dialogue, code, etc.)

        Returns:
            Rule: 优化后的规则副本
        """
        new_rule = self.copy()

        if content_type == "academic":
            # 学术文档优化
            new_rule.max_tokens = 1536
            new_rule.chunk_overlap = 300
            new_rule.separators = ["\n\n\n", "\n\n", "。", ".", "；", ";", "\n", " ", ""]
            new_rule.preserve_structure = True
            new_rule.quality_threshold = 0.9
        elif content_type == "news":
            # 新闻文档优化
            new_rule.max_tokens = 1024
            new_rule.chunk_overlap = 150
            new_rule.separators = ["\n\n", "\n", "。", ".", "！", "!", "？", "?", " ", ""]
            new_rule.enable_smart_splitting = True
        elif content_type == "dialogue":
            # 对话文档优化
            new_rule.max_tokens = 512
            new_rule.chunk_overlap = 50
            new_rule.separators = ["\n", "？", "?", "！", "!", "。", ".", " ", ""]
            new_rule.preserve_structure = False
        elif content_type == "code":
            # 代码文档优化
            new_rule.max_tokens = 2048
            new_rule.chunk_overlap = 100
            new_rule.separators = ["\n\n", "\n", "{", "}", ";", " ", ""]
            new_rule.clean_text = False
            new_rule.normalize_whitespace = False
        elif content_type == "legal":
            # 法律文档优化
            new_rule.max_tokens = 2048
            new_rule.chunk_overlap = 400
            new_rule.separators = ["第", "条", "款", "项", "\n\n", "\n", "。", ".", " ", ""]
            new_rule.preserve_structure = True
            new_rule.quality_threshold = 0.95

        return new_rule

    def merge_with(self, other: 'Rule') -> 'Rule':
        """与另一个规则合并

        Args:
            other: 另一个规则对象

        Returns:
            Rule: 合并后的规则
        """
        merged_dict = self.to_dict()
        other_dict = other.to_dict()

        # 合并自定义规则
        merged_custom_rules = merged_dict.get("custom_rules", {})
        merged_custom_rules.update(other_dict.get("custom_rules", {}))

        # 更新其他配置（other的配置优先）
        for key, value in other_dict.items():
            if key != "custom_rules":
                merged_dict[key] = value

        merged_dict["custom_rules"] = merged_custom_rules
        return Rule.from_dict(merged_dict)

    def get_effective_separators(self, is_subchunk: bool = False) -> List[str]:
        """获取有效的分隔符列表

        Args:
            is_subchunk: 是否为子块分割

        Returns:
            List[str]: 分隔符列表
        """
        if is_subchunk:
            return self.subchunk_separators
        else:
            return self.separators

    def calculate_optimal_chunk_size(self, content_length: int) -> int:
        """计算最优块大小

        Args:
            content_length: 内容长度

        Returns:
            int: 最优块大小
        """
        if not self.enable_smart_splitting:
            return self.max_tokens

        # 根据内容长度动态调整
        if content_length < 500:
            return min(self.max_tokens, content_length)
        elif content_length < 2000:
            return min(self.max_tokens, content_length // 2)
        else:
            return self.max_tokens


class SplitterConfigManager:
    """分割器配置管理器"""

    def __init__(self):
        self._presets: Dict[str, Rule] = {}
        self._load_default_presets()

    def _load_default_presets(self) -> None:
        """加载默认预设配置"""
        # 通用配置
        self._presets["default"] = Rule()

        # 父子文档配置
        self._presets["parent_child"] = Rule(
            mode=SplitMode.PARENT_CHILD,
            max_tokens=1024,
            chunk_overlap=200,
            subchunk_max_tokens=512,
            subchunk_overlap=50,
            enable_smart_splitting=True,
            preserve_structure=True
        )

        # 段落模式配置
        self._presets["paragraph"] = Rule(
            mode=SplitMode.PARAGRAPH,
            max_tokens=800,
            chunk_overlap=100,
            fixed_separator="\n\n",
            preserve_structure=True
        )

        # 问答模式配置
        self._presets["qa"] = Rule(
            mode=SplitMode.QA,
            max_tokens=512,
            chunk_overlap=50,
            separators=["？", "?", "。", ".", "\n", " ", ""],
            enable_smart_splitting=True
        )

        # 学术文档配置
        self._presets["academic"] = Rule(
            mode=SplitMode.PARENT_CHILD,
            max_tokens=1536,
            chunk_overlap=300,
            subchunk_max_tokens=768,
            subchunk_overlap=100,
            separators=["\n\n\n", "\n\n", "。", ".", "；", ";", "\n", " ", ""],
            preserve_structure=True,
            quality_threshold=0.9
        )

        # 新闻文档配置
        self._presets["news"] = Rule(
            mode=SplitMode.PARAGRAPH,
            max_tokens=1024,
            chunk_overlap=150,
            separators=["\n\n", "\n", "。", ".", "！", "!", "？", "?", " ", ""],
            enable_smart_splitting=True
        )

        # 代码文档配置
        self._presets["code"] = Rule(
            mode=SplitMode.PARAGRAPH,
            max_tokens=2048,
            chunk_overlap=100,
            separators=["\n\n", "\n", "{", "}", ";", " ", ""],
            clean_text=False,
            normalize_whitespace=False
        )

    def get_preset(self, preset_name: str) -> Optional[Rule]:
        """获取预设配置

        Args:
            preset_name: 预设名称

        Returns:
            Optional[Rule]: 预设规则，如果不存在返回None
        """
        return self._presets.get(preset_name)

    def add_preset(self, name: str, rule: Rule) -> None:
        """添加预设配置

        Args:
            name: 预设名称
            rule: 规则对象
        """
        self._presets[name] = rule.copy()

    def remove_preset(self, name: str) -> bool:
        """删除预设配置

        Args:
            name: 预设名称

        Returns:
            bool: 是否成功删除
        """
        if name in self._presets and name != "default":
            del self._presets[name]
            return True
        return False

    def list_presets(self) -> List[str]:
        """列出所有预设名称

        Returns:
            List[str]: 预设名称列表
        """
        return list(self._presets.keys())

    def create_rule_from_params(
        self,
        mode: str = "paragraph",
        parent_chunk_size: int = 1024,
        parent_chunk_overlap: int = 200,
        child_chunk_size: int = 512,
        child_chunk_overlap: int = 50,
        parent_separator: str = "\n\n",
        child_separator: str = "\n",
        content_type: Optional[str] = None,
        **kwargs
    ) -> Rule:
        """从参数创建规则

        Args:
            mode: 分割模式
            parent_chunk_size: 父块大小
            parent_chunk_overlap: 父块重叠
            child_chunk_size: 子块大小
            child_chunk_overlap: 子块重叠
            parent_separator: 父块分隔符
            child_separator: 子块分隔符
            content_type: 内容类型
            **kwargs: 其他参数

        Returns:
            Rule: 创建的规则对象
        """
        # 确定分割模式
        if mode == "parent_child":
            split_mode = SplitMode.PARENT_CHILD
        elif mode == "qa":
            split_mode = SplitMode.QA
        else:
            split_mode = SplitMode.PARAGRAPH

        # 创建基础规则
        rule = Rule(
            mode=split_mode,
            max_tokens=parent_chunk_size,
            chunk_overlap=parent_chunk_overlap,
            fixed_separator=parent_separator,
            subchunk_max_tokens=child_chunk_size,
            subchunk_overlap=child_chunk_overlap,
            subchunk_separator=child_separator,
            **kwargs
        )

        # 根据内容类型优化
        if content_type:
            rule = rule.optimize_for_content_type(content_type)

        return rule

    def get_recommended_rule(
        self,
        content_length: int,
        content_type: Optional[str] = None,
        use_parent_child: bool = True
    ) -> Rule:
        """获取推荐的规则配置

        Args:
            content_length: 内容长度
            content_type: 内容类型
            use_parent_child: 是否使用父子模式

        Returns:
            Rule: 推荐的规则配置
        """
        # 根据内容类型选择基础预设
        if content_type and content_type in self._presets:
            base_rule = self._presets[content_type].copy()
        elif use_parent_child:
            base_rule = self._presets["parent_child"].copy()
        else:
            base_rule = self._presets["paragraph"].copy()

        # 根据内容长度调整
        if content_length < 1000:
            # 短文档
            base_rule.max_tokens = min(base_rule.max_tokens, 512)
            base_rule.chunk_overlap = min(base_rule.chunk_overlap, 50)
        elif content_length > 10000:
            # 长文档
            base_rule.max_tokens = max(base_rule.max_tokens, 1536)
            base_rule.chunk_overlap = max(base_rule.chunk_overlap, 300)

        return base_rule


# 全局配置管理器实例
config_manager = SplitterConfigManager()

class DocumentSplitter:
    """文档分割器基类"""
    def __init__(
        self,
        chunk_size: int = 1024,  # 默认块大小
        chunk_overlap: int = 200,  # 默认重叠
        fixed_separator: str = "\n\n",  # 默认分隔符
        keep_separator: bool = True,
        add_start_index: bool = True
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.fixed_separator = fixed_separator
        self.keep_separator = keep_separator
        self.add_start_index = add_start_index
        
        # 创建文本分割器
        self.text_splitter = FixedRecursiveCharacterTextSplitter.from_encoder(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            fixed_separator=self.fixed_separator,
            separators=["\n\n", "\n", "。", "！", "？", ". ", " ", ""],
            keep_separator=self.keep_separator,
            length_function=lambda x: [len(text) for text in x]
        )
        
        logger.info(f"初始化文档分割器: 分块大小={self.chunk_size}, 重叠={self.chunk_overlap}")
        
    def _is_title(self, text: str) -> bool:
        """判断是否为标题"""
        # 标题模式
        title_patterns = [
            r"^第[一二三四五六七八九十百千万]+[章节篇]",  # 中文数字章节
            r"^[0-9]+\.[0-9]+(\.[0-9]+)?",  # 数字编号（如1.2, 1.2.3）
            r"^[一二三四五六七八九十][、.]",  # 中文数字编号
            r"^[A-Z]\.",  # 字母编号
            r"^[（(][一二三四五六七八九十][)）]",  # 带括号的中文数字
            r"^[（(][0-9]+[)）]",  # 带括号的数字
            r"^[【\[].+[】\]]$",  # 方括号包围
            r"^《.+》$",  # 书名号包围
            r"^目\s*录$",  # 目录
            r"^前\s*言$",  # 前言
            r"^概\s*述$",  # 概述
            r"^简\s*介$",  # 简介
            r"^说\s*明$",  # 说明
            r"^注\s*意$",  # 注意
            r"^警\s*告$",  # 警告
        ]
        return any(re.match(pattern, text.strip()) for pattern in title_patterns)

    def _is_list_item(self, text: str) -> bool:
        """判断是否为列表项"""
        # 列表项模式
        list_patterns = [
            r"^[•·○●◆▪-]",  # 常见列表符号
            r"^[0-9]+\.",  # 数字编号
            r"^[a-zA-Z]\.",  # 字母编号
            r"^\([0-9]+\)",  # 带括号的数字
            r"^\([a-zA-Z]\)",  # 带括号的字母
            r"^[①②③④⑤⑥⑦⑧⑨⑩]",  # 圆圈数字
            r"^[㈠㈡㈢㈣㈤㈥㈦㈧㈨㈩]",  # 括号数字
            r"^[⒈⒉⒊⒋⒌⒍⒎⒏⒐⒑]",  # 带点数字
        ]
        return any(re.match(pattern, text.strip()) for pattern in list_patterns)
        
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """智能分割段落"""
        # 1. 首先按双换行分割
        paragraphs = []
        
        # 预处理：规范化换行符
        text = text.replace('\r\n', '\n')
        text = re.sub(r'\n{3,}', '\n\n', text)  # 将多个换行符压缩为两个
        
        # 按双换行符分割
        raw_paragraphs = text.split("\n\n")
        
        current_paragraph = []
        
        for para in raw_paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # 处理单换行的情况
            lines = para.split("\n")
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                    
                # 如果是标题，作为独立段落
                if self._is_title(line):
                    # 保存之前的段落
                    if current_paragraph:
                        paragraphs.append("\n".join(current_paragraph))
                        current_paragraph = []
                    # 添加标题作为独立段落
                    paragraphs.append(line)
                    continue
                
                # 如果是列表项
                if self._is_list_item(line):
                    # 如果前一行不是列表项，开始新段落
                    if i > 0 and not self._is_list_item(lines[i-1].strip()):
                        if current_paragraph:
                            paragraphs.append("\n".join(current_paragraph))
                            current_paragraph = []
                    current_paragraph.append(line)
                    continue
                
                # 如果当前行以标点符号结尾，说明是一个完整句子
                if line[-1] in "。！？.!?":
                    current_paragraph.append(line)
                    # 如果下一行是新主题（首字有特殊标记或缩进），保存当前段落
                    if i < len(lines) - 1:
                        next_line = lines[i+1].strip()
                        if (next_line and 
                            (self._is_new_topic(next_line) or 
                             self._is_title(next_line) or 
                             self._is_list_item(next_line))):
                            if current_paragraph:
                                paragraphs.append("\n".join(current_paragraph))
                                current_paragraph = []
                else:
                    current_paragraph.append(line)
        
        # 保存最后一个段落
        if current_paragraph:
            paragraphs.append("\n".join(current_paragraph))
        
        return paragraphs
        
    def _is_new_topic(self, text: str) -> bool:
        """判断是否是新主题的开始"""
        # 1. 检查是否以特殊字符开头
        special_starts = ["第", "一、", "二、", "三、", "1.", "2.", "3.", "注：", "注意：", "提示：", "警告："]
        for start in special_starts:
            if text.startswith(start):
                return True
                
        # 2. 检查是否以括号开头
        if text.startswith(("（", "(", "【", "[", "《")):
            return True
            
        # 3. 检查是否以数字编号开头
        if re.match(r"^\d+[.、]", text):
            return True
            
        return False
        
    def split_documents(self, documents: List[Document], rule: Optional[Rule] = None) -> List[DocumentSegment]:
        """分割文档"""
        if not rule:
            rule = Rule()
            
        all_segments = []
        
        for doc in documents:
            # 1. 首先按段落分割
            paragraphs = self._split_into_paragraphs(doc.page_content)
            
            # 2. 处理每个段落
            for i, para in enumerate(paragraphs):
                # 父块编号（独立序列）
                parent_number = i + 1

                # 创建父文档
                parent_id = str(uuid.uuid4())
                parent_segment = DocumentSegment(
                    id=parent_id,
                    page_content=para,
                    metadata={
                        "source": doc.source,
                        "type": "parent",
                        "index": i + 1,  # 保持原有的index字段兼容性
                        "parent_number": parent_number,  # 新增父块编号
                        "original_doc_id": doc.doc_id
                    }
                )
                all_segments.append(parent_segment)

                # 如果段落较长，创建子文档
                if len(para) > rule.subchunk_max_tokens:
                    child_splitter = FixedRecursiveCharacterTextSplitter(
                        chunk_size=rule.subchunk_max_tokens,
                        chunk_overlap=rule.subchunk_overlap,
                        fixed_separator=rule.subchunk_separator
                    )
                    child_texts = child_splitter.split_text(para)

                    for j, child_text in enumerate(child_texts):
                        child_id = str(uuid.uuid4())

                        # 子块编号（每个父块内部重新开始）
                        child_number = j + 1
                        combined_number = f"{parent_number}-{child_number}"

                        child_segment = DocumentSegment(
                            id=child_id,
                            page_content=child_text,
                            metadata={
                                "source": doc.source,
                                "type": "child",
                                "parent_id": parent_id,
                                "index": j + 1,  # 保持原有的index字段兼容性
                                "parent_number": parent_number,  # 父块编号
                                "child_number": child_number,  # 子块编号（父块内独立）
                                "combined_number": combined_number,  # 组合编号格式
                                "original_doc_id": doc.doc_id
                            }
                        )
                        all_segments.append(child_segment)
        
        return all_segments

class QADocumentSplitter(DocumentSplitter):
    """问答文档分割器"""
    def split_documents(self, documents: List[Document], rule: Optional[Rule] = None) -> List[DocumentSegment]:
        """分割问答文档"""
        if not rule:
            rule = Rule(mode=SplitMode.QA)
            
        all_segments = []
        
        for doc in documents:
            # 使用正则表达式匹配问答对
            qa_pattern = r"Q\d+:\s*(.*?)\s*A\d+:\s*([\s\S]*?)(?=Q\d+:|$)"
            matches = re.findall(qa_pattern, doc.page_content, re.UNICODE)
            
            for i, (question, answer) in enumerate(matches):
                if not question.strip() or not answer.strip():
                    continue

                # QA编号（独立序列）
                qa_number = i + 1

                # 创建问答片段
                qa_id = str(uuid.uuid4())
                qa_segment = DocumentSegment(
                    id=qa_id,
                    page_content=f"问：{question.strip()}\n答：{answer.strip()}",
                    metadata={
                        "source": doc.source,
                        "type": "qa",
                        "index": i + 1,  # 保持原有的index字段兼容性
                        "qa_number": qa_number,  # 新增QA编号
                        "question": question.strip(),
                        "answer": answer.strip(),
                        "original_doc_id": doc.doc_id
                    }
                )
                all_segments.append(qa_segment)
        
        return all_segments

class ParentChildDocumentSplitter(DocumentSplitter):
    """父子文档分割器"""
    def split_documents(self, documents: List[Document], rule: Optional[Rule] = None) -> List[DocumentSegment]:
        """分割父子文档"""
        if not rule:
            rule = Rule(mode=SplitMode.PARENT_CHILD)

        all_segments = []

        for doc in documents:
            # 1. 检查文档内容是否为空
            if not doc.page_content or not doc.page_content.strip():
                continue

            # 2. 创建父文档分词器
            parent_splitter = FixedRecursiveCharacterTextSplitter.from_encoder(
                chunk_size=rule.max_tokens,
                chunk_overlap=rule.chunk_overlap,
                fixed_separator=rule.fixed_separator,  # 使用传入的父分隔符
                separators=[rule.fixed_separator, "\n", "。", ". ", " ", ""],  # 递归分隔符
                keep_separator=rule.keep_separator,
                length_function=lambda x: [len(text) for text in x]
            )

            # 3. 分割父文档
            parent_nodes = parent_splitter.split_text(doc.page_content)

            logger.info(f"父文档分割完成，得到 {len(parent_nodes)} 个父块")

            # 4. 处理每个父节点
            for i, parent_content in enumerate(parent_nodes):
                parent_content = parent_content.strip()
                if not parent_content:
                    continue

                # 创建父文档
                parent_id = str(uuid.uuid4())
                parent_hash = hashlib.sha256(parent_content.encode()).hexdigest()

                # 父块编号（独立序列）
                parent_number = i + 1

                # 继承原始文档的所有元数据
                parent_metadata = doc.metadata.copy() if doc.metadata else {}
                parent_metadata.update({
                    "id": parent_id,  # 添加段落的唯一ID
                    "source": doc.source,
                    "type": "parent",
                    "index": i + 1,  # 保持原有的index字段兼容性
                    "parent_number": parent_number,  # 新增父块编号
                    "original_doc_id": doc.doc_id,
                    "doc_hash": parent_hash
                })

                parent_segment = DocumentSegment(
                    id=parent_id,
                    page_content=parent_content,
                    metadata=parent_metadata
                )

                logger.info(f"处理父块 {i+1}: 长度 {len(parent_content)} 字符，内容: {parent_content[:50]}...")

                # 5. 创建子文档分词器并分割子文档
                # 为换行符分割提供更好的递归分隔符序列
                if rule.subchunk_separator in ['\\n', '\n']:
                    # 对于换行符分割，使用更合理的递归分隔符序列
                    child_separators = ["\n", "。", "！", "？", ". ", "! ", "? ", "，", ", ", " ", ""]
                else:
                    child_separators = [rule.subchunk_separator, "。", ". ", " ", ""]

                child_splitter = FixedRecursiveCharacterTextSplitter.from_encoder(
                    chunk_size=rule.subchunk_max_tokens,
                    chunk_overlap=rule.subchunk_overlap,
                    fixed_separator=rule.subchunk_separator,  # 使用传入的子分隔符
                    separators=child_separators,  # 使用优化的递归分隔符
                    keep_separator=rule.keep_separator,
                    length_function=lambda x: [len(text) for text in x]
                )

                # 6. 分割子文档
                child_nodes = child_splitter.split_text(parent_content)
                logger.info(f"父块 {i+1} 分割为 {len(child_nodes)} 个子块")

                # 7. 处理每个子节点
                parent_segment.children = []
                for j, child_content in enumerate(child_nodes):
                    child_content = child_content.strip()
                    if not child_content:  # 只检查内容是否为空
                        continue

                    # 创建子文档
                    child_id = str(uuid.uuid4())
                    child_hash = hashlib.sha256(child_content.encode()).hexdigest()

                    # 子块编号（每个父块内部重新开始）
                    child_number = j + 1
                    combined_number = f"{parent_number}-{child_number}"

                    # 继承原始文档的所有元数据
                    child_metadata = doc.metadata.copy() if doc.metadata else {}
                    child_metadata.update({
                        "id": child_id,  # 添加段落的唯一ID
                        "source": doc.source,
                        "type": "child",
                        "parent_id": parent_id,
                        "index": j + 1,  # 保持原有的index字段兼容性
                        "parent_number": parent_number,  # 父块编号
                        "child_number": child_number,  # 子块编号（父块内独立）
                        "combined_number": combined_number,  # 组合编号格式
                        "original_doc_id": doc.doc_id,
                        "doc_hash": child_hash
                    })

                    child_segment = DocumentSegment(
                        id=child_id,
                        page_content=child_content,
                        metadata=child_metadata
                    )
                    parent_segment.children.append(child_segment)
                    logger.info(f"  子块 {j+1}: 长度 {len(child_content)} 字符，内容: {child_content[:30]}...")

                # 只添加父文档到结果中，子块通过父文档的children属性访问
                all_segments.append(parent_segment)

        logger.info(f"文档分割完成，总共生成 {len(all_segments)} 个段落")
        return all_segments