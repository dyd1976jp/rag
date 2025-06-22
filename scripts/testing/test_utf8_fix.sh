#!/bin/bash

# UTF-8编码错误修复测试脚本
# 测试RAG文档预览分割API的UTF-8编码问题修复

set -e

# 配置
API_BASE_URL="http://localhost:8000/api/v1"
TOKEN_FILE="temp/admin_token.txt"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== RAG API UTF-8编码错误修复测试 ===${NC}"

# 检查token文件
if [ ! -f "$TOKEN_FILE" ]; then
    echo -e "${RED}错误: 找不到token文件 $TOKEN_FILE${NC}"
    echo "请先运行登录获取token"
    exit 1
fi

TOKEN=$(cat "$TOKEN_FILE")
if [ -z "$TOKEN" ]; then
    echo -e "${RED}错误: token文件为空${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Token已加载${NC}"

# 测试1: 测试纯文本分割预览端点（JSON格式）
echo -e "\n${YELLOW}测试1: 纯文本分割预览端点${NC}"
echo "端点: POST /rag/documents/preview-split"

curl -X POST "$API_BASE_URL/rag/documents/preview-split" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "这是一个测试文档。\n\n它包含多个段落。\n\n每个段落都有不同的内容。\n\n这样可以测试分割功能。",
    "parent_chunk_size": 100,
    "parent_chunk_overlap": 20,
    "parent_separator": "\n\n",
    "child_chunk_size": 50,
    "child_chunk_overlap": 10,
    "child_separator": "\n"
  }' \
  --max-time 30 \
  | jq '.success, .message, .total_segments' 2>/dev/null || echo "JSON解析失败，显示原始响应"

echo -e "\n${GREEN}✓ 测试1完成${NC}"

# 测试2: 测试文件上传预览端点（multipart/form-data格式）
echo -e "\n${YELLOW}测试2: 文件上传预览端点${NC}"
echo "端点: POST /rag/documents/upload (preview_only=true)"

# 创建测试PDF文件（如果不存在）
TEST_PDF="temp/测试文档.pdf"
if [ ! -f "$TEST_PDF" ]; then
    echo "创建测试PDF文件..."
    mkdir -p temp
    # 创建一个简单的文本文件，然后重命名为PDF（用于测试）
    echo "这是一个测试PDF文档。

它包含中文字符和多个段落。

第一段：介绍内容
第二段：详细说明
第三段：总结内容

这样可以测试PDF文件的上传和分割功能。" > "$TEST_PDF"
fi

curl -X POST "$API_BASE_URL/rag/documents/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$TEST_PDF" \
  -F "parent_chunk_size=200" \
  -F "parent_chunk_overlap=50" \
  -F "parent_separator=\n\n" \
  -F "child_chunk_size=100" \
  -F "child_chunk_overlap=20" \
  -F "child_separator=\n" \
  -F "preview_only=true" \
  --max-time 30 \
  | jq '.success, .message, .total_segments // .segments_count' 2>/dev/null || echo "JSON解析失败，显示原始响应"

echo -e "\n${GREEN}✓ 测试2完成${NC}"

# 测试3: 测试错误的端点调用（应该返回友好的错误信息）
echo -e "\n${YELLOW}测试3: 错误端点调用测试${NC}"
echo "测试向preview-split端点发送multipart数据（应该返回友好错误）"

curl -X POST "$API_BASE_URL/rag/documents/preview-split" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$TEST_PDF" \
  -F "parent_chunk_size=200" \
  --max-time 30 \
  | jq '.detail, .error_type, .suggestion' 2>/dev/null || echo "JSON解析失败，显示原始响应"

echo -e "\n${GREEN}✓ 测试3完成${NC}"

# 测试4: 测试空内容的处理
echo -e "\n${YELLOW}测试4: 空内容处理测试${NC}"

curl -X POST "$API_BASE_URL/rag/documents/preview-split" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "",
    "parent_chunk_size": 100
  }' \
  --max-time 30 \
  | jq '.detail' 2>/dev/null || echo "JSON解析失败，显示原始响应"

echo -e "\n${GREEN}✓ 测试4完成${NC}"

echo -e "\n${BLUE}=== 所有测试完成 ===${NC}"
echo -e "${GREEN}如果所有测试都返回了正确的JSON响应而不是500错误，说明UTF-8编码问题已修复${NC}"
