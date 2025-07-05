# 多阶段构建的Dockerfile，支持开发和生产环境

# ============================================================================
# 基础阶段：安装系统依赖
# ============================================================================
FROM python:3.10-slim as base

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 创建应用用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 设置工作目录
WORKDIR /app

# ============================================================================
# 依赖阶段：安装Python依赖
# ============================================================================
FROM base as dependencies

# 复制依赖文件
COPY backend/requirements.txt backend/requirements-dev.txt ./

# 安装Python依赖
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ============================================================================
# 开发阶段：包含开发工具
# ============================================================================
FROM dependencies as development

# 安装开发依赖
RUN pip install -r requirements-dev.txt

# 复制应用代码
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY logs/ ./logs/

# 创建必要的目录
RUN mkdir -p /app/data/uploads /app/data/temp /app/logs/app && \
    chown -R appuser:appuser /app

# 切换到应用用户
USER appuser

# 暴露端口
EXPOSE 8000

# 开发环境启动命令
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================================================
# 生产阶段：优化的生产镜像
# ============================================================================
FROM dependencies as production

# 复制应用代码
COPY backend/ ./backend/
COPY scripts/ ./scripts/

# 创建必要的目录和设置权限
RUN mkdir -p /app/data/uploads /app/data/temp /app/logs/app && \
    chown -R appuser:appuser /app

# 切换到应用用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 生产环境启动命令
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ============================================================================
# 测试阶段：用于CI/CD测试
# ============================================================================
FROM development as testing

# 复制测试文件
COPY backend/tests/ ./backend/tests/
COPY .github/ ./.github/

# 运行测试
RUN python -m pytest backend/tests/ -v --tb=short

# ============================================================================
# 最终阶段选择
# ============================================================================
FROM production as final
