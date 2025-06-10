# RAG-Chat 测试指南

本文档提供了RAG-Chat应用的测试相关信息和指导。

## 测试目录结构

所有测试文件已整理到`tests`目录中，按功能模块分类：

```
tests/
├── api/                # API测试
├── db/                 # 数据库测试
├── discover/           # 模型发现功能测试
├── mocks/              # 测试模拟数据
├── services/           # 服务层测试
└── ...                 # 其他测试文件和配置
```

## 快速入门

### 模型发现功能测试

模型发现功能的测试脚本已经整理到`tests/discover/`目录中：

```bash
# 测试模型发现API客户端
cd /Users/tei/go/RAG-chat/backend
python tests/discover/test_discover_client.py

# 测试服务层函数
python tests/discover/test_service.py

# 运行测试API服务器
python tests/discover/test_api_server.py
```

详细说明请参考：
- [tests/README.md](./tests/README.md) - 测试目录总体说明
- [tests/discover/README.md](./tests/discover/README.md) - 模型发现功能测试说明

## VSCode调试

使用VSCode的调试功能，可以方便地进行代码调试：

1. 打开要调试的测试文件
2. 在关键位置设置断点
3. 按F5或点击"运行和调试"按钮
4. 选择"Debug Uvicorn (从backend目录)"配置

## 常见问题

### 导入错误

如果遇到导入错误，请确保：
- 从`backend`目录运行测试脚本
- Python环境中已安装所有依赖

```bash
cd /Users/tei/go/RAG-chat/backend
pip install -r requirements.txt
pip install -r tests/requirements.txt
```

### 认证令牌过期

测试脚本中使用的认证令牌可能会过期，请根据需要更新。可以使用`tests/create_test_token.py`脚本生成新的令牌。

## 进一步阅读

- [README_DEBUG.md](./README_DEBUG.md) - 调试指南
- [README_RESULTS.md](./README_RESULTS.md) - 模型发现功能实现总结 