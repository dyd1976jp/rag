#!/usr/bin/env python3
"""
向量存储检查工具 - 用于查看和管理Milvus向量存储
"""
import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from pymilvus import Collection, utility, connections
from app.rag.vector_store import MilvusVectorStore
from app.rag.document_processor import Document
from app.rag.embedding_model import EmbeddingModel

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('vector_inspection.log')
    ]
)
logger = logging.getLogger(__name__)

class VectorStoreInspector:
    def __init__(self, host: str = None, port: int = None):
        """初始化向量存储检查器"""
        # 设置LM Studio的嵌入模型配置
        os.environ["EMBEDDING_MODEL"] = os.getenv("EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")
        os.environ["EMBEDDING_API_BASE"] = os.getenv("EMBEDDING_API_BASE", "http://192.168.1.30:1234")
        
        self.host = host or os.getenv("MILVUS_HOST", "localhost")
        self.port = port or int(os.getenv("MILVUS_PORT", 19530))
        self.vector_store = None
        self.collection = None
        
    def connect(self) -> bool:
        """连接到Milvus服务器"""
        try:
            connections.connect(host=self.host, port=str(self.port))
            logger.info(f"成功连接到Milvus服务器: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"连接Milvus服务器失败: {e}")
            return False
    
    def list_collections(self) -> List[str]:
        """列出所有集合"""
        try:
            collections = utility.list_collections()
            logger.info(f"找到 {len(collections)} 个集合")
            return collections
        except Exception as e:
            logger.error(f"获取集合列表失败: {e}")
            return []
    
    def describe_collection(self, collection_name: str) -> Dict[str, Any]:
        """获取集合的详细信息"""
        try:
            if not utility.has_collection(collection_name):
                logger.error(f"集合 '{collection_name}' 不存在")
                return {}
                
            collection = Collection(collection_name)
            collection.load()
            
            # 获取集合统计信息
            stats = {
                "name": collection_name,
                "description": collection.description,
                "num_entities": collection.num_entities,
                "primary_field": collection.primary_field,
                "auto_id": collection.schema.auto_id,
                "fields": [
                    {
                        "name": field.name,
                        "type": field.dtype.name,
                        "is_primary": field.is_primary,
                        "auto_id": field.auto_id,
                        "description": field.description or ""
                    }
                    for field in collection.schema.fields
                ],
                "indexes": []
            }
            
            # 获取索引信息
            try:
                for field in collection.schema.fields:
                    if field.name in ["vector", "sparse_vector"]:
                        # 获取索引状态（不指定字段名）
                        index_info = utility.index_building_progress(collection_name)
                        stats["indexes"].append({
                            "field": field.name,
                            "index_state": index_info
                        })
                        
                        # 获取索引参数
                        index_params = collection.index(index_name=f"{field.name}_index")
                        if index_params:
                            stats["indexes"][-1]["index_params"] = {
                                "index_type": index_params.params.get("index_type", ""),
                                "metric_type": index_params.params.get("metric_type", ""),
                                "params": index_params.params.get("params", {})
                            }
            except Exception as e:
                logger.warning(f"获取索引信息时出错: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"获取集合信息失败: {e}")
            return {}
    
    def query_vectors(self, collection_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """查询向量数据"""
        try:
            if not utility.has_collection(collection_name):
                logger.error(f"集合 '{collection_name}' 不存在")
                return []
                
            collection = Collection(collection_name)
            collection.load()
            
            # 获取集合中的记录
            results = []
            with collection.query_iterator(batch_size=min(limit, 1000)) as it:
                for i, item in enumerate(it):
                    if i >= limit:
                        break
                    
                    # 处理向量数据
                    result = {}
                    for field in collection.schema.fields:
                        if field.name in ["vector", "sparse_vector"]:
                            # 只显示向量维度和前几个值
                            vec = item[field.name]
                            if vec is not None and len(vec) > 0:
                                result[f"{field.name}_dims"] = len(vec)
                                result[f"{field.name}_sample"] = vec[:5].tolist() + ["..."]
                        else:
                            result[field.name] = item[field.name]
                    
                    results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"查询向量数据失败: {e}")
            return []
    
    def search_similar(self, collection_name: str, query: str, top_k: int = 3):
        """搜索相似向量"""
        if not self.connect():
            return []
            
        try:
            # 初始化嵌入模型
            embedding_model = EmbeddingModel()
            
            # 获取查询的嵌入向量
            logger.info("正在生成查询嵌入...")
            query_embedding = embedding_model.embed_query(query)
            logger.info(f"查询嵌入生成完成，维度: {len(query_embedding)}")
            
            # 确保集合存在
            if not utility.has_collection(collection_name):
                logger.error(f"集合 '{collection_name}' 不存在")
                return []
                
            # 获取集合信息
            collection = Collection(collection_name)
            collection.load()
            logger.info(f"集合 '{collection_name}' 已加载，包含 {collection.num_entities} 个实体")
            
            # 获取集合的字段
            fields = [field.name for field in collection.schema.fields]
            logger.info(f"集合字段: {fields}")
            
            # 准备搜索参数
            search_params = {
                "data": [query_embedding],
                "anns_field": "vector",
                "param": {"metric_type": "L2", "params": {"nprobe": 10}},
                "limit": top_k,
                "output_fields": ["*"]  # 返回所有字段
            }
            
            # 执行搜索
            logger.info("正在执行向量搜索...")
            results = collection.search(**search_params)
            
            # 处理结果
            formatted_results = []
            for i, hits in enumerate(results):
                for hit in hits:
                    result = {
                        "score": hit.distance,
                        "id": hit.id,
                        "entity": hit.entity.to_dict()
                    }
                    formatted_results.append(result)
            
            # 打印结果
            print(f"\n搜索与 '{query}' 相似的文档 (共 {len(formatted_results)} 个结果):")
            for i, result in enumerate(formatted_results, 1):
                print(f"\n结果 {i} (距离: {result['score']:.4f}):")
                print(f"ID: {result['id']}")
                entity = result['entity']
                for key, value in entity.items():
                    if isinstance(value, (str, int, float, bool)) or value is None:
                        print(f"{key}: {value}")
                    elif key == 'vector' and value is not None:
                        print(f"vector_dims: {len(value)}")
                        print(f"vector_sample: {value[:5]}..." if len(value) > 5 else f"vector: {value}")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"搜索相似向量失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

def print_collection_stats(stats: Dict[str, Any]):
    """打印集合统计信息"""
    print("\n=== 集合信息 ===")
    print(f"名称: {stats.get('name')}")
    print(f"实体数量: {stats.get('num_entities', 0):,}")
    print(f"主键字段: {stats.get('primary_field')}")
    
    print("\n字段:")
    for field in stats.get('fields', []):
        print(f"  - {field['name']} ({field['type']})")
        print(f"    主键: {'是' if field.get('is_primary') else '否'}")
        print(f"    描述: {field.get('description', '无')}")
    
    print("\n索引:")
    for idx in stats.get('indexes', []):
        print(f"  - 字段: {idx.get('field')}")
        print(f"    索引信息: {json.dumps(idx.get('index_info', {}), indent=4, ensure_ascii=False)}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='向量存储检查工具')
    parser.add_argument('--host', type=str, default=None, help='Milvus服务器主机')
    parser.add_argument('--port', type=int, default=None, help='Milvus服务器端口')
    parser.add_argument('--collection', type=str, help='指定要操作的集合名称')
    parser.add_argument('--list', action='store_true', help='列出所有集合')
    parser.add_argument('--stats', action='store_true', help='显示集合统计信息')
    parser.add_argument('--query', type=int, help='查询前N条记录')
    parser.add_argument('--search', type=str, help='搜索相似文本')
    parser.add_argument('--top-k', type=int, default=3, help='返回的相似结果数量，默认为3')
    
    args = parser.parse_args()
    
    # 初始化检查器
    inspector = VectorStoreInspector(host=args.host, port=args.port)
    
    # 连接到Milvus
    if not inspector.connect():
        sys.exit(1)
    
    # 列出所有集合
    if args.list:
        collections = inspector.list_collections()
        print("\n可用集合:")
        for i, col in enumerate(collections, 1):
            print(f"{i}. {col}")
    
    # 处理指定集合
    if args.collection:
        # 显示集合统计信息
        if args.stats:
            stats = inspector.describe_collection(args.collection)
            if stats:
                print_collection_stats(stats)
        
        # 查询记录
        if args.query:
            print(f"\n查询集合 '{args.collection}' 的前 {args.query} 条记录:")
            results = inspector.query_vectors(args.collection, limit=args.query)
            for i, result in enumerate(results, 1):
                print(f"\n记录 {i}:")
                for k, v in result.items():
                    if isinstance(v, (list, dict)):
                        print(f"  {k}: {json.dumps(v, ensure_ascii=False, indent=2)}")
                    else:
                        print(f"  {k}: {v}")
        
        # 搜索相似文本
        if args.search:
            print(f"\n搜索与 '{args.search}' 相似的文档:")
            results = inspector.search_similar(
                collection_name=args.collection,
                query=args.search,
                top_k=args.top_k
            )
            
            for i, result in enumerate(results, 1):
                print(f"\n结果 {i} (相似度: {1 - result.get('score', 0):.4f}):")
                print(f"  元数据: {json.dumps(result.get('metadata', {}), ensure_ascii=False, indent=2)}")
                print(f"  内容: {result.get('content', '')[:200]}...")

if __name__ == "__main__":
    main()
