#!/bin/bash
# LLM API 测试脚本 - 开发环境固定Token版本

# 固定的测试Token - 如果需要
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzUwMjMyNzE5fQ.lA-qsA9QhfbsYzg8YeKnA1wt8R6q-PcpDEf_r4sJLxY"

# LM Studio URL
LM_STUDIO_URL="http://0.0.0.0:1234"

# 使用方法
echo "=== LLM API 测试 - 开发模式 ==="
echo "请确认后端服务器正在运行，开发模式已启用。"
echo ""

echo "1. 获取所有LLM模型:"
echo "curl -v http://localhost:8000/api/v1/llm/ -H \"Authorization: Bearer \$TOKEN\""
echo ""

echo "2. 发现LM Studio模型:"
echo "curl -v \"http://localhost:8000/api/v1/llm/discover?provider=lmstudio&url=${LM_STUDIO_URL}\" -H \"Authorization: Bearer \$TOKEN\""
echo ""

echo "3. 注册模型示例:"
echo 'curl -v -X POST "http://localhost:8000/api/v1/llm/register-from-discovery" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '"'"'{"llm_model_id": "qwen3-14b-mlx", "provider": "Local", "name": "Qwen3-14B-MLX", "api_url": "http://0.0.0.0:1234/v1/chat/completions", "description": "通过API测试脚本自动注册的模型", "context_window": 8192, "set_as_default": true}'"'"''
echo ""

# 运行示例
echo "是否要运行这些命令? (y/n)"
read choice

if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
    echo "=== 执行测试 ==="
    
    echo -e "\n>>> 1. 获取所有LLM模型:"
    curl -s http://localhost:8000/api/v1/llm/ -H "Authorization: Bearer $TOKEN" | jq .
    
    echo -e "\n>>> 2. 发现LM Studio模型:"
    curl -s "http://localhost:8000/api/v1/llm/discover?provider=lmstudio&url=${LM_STUDIO_URL}" -H "Authorization: Bearer $TOKEN" | jq .
    
    echo -e "\n=== 测试完成 ==="
fi 