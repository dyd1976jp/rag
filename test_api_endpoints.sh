#!/bin/bash

# RAG Chat API 端点测试脚本
# 基于 API_DOCUMENTATION.md 中的示例

BASE_URL="http://localhost:8000"
CONTENT_TYPE="Content-Type: application/json"

echo "=== RAG Chat API 端点测试 ==="
echo "基础URL: $BASE_URL"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试函数
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local headers=$4
    local data=$5
    
    echo -e "${BLUE}测试: $description${NC}"
    echo "端点: $method $endpoint"
    
    if [ "$method" = "GET" ]; then
        if [ -n "$headers" ]; then
            response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL$endpoint" -H "$headers")
        else
            response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL$endpoint")
        fi
    elif [ "$method" = "POST" ]; then
        if [ -n "$data" ]; then
            response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint" -H "$CONTENT_TYPE" -H "$headers" -d "$data")
        else
            response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint" -H "$headers")
        fi
    fi
    
    # 分离响应体和状态码
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 201 ]; then
        echo -e "${GREEN}✓ 成功 (HTTP $http_code)${NC}"
    elif [ "$http_code" -eq 401 ]; then
        echo -e "${YELLOW}⚠ 需要认证 (HTTP $http_code)${NC}"
    elif [ "$http_code" -eq 404 ]; then
        echo -e "${YELLOW}⚠ 端点不存在 (HTTP $http_code)${NC}"
    else
        echo -e "${RED}✗ 失败 (HTTP $http_code)${NC}"
    fi
    
    # 显示响应（截断长响应）
    if [ ${#response_body} -gt 200 ]; then
        echo "响应: $(echo "$response_body" | head -c 200)..."
    else
        echo "响应: $response_body"
    fi
    echo ""
}

echo "1. 测试健康检查端点"
test_endpoint "GET" "/" "API根端点健康检查"

echo "2. 测试认证端点"
test_endpoint "GET" "/api/v1/llm/default" "获取默认LLM模型（无需认证）"

echo "3. 测试需要认证的端点"
test_endpoint "GET" "/api/v1/llm/" "获取所有LLM模型（需要认证）" "Authorization: Bearer invalid_token"

echo "4. 测试RAG状态端点"
test_endpoint "GET" "/api/v1/rag/status" "检查RAG服务状态（需要认证）" "Authorization: Bearer invalid_token"

echo "5. 测试管理端点"
test_endpoint "GET" "/admin/api/system/status" "获取系统状态（需要管理员认证）" "Authorization: Bearer invalid_admin_token"

echo "6. 测试文档集合端点"
test_endpoint "GET" "/api/v1/rag/collections/" "获取文档集列表（需要认证）" "Authorization: Bearer invalid_token"

echo "=== 测试完成 ==="
echo ""
echo "注意事项："
echo "- 大部分端点需要有效的JWT令牌"
echo "- 要获取令牌，请先注册用户并登录"
echo "- 管理端点需要管理员权限"
echo "- 详细的API使用方法请参考 API_DOCUMENTATION.md"
echo ""
echo "获取JWT令牌的步骤："
echo "1. 注册用户: curl -X POST \"$BASE_URL/api/v1/auth/register\" -H \"$CONTENT_TYPE\" -d '{\"email\":\"test@example.com\",\"username\":\"testuser\",\"password\":\"testpass\"}'"
echo "2. 登录获取令牌: curl -X POST \"$BASE_URL/api/v1/auth/login\" -H \"Content-Type: application/x-www-form-urlencoded\" -d \"username=test@example.com&password=testpass\""
echo "3. 使用令牌: curl -X GET \"$BASE_URL/api/v1/llm/\" -H \"Authorization: Bearer <your_jwt_token>\""
