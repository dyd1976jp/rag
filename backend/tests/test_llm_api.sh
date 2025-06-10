#!/bin/bash

# 测试LLM API的脚本
# 使用方法: ./test_llm_api.sh

# 配置
API_URL="http://localhost:8000"
AUTH_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxNzQ4MjYyNzUwfQ.x9vEcvY7OsoTVMmQTL8I4cqV2Cm8RjLqi61jI4lYZEg"
LM_STUDIO_URL="http://0.0.0.0:1234"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 辅助函数
log_info() {
  echo -e "${BLUE}[信息]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[成功]${NC} $1"
}

log_error() {
  echo -e "${RED}[错误]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[警告]${NC} $1"
}

log_title() {
  echo -e "\n${YELLOW}=== $1 ===${NC}"
}

# 创建临时文件存储HTTP响应
RESPONSE_FILE=$(mktemp)
DISCOVERED_MODELS_FILE=$(mktemp)
REGISTERED_MODEL_ID=""

# 1. 获取所有LLM模型
test_get_all_llms() {
  log_title "测试获取所有LLM模型"
  
  curl -s -X GET "${API_URL}/api/v1/llm/" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" \
    -o ${RESPONSE_FILE}
  
  if [ $? -eq 0 ]; then
    MODELS_COUNT=$(cat ${RESPONSE_FILE} | jq '. | length')
    if [[ "${MODELS_COUNT}" == "null" ]]; then
      MODELS_COUNT=0
    fi
    log_success "获取到 ${MODELS_COUNT} 个LLM模型"
    cat ${RESPONSE_FILE} | jq '.'
  else
    log_error "API请求失败"
    cat ${RESPONSE_FILE}
    return 1
  fi
}

# 2. 发现LM Studio中的模型
test_discover_models() {
  log_title "测试发现LM Studio中的模型"
  
  # 尝试不同的API路径
  curl -s -X GET "${API_URL}/api/llm/discover?provider=lmstudio&url=${LM_STUDIO_URL}" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" \
    -o ${DISCOVERED_MODELS_FILE}
  
  if [ $? -eq 0 ]; then
    # 检查是否有错误信息
    if cat ${DISCOVERED_MODELS_FILE} | jq -e '.detail' > /dev/null; then
      ERROR_MSG=$(cat ${DISCOVERED_MODELS_FILE} | jq -r '.detail')
      log_error "API返回错误: ${ERROR_MSG}"
      return 1
    fi
    
    MODELS_COUNT=$(cat ${DISCOVERED_MODELS_FILE} | jq '. | length')
    log_success "发现了 ${MODELS_COUNT} 个模型"
    cat ${DISCOVERED_MODELS_FILE} | jq '.'
    
    # 保存第一个模型ID用于后续测试
    FIRST_MODEL_ID=$(cat ${DISCOVERED_MODELS_FILE} | jq -r '.[0].id')
    log_info "第一个模型ID: ${FIRST_MODEL_ID}"
  else
    log_error "API请求失败"
    cat ${DISCOVERED_MODELS_FILE}
    return 1
  fi
}

# 3. 注册一个发现的模型
test_register_model() {
  log_title "测试注册模型"
  
  if [[ -z "${FIRST_MODEL_ID}" ]]; then
    log_error "没有可用的模型ID，请先运行发现模型的测试"
    return 1
  fi
  
  FIRST_MODEL_NAME=$(cat ${DISCOVERED_MODELS_FILE} | jq -r '.[0].name')
  MODEL_API_URL=$(cat ${DISCOVERED_MODELS_FILE} | jq -r '.[0].api_url')
  
  log_info "准备注册模型: ${FIRST_MODEL_ID}"
  
  curl -s -X POST "${API_URL}/api/v1/llm/register-from-discovery" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" \
    -d "{
      \"llm_model_id\": \"${FIRST_MODEL_ID}\",
      \"provider\": \"Local\",
      \"name\": \"测试自动注册 - ${FIRST_MODEL_NAME}\",
      \"api_url\": \"${MODEL_API_URL}\",
      \"description\": \"通过测试脚本自动注册的模型\",
      \"context_window\": 8192,
      \"set_as_default\": true
    }" \
    -o ${RESPONSE_FILE}
  
  if [ $? -eq 0 ]; then
    # 检查是否有错误信息
    if cat ${RESPONSE_FILE} | jq -e '.detail' > /dev/null; then
      ERROR_MSG=$(cat ${RESPONSE_FILE} | jq -r '.detail')
      log_error "API返回错误: ${ERROR_MSG}"
      return 1
    fi
    
    REGISTERED_MODEL_ID=$(cat ${RESPONSE_FILE} | jq -r '.id')
    log_success "模型注册成功，ID: ${REGISTERED_MODEL_ID}"
    cat ${RESPONSE_FILE} | jq '.'
  else
    log_error "API请求失败"
    cat ${RESPONSE_FILE}
    return 1
  fi
}

# 4. 测试注册的模型
test_model() {
  log_title "测试模型运行"
  
  if [[ -z "${REGISTERED_MODEL_ID}" ]]; then
    log_error "没有注册的模型ID，请先运行注册模型的测试"
    return 1
  fi
  
  log_info "测试模型: ${REGISTERED_MODEL_ID}"
  
  curl -s -X POST "${API_URL}/api/v1/llm/test" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" \
    -d "{
      \"llm_id\": \"${REGISTERED_MODEL_ID}\",
      \"prompt\": \"你好，请用中文简单介绍一下你自己。\"
    }" \
    -o ${RESPONSE_FILE}
  
  if [ $? -eq 0 ]; then
    # 检查是否有错误信息
    if cat ${RESPONSE_FILE} | jq -e '.detail' > /dev/null; then
      ERROR_MSG=$(cat ${RESPONSE_FILE} | jq -r '.detail')
      log_error "API返回错误: ${ERROR_MSG}"
      return 1
    fi
    
    log_success "模型测试成功"
    cat ${RESPONSE_FILE} | jq '.'
  else
    log_error "API请求失败"
    cat ${RESPONSE_FILE}
    return 1
  fi
}

# 执行测试
run_all_tests() {
  test_get_all_llms
  if [ $? -ne 0 ]; then
    log_error "获取模型列表失败，终止测试"
    return 1
  fi
  
  test_discover_models
  if [ $? -ne 0 ]; then
    log_error "发现模型失败，终止测试"
    return 1
  fi
  
  test_register_model
  if [ $? -ne 0 ]; then
    log_error "注册模型失败，终止测试"
    return 1
  fi
  
  test_model
  if [ $? -ne 0 ]; then
    log_error "测试模型失败"
    return 1
  fi
  
  log_title "所有测试已完成"
}

# 清理临时文件
cleanup() {
  rm -f ${RESPONSE_FILE} ${DISCOVERED_MODELS_FILE}
}

# 处理退出信号
trap cleanup EXIT

# 主函数
main() {
  log_title "LLM API 测试脚本"
  run_all_tests
}

main "$@" 