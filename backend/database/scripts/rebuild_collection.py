import os
import sys
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import numpy as np
import uuid

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.rag.constants import Field, DEFAULT_COLLECTION_NAME

def rebuild_collection():
    try:
        # 连接到 Milvus
        print("正在连接到 Milvus...")
        connections.connect(
            alias="default",
            host=os.environ.get("MILVUS_HOST", "localhost"),
            port=os.environ.get("MILVUS_PORT", "19530")
        )

        # 如果集合存在，先导出数据
        if utility.has_collection(DEFAULT_COLLECTION_NAME):
            print(f"发现现有集合 {DEFAULT_COLLECTION_NAME}，准备导出数据...")
            old_collection = Collection(DEFAULT_COLLECTION_NAME)
            
            try:
                old_collection.load()
                old_data = old_collection.query(expr="id != ''", output_fields=["*"])
                print(f"成功导出 {len(old_data)} 条数据")
            except Exception as e:
                print(f"导出数据失败（可能是集合为空或没有索引）：{str(e)}")
                old_data = []

            # 删除现有集合
            print(f"正在删除集合 {DEFAULT_COLLECTION_NAME}...")
            try:
                old_collection.release()
            except:
                pass
            utility.drop_collection(DEFAULT_COLLECTION_NAME)
            print("集合删除成功")
        else:
            old_data = []
            print("未发现现有集合，将创建新集合")

        # 创建新的集合
        print("正在创建新集合...")
        fields = [
            FieldSchema(
                name=Field.PRIMARY_KEY.value,
                dtype=DataType.VARCHAR,
                is_primary=True,
                auto_id=False,
                max_length=100
            ),
            FieldSchema(
                name=Field.VECTOR.value,
                dtype=DataType.FLOAT_VECTOR,
                dim=768
            ),
            FieldSchema(
                name=Field.CONTENT_KEY.value,
                dtype=DataType.VARCHAR,
                max_length=65535
            ),
            FieldSchema(
                name=Field.METADATA_KEY.value,
                dtype=DataType.JSON
            ),
            FieldSchema(
                name=Field.GROUP_KEY.value,
                dtype=DataType.VARCHAR,
                max_length=100
            ),
            FieldSchema(
                name=Field.SPARSE_VECTOR.value,
                dtype=DataType.FLOAT_VECTOR,
                dim=768
            )
        ]

        schema = CollectionSchema(
            fields=fields,
            description="Document vectors with text and metadata"
        )

        collection = Collection(
            name=DEFAULT_COLLECTION_NAME,
            schema=schema
        )

        print("新集合创建成功")

        # 如果有旧数据，导入到新集合
        if old_data:
            print("正在导入旧数据...")
            # 需要转换数据格式以匹配新的schema
            new_data = []
            default_vector = [0.0] * 768  # 默认向量
            
            for item in old_data:
                vector = item.get('vector')
                # 确保向量是有效的浮点数列表
                if not isinstance(vector, list) or len(vector) != 768 or not all(isinstance(x, (int, float)) for x in vector):
                    vector = default_vector
                
                new_item = {
                    Field.PRIMARY_KEY.value: item.get('id', str(uuid.uuid4())),
                    Field.VECTOR.value: vector,
                    Field.CONTENT_KEY.value: item.get('page_content', ''),
                    Field.METADATA_KEY.value: item.get('metadata', {}),
                    Field.GROUP_KEY.value: item.get('group_id', ''),
                    Field.SPARSE_VECTOR.value: vector  # 使用相同的向量作为稀疏向量
                }
                new_data.append(new_item)
            
            # 批量插入数据
            batch_size = 100
            for i in range(0, len(new_data), batch_size):
                batch = new_data[i:i + batch_size]
                collection.insert(batch)
                print(f"已导入 {min(i + batch_size, len(new_data))}/{len(new_data)} 条数据")

            print(f"成功导入 {len(new_data)} 条数据")

        # 创建索引
        print("正在创建索引...")
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        
        # 为 vector 字段创建索引
        print("为 vector 字段创建索引...")
        collection.create_index(Field.VECTOR.value, index_params)
        print("vector 字段索引创建成功")
        
        # 为 sparse_vector 字段创建索引
        print("为 sparse_vector 字段创建索引...")
        collection.create_index(Field.SPARSE_VECTOR.value, index_params)
        print("sparse_vector 字段索引创建成功")

        # 加载集合以验证
        print("正在加载集合进行验证...")
        collection.load()
        num_entities = collection.num_entities
        print(f"集合实体数量：{num_entities}")
        
        # 验证索引
        indexes = collection.indexes
        print(f"集合索引信息：{indexes}")
        
        collection.release()

        print("集合重建完成！")

    except Exception as e:
        print(f"错误：{str(e)}")
    finally:
        try:
            connections.disconnect("default")
        except:
            pass

if __name__ == "__main__":
    rebuild_collection() 