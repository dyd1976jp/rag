import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from ..config.settings import settings

async def init_mongodb():
    """初始化MongoDB连接和集合"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    
    # 创建索引
    await db.documents.create_index("title")
    await db.documents.create_index("file_path", unique=True)
    await db.documents.create_index("created_at")
    
    print("MongoDB初始化完成")
    return db

def init_milvus():
    """初始化Milvus连接和集合"""
    # 连接Milvus
    connections.connect(
        alias="default",
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT,
        user=settings.MILVUS_USER,
        password=settings.MILVUS_PASSWORD
    )
    
    # 检查集合是否存在，如果存在则删除
    if utility.has_collection(settings.MILVUS_COLLECTION):
        utility.drop_collection(settings.MILVUS_COLLECTION)
    
    # 定义集合字段
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=200),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=768)  # 使用text-embedding-nomic-embed-text-v1.5模型的维度
    ]
    
    # 创建集合schema
    schema = CollectionSchema(
        fields=fields,
        description="Document vectors for RAG system"
    )
    
    # 创建集合
    collection = Collection(
        name=settings.MILVUS_COLLECTION,
        schema=schema,
        using='default'
    )
    
    # 创建索引
    index_params = {
        "metric_type": "L2",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 1024}
    }
    collection.create_index(field_name="vector", index_params=index_params)
    
    print("Milvus初始化完成")
    return collection

async def init_databases():
    """初始化所有数据库"""
    try:
        # 初始化MongoDB
        db = await init_mongodb()
        
        # 初始化Milvus
        collection = init_milvus()
        
        print("所有数据库初始化完成")
        return db, collection
    except Exception as e:
        print(f"数据库初始化失败: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(init_databases()) 