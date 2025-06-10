#!/bin/bash
# LLM API 测试脚本

# 颜色设置
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===== LLM API 测试脚本 =====${NC}"

# 基本设置
API_URL="http://localhost:8000"
LM_STUDIO_URL="http://0.0.0.0:1234"

# 测试1: 获取LM Studio模型列表
echo -e "\n${BLUE}1. 获取LM Studio模型列表${NC}"
curl -s ${LM_STUDIO_URL}/v1/models/ | jq . || echo "无法连接到LM Studio"

# 测试2: 获取后端API所有LLM模型
echo -e "\n${BLUE}2. 获取后端API所有LLM模型${NC}"
curl -s ${API_URL}/api/v1/llm/ | jq . || echo "无法连接到后端API"

# 测试3: 发现LM Studio模型
echo -e "\n${BLUE}3. 发现LM Studio模型${NC}"
curl -s "${API_URL}/api/v1/llm/discover?provider=lmstudio&url=${LM_STUDIO_URL}" | jq . || echo "无法连接到发现API"

# 在开发模式下无需认证
echo -e "\n${GREEN}测试完成${NC}" 