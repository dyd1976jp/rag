from typing import List, Dict, Any
import uuid
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from app.core.vector_store import vector_store
from app.core.config import settings

class DocumentService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    async def process_document(self, content: str, metadata: Dict[str, Any]) -> str:
        """处理文档并存储到向量数据库"""
        # 分割文本
        chunks = self.text_splitter.split_text(content)
        
        # 生成文档ID
        doc_id = str(uuid.uuid4())
        
        # 准备元数据
        metadatas = [{
            **metadata,
            "chunk_index": i,
            "doc_id": doc_id
        } for i in range(len(chunks))]
        
        # 生成向量嵌入
        embeddings = await self.embeddings.aembed_documents(chunks)
        
        # 生成唯一ID
        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        
        # 存储到向量数据库
        vector_store.add_documents(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        return doc_id
    
    async def search_documents(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """搜索相关文档"""
        # 生成查询的向量嵌入
        query_embedding = await self.embeddings.aembed_query(query)
        
        # 搜索相似文档
        results = vector_store.search(query_embedding, n_results)
        return results
    
    async def delete_document(self, doc_id: str):
        """删除文档及其所有分块"""
        vector_store.delete_documents([doc_id])

# 创建全局文档服务实例
document_service = DocumentService() 