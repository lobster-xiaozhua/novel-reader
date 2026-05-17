#!/data/data/com.termux/files/usr/bin/bash

# Novel Reader Termux 一键安装脚本
# 支持 Android Termux 环境
# 用法: bash install-termux.sh [start|stop|status|uninstall]

set -e

PROJECT_NAME="novel-reader"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/data"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Termux 特殊路径
PREFIX="/data/data/com.termux/files/usr"
TERMUX_BIN="$PREFIX/bin"
VENV_DIR="$SCRIPT_DIR/.venv"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[OK]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERR]${NC} $1"; }
print_step() { echo -e "${CYAN}[->]${NC} $1"; }

print_banner() {
    clear
    echo ""
    echo -e "${CYAN}=======================================================${NC}"
    echo -e "  ${GREEN}Novel Reader - Termux 安装${NC}"
    echo -e "${CYAN}=======================================================${NC}"
    echo ""
}

check_termux() {
    if [ ! -d "$PREFIX" ]; then
        print_error "未检测到 Termux 环境"
        print_info "请在 Termux 中运行此脚本"
        exit 1
    fi
    print_success "检测到 Termux 环境"
}

setup_mirrors() {
    print_step "配置国内镜像源..."

    mkdir -p ~/.pip
    cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 120
[install]
trusted-host = mirrors.aliyun.com
EOF
    print_success "pip: 阿里云镜像"

    npm config set registry https://registry.npmmirror.com 2>/dev/null || true
    print_success "npm: npmmirror.com"
}

install_system_deps() {
    print_step "安装系统依赖..."

    pkg update -y && pkg upgrade -y

    pkg install -y python3 python3-dev nodejs npm redis git
    pkg install -y clang make libffi-dev openssl-dev
    pkg install -y sqlite

    print_success "系统依赖安装完成"
}

create_directories() {
    print_step "创建数据目录..."
    mkdir -p "$DATA_DIR"/{books,index,static,logs,cache,backups}
    mkdir -p "$BACKEND_DIR"/logs
    print_success "目录创建完成"
}

check_env() {
    if [ ! -f ".env" ]; then
        print_info "创建环境配置文件..."
        cat > .env << EOF
APP_NAME=Novel Reader
APP_VERSION=1.0.0
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://localhost:6379
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
BOOKS_DIR=./data/books
INDEX_DIR=./data/index
STATIC_DIR=./data/static
LOGS_DIR=./data/logs
PASSWORD_MIN_LENGTH=8
BCRYPT_ROUNDS=10
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_MINUTES=15
CRAWLER_MAX_CONCURRENT=3
CRAWLER_REQUEST_DELAY=2.0
CRAWLER_MAX_RETRIES=3
CRAWLER_TIMEOUT=30
CACHE_EXPIRE_MINUTES=10
SEARCH_RESULTS_LIMIT=50
PAGE_SIZE=20
EOF
        print_success ".env 已创建"
    fi
}

install_python_deps() {
    print_step "安装 Python 依赖..."

    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
        print_success "虚拟环境创建完成"
    fi

    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip -q
    pip install bcrypt>=4.0.1 -q
    pip install -r "$BACKEND_DIR/requirements.txt" -q
    deactivate
    print_success "Python 依赖安装完成"
}

install_node_deps() {
    print_step "安装 Node.js 依赖..."

    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        npm install --legacy-peer-deps
    fi

    print_info "构建前端..."
    npm run build

    cd "$SCRIPT_DIR"
    print_success "Node.js 依赖安装完成"
}

start_redis() {
    print_step "启动 Redis..."

    if pgrep redis-server > /dev/null; then
        print_success "Redis 已运行"
        return
    fi

    redis-server --daemonize yes --bind 127.0.0.1 --port 6379 \
        --maxmemory 32mb --maxmemory-policy allkeys-lru \
        --logfile "$DATA_DIR/logs/redis.log"

    sleep 2
    if redis-cli ping | grep -q PONG; then
        print_success "Redis 启动成功"
    else
        print_error "Redis 启动失败"
        exit 1
    fi
}

start_backend() {
    print_step "启动后端服务..."

    stop_backend || true

    source "$VENV_DIR/bin/activate"
    export PYTHONPATH="$SCRIPT_DIR"

    nohup uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 1 \
        --log-level info \
        > "$DATA_DIR/logs/backend.log" 2>&1 &

    echo $! > "$BACKEND_DIR/uvicorn.pid"

    deactivate

    for i in {1..30}; do
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            print_success "后端服务已就绪"
            return 0
        fi
        sleep 1
    done

    print_warning "后端启动较慢，请稍后检查"
    return 0
}

start_frontend() {
    print_step "启动前端服务..."

    stop_frontend || true

    cd "$FRONTEND_DIR"

    if command -v serve &> /dev/null; then
        nohup serve -s dist -l 80 > "$DATA_DIR/logs/frontend.log" 2>&1 &
    else
        npm install -g serve > /dev/null 2>&1
        nohup serve -s dist -l 80 > "$DATA_DIR/logs/frontend.log" 2>&1 &
    fi

    echo $! > "$FRONTEND_DIR/serve.pid"

    cd "$SCRIPT_DIR"
    print_success "前端服务已启动"
}

