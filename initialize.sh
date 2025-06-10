#!/bin/bash

echo "开始初始化RAG系统环境..."

# 激活Conda环境
echo "正在激活Conda环境(rag-chat)..."
source /opt/anaconda3/bin/activate rag-chat

# 创建必要的目录
echo "创建必要的数据目录..."
mkdir -p data/uploads
mkdir -p data/chroma

# 安装后端依赖
echo "安装后端依赖包..."
pip install -r requirements.txt

# 安装额外依赖
echo "安装额外依赖包..."
pip install PyPDF2 langchain langchain-community sentence-transformers psutil chromadb pymongo redis

# 安装前端依赖
echo "安装前端依赖包..."
cd frontend/admin
npm install
cd ../..

echo "初始化完成，现在可以运行 ./start.sh 启动系统。" 