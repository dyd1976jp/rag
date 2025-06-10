from pymilvus import connections, Collection, utility
from ..core.config import settings

class MilvusDB:
    collection: Collection = None

    def connect(self):
        connections.connect(
            alias="default",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT
        )
        
        # 如果集合不存在，创建集合
        if not utility.has_collection(settings.MILVUS_COLLECTION):
            from pymilvus import CollectionSchema, FieldSchema, DataType
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="user_id", dtype=DataType.INT64),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=settings.MILVUS_DIM)
            ]
            schema = CollectionSchema(fields=fields, description="Document embeddings")
            self.collection = Collection(name=settings.MILVUS_COLLECTION, schema=schema)
            
            # 创建索引
            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024}
            }
            self.collection.create_index(field_name="embedding", index_params=index_params)
        else:
            self.collection = Collection(settings.MILVUS_COLLECTION)
            
    def disconnect(self):
        connections.disconnect("default")

milvus_db = MilvusDB() 