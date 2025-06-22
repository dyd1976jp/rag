#!/bin/bash

# 确保脚本在错误时退出
set -e

echo "开始初始化数据库..."

# 检查MongoDB是否运行
if ! nc -z localhost 27017; then
    echo "错误: MongoDB未运行，请先启动MongoDB"
    exit 1
fi

# 检查Milvus是否运行
if ! nc -z localhost 19530; then
    echo "错误: Milvus未运行，请先启动Milvus"
    exit 1
fi

# 切换到backend目录
cd "$(dirname "$0")/../../.."

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 安装依赖
cd backend
pip install -r requirements.txt

# 运行Python初始化脚本
PYTHONPATH=. python -c "
import asyncio
from database.scripts.init_db import init_databases

asyncio.run(init_databases())
"

echo "数据库初始化完成！" 