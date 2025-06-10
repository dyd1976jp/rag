#!/bin/bash
# 测试新的discover-models端点

# 配置
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzUwMjMyNzE5fQ.lA-qsA9QhfbsYzg8YeKnA1wt8R6q-PcpDEf_r4sJLxY"
BASE_URL="http://localhost:8000/api/v1"
LM_STUDIO_URL="http://0.0.0.0:1234"

echo "=== 测试新的discover-models端点 ==="
echo "请确保后端服务器已启动"

# 测试新端点
echo -e "\n1. 测试新的discover-models端点:"
echo "curl -v \"${BASE_URL}/llm/discover-models?provider=lmstudio&url=${LM_STUDIO_URL}\" -H \"Authorization: Bearer ${TOKEN}\""

echo -e "\n执行中..."
curl -v "${BASE_URL}/llm/discover-models?provider=lmstudio&url=${LM_STUDIO_URL}" \
    -H "Authorization: Bearer ${TOKEN}"

# 测试注册端点
echo -e "\n\n2. 使用注册端点注册模型:"
echo "curl -v -X POST \"${BASE_URL}/llm/register-from-discovery\" -H \"Authorization: Bearer ${TOKEN}\" -H \"Content-Type: application/json\" -d '{\"llm_model_id\": \"text-embedding-nomic-embed-text-v1.5\", \"provider\": \"Local\", \"name\": \"测试 - Embedding Model\", \"api_url\": \"${LM_STUDIO_URL}/v1/chat/completions\", \"description\": \"通过API测试脚本自动注册的Embedding模型\", \"context_window\": 8192, \"set_as_default\": false}'"

echo -e "\n是否要测试注册新模型? (y/n)"
read choice

if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
    curl -v -X POST "${BASE_URL}/llm/register-from-discovery" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"llm_model_id\": \"text-embedding-nomic-embed-text-v1.5\", \"provider\": \"Local\", \"name\": \"测试 - Embedding Model\", \"api_url\": \"${LM_STUDIO_URL}/v1/chat/completions\", \"description\": \"通过API测试脚本自动注册的Embedding模型\", \"context_window\": 8192, \"set_as_default\": false}"
fi

echo -e "\n=== 测试完成 ===" 