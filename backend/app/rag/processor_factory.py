"""
索引处理器工厂模式

提供统一的处理器创建和管理接口，支持不同类型的索引处理器。
基于工厂模式设计，便于扩展和维护。
"""

import logging
from typing import Dict, Any, Optional, Type, Union
from enum import Enum
from abc import ABC, abstractmethod

from .index_processor import BaseIndexProcessor, ParentChildIndexProcessor
from .vector_store import MilvusVectorStore
from .document_store import DocumentStore
from .embedding_model import EmbeddingModel
from .retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class ProcessorType(str, Enum):
    """处理器类型枚举"""
    PARENT_CHILD = "parent_child"      # 父子文档处理器
    STANDARD = "standard"              # 标准文档处理器
    HIERARCHICAL = "hierarchical"      # 层次化文档处理器
    SEMANTIC = "semantic"              # 语义分割处理器
    HYBRID = "hybrid"                  # 混合处理器
    CUSTOM = "custom"                  # 自定义处理器


class ProcessorPriority(int, Enum):
    """处理器优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class ProcessorStatus(str, Enum):
    """处理器状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    DISABLED = "disabled"


class ProcessorConfig:
    """处理器配置类"""

    def __init__(
        self,
        processor_type: ProcessorType = ProcessorType.PARENT_CHILD,
        vector_store_config: Optional[Dict[str, Any]] = None,
        document_store_config: Optional[Dict[str, Any]] = None,
        embedding_model_config: Optional[Dict[str, Any]] = None,
        retrieval_service_config: Optional[Dict[str, Any]] = None,
        priority: ProcessorPriority = ProcessorPriority.NORMAL,
        max_concurrent_tasks: int = 5,
        timeout_seconds: int = 300,
        retry_attempts: int = 3,
        enable_caching: bool = True,
        cache_ttl_seconds: int = 3600,
        enable_monitoring: bool = True,
        custom_settings: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """初始化处理器配置

        Args:
            processor_type: 处理器类型
            vector_store_config: 向量存储配置
            document_store_config: 文档存储配置
            embedding_model_config: 嵌入模型配置
            retrieval_service_config: 检索服务配置
            priority: 处理器优先级
            max_concurrent_tasks: 最大并发任务数
            timeout_seconds: 超时时间（秒）
            retry_attempts: 重试次数
            enable_caching: 是否启用缓存
            cache_ttl_seconds: 缓存TTL（秒）
            enable_monitoring: 是否启用监控
            custom_settings: 自定义设置
            **kwargs: 其他配置参数
        """
        self.processor_type = processor_type
        self.vector_store_config = vector_store_config or {}
        self.document_store_config = document_store_config or {}
        self.embedding_model_config = embedding_model_config or {}
        self.retrieval_service_config = retrieval_service_config or {}
        self.priority = priority
        self.max_concurrent_tasks = max_concurrent_tasks
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.enable_caching = enable_caching
        self.cache_ttl_seconds = cache_ttl_seconds
        self.enable_monitoring = enable_monitoring
        self.custom_settings = custom_settings or {}
        self.extra_config = kwargs

        # 验证配置
        self._validate_config()

    def _validate_config(self) -> None:
        """验证配置参数"""
        if self.max_concurrent_tasks <= 0:
            raise ValueError("max_concurrent_tasks必须大于0")

        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds必须大于0")

        if self.retry_attempts < 0:
            raise ValueError("retry_attempts不能小于0")

        if self.cache_ttl_seconds <= 0:
            raise ValueError("cache_ttl_seconds必须大于0")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            "processor_type": self.processor_type.value,
            "vector_store_config": self.vector_store_config,
            "document_store_config": self.document_store_config,
            "embedding_model_config": self.embedding_model_config,
            "retrieval_service_config": self.retrieval_service_config,
            "priority": self.priority.value,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "timeout_seconds": self.timeout_seconds,
            "retry_attempts": self.retry_attempts,
            "enable_caching": self.enable_caching,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "enable_monitoring": self.enable_monitoring,
            "custom_settings": self.custom_settings,
            **self.extra_config
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ProcessorConfig':
        """从字典创建配置对象

        Args:
            config_dict: 配置字典

        Returns:
            ProcessorConfig: 配置对象
        """
        # 提取已知参数
        processor_type = ProcessorType(config_dict.get("processor_type", ProcessorType.PARENT_CHILD))
        priority = ProcessorPriority(config_dict.get("priority", ProcessorPriority.NORMAL))

        # 提取其他参数
        kwargs = {k: v for k, v in config_dict.items()
                 if k not in ["processor_type", "priority"]}

        return cls(
            processor_type=processor_type,
            priority=priority,
            **kwargs
        )

    def merge_with(self, other: 'ProcessorConfig') -> 'ProcessorConfig':
        """与另一个配置合并

        Args:
            other: 另一个配置对象

        Returns:
            ProcessorConfig: 合并后的配置
        """
        merged_dict = self.to_dict()
        other_dict = other.to_dict()

        # 深度合并配置
        for key, value in other_dict.items():
            if key in merged_dict and isinstance(merged_dict[key], dict) and isinstance(value, dict):
                merged_dict[key].update(value)
            else:
                merged_dict[key] = value

        return ProcessorConfig.from_dict(merged_dict)

    def copy(self) -> 'ProcessorConfig':
        """创建配置副本

        Returns:
            ProcessorConfig: 配置副本
        """
        return ProcessorConfig.from_dict(self.to_dict())


class IProcessorFactory(ABC):
    """处理器工厂接口"""
    
    @abstractmethod
    def create_processor(
        self,
        processor_type: ProcessorType,
        config: Optional[ProcessorConfig] = None
    ) -> BaseIndexProcessor:
        """创建处理器
        
        Args:
            processor_type: 处理器类型
            config: 处理器配置
            
        Returns:
            BaseIndexProcessor: 创建的处理器实例
        """
        pass
    
    @abstractmethod
    def get_supported_types(self) -> list[ProcessorType]:
        """获取支持的处理器类型
        
        Returns:
            list[ProcessorType]: 支持的处理器类型列表
        """
        pass


class IndexProcessorFactory(IProcessorFactory):
    """索引处理器工厂
    
    实现工厂模式，负责创建和管理不同类型的索引处理器。
    支持处理器的注册、创建、配置和生命周期管理。
    """
    
    def __init__(self):
        """初始化工厂"""
        import time
        self._start_time = time.time()
        self._processors: Dict[str, Type[BaseIndexProcessor]] = {}
        self._instances: Dict[str, BaseIndexProcessor] = {}
        self._processor_configs: Dict[str, ProcessorConfig] = {}
        self._processor_status: Dict[str, ProcessorStatus] = {}
        self._processor_metrics: Dict[str, Dict[str, Any]] = {}
        self._creation_timestamps: Dict[str, float] = {}
        self._access_counts: Dict[str, int] = {}
        self._register_default_processors()
    
    def _register_default_processors(self):
        """注册默认处理器"""
        self.register_processor(ProcessorType.PARENT_CHILD, ParentChildIndexProcessor)
        logger.info("已注册默认处理器")
    
    def register_processor(
        self,
        processor_type: ProcessorType,
        processor_class: Type[BaseIndexProcessor],
        default_config: Optional[ProcessorConfig] = None
    ) -> None:
        """注册处理器类型

        Args:
            processor_type: 处理器类型
            processor_class: 处理器类
            default_config: 默认配置
        """
        if not issubclass(processor_class, BaseIndexProcessor):
            raise ValueError(f"处理器类必须继承自BaseIndexProcessor: {processor_class}")

        self._processors[processor_type.value] = processor_class
        self._processor_status[processor_type.value] = ProcessorStatus.IDLE

        # 设置默认配置
        if default_config:
            self._processor_configs[processor_type.value] = default_config

        # 初始化指标
        self._processor_metrics[processor_type.value] = {
            "total_created": 0,
            "total_accessed": 0,
            "last_access_time": None,
            "average_creation_time": 0.0,
            "error_count": 0
        }

        logger.info(f"已注册处理器类型: {processor_type.value}")
    
    def unregister_processor(self, processor_type: ProcessorType) -> None:
        """注销处理器类型
        
        Args:
            processor_type: 处理器类型
        """
        if processor_type.value in self._processors:
            del self._processors[processor_type.value]
            logger.info(f"已注销处理器类型: {processor_type.value}")
        
        # 清理实例缓存
        if processor_type.value in self._instances:
            del self._instances[processor_type.value]
    
    def create_processor(
        self,
        processor_type: ProcessorType,
        config: Optional[ProcessorConfig] = None
    ) -> BaseIndexProcessor:
        """创建处理器实例

        Args:
            processor_type: 处理器类型
            config: 处理器配置

        Returns:
            BaseIndexProcessor: 创建的处理器实例

        Raises:
            ValueError: 不支持的处理器类型
            Exception: 处理器创建失败
        """
        import time
        start_time = time.time()

        try:
            logger.info(f"开始创建处理器: {processor_type.value}")

            if processor_type.value not in self._processors:
                raise ValueError(f"不支持的处理器类型: {processor_type.value}")

            # 检查处理器状态
            if self._processor_status.get(processor_type.value) == ProcessorStatus.DISABLED:
                raise ValueError(f"处理器已被禁用: {processor_type.value}")

            # 更新状态
            self._processor_status[processor_type.value] = ProcessorStatus.RUNNING

            processor_class = self._processors[processor_type.value]

            # 合并配置（默认配置 + 传入配置）
            final_config = self._merge_configs(processor_type, config)

            # 准备初始化参数
            init_kwargs = self._prepare_init_kwargs(final_config)

            # 创建处理器实例
            processor = processor_class(**init_kwargs)

            # 记录创建时间和更新指标
            creation_time = time.time() - start_time
            self._update_creation_metrics(processor_type, creation_time)

            # 更新状态
            self._processor_status[processor_type.value] = ProcessorStatus.IDLE

            logger.info(f"成功创建处理器: {processor_type.value} (耗时: {creation_time:.3f}s)")
            return processor

        except Exception as e:
            # 更新错误状态和指标
            self._processor_status[processor_type.value] = ProcessorStatus.ERROR
            self._update_error_metrics(processor_type, str(e))

            logger.error(f"创建处理器失败 {processor_type.value}: {str(e)}")
            raise
    
    def get_or_create_processor(
        self,
        processor_type: ProcessorType,
        config: Optional[ProcessorConfig] = None,
        use_cache: bool = True
    ) -> BaseIndexProcessor:
        """获取或创建处理器实例（支持缓存）

        Args:
            processor_type: 处理器类型
            config: 处理器配置
            use_cache: 是否使用缓存

        Returns:
            BaseIndexProcessor: 处理器实例
        """
        # 更新访问指标
        self._update_access_metrics(processor_type)

        cache_key = processor_type.value

        # 检查缓存
        if use_cache and cache_key in self._instances:
            # 检查缓存是否过期（如果配置了TTL）
            final_config = self._merge_configs(processor_type, config)
            if final_config and final_config.enable_caching:
                creation_time = self._creation_timestamps.get(cache_key, 0)
                import time
                current_time = time.time()
                if current_time - creation_time > final_config.cache_ttl_seconds:
                    logger.info(f"处理器缓存已过期，重新创建: {processor_type.value}")
                    del self._instances[cache_key]
                else:
                    logger.info(f"使用缓存的处理器实例: {processor_type.value}")
                    return self._instances[cache_key]
            else:
                logger.info(f"使用缓存的处理器实例: {processor_type.value}")
                return self._instances[cache_key]

        # 创建新实例
        processor = self.create_processor(processor_type, config)

        if use_cache:
            self._instances[cache_key] = processor
            logger.info(f"已缓存处理器实例: {processor_type.value}")

        return processor

    def _merge_configs(
        self,
        processor_type: ProcessorType,
        config: Optional[ProcessorConfig]
    ) -> Optional[ProcessorConfig]:
        """合并默认配置和传入配置

        Args:
            processor_type: 处理器类型
            config: 传入的配置

        Returns:
            Optional[ProcessorConfig]: 合并后的配置
        """
        default_config = self._processor_configs.get(processor_type.value)

        if not default_config and not config:
            return None
        elif not config:
            return default_config
        elif not default_config:
            return config
        else:
            return default_config.merge_with(config)

    def _update_creation_metrics(self, processor_type: ProcessorType, creation_time: float) -> None:
        """更新创建指标

        Args:
            processor_type: 处理器类型
            creation_time: 创建耗时
        """
        metrics = self._processor_metrics.get(processor_type.value, {})

        metrics["total_created"] = metrics.get("total_created", 0) + 1

        # 更新平均创建时间
        total_created = metrics["total_created"]
        current_avg = metrics.get("average_creation_time", 0.0)
        new_avg = (current_avg * (total_created - 1) + creation_time) / total_created
        metrics["average_creation_time"] = new_avg

        self._processor_metrics[processor_type.value] = metrics
        import time
        self._creation_timestamps[processor_type.value] = time.time()

    def _update_error_metrics(self, processor_type: ProcessorType, error_msg: str) -> None:
        """更新错误指标

        Args:
            processor_type: 处理器类型
            error_msg: 错误信息
        """
        metrics = self._processor_metrics.get(processor_type.value, {})
        metrics["error_count"] = metrics.get("error_count", 0) + 1
        metrics["last_error"] = error_msg
        import time
        metrics["last_error_time"] = time.time()

        self._processor_metrics[processor_type.value] = metrics

    def _update_access_metrics(self, processor_type: ProcessorType) -> None:
        """更新访问指标

        Args:
            processor_type: 处理器类型
        """
        import time

        metrics = self._processor_metrics.get(processor_type.value, {})
        metrics["total_accessed"] = metrics.get("total_accessed", 0) + 1
        metrics["last_access_time"] = time.time()

        self._processor_metrics[processor_type.value] = metrics
        self._access_counts[processor_type.value] = self._access_counts.get(processor_type.value, 0) + 1
    
    def _prepare_init_kwargs(self, config: Optional[ProcessorConfig]) -> Dict[str, Any]:
        """准备处理器初始化参数
        
        Args:
            config: 处理器配置
            
        Returns:
            Dict[str, Any]: 初始化参数
        """
        if not config:
            return {}
        
        init_kwargs = {}
        
        # 创建向量存储
        if config.vector_store_config:
            try:
                vector_store = MilvusVectorStore(**config.vector_store_config)
                init_kwargs["vector_store"] = vector_store
            except Exception as e:
                logger.warning(f"创建向量存储失败: {str(e)}")
        
        # 创建文档存储
        if config.document_store_config:
            try:
                document_store = DocumentStore(**config.document_store_config)
                init_kwargs["document_store"] = document_store
            except Exception as e:
                logger.warning(f"创建文档存储失败: {str(e)}")
        
        # 创建嵌入模型
        if config.embedding_model_config:
            try:
                embedding_model = EmbeddingModel(**config.embedding_model_config)
                init_kwargs["embedding_model"] = embedding_model
            except Exception as e:
                logger.warning(f"创建嵌入模型失败: {str(e)}")
        
        # 创建检索服务
        if config.retrieval_service_config:
            try:
                retrieval_service = RetrievalService(**config.retrieval_service_config)
                init_kwargs["retrieval_service"] = retrieval_service
            except Exception as e:
                logger.warning(f"创建检索服务失败: {str(e)}")
        
        # 添加额外配置
        init_kwargs.update(config.extra_config)
        
        return init_kwargs
    
    def get_supported_types(self) -> list[ProcessorType]:
        """获取支持的处理器类型
        
        Returns:
            list[ProcessorType]: 支持的处理器类型列表
        """
        return [ProcessorType(type_name) for type_name in self._processors.keys()]
    
    def set_processor_status(self, processor_type: ProcessorType, status: ProcessorStatus) -> None:
        """设置处理器状态

        Args:
            processor_type: 处理器类型
            status: 新状态
        """
        if processor_type.value in self._processors:
            self._processor_status[processor_type.value] = status
            logger.info(f"处理器状态已更新: {processor_type.value} -> {status.value}")
        else:
            raise ValueError(f"未注册的处理器类型: {processor_type.value}")

    def get_processor_status(self, processor_type: ProcessorType) -> ProcessorStatus:
        """获取处理器状态

        Args:
            processor_type: 处理器类型

        Returns:
            ProcessorStatus: 处理器状态
        """
        return self._processor_status.get(processor_type.value, ProcessorStatus.IDLE)

    def disable_processor(self, processor_type: ProcessorType) -> None:
        """禁用处理器

        Args:
            processor_type: 处理器类型
        """
        self.set_processor_status(processor_type, ProcessorStatus.DISABLED)

        # 清理相关缓存
        if processor_type.value in self._instances:
            del self._instances[processor_type.value]
            logger.info(f"已清理禁用处理器的缓存: {processor_type.value}")

    def enable_processor(self, processor_type: ProcessorType) -> None:
        """启用处理器

        Args:
            processor_type: 处理器类型
        """
        self.set_processor_status(processor_type, ProcessorStatus.IDLE)

    def get_processor_metrics(self, processor_type: ProcessorType) -> Dict[str, Any]:
        """获取处理器指标

        Args:
            processor_type: 处理器类型

        Returns:
            Dict[str, Any]: 处理器指标
        """
        return self._processor_metrics.get(processor_type.value, {})

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """获取所有处理器指标

        Returns:
            Dict[str, Dict[str, Any]]: 所有处理器指标
        """
        return self._processor_metrics.copy()

    def clear_cache(self, processor_type: Optional[ProcessorType] = None) -> None:
        """清理处理器实例缓存

        Args:
            processor_type: 指定处理器类型，None表示清理所有
        """
        if processor_type:
            if processor_type.value in self._instances:
                del self._instances[processor_type.value]
                logger.info(f"已清理处理器缓存: {processor_type.value}")
        else:
            self._instances.clear()
            logger.info("已清理所有处理器实例缓存")

    def reset_metrics(self, processor_type: Optional[ProcessorType] = None) -> None:
        """重置处理器指标

        Args:
            processor_type: 指定处理器类型，None表示重置所有
        """
        if processor_type:
            if processor_type.value in self._processor_metrics:
                self._processor_metrics[processor_type.value] = {
                    "total_created": 0,
                    "total_accessed": 0,
                    "last_access_time": None,
                    "average_creation_time": 0.0,
                    "error_count": 0
                }
                logger.info(f"已重置处理器指标: {processor_type.value}")
        else:
            for ptype in self._processor_metrics:
                self._processor_metrics[ptype] = {
                    "total_created": 0,
                    "total_accessed": 0,
                    "last_access_time": None,
                    "average_creation_time": 0.0,
                    "error_count": 0
                }
            logger.info("已重置所有处理器指标")
    
    def get_processor_info(self) -> Dict[str, Any]:
        """获取处理器工厂信息

        Returns:
            Dict[str, Any]: 工厂信息
        """
        import time
        current_time = time.time()

        # 计算总体统计
        total_created = sum(metrics.get("total_created", 0) for metrics in self._processor_metrics.values())
        total_accessed = sum(metrics.get("total_accessed", 0) for metrics in self._processor_metrics.values())
        total_errors = sum(metrics.get("error_count", 0) for metrics in self._processor_metrics.values())

        # 处理器状态统计
        status_counts = {}
        for status in ProcessorStatus:
            status_counts[status.value] = sum(1 for s in self._processor_status.values() if s == status)

        return {
            "supported_types": [ptype.value for ptype in self.get_supported_types()],
            "registered_processors": list(self._processors.keys()),
            "cached_instances": list(self._instances.keys()),
            "total_registered": len(self._processors),
            "total_cached": len(self._instances),
            "processor_status": dict(self._processor_status),
            "status_counts": status_counts,
            "total_statistics": {
                "total_created": total_created,
                "total_accessed": total_accessed,
                "total_errors": total_errors,
                "cache_hit_rate": len(self._instances) / max(total_created, 1) * 100
            },
            "metrics_summary": self._processor_metrics,
            "factory_uptime": current_time - getattr(self, '_start_time', current_time)
        }

    def health_check(self) -> Dict[str, Any]:
        """工厂健康检查

        Returns:
            Dict[str, Any]: 健康状态信息
        """
        health_status = {
            "status": "healthy",
            "issues": [],
            "warnings": []
        }

        # 检查禁用的处理器
        disabled_processors = [
            ptype for ptype, status in self._processor_status.items()
            if status == ProcessorStatus.DISABLED
        ]
        if disabled_processors:
            health_status["warnings"].append(f"禁用的处理器: {disabled_processors}")

        # 检查错误状态的处理器
        error_processors = [
            ptype for ptype, status in self._processor_status.items()
            if status == ProcessorStatus.ERROR
        ]
        if error_processors:
            health_status["issues"].append(f"错误状态的处理器: {error_processors}")
            health_status["status"] = "degraded"

        # 检查高错误率的处理器
        for ptype, metrics in self._processor_metrics.items():
            error_count = metrics.get("error_count", 0)
            total_created = metrics.get("total_created", 0)
            if total_created > 0 and error_count / total_created > 0.1:  # 错误率超过10%
                health_status["warnings"].append(f"处理器 {ptype} 错误率过高: {error_count}/{total_created}")

        return health_status


# 全局工厂实例
_global_factory: Optional[IndexProcessorFactory] = None


def get_processor_factory() -> IndexProcessorFactory:
    """获取全局处理器工厂实例
    
    Returns:
        IndexProcessorFactory: 工厂实例
    """
    global _global_factory
    if _global_factory is None:
        _global_factory = IndexProcessorFactory()
    return _global_factory


def create_processor(
    processor_type: Union[ProcessorType, str],
    config: Optional[ProcessorConfig] = None
) -> BaseIndexProcessor:
    """便捷函数：创建处理器
    
    Args:
        processor_type: 处理器类型
        config: 处理器配置
        
    Returns:
        BaseIndexProcessor: 处理器实例
    """
    if isinstance(processor_type, str):
        processor_type = ProcessorType(processor_type)
    
    factory = get_processor_factory()
    return factory.create_processor(processor_type, config)
