#!/bin/bash

# 测试两个端点的一致性

# 设置变量
PREVIEW_SPLIT_URL="http://localhost:8000/api/v1/rag/documents/preview-split"
UPLOAD_URL="http://localhost:8000/api/v1/rag/documents/upload"
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzUwMjMyNzE5fQ.lA-qsA9QhfbsYzg8YeKnA1wt8R6q-PcpDEf_r4sJLxY"
FILE_PATH="/Users/tei/go/RAG-chat/data/uploads/初赛训练数据集.pdf"

# 相同的分割参数
PARENT_CHUNK_SIZE=1024
PARENT_CHUNK_OVERLAP=200
PARENT_SEPARATOR="\n\n"
CHILD_CHUNK_SIZE=512
CHILD_CHUNK_OVERLAP=50
CHILD_SEPARATOR="\n"

echo "=== 测试端点一致性 ==="
echo "使用相同的参数测试两个端点："
echo "  parent_chunk_size: $PARENT_CHUNK_SIZE"
echo "  parent_chunk_overlap: $PARENT_CHUNK_OVERLAP"
echo "  child_chunk_size: $CHILD_CHUNK_SIZE"
echo "  child_chunk_overlap: $CHILD_CHUNK_OVERLAP"
echo ""

# 检查文件是否存在
if [ ! -f "$FILE_PATH" ]; then
    echo "错误: 文件不存在 - $FILE_PATH"
    exit 1
fi

echo "=== 测试 Preview-Split 端点 ==="
curl -X POST "$PREVIEW_SPLIT_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$FILE_PATH" \
  -F "parent_chunk_size=$PARENT_CHUNK_SIZE" \
  -F "parent_chunk_overlap=$PARENT_CHUNK_OVERLAP" \
  -F "parent_separator=$PARENT_SEPARATOR" \
  -F "child_chunk_size=$CHILD_CHUNK_SIZE" \
  -F "child_chunk_overlap=$CHILD_CHUNK_OVERLAP" \
  -F "child_separator=$CHILD_SEPARATOR" \
  --max-time 30 \
  | jq '.success, .total_segments, .segments | length, .segments[0].children | length' 2>/dev/null > preview_result.txt

echo ""
echo "Preview-Split 结果:"
cat preview_result.txt

echo ""
echo "=== 测试 Upload 端点 (预览模式) ==="
curl -X POST "$UPLOAD_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$FILE_PATH" \
  -F "parent_chunk_size=$PARENT_CHUNK_SIZE" \
  -F "parent_chunk_overlap=$PARENT_CHUNK_OVERLAP" \
  -F "parent_separator=$PARENT_SEPARATOR" \
  -F "child_chunk_size=$CHILD_CHUNK_SIZE" \
  -F "child_chunk_overlap=$CHILD_CHUNK_OVERLAP" \
  -F "child_separator=$CHILD_SEPARATOR" \
  -F "preview_only=true" \
  --max-time 30 \
  | jq '.success, .total_segments, .statistics.total_segments' 2>/dev/null > upload_result.txt

echo ""
echo "Upload (预览模式) 结果:"
cat upload_result.txt

echo ""
echo "=== 对比结果 ==="
echo "Preview-Split 结果:"
cat preview_result.txt
echo ""
echo "Upload (预览模式) 结果:"
cat upload_result.txt

# 清理临时文件
rm -f preview_result.txt upload_result.txt

echo ""
echo "=== 测试完成 ==="
