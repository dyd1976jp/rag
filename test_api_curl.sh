#!/bin/bash

# 测试文档分割API的curl脚本
# 用于验证API的功能和性能
#
# 重要参数说明:
# - use_new_processor=false: 使用传统处理器，确保与页面预览一致
# - preview_only=true: 预览模式，不保存到数据库
# - 其他参数: parent_chunk_size, child_chunk_size等用于控制分割粒度

echo "=== 测试文档分割API ==="

# API端点
API_URL="http://localhost:8000/api/v1/rag/documents/upload"

# 测试文件路径
TEST_FILE="data/uploads/长文档测试.txt"

# 检查文件是否存在
if [ ! -f "$TEST_FILE" ]; then
    echo "错误: 测试文件不存在: $TEST_FILE"
    exit 1
fi

echo "测试文件: $TEST_FILE"
echo "API端点: $API_URL"
echo "使用传统处理器 (use_new_processor=false)"

# 执行curl请求
echo "发送请求..."
curl -X POST "$API_URL" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@$TEST_FILE" \
  -F "parent_chunk_size=1024" \
  -F "parent_chunk_overlap=200" \
  -F "parent_separator=\n\n" \
  -F "child_chunk_size=512" \
  -F "child_chunk_overlap=50" \
  -F "child_separator=\n" \
  -F "preview_only=true" \
  -F "processor_type=parent_child" \
  -F "parent_mode=paragraph" \
  -F "use_new_processor=false" \
  | jq '.'

echo ""
echo "=== 测试完成 ==="
