# RAG系统管理后台

这是RAG（检索增强生成）系统的管理后台，用于监控和管理系统的各项组件。

## 功能特性

- MongoDB数据库管理
- 向量存储（Milvus）管理
- 系统资源监控
- 用户认证和权限控制

## 技术栈

- Vue 3
- Element Plus
- Vite
- Axios
- ECharts
- Pinia

## 开发环境设置

### 前提条件

- Node.js 14.x 或更高版本
- npm 或 yarn

### 安装依赖

```bash
# 使用npm
npm install

# 使用yarn
yarn
```

### 开发服务器

```bash
# 使用npm
npm run dev

# 使用yarn
yarn dev
```

### 构建生产版本

```bash
# 使用npm
npm run build

# 使用yarn
yarn build
```

## 项目结构

```
src/
├── api/              # API请求
├── assets/           # 静态资源
│   └── styles/       # 样式文件
├── components/       # 可复用组件
├── router/           # 路由配置
├── store/            # Pinia状态管理
├── utils/            # 工具函数
└── views/            # 页面组件
    ├── dashboard/    # 仪表盘
    ├── layout/       # 布局组件
    ├── login/        # 登录页面
    ├── mongodb/      # MongoDB管理
    ├── vectorstore/  # 向量存储管理
    └── system/       # 系统监控
```

## 管理员账户

默认管理员账户：
- 用户名：admin
- 密码：adminpassword

**注意**：在生产环境中，请修改默认密码以提高安全性。 