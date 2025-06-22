#!/bin/bash
# 每周维护检查脚本
# 功能：执行常规维护检查任务
# 作者：RAG-Chat维护团队
# 创建时间：2025-06-21

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
readonly LOG_FILE="$PROJECT_ROOT/logs/maintenance/weekly_$(date +%Y%m%d).log"

# 创建日志目录
mkdir -p "$(dirname "$LOG_FILE")"

function log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

function check_symlinks() {
    log "🔗 检查符号链接..."
    if "$SCRIPT_DIR/validate_symlinks.sh" >> "$LOG_FILE" 2>&1; then
        log "✅ 符号链接检查通过"
        return 0
    else
        log "❌ 符号链接检查失败"
        return 1
    fi
}

function check_permissions() {
    log "🔐 检查脚本执行权限..."
    local failed=0
    
    find "$PROJECT_ROOT/scripts" -name "*.sh" -type f | while read -r script; do
        if [[ ! -x "$script" ]]; then
            log "⚠️  $script 缺少执行权限"
            chmod +x "$script"
            log "✅ 已修复 $script 执行权限"
        fi
    done
    
    log "✅ 脚本权限检查完成"
}

function check_documentation() {
    log "📝 检查文档同步状态..."
    
    # 检查每个子目录是否有README
    for dir in setup deployment testing tools backend database; do
        readme_path="$PROJECT_ROOT/scripts/$dir/README.md"
        if [[ ! -f "$readme_path" ]]; then
            log "❌ 缺少文档: $readme_path"
        else
            log "✅ 文档存在: $dir/README.md"
        fi
    done
}

function check_new_scripts() {
    log "🆕 检查新增脚本分类..."
    
    # 检查是否有未分类的脚本
    if find "$PROJECT_ROOT/scripts" -maxdepth 1 -name "*.sh" -o -name "*.py" | grep -q .; then
        log "⚠️  发现根目录下有未分类脚本"
        find "$PROJECT_ROOT/scripts" -maxdepth 1 -name "*.sh" -o -name "*.py" | while read -r script; do
            log "   - $(basename "$script")"
        done
    else
        log "✅ 所有脚本已正确分类"
    fi
}

function generate_report() {
    log "📊 生成维护报告..."
    
    cat >> "$LOG_FILE" << EOF

=== 维护检查报告 ===
检查时间: $(date '+%Y-%m-%d %H:%M:%S')
检查项目: 符号链接、权限、文档、脚本分类
日志文件: $LOG_FILE

建议操作:
1. 查看完整日志了解详细情况
2. 修复发现的问题
3. 更新相关文档

EOF
    
    log "📋 维护报告已生成"
}

function main() {
    log "🚀 开始每周维护检查..."
    
    local exit_code=0
    
    check_symlinks || exit_code=1
    check_permissions
    check_documentation
    check_new_scripts
    generate_report
    
    if [[ $exit_code -eq 0 ]]; then
        log "🎉 每周维护检查完成，无严重问题"
    else
        log "⚠️  每周维护检查完成，发现需要修复的问题"
    fi
    
    echo "📄 详细日志: $LOG_FILE"
    return $exit_code
}

main "$@"
