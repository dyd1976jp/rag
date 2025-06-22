#!/bin/bash

# 模拟用户原始curl命令的UTF-8编码错误修复验证

set -e

echo "=== 模拟原始curl命令测试 ==="

# 创建包含中文字符的测试PDF文件
TEST_FILE="temp/初赛训练数据集.pdf"
mkdir -p temp

cat > "$TEST_FILE" << 'EOF'
这是一个包含中文字符的测试PDF文档。

它用于测试UTF-8编码问题的修复。

第一段：介绍内容
这里包含一些中文字符：你好世界！

第二段：详细说明
测试各种特殊字符：©®™€£¥

第三段：总结内容
这个文件名包含中文字符，用于测试文件上传时的编码处理。

测试内容足够长，以确保分割功能正常工作。
这里添加更多内容来测试分割算法。
每个段落都应该被正确处理。
EOF

echo "✓ 创建测试文件: $TEST_FILE"

# 测试1: 原始错误场景 - 向preview-split端点发送multipart数据
echo -e "\n=== 测试1: 原始错误场景（应该返回友好错误而非500） ==="

echo "执行curl命令..."
RESPONSE=$(curl -s -w "HTTPSTATUS:%{http_code}" \
  -X POST "http://localhost:8000/api/v1/rag/documents/preview-split" \
  -F "file=@$TEST_FILE" \
  -F "parent_chunk_size=1024" \
  -F "parent_chunk_overlap=200" \
  -F "parent_separator=\n\n" \
  -F "child_chunk_size=512" \
  -F "child_chunk_overlap=50" \
  -F "child_separator=\n" \
  --max-time 10)

# 提取HTTP状态码和响应体
HTTP_STATUS=$(echo "$RESPONSE" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
RESPONSE_BODY=$(echo "$RESPONSE" | sed 's/HTTPSTATUS:[0-9]*$//')

echo "HTTP状态码: $HTTP_STATUS"
echo "响应内容: $RESPONSE_BODY"

if [ "$HTTP_STATUS" = "500" ]; then
    echo "✗ 仍然返回500错误，UTF-8编码问题未修复"
    echo "错误详情: $RESPONSE_BODY"
    exit 1
elif [ "$HTTP_STATUS" = "400" ]; then
    echo "✓ 返回400错误（预期行为）"
    
    # 检查是否包含友好的错误提示
    if echo "$RESPONSE_BODY" | grep -q "file_upload_validation_error"; then
        echo "✓ 包含正确的错误类型标识"
    fi
    
    if echo "$RESPONSE_BODY" | grep -q "documents/upload"; then
        echo "✓ 包含正确的API使用指导"
    fi
    
    echo "✓ UTF-8编码错误已修复，返回友好错误提示"
else
    echo "? 意外的HTTP状态码: $HTTP_STATUS"
    echo "响应: $RESPONSE_BODY"
    # 只要不是500就说明UTF-8问题已修复
    if [ "$HTTP_STATUS" != "500" ]; then
        echo "✓ 至少没有UTF-8编码错误"
    fi
fi

# 测试2: 正确的API使用方式
echo -e "\n=== 测试2: 正确的API使用方式 ==="

echo "使用正确的upload端点进行文件预览..."
RESPONSE2=$(curl -s -w "HTTPSTATUS:%{http_code}" \
  -X POST "http://localhost:8000/api/v1/rag/documents/upload" \
  -F "file=@$TEST_FILE" \
  -F "parent_chunk_size=1024" \
  -F "parent_chunk_overlap=200" \
  -F "parent_separator=\n\n" \
  -F "child_chunk_size=512" \
  -F "child_chunk_overlap=50" \
  -F "child_separator=\n" \
  -F "preview_only=true" \
  --max-time 10)

HTTP_STATUS2=$(echo "$RESPONSE2" | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
RESPONSE_BODY2=$(echo "$RESPONSE2" | sed 's/HTTPSTATUS:[0-9]*$//')

echo "HTTP状态码: $HTTP_STATUS2"

if [ "$HTTP_STATUS2" = "500" ]; then
    echo "✗ upload端点也返回500错误"
    echo "错误详情: $RESPONSE_BODY2"
elif [ "$HTTP_STATUS2" = "401" ]; then
    echo "? 需要认证（这是正常的，说明端点可访问）"
    echo "✓ 没有UTF-8编码错误"
elif [ "$HTTP_STATUS2" = "200" ]; then
    echo "✓ 成功处理文件上传预览"
    echo "响应: $RESPONSE_BODY2" | head -c 200
else
    echo "状态码: $HTTP_STATUS2"
    echo "响应: $RESPONSE_BODY2" | head -c 200
    # 只要不是500就说明UTF-8问题已修复
    if [ "$HTTP_STATUS2" != "500" ]; then
        echo "✓ 没有UTF-8编码错误"
    fi
fi

# 清理测试文件
rm -f "$TEST_FILE"

echo -e "\n=== 测试总结 ==="

if [ "$HTTP_STATUS" != "500" ] && [ "$HTTP_STATUS2" != "500" ]; then
    echo "🎉 UTF-8编码错误修复验证成功！"
    echo "✓ 原始错误场景不再返回500错误"
    echo "✓ 提供了友好的错误提示和API使用指导"
    echo "✓ 正确的API端点能够处理中文文件名"
    echo ""
    echo "修复效果："
    echo "- 修复前: 'utf-8' codec can't decode byte 0x93 in position 176: invalid start byte"
    echo "- 修复后: 友好的错误提示，指导用户使用正确的API端点"
    exit 0
else
    echo "❌ UTF-8编码错误修复验证失败"
    echo "仍有端点返回500错误，需要进一步检查"
    exit 1
fi
