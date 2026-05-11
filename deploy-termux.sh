#!/bin/bash

# Novel Reader Android/Termux 部署脚本
# 专为 Termux (Android) 优化，无需 root
# 用法:
#   ./deploy-termux.sh           - 交互式菜单
#   ./deploy-termux.sh local     - 本地安装
#   ./deploy-termux.sh status    - 查看状态
#   ./deploy-termux.sh update     - 更新项目
#   ./deploy-termux.sh uninstall  - 卸载

set -e

PROJECT_NAME="novel-reader"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DATA_DIR="$SCRIPT_DIR/data"
INSTALL_MARKER="$SCRIPT_DIR/.installed-termux"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[OK]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_err() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() { echo -e "\n${MAGENTA}══════ $1 ══════${NC}"; }

check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

is_termux() {
    if [ -n "$TERMUX_VERSION" ] || [ -d "$PREFIX" ]; then
        return 0
    fi
    return 1
}

setup_termux_repos() {
    print_info "配置 Termux 仓库..."
    if [ ! -f ~/.termux/boot ]; then
        mkdir -p ~/.termux
    fi
    print_success "Termux 环境检测完成"
}

update_packages() {
    print_header "更新 Termux 包"
    pkg update && pkg upgrade -y
    print_success "包更新完成"
}

install_python_deps_termux() {
    print_header "安装 Python 依赖"

    if [ ! -d "$BACKEND_DIR/venv" ]; then
        print_info "创建 Python 虚拟环境..."
        python -m venv "$BACKEND_DIR/venv"
    fi

    source "$BACKEND_DIR/venv/bin/activate"

    pip install --upgrade pip -q

    if [ -f "$BACKEND_DIR/requirements-pure-python.txt" ]; then
        print_info "使用纯 Python 依赖列表..."
        pip install -r "$BACKEND_DIR/requirements-pure-python.txt" -q
    else
        pip install -r "$BACKEND_DIR/requirements.txt" -q
    fi

    deactivate
    print_success "Python 依赖安装完成"
}

install_node_deps_termux() {
    print_header "安装 Node.js 依赖"
    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        npm config set registry https://registry.npmmirror.com
        npm install
    fi

    cd ..
    print_success "Node.js 依赖安装完成"
}

create_dirs_termux() {
    print_info "创建数据目录..."
    mkdir -p "$DATA_DIR"/{books,index,static,logs,cache,backups,versions}
    print_success "目录创建完成"
}

test_env_termux() {
    if [ ! -f ".env" ]; then
        print_info "创建 .env 配置文件..."
        SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        cat > .env << EOF
SECRET_KEY=$SECRET
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///$DATA_DIR/novel.db
REDIS_URL=redis://localhost:6379
DATA_DIR=$DATA_DIR
BOOKS_DIR=$DATA_DIR/books
INDEX_DIR=$DATA_DIR/index
STATIC_DIR=$DATA_DIR/static
LOGS_DIR=$DATA_DIR/logs
CACHE_DIR=$DATA_DIR/cache
EOF
        print_success ".env 已创建"
    fi
}

start_redis_termux() {
    print_header "启动 Redis"

    if ! check_command "redis-server"; then
        print_info "安装 Redis..."
        pkg install redis -y
    fi

    if pgrep -x redis-server > /dev/null; then
        print_info "Redis 已在运行"
    else
        redis-server --daemonize yes --port 6379
        sleep 1
        if redis-cli ping > /dev/null 2>&1; then
            print_success "Redis 已启动"
        else
            print_warn "Redis 启动失败，缓存功能将不可用"
        fi
    fi
}

deploy_local_termux() {
    print_header "Termux 本地部署"

    if ! is_termux; then
        print_warn "检测到非 Termux 环境，某些功能可能受限"
    fi

    update_packages

    print_info "安装基础工具..."
    pkg install -y python nodejs-lts git curl wget

    setup_termux_repos
    create_dirs_termux
    test_env_termux
    start_redis_termux

    print_info "安装 Python 依赖 (纯 Python 版本)..."
    install_python_deps_termux

    print_info "安装 Node.js 依赖..."
    install_node_deps_termux

    print_success "Termux 部署完成!"
    echo ""
    echo -e "${YELLOW}启动服务:${NC}"
    echo ""
    echo -e "${CYAN}方式 1 - 使用一键脚本:${NC}"
    echo "  cd $PROJECT_DIR && ./start.sh"
    echo ""
    echo -e "${CYAN}方式 2 - 手动启动:${NC}"
    echo "  cd $BACKEND_DIR"
    echo "  source venv/bin/activate"
    echo "  uvicorn main:app --host 0.0.0.0 --port 8000"
    echo ""
    echo -e "${CYAN}方式 3 - 后台运行:${NC}"
    echo "  cd $BACKEND_DIR"
    echo "  source venv/bin/activate"
    echo "  nohup uvicorn main:app --host 0.0.0.0 --port 8000 > ../data/logs/backend.log 2>&1 &"
    echo ""
    echo -e "${YELLOW}访问地址:${NC}"
    echo "  http://localhost:8000      (API 文档)"
    echo "  http://localhost:8001      (前端 Dev 服务器)"
    echo ""
    echo -e "${CYAN}停止服务:${NC}"
    echo "  pkill -f uvicorn"
    echo "  pkill -f vite"

    echo "termux" > "$INSTALL_MARKER"
    return 0
}

