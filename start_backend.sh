#!/bin/bash

# RAG-Chat Backend 启动脚本
# 
# 使用方法:
#   ./start_backend.sh                    # 从backend目录启动 (推荐)
#   ./start_backend.sh --from-root        # 从项目根目录启动
#   ./start_backend.sh --port 8080        # 指定端口
#   ./start_backend.sh --help             # 显示帮助

set -e

# 默认配置
DEFAULT_PORT=8000
DEFAULT_HOST="0.0.0.0"
FROM_ROOT=false
PORT=$DEFAULT_PORT
HOST=$DEFAULT_HOST

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --from-root)
            FROM_ROOT=true
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --help)
            echo "RAG-Chat Backend 启动脚本"
            echo ""
            echo "使用方法:"
            echo "  $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --from-root     从项目根目录启动 (需要设置PYTHONPATH)"
            echo "  --port PORT     指定端口 (默认: $DEFAULT_PORT)"
            echo "  --host HOST     指定主机 (默认: $DEFAULT_HOST)"
            echo "  --help          显示此帮助信息"
            echo ""
            echo "推荐启动方式:"
            echo "  cd backend && ../start_backend.sh"
            echo ""
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            echo "使用 --help 查看帮助"
            exit 1
            ;;
    esac
done

# 检查是否在正确的目录
if [[ "$FROM_ROOT" == "true" ]]; then
    # 从根目录启动
    if [[ ! -f "backend/app/main.py" ]]; then
        echo "错误: 请在项目根目录运行此脚本 (包含backend/app/main.py的目录)"
        exit 1
    fi
    
    echo "从项目根目录启动 FastAPI 应用..."
    echo "端口: $PORT"
    echo "主机: $HOST"
    echo "模块: backend.app.main:app"
    echo ""
    
    export PYTHONPATH=backend:$PYTHONPATH
    exec python -m uvicorn backend.app.main:app --reload --host "$HOST" --port "$PORT"
    
else
    # 从backend目录启动 (推荐方式)
    if [[ ! -f "app/main.py" ]]; then
        echo "错误: 请在backend目录运行此脚本，或使用 --from-root 选项"
        echo "当前目录: $(pwd)"
        echo "期望文件: app/main.py"
        exit 1
    fi
    
    echo "从backend目录启动 FastAPI 应用..."
    echo "端口: $PORT"
    echo "主机: $HOST"
    echo "模块: app.main:app"
    echo ""
    
    exec python -m uvicorn app.main:app --reload --host "$HOST" --port "$PORT"
fi
