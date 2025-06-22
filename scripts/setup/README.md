# 环境设置脚本

此目录包含RAG-Chat项目的环境初始化和设置脚本。

## 📋 脚本列表

### initialize.sh
- **用途**: 初始化RAG系统环境
- **使用方法**: `./scripts/setup/initialize.sh`
- **功能**:
  - 激活Conda环境
  - 创建必要的目录结构
  - 设置目录权限
  - 安装后端依赖包
  - 安装前端依赖包
  - 安装管理后台依赖包

## 🚀 使用指南

### 首次部署
```bash
# 运行环境初始化脚本
./scripts/setup/initialize.sh
```

### 脚本功能详解

#### 1. 环境准备
- 激活Conda环境 `rag-chat`
- 检查必要的系统依赖

#### 2. 目录结构创建
```
data/
├── raw/                # 原始数据
├── processed/          # 处理后的数据
├── uploads/            # 上传文件
├── vectors/            # 向量数据
├── embeddings/         # 嵌入数据
├── cache/splitter/     # 分割缓存
├── exports/            # 导出数据
└── db/                 # 数据库文件
    ├── mongodb/
    ├── milvus/
    └── chroma/

logs/
├── app/                # 应用日志
│   ├── api/
│   ├── worker/
│   └── debug/
├── tests/              # 测试日志
└── services/           # 服务日志
    ├── mongodb/
    └── milvus/
```

#### 3. 依赖安装
- **后端依赖**: 从 `requirements.txt` 安装
- **额外依赖**: PyPDF2, langchain, sentence-transformers 等
- **前端依赖**: 主应用和管理后台的 npm 包

## ⚠️ 注意事项

1. **Conda环境**: 确保已安装并配置Conda，环境名为 `rag-chat`
2. **权限要求**: 脚本需要创建目录和设置权限的权限
3. **网络连接**: 需要网络连接来下载依赖包
4. **磁盘空间**: 确保有足够的磁盘空间存储依赖和数据

## 🔧 故障排除

### 常见问题

1. **Conda环境不存在**
   ```bash
   conda create -n rag-chat python=3.10
   conda activate rag-chat
   ```

2. **权限不足**
   ```bash
   chmod +x scripts/setup/initialize.sh
   ```

3. **依赖安装失败**
   - 检查网络连接
   - 更新pip: `pip install --upgrade pip`
   - 清理缓存: `pip cache purge`

## 📞 支持

如遇到问题，请检查：
1. 系统环境是否满足要求
2. 网络连接是否正常
3. 磁盘空间是否充足
4. 相关服务是否正常运行
