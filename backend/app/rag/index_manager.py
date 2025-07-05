"""
索引管理器
实现索引生命周期管理、索引优化、索引监控和索引恢复功能
"""

import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import os

from pymilvus import Collection, utility, connections
from motor.motor_asyncio import AsyncIOMotorDatabase

from .vector_store import MilvusVectorStore
from .collection_manager import MilvusCollectionManager
from .constants import VECTOR_STORE_CONFIG
from ..db.connections.mongodb import mongodb_manager
from ..db.connections.milvus import milvus_manager

logger = logging.getLogger(__name__)


class IndexStatus(str, Enum):
    """索引状态"""
    CREATING = "creating"          # 创建中
    ACTIVE = "active"             # 活跃
    OPTIMIZING = "optimizing"     # 优化中
    DEGRADED = "degraded"         # 降级
    FAILED = "failed"             # 失败
    MAINTENANCE = "maintenance"   # 维护中
    ARCHIVED = "archived"         # 已归档


class IndexType(str, Enum):
    """索引类型"""
    VECTOR = "vector"             # 向量索引
    SPARSE_VECTOR = "sparse_vector"  # 稀疏向量索引
    METADATA = "metadata"         # 元数据索引
    FULL_TEXT = "full_text"       # 全文索引


@dataclass
class IndexMetrics:
    """索引指标"""
    name: str
    index_type: IndexType
    status: IndexStatus
    entity_count: int = 0
    index_size_mb: float = 0.0
    build_time_seconds: float = 0.0
    last_optimized: Optional[datetime] = None
    query_performance_ms: float = 0.0
    memory_usage_mb: float = 0.0
    disk_usage_mb: float = 0.0
    error_count: int = 0
    last_error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class IndexConfig:
    """索引配置"""
    name: str
    index_type: IndexType
    field_name: str
    index_params: Dict[str, Any]
    auto_optimize: bool = True
    optimization_threshold: int = 10000  # 实体数量阈值
    backup_enabled: bool = True
    monitoring_enabled: bool = True
    retention_days: int = 30


@dataclass
class OptimizationPlan:
    """优化计划"""
    index_name: str
    current_config: Dict[str, Any]
    recommended_config: Dict[str, Any]
    reason: str
    estimated_improvement: float
    estimated_time_minutes: float
    priority: int = 1  # 1-5, 1最高


