#!/bin/bash

# 测试 RAG 文档上传 API 的脚本

# 设置变量
API_URL="http://localhost:8000/api/v1/rag/documents/upload"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzUwMjMyNzE5fQ.lA-qsA9QhfbsYzg8YeKnA1wt8R6q-PcpDEf_r4sJLxY"
FILE_PATH="/Users/tei/go/RAG-chat/data/uploads/初赛训练数据集.pdf"

echo "=== 测试 RAG 文档上传 API ==="
echo "API URL: $API_URL"
echo "文件路径: $FILE_PATH"
echo ""

# 检查文件是否存在
if [ ! -f "$FILE_PATH" ]; then
    echo "错误: 文件不存在 - $FILE_PATH"
    exit 1
fi

echo "开始发送上传请求..."

# 测试文档上传（预览模式）
echo "=== 测试预览模式上传 ==="
curl -X POST "$API_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$FILE_PATH" \
  -F "parent_chunk_size=1024" \
  -F "parent_chunk_overlap=200" \
  -F "parent_separator=\n\n" \
  -F "child_chunk_size=512" \
  -F "child_chunk_overlap=50" \
  -F "child_separator=\n" \
  -F "preview_only=true" \
  --max-time 30 \
  | jq '.success, .message, .segments_count // .total_segments' 2>/dev/null || cat

echo ""
echo "=== 预览模式测试完成 ==="

echo ""
echo "=== 测试实际上传模式 ==="
curl -X POST "$API_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$FILE_PATH" \
  -F "parent_chunk_size=512" \
  -F "parent_chunk_overlap=100" \
  -F "parent_separator=\n\n" \
  -F "child_chunk_size=256" \
  -F "child_chunk_overlap=25" \
  -F "child_separator=\n" \
  -F "preview_only=false" \
  --max-time 60 \
  | jq '.success, .message, .doc_id, .segments_count' 2>/dev/null || cat

echo ""
echo "=== 实际上传测试完成 ==="
