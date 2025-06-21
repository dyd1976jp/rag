# RAG系统启动指南

> 📍 **文档迁移通知**: 此文档的内容已整合到主 [README.md](../README.md) 文件中。
> 请查看主README文件获取最新的启动说明。

本文档提供了同时启动RAG系统后端和前端管理界面的操作说明。

## 系统组件

1. **后端服务**：基于FastAPI的API服务，提供RAG核心功能和管理API
2. **前端管理界面**：基于Vue 3的管理后台，用于监控和管理系统

## 快速启动

我们提供了简便的脚本来启动和停止整个系统。

### 启动系统

```bash
# 切换到项目根目录
cd /Users/tei/go/RAG-chat

# 执行启动脚本
./start.sh
```

启动后，系统将自动在后台运行：
- 后端API服务运行在：http://localhost:8000
- 前端管理界面运行在：http://localhost:5173

### 停止系统

```bash
# 切换到项目根目录
cd /Users/tei/go/RAG-chat

# 执行停止脚本
./stop.sh
```

## 管理员登录

启动系统后，访问前端管理界面：http://localhost:5173

使用以下默认凭据登录：
- 用户名：admin
- 密码：adminpassword

**注意**：在生产环境中，请修改默认密码以提高安全性。

## 手动启动（如需单独控制）

如果需要单独控制各个组件，可以按以下步骤操作：

### 手动启动后端

```bash
cd /Users/tei/go/RAG-chat
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 手动启动前端

```bash
cd /Users/tei/go/RAG-chat/frontend/admin
npm run dev
```

## 常见问题

1. **端口冲突**：如果8000或5173端口已被占用，请修改`start.sh`中的端口设置
2. **依赖问题**：确保已安装所有必要的依赖：`pip install -r backend/requirements.txt` 和 `cd frontend/admin && npm install`
3. **权限问题**：确保脚本有执行权限：`chmod +x start.sh stop.sh`
4. **模块导入错误**：如果出现类似 `ModuleNotFoundError: No module named 'app'` 的错误，请检查 Python 导入路径。当前脚本已通过设置 PYTHONPATH 环境变量解决此问题。
5. **进程无法正常终止**：如果使用 `stop.sh` 后仍有进程未终止，可以手动终止：
   ```bash
   # 查找并终止uvicorn进程
   ps aux | grep uvicorn
   kill -9 <进程ID>
   
   # 查找并终止vite进程
   ps aux | grep vite
   kill -9 <进程ID>
   ```

## 最近更新

- 修复了Python模块导入路径问题
- 改进了进程停止脚本，使用pkill命令更可靠地终止进程
- 使用相对导入替换了绝对导入，提高了代码的可移植性 