# 开发工具脚本

此目录包含RAG-Chat项目的开发工具、代码质量检查和文档生成脚本。

## 📋 脚本列表

### 代码质量工具

#### code_quality_check.py
- **用途**: 代码质量检查工具
- **使用方法**: `python scripts/tools/code_quality_check.py <directory>`
- **功能**:
  - 检查文件长度（默认最大500行）
  - 检查函数长度（默认最大50行）
  - 检查文档字符串
  - 检查类型提示
  - 检查导入语句

**参数选项**:
```bash
python scripts/tools/code_quality_check.py backend/ \
  --max-function-lines 50 \
  --max-file-lines 500
```

### 文档生成工具

#### generate_api_docs.py
- **用途**: 生成API文档
- **使用方法**: `python scripts/tools/generate_api_docs.py`
- **功能**:
  - 扫描API端点
  - 生成文档结构
  - 输出格式化文档

#### api_summary.py
- **用途**: API端点汇总工具
- **使用方法**: `python scripts/tools/api_summary.py`
- **功能**:
  - 分析所有API端点
  - 统计端点信息
  - 生成汇总报告
  - 权限分析

### 项目管理工具

#### sync_github_templates.sh
- **用途**: 同步GitHub模板文件
- **使用方法**: `./scripts/tools/sync_github_templates.sh`
- **功能**:
  - 同步Issue模板
  - 同步PR模板
  - 更新.github目录

## 🚀 使用指南

### 代码质量检查
```bash
# 检查整个后端代码
python scripts/tools/code_quality_check.py backend/

# 检查特定模块
python scripts/tools/code_quality_check.py backend/app/api/

# 自定义参数
python scripts/tools/code_quality_check.py backend/ \
  --max-function-lines 30 \
  --max-file-lines 300
```

### API文档生成
```bash
# 生成API文档
python scripts/tools/generate_api_docs.py

# 生成API汇总
python scripts/tools/api_summary.py
```

### GitHub模板同步
```bash
# 同步模板文件
./scripts/tools/sync_github_templates.sh
```

## 📊 输出示例

### 代码质量检查报告
```
=== 代码质量检查报告 ===
检查目录: backend/
总文件数: 45
检查文件数: 45
发现问题数: 3

=== 问题详情 ===
1. 文件过长: backend/app/services/large_service.py (520行)
2. 函数过长: backend/app/utils/helper.py:process_data (65行)
3. 缺少文档字符串: backend/app/models/user.py:User.validate
```

### API汇总报告
```
📊 API端点统计
总端点数: 25
需要认证: 20
需要管理员权限: 5

📁 auth (/api/v1/auth)
  🔓 POST   /register                        - 用户注册
  🔓 POST   /login                           - 用户登录
  🔒 POST   /logout                          - 用户登出

📁 rag (/api/v1/rag)
  🔒 GET    /status                          - RAG服务状态
  🔒 POST   /documents/upload                - 文档上传
```

## 🔧 配置选项

### 代码质量检查配置
- `--max-function-lines`: 函数最大行数（默认50）
- `--max-file-lines`: 文件最大行数（默认500）

### 文档生成配置
工具会自动扫描以下目录：
- `backend/app/api/` - API端点
- `backend/app/schemas/` - 数据模式
- `backend/app/models/` - 数据模型

### GitHub模板配置
同步路径：
- 源目录: `docs/github_templates/`
- 目标目录: `.github/`

## ⚠️ 注意事项

1. **Python环境**: 确保在正确的Python环境中运行
2. **文件权限**: 确保脚本有读取源代码的权限
3. **依赖包**: 某些工具需要特定的Python包
4. **路径设置**: 确保在项目根目录运行脚本

## 🔧 故障排除

### 常见问题

1. **模块导入错误**
   ```bash
   # 设置Python路径
   export PYTHONPATH=/path/to/RAG-chat/backend
   ```

2. **权限不足**
   ```bash
   chmod +x scripts/tools/*.sh
   ```

3. **依赖缺失**
   ```bash
   pip install ast argparse pathlib
   ```

4. **文件不存在**
   ```bash
   # 检查文件路径
   ls -la docs/github_templates/
   ```

## 📈 最佳实践

### 代码质量检查
- 定期运行质量检查
- 设置合理的行数限制
- 关注文档字符串覆盖率
- 保持导入语句整洁

### 文档维护
- 定期更新API文档
- 保持模板文件同步
- 及时更新变更说明

### 自动化集成
可以将这些工具集成到CI/CD流程中：
```bash
# 在CI中运行质量检查
python scripts/tools/code_quality_check.py backend/
if [ $? -ne 0 ]; then
  echo "代码质量检查失败"
  exit 1
fi
```

## 📞 支持

如遇到工具使用问题，请检查：
1. Python环境是否正确
2. 依赖包是否安装
3. 文件路径是否正确
4. 权限设置是否合适