class IndexManager:
    """索引管理器"""
    
    def __init__(
        self,
        vector_store: Optional[MilvusVectorStore] = None,
        mongodb_db: Optional[AsyncIOMotorDatabase] = None
    ):
        self.vector_store = vector_store or MilvusVectorStore()
        self.mongodb_db = mongodb_db
        self.collection_manager = MilvusCollectionManager()
        
        # 索引注册表
        self.registered_indexes: Dict[str, IndexConfig] = {}
        self.index_metrics: Dict[str, IndexMetrics] = {}
        
        # 监控配置
        self.monitoring_enabled = True
        self.monitoring_interval = 300  # 5分钟
        self.optimization_enabled = True
        
        # 备份配置
        self.backup_enabled = True
        self.backup_retention_days = 30
        
        # 性能阈值
        self.performance_thresholds = {
            "query_time_ms": 1000,      # 查询时间阈值
            "memory_usage_mb": 2048,    # 内存使用阈值
            "error_rate": 0.05          # 错误率阈值
        }
    
    async def initialize(self):
        """初始化索引管理器"""
        logger.info("初始化索引管理器...")
        
        try:
            # 连接到数据库
            if not self.mongodb_db:
                self.mongodb_db = await mongodb_manager.get_async_database()
            
            # 确保连接到Milvus
            if not connections.has_connection("default"):
                connections.connect(host="localhost", port="19530")
            
            # 发现现有索引
            await self.discover_existing_indexes()
            
            # 启动监控
            if self.monitoring_enabled:
                asyncio.create_task(self.start_monitoring())
            
            logger.info("索引管理器初始化完成")
            
        except Exception as e:
            logger.error(f"索引管理器初始化失败: {e}")
            raise
    
    async def discover_existing_indexes(self):
        """发现现有索引"""
        logger.info("发现现有索引...")
        
        try:
            # 发现Milvus索引
            await self._discover_milvus_indexes()
            
            # 发现MongoDB索引
            await self._discover_mongodb_indexes()
            
            logger.info(f"发现 {len(self.registered_indexes)} 个索引")
            
        except Exception as e:
            logger.error(f"发现索引失败: {e}")
            raise
    
    async def _discover_milvus_indexes(self):
        """发现Milvus索引"""
        try:
            # 获取所有集合
            collections = utility.list_collections()
            
            for collection_name in collections:
                collection = Collection(collection_name)
                
                # 获取集合schema
                schema = collection.schema
                
                for field in schema.fields:
                    if field.dtype in [101, 102]:  # 向量字段类型
                        try:
                            # 检查是否有索引
                            indexes = collection.indexes
                            for index in indexes:
                                if index.field_name == field.name:
                                    index_name = f"{collection_name}_{field.name}"
                                    
                                    # 创建索引配置
                                    config = IndexConfig(
                                        name=index_name,
                                        index_type=IndexType.VECTOR if field.name == "vector" else IndexType.SPARSE_VECTOR,
                                        field_name=field.name,
                                        index_params=index.params
                                    )
                                    
                                    self.registered_indexes[index_name] = config
                                    
                                    # 创建初始指标
                                    metrics = IndexMetrics(
                                        name=index_name,
                                        index_type=config.index_type,
                                        status=IndexStatus.ACTIVE,
                                        entity_count=collection.num_entities
                                    )
                                    
                                    self.index_metrics[index_name] = metrics
                                    
                        except Exception as e:
                            logger.warning(f"检查集合 {collection_name} 字段 {field.name} 索引失败: {e}")
                            
        except Exception as e:
            logger.error(f"发现Milvus索引失败: {e}")
    
    async def _discover_mongodb_indexes(self):
        """发现MongoDB索引"""
        try:
            if not self.mongodb_db:
                return
            
            # 获取所有集合
            collections = await self.mongodb_db.list_collection_names()
            
            for collection_name in collections:
                collection = self.mongodb_db[collection_name]
                
                # 获取索引信息
                indexes = await collection.list_indexes().to_list(None)
                
                for index_info in indexes:
                    if index_info["name"] != "_id_":  # 跳过默认_id索引
                        index_name = f"mongodb_{collection_name}_{index_info['name']}"
                        
                        # 创建索引配置
                        config = IndexConfig(
                            name=index_name,
                            index_type=IndexType.METADATA,
                            field_name=str(index_info.get("key", {})),
                            index_params=index_info
                        )
                        
                        self.registered_indexes[index_name] = config
                        
                        # 创建初始指标
                        metrics = IndexMetrics(
                            name=index_name,
                            index_type=IndexType.METADATA,
                            status=IndexStatus.ACTIVE
                        )
                        
                        self.index_metrics[index_name] = metrics
                        
        except Exception as e:
            logger.error(f"发现MongoDB索引失败: {e}")
    
    async def create_index(
        self,
        collection_name: str,
        field_name: str,
        index_type: IndexType,
        index_params: Dict[str, Any],
        index_name: Optional[str] = None
    ) -> bool:
        """创建索引"""
        if not index_name:
            index_name = f"{collection_name}_{field_name}"
        
        logger.info(f"创建索引: {index_name}")
        
        try:
            # 更新状态
            if index_name in self.index_metrics:
                self.index_metrics[index_name].status = IndexStatus.CREATING
            
            start_time = time.time()
            
            if index_type in [IndexType.VECTOR, IndexType.SPARSE_VECTOR]:
                # 创建Milvus索引
                success = await self._create_milvus_index(
                    collection_name, field_name, index_params
                )
            elif index_type == IndexType.METADATA:
                # 创建MongoDB索引
                success = await self._create_mongodb_index(
                    collection_name, field_name, index_params
                )
            else:
                raise ValueError(f"不支持的索引类型: {index_type}")
            
            build_time = time.time() - start_time
            
            if success:
                # 注册索引
                config = IndexConfig(
                    name=index_name,
                    index_type=index_type,
                    field_name=field_name,
                    index_params=index_params
                )
                self.registered_indexes[index_name] = config
                
                # 更新指标
                metrics = IndexMetrics(
                    name=index_name,
                    index_type=index_type,
                    status=IndexStatus.ACTIVE,
                    build_time_seconds=build_time
                )
                self.index_metrics[index_name] = metrics
                
                logger.info(f"索引 {index_name} 创建成功，耗时 {build_time:.2f} 秒")
                return True
            else:
                # 更新失败状态
                if index_name in self.index_metrics:
                    self.index_metrics[index_name].status = IndexStatus.FAILED
                return False
                
        except Exception as e:
            logger.error(f"创建索引 {index_name} 失败: {e}")
            
            # 更新失败状态
            if index_name in self.index_metrics:
                self.index_metrics[index_name].status = IndexStatus.FAILED
                self.index_metrics[index_name].last_error = str(e)
                self.index_metrics[index_name].error_count += 1
            
            return False
    
    async def _create_milvus_index(
        self,
        collection_name: str,
        field_name: str,
        index_params: Dict[str, Any]
    ) -> bool:
        """创建Milvus索引"""
        try:
            collection = Collection(collection_name)
            
            # 创建索引
            collection.create_index(
                field_name=field_name,
                index_params=index_params
            )
            
            # 等待索引构建完成
            utility.wait_for_index_building_complete(collection_name, field_name)
            
            return True
            
        except Exception as e:
            logger.error(f"创建Milvus索引失败: {e}")
            return False
    
    async def _create_mongodb_index(
        self,
        collection_name: str,
        field_name: str,
        index_params: Dict[str, Any]
    ) -> bool:
        """创建MongoDB索引"""
        try:
            if not self.mongodb_db:
                return False
            
            collection = self.mongodb_db[collection_name]
            
            # 创建索引
            await collection.create_index(field_name, **index_params)
            
            return True
            
        except Exception as e:
            logger.error(f"创建MongoDB索引失败: {e}")
            return False
    
    async def drop_index(self, index_name: str) -> bool:
        """删除索引"""
        logger.info(f"删除索引: {index_name}")
        
        try:
            if index_name not in self.registered_indexes:
                logger.warning(f"索引 {index_name} 未注册")
                return False
            
            config = self.registered_indexes[index_name]
            
            if config.index_type in [IndexType.VECTOR, IndexType.SPARSE_VECTOR]:
                # 删除Milvus索引
                success = await self._drop_milvus_index(index_name, config)
            elif config.index_type == IndexType.METADATA:
                # 删除MongoDB索引
                success = await self._drop_mongodb_index(index_name, config)
            else:
                success = False
            
            if success:
                # 从注册表中移除
                del self.registered_indexes[index_name]
                if index_name in self.index_metrics:
                    del self.index_metrics[index_name]
                
                logger.info(f"索引 {index_name} 删除成功")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"删除索引 {index_name} 失败: {e}")
            return False
    
    async def _drop_milvus_index(self, index_name: str, config: IndexConfig) -> bool:
        """删除Milvus索引"""
        try:
            # 从索引名称解析集合名称
            collection_name = index_name.split("_")[0]
            collection = Collection(collection_name)
            
            # 删除索引
            collection.drop_index(field_name=config.field_name)
            
            return True
            
        except Exception as e:
            logger.error(f"删除Milvus索引失败: {e}")
            return False
    
    async def _drop_mongodb_index(self, index_name: str, config: IndexConfig) -> bool:
        """删除MongoDB索引"""
        try:
            if not self.mongodb_db:
                return False
            
            # 从索引名称解析集合名称
            parts = index_name.split("_")
            collection_name = parts[1] if len(parts) > 1 else parts[0]
            
            collection = self.mongodb_db[collection_name]
            
            # 删除索引
            await collection.drop_index(config.field_name)
            
            return True
            
        except Exception as e:
            logger.error(f"删除MongoDB索引失败: {e}")
            return False
    
    async def optimize_index(self, index_name: str) -> bool:
        """优化索引"""
        logger.info(f"优化索引: {index_name}")
        
        try:
            if index_name not in self.registered_indexes:
                logger.warning(f"索引 {index_name} 未注册")
                return False
            
            config = self.registered_indexes[index_name]
            
            # 更新状态
            if index_name in self.index_metrics:
                self.index_metrics[index_name].status = IndexStatus.OPTIMIZING
            
            # 生成优化计划
            plan = await self.generate_optimization_plan(index_name)
            
            if plan:
                # 执行优化
                success = await self._execute_optimization_plan(plan)
                
                if success:
                    # 更新指标
                    if index_name in self.index_metrics:
                        self.index_metrics[index_name].status = IndexStatus.ACTIVE
                        self.index_metrics[index_name].last_optimized = datetime.now()
                    
                    logger.info(f"索引 {index_name} 优化成功")
                    return True
                else:
                    # 恢复状态
                    if index_name in self.index_metrics:
                        self.index_metrics[index_name].status = IndexStatus.DEGRADED
                    return False
            else:
                logger.info(f"索引 {index_name} 无需优化")
                if index_name in self.index_metrics:
                    self.index_metrics[index_name].status = IndexStatus.ACTIVE
                return True
                
        except Exception as e:
            logger.error(f"优化索引 {index_name} 失败: {e}")
            
            # 更新失败状态
            if index_name in self.index_metrics:
                self.index_metrics[index_name].status = IndexStatus.FAILED
                self.index_metrics[index_name].last_error = str(e)
                self.index_metrics[index_name].error_count += 1
            
            return False

    async def generate_optimization_plan(self, index_name: str) -> Optional[OptimizationPlan]:
        """生成优化计划"""
        try:
            if index_name not in self.registered_indexes or index_name not in self.index_metrics:
                return None

            config = self.registered_indexes[index_name]
            metrics = self.index_metrics[index_name]

            # 分析当前性能
            current_params = config.index_params
            entity_count = metrics.entity_count
            query_time = metrics.query_performance_ms

            # 根据数据量和性能选择优化策略
            if config.index_type == IndexType.VECTOR:
                return await self._generate_vector_optimization_plan(
                    index_name, current_params, entity_count, query_time
                )
            elif config.index_type == IndexType.METADATA:
                return await self._generate_metadata_optimization_plan(
                    index_name, current_params, entity_count, query_time
                )

            return None

        except Exception as e:
            logger.error(f"生成优化计划失败: {e}")
            return None

    async def _generate_vector_optimization_plan(
        self,
        index_name: str,
        current_params: Dict[str, Any],
        entity_count: int,
        query_time: float
    ) -> Optional[OptimizationPlan]:
        """生成向量索引优化计划"""
        try:
            current_index_type = current_params.get("index_type", "IVF_FLAT")

            # 根据数据量推荐索引类型
            if entity_count < 1000:
                recommended_type = "FLAT"
                recommended_params = {
                    "index_type": "FLAT",
                    "metric_type": current_params.get("metric_type", "L2"),
                    "params": {}
                }
                reason = "小数据集，推荐使用FLAT索引以获得最佳精度"
                improvement = 0.1
            elif entity_count < 10000:
                recommended_type = "IVF_FLAT"
                recommended_params = {
                    "index_type": "IVF_FLAT",
                    "metric_type": current_params.get("metric_type", "L2"),
                    "params": {"nlist": min(1024, entity_count // 10)}
                }
                reason = "中等数据集，推荐使用IVF_FLAT索引平衡性能和精度"
                improvement = 0.2
            else:
                recommended_type = "IVF_SQ8"
                recommended_params = {
                    "index_type": "IVF_SQ8",
                    "metric_type": current_params.get("metric_type", "L2"),
                    "params": {"nlist": min(4096, entity_count // 100)}
                }
                reason = "大数据集，推荐使用IVF_SQ8索引节省内存"
                improvement = 0.3

            # 如果当前配置已经是推荐配置，无需优化
            if current_index_type == recommended_type:
                return None

            # 估算优化时间
            estimated_time = max(1, entity_count / 10000)  # 每万条数据约1分钟

            return OptimizationPlan(
                index_name=index_name,
                current_config=current_params,
                recommended_config=recommended_params,
                reason=reason,
                estimated_improvement=improvement,
                estimated_time_minutes=estimated_time,
                priority=2 if query_time > self.performance_thresholds["query_time_ms"] else 3
            )

        except Exception as e:
            logger.error(f"生成向量索引优化计划失败: {e}")
            return None

    async def _generate_metadata_optimization_plan(
        self,
        index_name: str,
        current_params: Dict[str, Any],
        entity_count: int,
        query_time: float
    ) -> Optional[OptimizationPlan]:
        """生成元数据索引优化计划"""
        try:
            # MongoDB索引优化建议
            if query_time > self.performance_thresholds["query_time_ms"]:
                recommended_params = {
                    **current_params,
                    "background": True,  # 后台构建
                    "sparse": True       # 稀疏索引
                }

                return OptimizationPlan(
                    index_name=index_name,
                    current_config=current_params,
                    recommended_config=recommended_params,
                    reason="查询性能较差，建议优化索引配置",
                    estimated_improvement=0.3,
                    estimated_time_minutes=2,
                    priority=1
                )

            return None

        except Exception as e:
            logger.error(f"生成元数据索引优化计划失败: {e}")
            return None

    async def _execute_optimization_plan(self, plan: OptimizationPlan) -> bool:
        """执行优化计划"""
        logger.info(f"执行优化计划: {plan.index_name}")
        logger.info(f"优化原因: {plan.reason}")
        logger.info(f"预期改进: {plan.estimated_improvement:.1%}")

        try:
            config = self.registered_indexes[plan.index_name]

            # 备份当前配置
            if self.backup_enabled:
                await self._backup_index_config(plan.index_name, config)

            # 删除旧索引
            collection_name = plan.index_name.split("_")[0]
            if config.index_type in [IndexType.VECTOR, IndexType.SPARSE_VECTOR]:
                collection = Collection(collection_name)
                collection.drop_index(field_name=config.field_name)

            # 创建新索引
            if config.index_type in [IndexType.VECTOR, IndexType.SPARSE_VECTOR]:
                success = await self._create_milvus_index(
                    collection_name, config.field_name, plan.recommended_config
                )
            else:
                success = await self._create_mongodb_index(
                    collection_name, config.field_name, plan.recommended_config
                )

            if success:
                # 更新配置
                config.index_params = plan.recommended_config
                logger.info(f"优化计划执行成功: {plan.index_name}")
                return True
            else:
                # 恢复原配置
                await self._restore_index_config(plan.index_name)
                return False

        except Exception as e:
            logger.error(f"执行优化计划失败: {e}")
            # 尝试恢复
            await self._restore_index_config(plan.index_name)
            return False

    async def _backup_index_config(self, index_name: str, config: IndexConfig):
        """备份索引配置"""
        try:
            backup_data = {
                "index_name": index_name,
                "config": {
                    "name": config.name,
                    "index_type": config.index_type.value,
                    "field_name": config.field_name,
                    "index_params": config.index_params
                },
                "backup_time": datetime.now().isoformat()
            }

            # 保存到文件或数据库
            backup_file = f"index_backup_{index_name}_{int(time.time())}.json"
            backup_path = os.path.join("/tmp", backup_file)

            with open(backup_path, "w") as f:
                json.dump(backup_data, f, indent=2)

            logger.info(f"索引配置已备份: {backup_path}")

        except Exception as e:
            logger.error(f"备份索引配置失败: {e}")

    async def _restore_index_config(self, index_name: str):
        """恢复索引配置"""
        try:
            # 查找最新的备份文件
            backup_files = [f for f in os.listdir("/tmp") if f.startswith(f"index_backup_{index_name}_")]
            if not backup_files:
                logger.warning(f"未找到索引 {index_name} 的备份文件")
                return

            # 选择最新的备份
            latest_backup = max(backup_files)
            backup_path = os.path.join("/tmp", latest_backup)

            with open(backup_path, "r") as f:
                backup_data = json.load(f)

            # 恢复配置
            config_data = backup_data["config"]
            original_params = config_data["index_params"]

            # 重新创建索引
            collection_name = index_name.split("_")[0]
            if config_data["index_type"] in ["vector", "sparse_vector"]:
                await self._create_milvus_index(
                    collection_name, config_data["field_name"], original_params
                )
            else:
                await self._create_mongodb_index(
                    collection_name, config_data["field_name"], original_params
                )

            logger.info(f"索引配置已恢复: {index_name}")

        except Exception as e:
            logger.error(f"恢复索引配置失败: {e}")

    async def start_monitoring(self):
        """启动监控"""
        logger.info("启动索引监控...")

        while self.monitoring_enabled:
            try:
                await self.collect_metrics()
                await self.check_health()

                if self.optimization_enabled:
                    await self.auto_optimize()

                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"监控过程中发生错误: {e}")
                await asyncio.sleep(60)  # 错误时等待1分钟再重试

    async def collect_metrics(self):
        """收集指标"""
        try:
            for index_name, config in self.registered_indexes.items():
                if index_name not in self.index_metrics:
                    continue

                metrics = self.index_metrics[index_name]

                if config.index_type in [IndexType.VECTOR, IndexType.SPARSE_VECTOR]:
                    await self._collect_milvus_metrics(index_name, metrics)
                elif config.index_type == IndexType.METADATA:
                    await self._collect_mongodb_metrics(index_name, metrics)

                metrics.updated_at = datetime.now()

        except Exception as e:
            logger.error(f"收集指标失败: {e}")

    async def _collect_milvus_metrics(self, index_name: str, metrics: IndexMetrics):
        """收集Milvus指标"""
        try:
            collection_name = index_name.split("_")[0]
            collection = Collection(collection_name)

            # 更新实体数量
            metrics.entity_count = collection.num_entities

            # 获取集合统计信息
            try:
                stats = collection.get_stats()
                if stats:
                    metrics.memory_usage_mb = stats.get("memory_size", 0) / (1024 * 1024)
                    metrics.disk_usage_mb = stats.get("disk_size", 0) / (1024 * 1024)
            except:
                pass

            # 测试查询性能
            if metrics.entity_count > 0:
                start_time = time.time()
                # 执行一个简单的查询来测试性能
                try:
                    collection.query(expr="id != ''", limit=1)
                    metrics.query_performance_ms = (time.time() - start_time) * 1000
                except:
                    pass

        except Exception as e:
            logger.warning(f"收集Milvus指标失败: {e}")
            metrics.error_count += 1
            metrics.last_error = str(e)

    async def _collect_mongodb_metrics(self, index_name: str, metrics: IndexMetrics):
        """收集MongoDB指标"""
        try:
            if not self.mongodb_db:
                return

            # 从索引名称解析集合名称
            parts = index_name.split("_")
            collection_name = parts[1] if len(parts) > 1 else parts[0]

            collection = self.mongodb_db[collection_name]

            # 获取集合统计信息
            try:
                stats = await collection.stats()
                if stats:
                    metrics.entity_count = stats.get("count", 0)
                    metrics.index_size_mb = stats.get("totalIndexSize", 0) / (1024 * 1024)
                    metrics.disk_usage_mb = stats.get("storageSize", 0) / (1024 * 1024)
            except:
                pass

        except Exception as e:
            logger.warning(f"收集MongoDB指标失败: {e}")
            metrics.error_count += 1
            metrics.last_error = str(e)

    async def check_health(self):
        """检查索引健康状态"""
        try:
            for index_name, metrics in self.index_metrics.items():
                old_status = metrics.status

                # 检查错误率
                if metrics.error_count > 10:
                    metrics.status = IndexStatus.FAILED
                elif metrics.query_performance_ms > self.performance_thresholds["query_time_ms"]:
                    metrics.status = IndexStatus.DEGRADED
                elif metrics.memory_usage_mb > self.performance_thresholds["memory_usage_mb"]:
                    metrics.status = IndexStatus.DEGRADED
                else:
                    if metrics.status in [IndexStatus.DEGRADED, IndexStatus.FAILED]:
                        metrics.status = IndexStatus.ACTIVE

                # 记录状态变化
                if old_status != metrics.status:
                    logger.info(f"索引 {index_name} 状态变化: {old_status} -> {metrics.status}")

                    # 如果状态恶化，发送告警
                    if metrics.status in [IndexStatus.DEGRADED, IndexStatus.FAILED]:
                        await self._send_alert(index_name, metrics, old_status)

        except Exception as e:
            logger.error(f"健康检查失败: {e}")

    async def _send_alert(self, index_name: str, metrics: IndexMetrics, old_status: IndexStatus):
        """发送告警"""
        try:
            alert_message = f"""
            索引告警:
            - 索引名称: {index_name}
            - 状态变化: {old_status} -> {metrics.status}
            - 错误次数: {metrics.error_count}
            - 查询性能: {metrics.query_performance_ms:.2f}ms
            - 内存使用: {metrics.memory_usage_mb:.2f}MB
            - 最后错误: {metrics.last_error}
            """

            logger.warning(alert_message)

            # 这里可以集成邮件、钉钉、企业微信等告警系统

        except Exception as e:
            logger.error(f"发送告警失败: {e}")

    async def auto_optimize(self):
        """自动优化"""
        try:
            optimization_plans = []

            # 为所有需要优化的索引生成优化计划
            for index_name, config in self.registered_indexes.items():
                if not config.auto_optimize:
                    continue

                metrics = self.index_metrics.get(index_name)
                if not metrics:
                    continue

                # 检查是否需要优化
                if (metrics.entity_count > config.optimization_threshold or
                    metrics.status == IndexStatus.DEGRADED):

                    plan = await self.generate_optimization_plan(index_name)
                    if plan:
                        optimization_plans.append(plan)

            # 按优先级排序
            optimization_plans.sort(key=lambda x: x.priority)

            # 执行优化计划（限制并发数）
            max_concurrent_optimizations = 2
            semaphore = asyncio.Semaphore(max_concurrent_optimizations)

            async def execute_plan(plan):
                async with semaphore:
                    await self._execute_optimization_plan(plan)

            # 并发执行优化计划
            if optimization_plans:
                logger.info(f"开始执行 {len(optimization_plans)} 个自动优化计划")
                tasks = [execute_plan(plan) for plan in optimization_plans[:5]]  # 限制最多5个
                await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"自动优化失败: {e}")

    async def get_index_status(self, index_name: Optional[str] = None) -> Dict[str, Any]:
        """获取索引状态"""
        try:
            if index_name:
                if index_name not in self.index_metrics:
                    return {"error": f"索引 {index_name} 不存在"}

                metrics = self.index_metrics[index_name]
                config = self.registered_indexes.get(index_name)

                return {
                    "name": metrics.name,
                    "type": metrics.index_type.value,
                    "status": metrics.status.value,
                    "entity_count": metrics.entity_count,
                    "index_size_mb": metrics.index_size_mb,
                    "query_performance_ms": metrics.query_performance_ms,
                    "memory_usage_mb": metrics.memory_usage_mb,
                    "disk_usage_mb": metrics.disk_usage_mb,
                    "error_count": metrics.error_count,
                    "last_error": metrics.last_error,
                    "last_optimized": metrics.last_optimized.isoformat() if metrics.last_optimized else None,
                    "created_at": metrics.created_at.isoformat(),
                    "updated_at": metrics.updated_at.isoformat(),
                    "config": {
                        "auto_optimize": config.auto_optimize if config else False,
                        "backup_enabled": config.backup_enabled if config else False,
                        "monitoring_enabled": config.monitoring_enabled if config else False
                    } if config else {}
                }
            else:
                # 返回所有索引的状态摘要
                summary = {
                    "total_indexes": len(self.index_metrics),
                    "status_distribution": {},
                    "indexes": []
                }

                for status in IndexStatus:
                    count = sum(1 for m in self.index_metrics.values() if m.status == status)
                    summary["status_distribution"][status.value] = count

                for index_name, metrics in self.index_metrics.items():
                    summary["indexes"].append({
                        "name": metrics.name,
                        "type": metrics.index_type.value,
                        "status": metrics.status.value,
                        "entity_count": metrics.entity_count,
                        "query_performance_ms": metrics.query_performance_ms,
                        "error_count": metrics.error_count
                    })

                return summary

        except Exception as e:
            logger.error(f"获取索引状态失败: {e}")
            return {"error": str(e)}

    async def rebuild_index(self, index_name: str) -> bool:
        """重建索引"""
        logger.info(f"重建索引: {index_name}")

        try:
            if index_name not in self.registered_indexes:
                logger.error(f"索引 {index_name} 未注册")
                return False

            config = self.registered_indexes[index_name]

            # 更新状态
            if index_name in self.index_metrics:
                self.index_metrics[index_name].status = IndexStatus.MAINTENANCE

            # 备份当前配置
            if self.backup_enabled:
                await self._backup_index_config(index_name, config)

            # 删除现有索引
            await self.drop_index(index_name)

            # 重新创建索引
            success = await self.create_index(
                collection_name=index_name.split("_")[0],
                field_name=config.field_name,
                index_type=config.index_type,
                index_params=config.index_params,
                index_name=index_name
            )

            if success:
                logger.info(f"索引 {index_name} 重建成功")
                return True
            else:
                logger.error(f"索引 {index_name} 重建失败")
                # 尝试恢复
                await self._restore_index_config(index_name)
                return False

        except Exception as e:
            logger.error(f"重建索引 {index_name} 失败: {e}")

            # 更新失败状态
            if index_name in self.index_metrics:
                self.index_metrics[index_name].status = IndexStatus.FAILED
                self.index_metrics[index_name].last_error = str(e)
                self.index_metrics[index_name].error_count += 1

            return False

    async def cleanup_old_backups(self):
        """清理旧备份"""
        try:
            backup_dir = "/tmp"
            current_time = time.time()
            retention_seconds = self.backup_retention_days * 24 * 3600

            backup_files = [f for f in os.listdir(backup_dir) if f.startswith("index_backup_")]

            for backup_file in backup_files:
                backup_path = os.path.join(backup_dir, backup_file)

                # 检查文件年龄
                file_age = current_time - os.path.getmtime(backup_path)

                if file_age > retention_seconds:
                    os.remove(backup_path)
                    logger.info(f"删除过期备份: {backup_file}")

        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")

    async def stop_monitoring(self):
        """停止监控"""
        logger.info("停止索引监控...")
        self.monitoring_enabled = False

    def get_registered_indexes(self) -> Dict[str, IndexConfig]:
        """获取已注册的索引"""
        return self.registered_indexes.copy()

    def get_index_metrics(self) -> Dict[str, IndexMetrics]:
        """获取索引指标"""
        return self.index_metrics.copy()
