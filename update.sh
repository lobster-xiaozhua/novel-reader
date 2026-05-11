#!/bin/bash
# update.sh - Novel Reader 项目更新脚本
# 用法: bash update.sh [options]  或  ./update.sh [options]（需执行权限）
#
# 选项:
#   bash update.sh          - 交互式更新
#   bash update.sh -y       - 自动确认更新
#   bash update.sh --check  - 仅检查更新
#   bash update.sh --force  - 强制更新（忽略本地修改）
#   bash update.sh --backup - 更新前创建备份
#   bash update.sh --docker - 使用 Docker 模式重启服务

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="novel-reader"
BACKUP_ENABLED=true
AUTO_CONFIRM=false
CHECK_ONLY=false
FORCE_UPDATE=false
RUN_MODE="${READWEB_MODE:-local}"

while [[ $# -gt 0 ]]; do
    case $1 in
        -y|--yes) AUTO_CONFIRM=true; shift ;;
        --check) CHECK_ONLY=true; shift ;;
        --force) FORCE_UPDATE=true; shift ;;
        --no-backup) BACKUP_ENABLED=false; shift ;;
        --docker) RUN_MODE="docker"; shift ;;
        -h|--help)
            echo "用法: bash update.sh [options]"
            echo ""
            echo "选项:"
            echo "  -y, --yes       自动确认更新"
            echo "  --check         仅检查更新"
            echo "  --force         强制更新（忽略本地修改）"
            echo "  --no-backup     跳过备份"
            echo "  --docker        使用 Docker 模式重启"
            echo "  -h, --help      显示帮助"
            echo ""
            echo "快捷方式（需执行权限）:"
            echo "  ./update.sh --check"
            exit 0
            ;;
        *) log_error "未知选项: $1"; exit 1 ;;
    esac
done

cd "$SCRIPT_DIR"

print_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Novel Reader - 项目更新工具${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo ""
}

check_git() {
    if [ ! -d ".git" ]; then
        log_error "不是 git 仓库，无法更新"
        exit 1
    fi
}

check_git_status() {
    log_info "检查 git 状态..."

    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        log_warning "存在未提交的修改"
        if [ "$FORCE_UPDATE" = true ]; then
            log_info "使用 --force 选项，将保留本地修改"
        else
            log_info "请先提交或 stash 您的修改"
            git status --short
            return 1
        fi
    fi

    return 0
}

fetch_remote() {
    log_info "获取远程更新..."
    git fetch origin
    log_success "远程信息已更新"
}

check_updates() {
    log_info "检查更新..."

    local local_rev=$(git rev-parse HEAD)
    local remote_rev=$(git rev-parse origin/main)
    local behind=0
    local ahead=0

    if [ "$local_rev" != "$remote_rev" ]; then
        behind=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo "0")
        ahead=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo "0")
    fi

    echo ""
    echo -e "当前版本: ${CYAN}$local_rev${NC}"
    echo -e "最新版本: ${CYAN}$remote_rev${NC}"
    echo ""

    if [ "$behind" -gt 0 ]; then
        echo -e "${YELLOW}发现 $behind 个更新可用${NC}"
        echo ""
        echo "更新内容:"
        git log HEAD..origin/main --oneline 2>/dev/null | head -10
        echo ""
        return 1
    elif [ "$ahead" -gt 0 ]; then
        log_info "本地版本领先于远程"
        return 0
    else
        log_success "已是最新版本"
        return 0
    fi
}

create_backup() {
    if [ "$BACKUP_ENABLED" = false ]; then
        return 0
    fi

    log_info "创建备份..."

    local backup_dir="data/backups"
    mkdir -p "$backup_dir"

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$backup_dir/pre_update_$timestamp.tar.gz"

    tar -czf "$backup_file" \
        -C data \
        books db.json settings.json \
        --exclude='books/cache' \
        --exclude='books/tmp' \
        --exclude='*.pyc' \
        2>/dev/null || true

    log_success "备份已保存: $backup_file"
}

do_update() {
    log_info "开始更新..."

    if [ "$FORCE_UPDATE" = true ]; then
        log_info "强制模式: 使用 git reset --hard"
        git fetch origin
        git reset --hard origin/main
    else
        git pull origin main
    fi

    log_success "代码更新完成"
}

update_dependencies() {
    log_info "更新依赖..."

    if [ -f "backend/requirements.txt" ]; then
        log_info "更新 Python 依赖..."
        cd backend
        if [ -d "venv" ]; then
            source venv/bin/activate
            pip install -r requirements.txt -q
            deactivate
        fi
        cd ..
    fi

    if [ -f "frontend/package.json" ]; then
        log_info "更新 Node.js 依赖..."
        cd frontend
        if [ -d "package-lock.json" ]; then
            npm install
        fi
        cd ..
    fi

    log_success "依赖更新完成"
}

rebuild_frontend() {
    if [ ! -f "frontend/package.json" ]; then
        return 0
    fi

    log_info "重建前端..."
    cd frontend

    if [ ! -d "node_modules" ]; then
        npm install
    fi

    npm run build
    cd ..

    log_success "前端重建完成"
}

stop_local_services() {
    log_info "停止本地服务..."

    if [ -f "backend/uvicorn.pid" ]; then
        kill $(cat backend/uvicorn.pid) 2>/dev/null || true
        rm -f backend/uvicorn.pid
        log_success "后端已停止"
    fi

    if [ -f "frontend/vite.pid" ]; then
        kill $(cat frontend/vite.pid) 2>/dev/null || true
        rm -f frontend/vite.pid
        log_success "前端已停止"
    fi
}

start_local_services() {
    log_info "启动本地服务..."

    cd backend
    if [ -d "venv" ]; then
        source venv/bin/activate
        nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../data/logs/backend.log 2>&1 &
        echo $! > uvicorn.pid
        deactivate
    fi
    cd ..

    cd frontend
    npm run dev > ../data/logs/frontend.log 2>&1 &
    echo $! > vite.pid
    cd ..

    log_success "本地服务已启动"
}

restart_services() {
    log_info "重启服务..."

    if [ "$RUN_MODE" = "docker" ]; then
        if docker-compose ps 2>/dev/null | grep -q "Up"; then
            docker-compose up -d --force-recreate backend frontend
            log_success "Docker 服务已重启"
        else
            log_info "Docker 服务未运行，跳过重启"
        fi
    else
        stop_local_services
        sleep 1
        start_local_services
    fi
}

show_changelog() {
    echo ""
    echo -e "${CYAN}更新内容:${NC}"
    echo ""
    git log HEAD..origin/main --oneline --format="%h - %s" 2>/dev/null | head -20 || true
    echo ""
}

main() {
    print_header

    if ! command -v git &> /dev/null; then
        log_error "Git 未安装"
        exit 1
    fi

    check_git
    check_git_status || exit 1
    fetch_remote

    if ! check_updates; then
        if [ "$CHECK_ONLY" = true ]; then
            exit 1
        fi

        echo ""
        if [ "$AUTO_CONFIRM" = false ]; then
            read -p "是否更新? (y/N): " confirm
            if [[ ! $confirm =~ ^[Yy]$ ]]; then
                log_info "已取消更新"
                exit 0
            fi
        fi

        create_backup
        do_update
        show_changelog
        update_dependencies
        rebuild_frontend
        restart_services

        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  更新完成!${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "  ${GREEN}📖${NC} 前端: http://localhost"
        echo -e "  ${GREEN}🔧${NC} API:  http://localhost:8000/docs"
        echo ""

    else
        log_success "无需更新"
    fi
}

main
