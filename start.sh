#!/bin/bash

echo "开始启动RAG系统..."

# 定义变量
BACKEND_DIR="/Users/tei/go/RAG-chat"
FRONTEND_DIR="/Users/tei/go/RAG-chat/frontend/admin"

# 检查MongoDB是否已经运行，但不自动启动
echo "检查MongoDB服务状态..."
if docker ps | grep -q "mongodb"; then
    echo "MongoDB服务已经在运行"
else
    echo "警告: MongoDB服务未运行，请手动启动:"
    echo "docker run -d --name mongodb -p 27017:27017 -v /Users/tei/go/RAG-chat/data/mongodb:/data/db mongo:4.4"
    echo "部分功能可能无法正常工作"
fi

# 检查Milvus是否已经运行，但不自动启动
echo "检查Milvus服务状态..."
if docker ps | grep -q "milvus-standalone"; then
    echo "Milvus服务已经在运行"
else
    echo "警告: Milvus服务未运行，请手动启动:"
    echo "docker run -d --name milvus-standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:latest standalone"
    echo "RAG功能可能无法正常工作"
fi

# 创建后端启动脚本
cat > /tmp/start_backend.sh << 'EOF'
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
chmod +x /tmp/start_backend.sh

# 创建前端启动脚本
cat > /tmp/start_frontend.sh << 'EOF'
#!/bin/bash
cd "/Users/tei/go/RAG-chat/frontend/admin"
# 启动前端服务
npm run dev
EOF
chmod +x /tmp/start_frontend.sh

# 在新终端窗口中启动后端服务
echo "正在启动后端服务..."
osascript -e 'tell application "Terminal" to do script "/tmp/start_backend.sh"'
echo "后端服务正在新窗口中启动"

# 等待1秒
sleep 1

# 在新终端窗口中启动前端服务
echo "正在启动前端管理界面..."
osascript -e 'tell application "Terminal" to do script "/tmp/start_frontend.sh"'
echo "前端管理界面正在新窗口中启动"

echo "系统启动完成！"
echo "MongoDB: mongodb://localhost:27017"
echo "Milvus: localhost:19530"
echo "后端访问地址: http://localhost:8000"
echo "管理界面访问地址: http://localhost:5173"
echo "Milvus管理界面: http://localhost:9091"
echo "管理员账户: admin"
echo "默认密码: adminpassword"

echo ""
echo "各服务已在独立窗口中启动，请在相应窗口中查看日志"
echo "关闭相应终端窗口即可停止对应服务" 