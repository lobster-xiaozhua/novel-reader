#!/bin/bash
# Novel Reader 跨平台部署脚本 - Android/Termux
# 支持: Termux (Android), 纯本地模式无编译
# 用法: ./deploy-termux.sh [command]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
PROJECT_NAME="novel-reader"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DATA_DIR="$SCRIPT_DIR/data"
REQUIREMENTS_FILE="$BACKEND_DIR/requirements.txt"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
}

IS_TERMUX=false
if [ -d "$PREFIX" ] && [ -w "$PREFIX" ]; then
    IS_TERMUX=true
fi

check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

is_termux() {
    if [ -d "$PREFIX" ] && [ -w "$PREFIX" ]; then
        return 0
    fi
    return 1
}

install_termux_deps() {
    header "安装 Termux 依赖"
    if is_termux; then
        info "检测到 Termux 环境"
        pkg update -y
        pkg install -y python python-pip git curl wget nodejs
        success "Termux 依赖安装完成"
    else
        warning "检测到非 Termux 环境"
    fi
}

set_pip_mirror() {
    info "配置 pip 镜像源 (清华)..."
    mkdir -p ~/.pip
    cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple/
timeout = 120
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF
    success "pip 镜像配置完成"
}

set_npm_mirror() {
    info "配置 npm 镜像源..."
    npm config set registry https://registry.npmmirror.com
    success "npm 镜像配置完成"
}

install_python_deps() {
    header "安装 Python 依赖"
    if ! check_command python3 && ! check_command python; then
        error "Python 未安装"
        return 1
    fi
    set_pip_mirror
    cd "$BACKEND_DIR"
    if [ ! -d "venv" ]; then
        info "创建虚拟环境..."
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install --upgrade pip
    info "安装依赖 (纯 Python 版本，无编译)..."
    pip install -r requirements.txt
    deactivate
    cd "$SCRIPT_DIR"
    success "Python 依赖安装完成"
}

install_node_deps() {
    header "安装 Node.js 依赖"
    if ! check_command node; then
        error "Node.js 未安装"
        return 1
    fi
    set_npm_mirror
    cd "$FRONTEND_DIR"
    npm install
    cd "$SCRIPT_DIR"
    success "Node.js 依赖安装完成"
}

install_redis_termux() {
    header "安装 Redis (Termux)"
    if is_termux; then
        pkg install -y redis
        if check_command redis-server; then
            redis-server --daemonize yes --port 6379 --maxmemory 64mb --maxmemory-policy allkeys-lru
            success "Redis 安装完成"
        fi
    else
        warning "Redis 仅在 Termux 中可用"
    fi
}

create_directories() {
    header "创建数据目录"
    mkdir -p "$DATA_DIR"/{books,index,static,logs,cache,backups,versions}
    success "数据目录创建完成"
}

test_env_file() {
    local env_file="$SCRIPT_DIR/.env"
    if [ ! -f "$env_file" ]; then
        info "创建 .env 配置文件..."
        local secret_key=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        cat > "$env_file" << EOF
SECRET_KEY=$secret_key
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://localhost:6379
EOF
        success ".env 文件已创建"
    fi
}

setup_permissions() {
    header "配置 Termux 权限"
    if is_termux; then
        termux-setup-storage 2>/dev/null || true
        success "Termux 权限配置完成"
    fi
}

install_all() {
    header "完整安装 (Android/Termux)"
    install_termux_deps
    setup_permissions
    install_redis_termux
    install_python_deps
    install_node_deps
    create_directories
    test_env_file
    header "安装完成"
    success "Novel Reader 环境配置完成!"
}

start_local() {
    header "启动服务 (本地模式)"
    test_env_file
    create_directories
    info "启动后端 (端口 8080)..."
    cd "$BACKEND_DIR"
    if [ ! -d "venv" ]; then python3 -m venv venv; fi
    source venv/bin/activate
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload > ../data/logs/backend.log 2>&1 &
    echo $! > uvicorn.pid
    deactivate
    cd "$SCRIPT_DIR"
    info "启动前端..."
    cd "$FRONTEND_DIR"
    nohup npm run dev -- --port 5173 > ../data/logs/frontend.log 2>&1 &
    echo $! > vite.pid
    cd "$SCRIPT_DIR"
    success "服务已启动"
    echo ""
    echo "  访问地址 (手机浏览器):"
    echo "  前端: http://localhost:5173"
    echo "  API:  http://localhost:8080/docs"
}

stop_local() {
    header "停止服务"
    [ -f "$BACKEND_DIR/uvicorn.pid" ] && kill $(cat "$BACKEND_DIR/uvicorn.pid") 2>/dev/null && rm -f "$BACKEND_DIR/uvicorn.pid"
    [ -f "$FRONTEND_DIR/vite.pid" ] && kill $(cat "$FRONTEND_DIR/vite.pid") 2>/dev/null && rm -f "$FRONTEND_DIR/vite.pid"
    success "服务已停止"
}

show_status() {
    header "服务状态"
    curl -s http://localhost:8080/api/health > /dev/null 2>&1 && success "后端 API: 运行中 (8080)" || error "后端 API: 未运行"
    curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 2>/dev/null | grep -q "200" && success "前端页面: 运行中 (5173)" || error "前端页面: 未运行"
}

show_help() {
    cat << EOF
Novel Reader 跨平台部署脚本 (Android/Termux)

用法: ./deploy-termux.sh [command]

命令:
  install       完整安装所有依赖
  python        仅安装 Python 依赖
  node          仅安装 Node.js 依赖
  redis         安装 Redis (Termux)
  start         启动服务 (本地模式)
  stop          停止服务
  status        查看服务状态
  perm          配置 Termux 权限
  help          显示帮助信息

示例:
  ./deploy-termux.sh install    # 完整安装
  ./deploy-termux.sh start       # 启动服务

Termux 特殊说明:
  1. 首次运行需要授予存储权限
  2. 使用纯 Python 版本，无需编译
  3. 服务使用非标准端口 (8080/5173)
  4. 无需 root

访问地址 (手机浏览器):
  前端: http://localhost:5173
  API:  http://localhost:8080/docs
EOF
}

case "${1:-}" in
    install) install_all ;;
    python) install_python_deps ;;
    node) install_node_deps ;;
    redis) install_redis_termux ;;
    start) start_local ;;
    stop) stop_local ;;
    status) show_status ;;
    perm) setup_permissions ;;
    help|--help|-h|"") show_help ;;
    *) error "未知命令: $1"; show_help; exit 1 ;;
esac
