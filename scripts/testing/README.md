# 集成测试脚本

此目录包含RAG-Chat项目的集成测试、端到端测试和验证脚本。

## 📋 脚本列表

### API测试脚本

#### test_api_endpoints.sh
- **用途**: 测试各种API端点的可用性
- **使用方法**: `./scripts/testing/test_api_endpoints.sh`
- **测试内容**:
  - 健康检查端点
  - 认证端点
  - RAG服务状态
  - 管理端点

#### test_endpoint_consistency.sh
- **用途**: 测试端点行为一致性
- **使用方法**: `./scripts/testing/test_endpoint_consistency.sh`
- **测试内容**:
  - 预览分割端点
  - 文档上传端点
  - 参数一致性验证

### 文档上传测试

#### test_document_upload.sh
- **用途**: 测试文档上传功能
- **使用方法**: `./scripts/testing/test_document_upload.sh`
- **测试内容**:
  - 预览模式上传
  - 实际上传模式
  - 分割参数测试

#### test_document_upload_detailed.sh
- **用途**: 详细的文档上传测试
- **使用方法**: `./scripts/testing/test_document_upload_detailed.sh`
- **测试内容**:
  - 详细的上传流程
  - 错误处理验证
  - 响应格式检查

### 修复验证脚本

#### test_utf8_fix.sh
- **用途**: 验证UTF-8编码修复
- **使用方法**: `./scripts/testing/test_utf8_fix.sh`
- **测试内容**:
  - UTF-8编码处理
  - 中文字符支持
  - 错误处理改进

#### final_test.sh
- **用途**: 最终修复验证测试
- **使用方法**: `./scripts/testing/final_test.sh`
- **测试内容**:
  - 综合功能验证
  - 修复效果确认
  - 完整性检查

### 基础测试

#### curl_test.sh
- **用途**: 基础curl测试
- **使用方法**: `./scripts/testing/curl_test.sh`
- **测试内容**:
  - 基本API连通性
  - 简单请求响应

## 🚀 使用指南

### 运行所有测试
```bash
# 进入测试目录
cd scripts/testing

# 运行API端点测试
./test_api_endpoints.sh

# 运行文档上传测试
./test_document_upload.sh

# 运行一致性测试
./test_endpoint_consistency.sh
```

### 单独运行测试
```bash
# 测试特定功能
./scripts/testing/test_utf8_fix.sh
./scripts/testing/final_test.sh
```

## 🔧 测试配置

### 环境要求
- 后端服务运行在 http://localhost:8000
- 有效的JWT令牌（某些测试需要）
- 测试文件存在于指定路径

### 测试参数
大多数测试脚本包含以下可配置参数：
- API基础URL
- 认证令牌
- 测试文件路径
- 分割参数

### 示例配置
```bash
BASE_URL="http://localhost:8000"
TOKEN="your_jwt_token_here"
FILE_PATH="/path/to/test/file.pdf"
```

## 📊 测试结果

### 状态码说明
- ✅ **200/201**: 成功
- ⚠️ **401**: 需要认证（预期行为）
- ⚠️ **404**: 端点不存在
- ❌ **500**: 服务器错误

### 输出格式
测试脚本提供彩色输出：
- 🟢 绿色: 测试通过
- 🟡 黄色: 警告或需要注意
- 🔴 红色: 测试失败

## ⚠️ 注意事项

1. **服务依赖**: 确保后端服务正在运行
2. **认证令牌**: 某些测试需要有效的JWT令牌
3. **测试文件**: 确保测试文件存在且可访问
4. **网络连接**: 测试需要网络连接到API服务

## 🔧 故障排除

### 常见问题

1. **连接被拒绝**
   ```bash
   # 检查服务状态
   curl http://localhost:8000/
   # 启动后端服务
   ./scripts/deployment/restart_backend.sh
   ```

2. **认证失败**
   ```bash
   # 获取新的JWT令牌
   curl -X POST "http://localhost:8000/api/v1/auth/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=your_email&password=your_password"
   ```

3. **文件不存在**
   ```bash
   # 检查文件路径
   ls -la /path/to/test/file.pdf
   # 使用正确的文件路径
   ```

4. **权限问题**
   ```bash
   chmod +x scripts/testing/*.sh
   ```

## 📞 支持

测试失败时，请检查：
1. 后端服务是否正常运行
2. 数据库连接是否正常
3. 测试文件是否存在
4. 网络连接是否稳定
