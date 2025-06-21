from pymilvus import connections, Collection, utility
from ..core.config import settings

class MilvusDB:
    collection: Collection = None

    def connect(self):
        connections.connect(
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT
        )
        
        # 如果集合不存在，创建集合
        if not utility.has_collection(settings.MILVUS_COLLECTION):
            from ..rag.collection_manager import collection_manager

            # 使用统一的集合管理器创建集合
            self.collection = collection_manager.create_collection(
                collection_name=settings.MILVUS_COLLECTION,
                dimension=settings.MILVUS_DIM,
                drop_existing=False
            )

            if self.collection:
                # 创建索引
                collection_manager.create_indexes(self.collection)
            else:
                raise Exception("集合创建失败")
        else:
            self.collection = Collection(settings.MILVUS_COLLECTION)
            
    def disconnect(self):
        # 断开所有连接
        connections.disconnect()

milvus_db = MilvusDB() 