#!/bin/bash

echo "正在初始化 Milvus 集合并重启后端服务..."

# 激活Conda环境
echo "正在激活Conda环境(rag-chat)..."
source /opt/anaconda3/bin/activate rag-chat

# 设置环境变量
export PYTHONPATH="/Users/tei/go/RAG-chat/backend"
export MONGODB_URL="mongodb://localhost:27017"
export MONGODB_DB="ragchat"
export ENVIRONMENT="development"
export LOGLEVEL="INFO"
export MILVUS_HOST="localhost"
export MILVUS_PORT="19530"

# 首先初始化 Milvus 集合
echo "初始化 Milvus 集合..."
cd "/Users/tei/go/RAG-chat"
python backend/scripts/initialize_milvus.py

# 检查初始化是否成功
if [ $? -ne 0 ]; then
    echo "Milvus 集合初始化失败，请检查错误信息"
    exit 1
fi

echo "Milvus 集合初始化成功，准备重启后端服务..."

# 使用 restart_backend.sh 重启服务
./restart_backend.sh 