stop_backend() {
    if [ -f "$BACKEND_DIR/uvicorn.pid" ]; then
        kill $(cat "$BACKEND_DIR/uvicorn.pid") 2>/dev/null || true
        rm -f "$BACKEND_DIR/uvicorn.pid"
    fi
}

stop_frontend() {
    if [ -f "$FRONTEND_DIR/serve.pid" ]; then
        kill $(cat "$FRONTEND_DIR/serve.pid") 2>/dev/null || true
        rm -f "$FRONTEND_DIR/serve.pid"
    fi
}

stop_redis() {
    redis-cli shutdown 2>/dev/null || true
}

stop_all() {
    print_step "停止所有服务..."
    stop_frontend
    stop_backend
    stop_redis
    print_success "所有服务已停止"
}

show_status() {
    print_step "服务状态"
    echo ""

    if redis-cli ping 2>/dev/null | grep -q PONG; then
        print_success "Redis: 运行中"
    else
        print_error "Redis: 未运行"
    fi

    if [ -f "$BACKEND_DIR/uvicorn.pid" ] && kill -0 $(cat "$BACKEND_DIR/uvicorn.pid") 2>/dev/null; then
        print_success "后端: 运行中"
    else
        print_error "后端: 未运行"
    fi

    if [ -f "$FRONTEND_DIR/serve.pid" ] && kill -0 $(cat "$FRONTEND_DIR/serve.pid") 2>/dev/null; then
        print_success "前端: 运行中"
    else
        print_error "前端: 未运行"
    fi

    echo ""

    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        print_success "API: 正常"
    else
        print_error "API: 未响应"
    fi

    echo ""
    print_info "访问地址:"
    echo "  前端: http://localhost"
    echo "  API:  http://localhost:8000"

    if command -v ip > /dev/null; then
        IP=$(ip addr show wlan0 2>/dev/null | grep inet | grep -v 127.0.0.1 | awk '{print $2}' | cut -d '/' -f 1 | head -1)
        if [ -n "$IP" ]; then
            echo "  局域网: http://$IP"
            echo "  局域网API: http://$IP:8000"
        fi
    fi
}

show_logs() {
    print_step "查看日志"
    echo "按 Ctrl+C 退出"
    tail -f "$DATA_DIR/logs/"*.log 2>/dev/null || echo "日志文件不存在"
}

install_global() {
    print_step "配置全局命令..."

    if [ -f "$SCRIPT_DIR/readweb" ]; then
        ln -sf "$SCRIPT_DIR/readweb" "$TERMUX_BIN/readweb"
        chmod +x "$TERMUX_BIN/readweb"
        print_success "readweb -> $TERMUX_BIN/readweb"
        echo ""
        print_success "全局命令配置完成!"
        echo -e "${YELLOW}以后可直接使用:${NC}"
        echo "  readweb start    # 启动项目"
        echo "  readweb stop     # 停止项目"
        echo "  readweb status   # 查看状态"
    fi
}

uninstall() {
    print_warning "此操作将停止服务并删除所有数据!"
    read -p "确认继续? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        print_info "操作已取消"
        return
    fi

    stop_all

    print_info "删除数据目录..."
    rm -rf "$DATA_DIR"

    print_info "删除虚拟环境..."
    rm -rf "$VENV_DIR"

    print_info "删除前端依赖..."
    rm -rf "$FRONTEND_DIR/node_modules"

    print_info "删除全局命令..."
    rm -f "$TERMUX_BIN/readweb"

    print_success "卸载完成"
}

install() {
    print_banner

    check_termux

    echo -e "${YELLOW}此脚本将安装 Novel Reader 到 Termux${NC}"
    echo -e "${YELLOW}需要约 500MB 存储空间${NC}"
    echo ""

    install_system_deps
    setup_mirrors
    create_directories
    check_env
    install_python_deps
    install_node_deps
    install_global

    echo ""
    echo -e "${GREEN}=======================================================${NC}"
    echo -e "${GREEN}  安装完成!${NC}"
    echo -e "${GREEN}=======================================================${NC}"
    echo ""
    echo -e "${YELLOW}启动命令:${NC}"
    echo "  ./install-termux.sh start"
    echo "  或: readweb start"
    echo ""
}

start() {
    print_banner

    create_directories

    start_redis
    start_backend
    start_frontend

    echo ""
    echo -e "${GREEN}=======================================================${NC}"
    echo -e "${GREEN}  服务已启动!${NC}"
    echo -e "${GREEN}=======================================================${NC}"
    echo ""
    show_status
}

show_help() {
    print_banner
    cat << EOF
Novel Reader Termux 安装脚本

用法: bash install-termux.sh [command]

命令:
  (无)      安装并配置环境
  install   安装并配置环境
  start     启动所有服务
  stop      停止所有服务
  restart   重启服务
  status    查看服务状态
  logs      查看日志
  uninstall 卸载（删除所有数据）
  help      显示此帮助

示例:
  bash install-termux.sh      # 首次安装
  bash install-termux.sh start # 启动服务
  readweb start               # 配置全局命令后可用

访问地址:
  前端: http://localhost
  API:  http://localhost:8000
  文档: http://localhost:8000/docs
EOF
}

case "${1:-install}" in
    install)
        install
        ;;
    start)
        start
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep 1
        start
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    uninstall)
        uninstall
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "未知命令: $1"
        show_help
        exit 1
        ;;
esac
