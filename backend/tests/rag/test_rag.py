import asyncio
import logging
import uuid
import sys
import os
import socket

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.db.mongodb import mongodb
from app.rag import initialize_rag
from app.rag.document_processor import Document
import app.rag as rag

def check_milvus_available():
    """检查Milvus服务是否可用"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', 19530))
        sock.close()
        return result == 0
    except Exception:
        return False

async def test_document_storage_verification():
    """
    测试文档分割和存储的正确性。
    1. 分割文档。
    2. 存储分块。
    3. 从数据库中取回分块。
    4. 验证内容是否一致。
    """
    logger.info("开始测试文档存储验证")

    if not check_milvus_available():
        logger.error("Milvus服务不可用，测试无法继续")
        return

    await mongodb.connect()
    await initialize_rag()

    try:
        # 1. Arrange: 准备测试数据
        doc_id = f"test-doc-{uuid.uuid4()}"
        dataset_id = "storage-verification-dataset"
        content = "这是第一句，用于验证。这是第二句，同样用于验证。这是第三句，确保内容完整。"
        
        document = Document(
            page_content=content,
            metadata={
                "doc_id": doc_id,
                "document_id": doc_id,
                "dataset_id": dataset_id,
                "file_name": "storage_test.txt"
            }
        )

        # 创建集合
        collection_name = "test_verification_collection"
        rag.retrieval_service.vector_store.create_collection(collection_name, 768)

        # 模拟 RAGService 在 MongoDB 中创建初始记录
        await mongodb.db["documents"].insert_one({
            "id": doc_id,
            "status": "processing",
            "file_name": "storage_test.txt",
            "user_id": "test_user"
        })

        # 2. Act: 分割和存储
        segments = rag.document_splitter.split_document(document)
        logger.info(f"文档分割成 {len(segments)} 个段落")
        assert len(segments) > 0, "文档未能成功分割"

        segment_ids = [seg.metadata["doc_id"] for seg in segments]

        try:
            batch_result = await rag.retrieval_service.process_and_index_documents_batch(
                documents=segments,
                collection_name=collection_name
            )
            assert batch_result["success"], "批量索引失败"
            logger.info("文档批量索引成功")
        except Exception as e:
            logger.error(f"批量索引过程中出现异常: {e}")
            return

        # 更新 MongoDB 中的文档状态
        await mongodb.db["documents"].update_one(
            {"id": doc_id},
            {"$set": {"status": "ready", "segments_count": len(segments)}}
        )

        # 3. Assert: 验证存储的数据
        logger.info("开始验证存储的数据")

        # a. 验证 Vector DB (Milvus) 中的数据
        try:
            retrieved_segments = rag.retrieval_service.vector_store.get_by_ids(segment_ids)
            assert len(retrieved_segments) == len(segments), "从向量数据库中检索到的段落数量不匹配"
            logger.info(f"成功从向量数据库中检索到 {len(retrieved_segments)} 个段落")

            original_contents = {seg.metadata["doc_id"]: seg.page_content for seg in segments}
            
            for retrieved_seg in retrieved_segments:
                original_content = original_contents.get(retrieved_seg.metadata["doc_id"])
                assert original_content is not None, f"未找到ID为 {retrieved_seg.metadata['doc_id']} 的原始段落"
                assert retrieved_seg.page_content == original_content, "检索到的段落内容与原始内容不匹配"
            
            logger.info("向量数据库中的所有段落内容验证成功")

        except Exception as e:
            logger.error(f"从向量数据库验证数据时出错: {e}")
            assert False, f"向量数据库验证失败: {e}"

        # b. 验证 MongoDB 中的元数据
        try:
            doc_record = await mongodb.db["documents"].find_one({"id": doc_id})
            assert doc_record is not None, "在 MongoDB 中未找到文档记录"
            assert doc_record["status"] == "ready", f"MongoDB 中文档状态不正确: {doc_record['status']}"
            assert doc_record["segments_count"] == len(segments), "MongoDB 中的段落数量不正确"
            logger.info("MongoDB 中的文档元数据验证成功")

        except Exception as e:
            logger.error(f"从 MongoDB 验证数据时出错: {e}")
            assert False, f"MongoDB 验证失败: {e}"

    finally:
        # 清理测试数据
        await mongodb.db["documents"].delete_one({"id": doc_id})
        rag.retrieval_service.vector_store.delete(segment_ids)
        logger.info(f"测试数据清理完毕: doc_id={doc_id}")
        await mongodb.close()

    logger.info("文档存储验证测试成功完成")

if __name__ == "__main__":
    asyncio.run(test_document_storage_verification()) 