#!/bin/bash
# 符号链接验证脚本
# 功能：检查所有符号链接的有效性
# 作者：RAG-Chat维护团队
# 创建时间：2025-06-21

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

function log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

function check_symlinks() {
    log "🔗 开始验证符号链接..."

    # 定义需要检查的符号链接 (link:target格式)
    local symlinks=(
        "initialize.sh:scripts/setup/initialize.sh"
        "restart_backend.sh:scripts/deployment/restart_backend.sh"
        "restart_backend_with_init.sh:scripts/deployment/restart_backend_with_init.sh"
        "backend/scripts/create_admin.py:../../scripts/backend/create_admin.py"
        "backend/database/scripts/init_db.py:../../../scripts/database/init_db.py"
        "backend/database/scripts/init_db.sh:../../../scripts/database/init_db.sh"
    )

    local failed_links=()

    for symlink_pair in "${symlinks[@]}"; do
        local link="${symlink_pair%%:*}"
        local target="${symlink_pair##*:}"
        local full_link_path="$PROJECT_ROOT/$link"

        if [[ -L "$full_link_path" ]]; then
            if [[ -e "$full_link_path" ]]; then
                log "✅ $link -> $target (有效)"
            else
                log "❌ $link -> $target (目标不存在)"
                failed_links+=("$link")
            fi
        else
            log "⚠️  $link (不是符号链接)"
            failed_links+=("$link")
        fi
    done

    if [[ ${#failed_links[@]} -eq 0 ]]; then
        log "🎉 所有符号链接验证通过！"
        return 0
    else
        log "💥 发现 ${#failed_links[@]} 个问题链接："
        printf '%s\n' "${failed_links[@]}"
        return 1
    fi
}

function main() {
    cd "$PROJECT_ROOT"
    check_symlinks
}

main "$@"
