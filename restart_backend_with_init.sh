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
python backend/initialize_milvus.py

# 检查初始化是否成功
if [ $? -ne 0 ]; then
    echo "Milvus 集合初始化失败，请检查错误信息"
    exit 1
fi

echo "Milvus 集合初始化成功，准备重启后端服务..."

# 杀死现有的uvicorn进程
echo "停止现有的后端服务..."
pkill -f "uvicorn app.main:app"

# 等待进程结束
sleep 2

# 检查是否有uvicorn进程还在运行
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "警告: uvicorn进程仍在运行，尝试强制终止..."
    pkill -9 -f "uvicorn app.main:app"
    sleep 1
fi

# 创建后端启动脚本
cat > /tmp/restart_backend_with_init.sh << 'EOF'
#!/bin/bash
cd "/Users/tei/go/RAG-chat" 

# 激活Conda环境
echo "正在激活Conda环境(rag-chat)..."
source /opt/anaconda3/bin/activate rag-chat

# 设置环境变量
export MONGODB_URL="mongodb://localhost:27017"
export MONGODB_DB="ragchat"
export ENVIRONMENT="development"
export LOGLEVEL="INFO"
export MILVUS_HOST="localhost"
export MILVUS_PORT="19530"

# 确保必要的目录存在
mkdir -p data/uploads
mkdir -p data/chroma

# 进入backend目录启动
cd "/Users/tei/go/RAG-chat/backend"
export PYTHONPATH="/Users/tei/go/RAG-chat/backend"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
EOF
chmod +x /tmp/restart_backend_with_init.sh

# 在新终端窗口中启动后端服务
echo "正在重新启动后端服务..."
osascript -e 'tell application "Terminal" to do script "/tmp/restart_backend_with_init.sh"'

echo "后端服务正在新窗口中重新启动"
echo "访问地址: http://localhost:8000" 