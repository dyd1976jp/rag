from fastapi import APIRouter
from app.api.v1.endpoints import llm, discover, rag, document_collections

api_v1_router = APIRouter()

# 只包含存在的llm路由
api_v1_router.include_router(llm.router, prefix="/llm", tags=["大语言模型"]) 

# 添加发现模型路由
api_v1_router.include_router(discover.router, prefix="/discover", tags=["模型发现"])

# 添加RAG路由
api_v1_router.include_router(rag.router, prefix="/rag", tags=["检索增强生成"])

# 添加文档集合路由
api_v1_router.include_router(document_collections.router,prefix="/rag/collections",tags=["文档集"])

# 其他路由暂时注释掉，等模块创建好后再启用
# api_v1_router.include_router(auth.router, prefix="/auth", tags=["认证"])
# api_v1_router.include_router(users.router, prefix="/users", tags=["用户"])
# api_v1_router.include_router(documents.router, prefix="/documents", tags=["文档"])
# api_v1_router.include_router(knowledge_base.router, prefix="/knowledge-base", tags=["知识库"])
# api_v1_router.include_router(chat.router, prefix="/chat", tags=["聊天"])