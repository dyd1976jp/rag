#!/bin/bash
# 符号链接修复脚本
# 功能：自动修复损坏的符号链接
# 作者：RAG-Chat维护团队
# 创建时间：2025-06-21

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

function log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

function fix_symlinks() {
    log "🔧 开始修复符号链接..."

    cd "$PROJECT_ROOT"

    # 根目录符号链接
    log "创建根目录符号链接..."
    ln -sf scripts/setup/initialize.sh initialize.sh
    ln -sf scripts/deployment/restart_backend.sh restart_backend.sh
    ln -sf scripts/deployment/restart_backend_with_init.sh restart_backend_with_init.sh

    # backend目录符号链接
    log "创建backend目录符号链接..."
    mkdir -p backend/scripts
    ln -sf ../../scripts/backend/create_admin.py backend/scripts/create_admin.py

    # database目录符号链接
    log "创建database目录符号链接..."
    mkdir -p backend/database/scripts
    ln -sf ../../../scripts/database/init_db.py backend/database/scripts/init_db.py
    ln -sf ../../../scripts/database/init_db.sh backend/database/scripts/init_db.sh

    log "✅ 符号链接修复完成！"
}

function verify_fix() {
    log "🔍 验证修复结果..."
    if "$SCRIPT_DIR/validate_symlinks.sh"; then
        log "🎉 所有符号链接修复成功！"
        return 0
    else
        log "❌ 修复后仍有问题，请手动检查"
        return 1
    fi
}

function main() {
    fix_symlinks
    verify_fix
}

main "$@"