show_status_termux() {
    print_header "服务状态 (Termux)"

    echo -e "${CYAN}进程状态:${NC}"

    if pgrep -f "uvicorn main:app" > /dev/null; then
        print_success "后端 (uvicorn): 运行中"
    else
        print_warn "后端 (uvicorn): 未运行"
    fi

    if pgrep -f "vite" > /dev/null; then
        print_success "前端 (vite): 运行中"
    else
        print_warn "前端 (vite): 未运行"
    fi

    if check_command "redis-cli" && redis-cli ping > /dev/null 2>&1; then
        print_success "Redis: 运行中"
    else
        print_warn "Redis: 未运行"
    fi

    echo ""
    echo -e "${CYAN}健康检查:${NC}"

    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        print_success "后端 API: 运行中 (http://localhost:8000)"
    else
        print_err "后端 API: 未响应"
    fi

    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8001 2>/dev/null | grep -qE "^(200|301|302)"; then
        print_success "前端页面: 运行中 (http://localhost:8001)"
    else
        print_warn "前端页面: 未运行"
    fi

    echo ""
    echo -e "${CYAN}存储空间:${NC}"
    df -h "$PROJECT_DIR" 2>/dev/null | tail -1 || print_info "无法获取存储信息"
}

stop_services_termux() {
    print_header "停止服务"

    pkill -f "uvicorn main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    pkill -f "redis-server" 2>/dev/null || true

    print_success "服务已停止"
}

update_project() {
    print_header "更新项目"

    cd "$PROJECT_DIR"

    if [ -d ".git" ]; then
        print_info "拉取最新代码..."
        git pull origin main || git pull origin master
        print_success "代码更新完成"
    else
        print_warn "非 Git 仓库，跳过更新"
    fi

    print_info "更新 Python 依赖..."
    install_python_deps_termux

    print_info "更新 Node.js 依赖..."
    install_node_deps_termux

    print_success "项目更新完成"
}

uninstall_termux() {
    print_header "卸载"
    print_warn "此操作将删除虚拟环境和配置!"

    stop_services_termux

    if [ -d "$BACKEND_DIR/venv" ]; then
        rm -rf "$BACKEND_DIR/venv"
        print_success "已删除虚拟环境"
    fi

    if [ -f "$INSTALL_MARKER" ]; then
        rm -f "$INSTALL_MARKER"
        print_success "已删除安装标记"
    fi

    print_success "卸载完成"
}

show_help_termux() {
    cat << EOF
Novel Reader Android/Termux 部署脚本

用法: ./deploy-termux.sh [command]

命令:
  local       本地安装 (首次使用)
  status      查看服务状态
  stop        停止服务
  update      更新项目
  uninstall   卸载
  help        显示帮助

首次使用步骤:
  1. pkg update && pkg upgrade
  2. pkg install git
  3. cd 到项目目录
  4. ./deploy-termux.sh local

注意:
  - Termux 版本需要 >= 0.118
  - 推荐使用 proot-distro 安装 Ubuntu 获得更完整的体验
  - Python 依赖使用纯 Python 版本，无需编译
  - Redis 用于缓存，如无需缓存功能可跳过

故障排除:
  - 如遇权限问题，检查 Termux 存储权限
  - 如遇网络问题，使用镜像源
  - 如遇启动失败，查看 logs 目录下的日志
EOF
}

show_menu_termux() {
    echo ""
    echo -e "${MAGENTA}═══════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}  Novel Reader - Termux 部署工具${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════${NC}"
    echo ""
    echo "1. 本地安装             (首次使用必选)"
    echo "2. 查看状态"
    echo "3. 停止服务"
    echo "4. 更新项目"
    echo "5. 卸载"
    echo ""
    echo "q. 退出"
    echo ""
    echo -e "${MAGENTA}═══════════════════════════════════════════${NC}"
    echo ""
}

case "${1:-}" in
    local)
        deploy_local_termux
        ;;
    status)
        show_status_termux
        ;;
    stop)
        stop_services_termux
        ;;
    update)
        update_project
        ;;
    uninstall)
        uninstall_termux
        ;;
    help|--help|-h)
        show_help_termux
        ;;
    "")
        show_menu_termux
        read -p "请选择 (1-5, q): " choice
        case "$choice" in
            1) deploy_local_termux ;;
            2) show_status_termux ;;
            3) stop_services_termux ;;
            4) update_project ;;
            5) uninstall_termux ;;
            q) exit 0 ;;
        esac
        ;;
    *)
        print_err "未知命令: $1"
        show_help_termux
        exit 1
        ;;
esac
