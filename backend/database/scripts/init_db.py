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
    # 连接Milvus - 使用Docker兼容的连接方式
    connections.connect(
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT
    )
    
    # 检查集合是否存在，如果存在则删除
    if utility.has_collection(settings.MILVUS_COLLECTION):
        utility.drop_collection(settings.MILVUS_COLLECTION)
    
    # 使用统一的集合管理器创建标准schema
    from app.rag.collection_manager import collection_manager

    # 创建支持动态字段的标准schema
    schema = collection_manager.create_standard_schema(dimension=768)
    
    # 创建集合
    collection = Collection(
        name=settings.MILVUS_COLLECTION,
        schema=schema
    )

    # 使用集合管理器创建索引
    collection_manager.create_indexes(collection)
    
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