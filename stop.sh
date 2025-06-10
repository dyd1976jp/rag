#!/bin/bash

echo "正在停止RAG系统..."

# 注意：此脚本不会自动停止数据库服务
# 如果需要停止数据库服务，请取消下面的注释

# 停止MongoDB容器
# if docker ps | grep -q "mongodb"; then
#     echo "停止MongoDB数据库..."
#     docker stop mongodb
#     docker rm mongodb
#     echo "MongoDB数据库已停止"
# fi

# 停止Milvus容器
# if docker ps | grep -q "milvus-standalone"; then
#     echo "停止Milvus向量数据库..."
#     docker stop milvus-standalone
#     docker rm milvus-standalone
#     echo "Milvus向量数据库已停止"
# fi

# 清理临时脚本
echo "清理临时文件..."
rm -f /tmp/start_backend.sh
rm -f /tmp/start_frontend.sh

echo "前端和后端服务已停止"
echo "提示: 数据库服务(MongoDB和Milvus)仍在运行"
echo "如需停止数据库服务，请编辑此脚本并取消相关代码的注释" 