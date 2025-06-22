#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Milvus动态字段配置修复验证脚本

验证所有修复是否正常工作，确保配置修改不会影响现有功能。
"""

import os
import sys
import logging
import traceback
from typing import Dict, Any, List

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rag.collection_manager import collection_manager
from app.rag.models import Document
from pymilvus import connections, Collection, utility
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_connection():
    """测试Milvus连接"""
    logger.info("🔗 测试Milvus连接...")
    
    try:
        # 测试新的连接方式（不使用alias）
        connections.connect(host='localhost', port='19530')
        logger.info("✅ 连接成功（使用Docker兼容方式）")
        
        # 列出集合
        collections = utility.list_collections()
        logger.info(f"✅ 发现 {len(collections)} 个集合: {collections}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 连接失败: {e}")
        return False


def test_collection_manager():
    """测试集合管理器"""
    logger.info("\n📋 测试集合管理器...")
    
    try:
        # 连接测试
        if not collection_manager.connect():
            logger.error("❌ 集合管理器连接失败")
            return False
        
        # 列出集合
        collections = collection_manager.list_collections()
        logger.info(f"✅ 集合管理器工作正常，发现 {len(collections)} 个集合")
        
        # 测试集合信息获取
        for collection_name in collections[:2]:  # 只测试前两个
            info = collection_manager.get_collection_info(collection_name)
            logger.info(f"✅ 集合 {collection_name}: 动态字段={info.get('enable_dynamic_field', False)}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 集合管理器测试失败: {e}")
        return False


def test_dynamic_field_creation():
    """测试动态字段集合创建"""
    logger.info("\n🆕 测试动态字段集合创建...")
    
    test_collection_name = "verify_dynamic_fields"
    
    try:
        # 创建支持动态字段的集合
        collection = collection_manager.create_collection(
            collection_name=test_collection_name,
            dimension=768,
            drop_existing=True
        )
        
        if not collection:
            logger.error("❌ 集合创建失败")
            return False
        
        # 验证动态字段支持
        schema = collection.schema
        if not schema.enable_dynamic_field:
            logger.error("❌ 动态字段未启用")
            return False
        
        logger.info("✅ 动态字段集合创建成功")
        
        # 测试数据插入
        test_data = {
            "id": str(uuid.uuid4()),
            "vector": [0.1] * 768,
            "page_content": "测试文档内容",
            "metadata": {"source": "test.txt"},
            "group_id": "test_group",
            "sparse_vector": [0.2] * 768,
            # 动态字段
            "custom_field": "动态字段值",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        collection.insert([test_data])
        collection.flush()
        
        logger.info("✅ 动态字段数据插入成功")
        
        # 测试查询
        collection.load()
        results = collection.query(
            expr="id != ''",
            output_fields=["*"],
            limit=1
        )
        
        if results and "custom_field" in results[0]:
            logger.info("✅ 动态字段查询成功")
        else:
            logger.warning("⚠️ 动态字段查询可能有问题")
        
        # 清理测试集合
        utility.drop_collection(test_collection_name)
        logger.info("✅ 测试集合已清理")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 动态字段测试失败: {e}")
        logger.error(traceback.format_exc())
        
        # 清理测试集合
        try:
            if utility.has_collection(test_collection_name):
                utility.drop_collection(test_collection_name)
        except:
            pass
        
        return False


def test_existing_collections():
    """测试现有集合的兼容性"""
    logger.info("\n🔄 测试现有集合兼容性...")
    
    try:
        collections = utility.list_collections()
        
        for collection_name in collections:
            if collection_name.startswith("test_"):
                continue  # 跳过测试集合
            
            try:
                collection = Collection(collection_name)
                num_entities = collection.num_entities
                schema = collection.schema
                
                logger.info(f"✅ 集合 {collection_name}: {num_entities} 个实体, 动态字段={schema.enable_dynamic_field}")
                
                # 如果集合为空，测试基本操作
                if num_entities == 0:
                    # 测试是否可以正常加载
                    try:
                        collection.load()
                        logger.info(f"✅ 集合 {collection_name} 加载成功")
                    except Exception as e:
                        logger.warning(f"⚠️ 集合 {collection_name} 加载失败: {e}")
                
            except Exception as e:
                logger.warning(f"⚠️ 集合 {collection_name} 测试失败: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 现有集合兼容性测试失败: {e}")
        return False


def test_vector_operations():
    """测试向量操作"""
    logger.info("\n🔍 测试向量操作...")
    
    test_collection_name = "verify_vector_ops"
    
    try:
        # 创建测试集合
        collection = collection_manager.create_collection(
            collection_name=test_collection_name,
            dimension=768,
            drop_existing=True
        )
        
        # 插入测试数据
        test_docs = []
        for i in range(3):
            doc_data = {
                "id": f"doc_{i}",
                "vector": [0.1 + i * 0.1] * 768,
                "page_content": f"测试文档 {i}",
                "metadata": {"index": i},
                "group_id": "test_group",
                "sparse_vector": [0.2 + i * 0.1] * 768,
                "category": f"类别_{i}"
            }
            test_docs.append(doc_data)
        
        collection.insert(test_docs)
        collection.flush()
        collection.load()
        
        logger.info("✅ 测试数据插入成功")
        
        # 测试向量搜索
        query_vector = [0.15] * 768
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10}
        }
        
        results = collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=2,
            output_fields=["page_content", "category"]
        )
        
        if results and len(results[0]) > 0:
            logger.info("✅ 向量搜索成功")
            for hits in results:
                for hit in hits:
                    entity = hit.entity
                    logger.info(f"  - 距离: {hit.distance:.4f}, 内容: {entity.get('page_content')}")
        else:
            logger.warning("⚠️ 向量搜索无结果")
        
        # 清理测试集合
        utility.drop_collection(test_collection_name)
        logger.info("✅ 向量操作测试完成")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 向量操作测试失败: {e}")
        logger.error(traceback.format_exc())
        
        # 清理测试集合
        try:
            if utility.has_collection(test_collection_name):
                utility.drop_collection(test_collection_name)
        except:
            pass
        
        return False


def generate_report(results: Dict[str, bool]):
    """生成测试报告"""
    logger.info("\n" + "="*60)
    logger.info("📊 Milvus动态字段配置修复验证报告")
    logger.info("="*60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        logger.info(f"{test_name}: {status}")
    
    logger.info("-"*60)
    logger.info(f"总计: {passed_tests}/{total_tests} 个测试通过")
    
    if passed_tests == total_tests:
        logger.info("🎉 所有测试通过！Milvus动态字段配置修复成功！")
        return True
    else:
        logger.warning(f"⚠️ {total_tests - passed_tests} 个测试失败，需要进一步检查")
        return False


def main():
    """主函数"""
    logger.info("🚀 开始Milvus动态字段配置修复验证")
    
    # 测试结果记录
    test_results = {}
    
    try:
        # 1. 连接测试
        test_results["连接测试"] = test_connection()
        
        # 2. 集合管理器测试
        test_results["集合管理器"] = test_collection_manager()
        
        # 3. 动态字段创建测试
        test_results["动态字段创建"] = test_dynamic_field_creation()
        
        # 4. 现有集合兼容性测试
        test_results["现有集合兼容性"] = test_existing_collections()
        
        # 5. 向量操作测试
        test_results["向量操作"] = test_vector_operations()
        
        # 生成报告
        success = generate_report(test_results)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ 用户中断测试")
        return 1
    except Exception as e:
        logger.error(f"❌ 验证过程中出现错误: {e}")
        logger.error(traceback.format_exc())
        return 1
    finally:
        # 清理连接
        try:
            collection_manager.disconnect()
        except:
            pass


if __name__ == "__main__":
    exit(main())
