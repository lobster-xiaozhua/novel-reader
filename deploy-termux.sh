#!/bin/bash

# Novel Reader 部署脚本 (Android/Termux)
# 专为 Termux 环境优化，无需 root
# 版本: 1.0.0

set -euo pipefail

SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DATA_DIR="$SCRIPT_DIR/data"

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
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_step() { echo -e "${CYAN}[>]${NC} $1"; }

print_banner() {
    echo ""
    echo -e "${MAGENTA}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║  Novel Reader 部署 (Termux/Android) v${SCRIPT_VERSION}     ║${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_termux() {
    if [ -z "${TERMUX_VERSION:-}" ]; then
        print_warn "检测到非 Termux 环境"
        print_info "本脚本专门为 Termux 优化，在标准 Linux 上请使用 deploy.sh"
        echo ""
    fi
}

check_prereq() {
    print_step "检查环境..."

    if ! command -v pkg &>/dev/null && ! command -v apt &>/dev/null; then
        print_error "未检测到包管理器，请确保在 Termux 环境中运行"
        return 1
    fi

    print_success "环境检查通过"
}

install_prereq() {
    print_step "安装基础工具..."

    if command -v pkg &>/dev/null; then
        pkg update -y 2>/dev/null || true
        pkg install -y \
            python \
            python-pip \
            python-venv \
            nodejs-lts \
            git \
            curl \
            wget \
            termux-services \
            openssl \
            libmagic \
            2>/dev/null || true
    elif command -v apt &>/dev/null; then
        sudo apt-get update
        sudo apt-get install -y \
            python3 python3-pip python3-venv \
            nodejs npm \
            git curl wget \
            libmagic1
    fi

    print_success "基础工具安装完成"
}

setup_python() {
    print_step "配置 Python 环境..."

    if ! command -v python &>/dev/null; then
        print_error "Python 未安装"
        return 1
    fi

    local pip_ver=$(python -m pip --version 2>/dev/null | head -1 || echo "not found")
    print_info "Python 版本: $(python --version 2>&1)"
    print_info "Pip 版本: $pip_ver"

    print_success "Python 环境就绪"
}

install_python_deps() {
    print_step "安装 Python 依赖..."

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        print_info "创建虚拟环境..."
        python -m venv venv
    fi

    source venv/bin/activate

    print_info "升级 pip..."
    pip install --upgrade pip -q

    print_info "安装依赖 (使用预编译 wheel)..."
    pip install --only-binary :all: -r requirements-compat.txt 2>/dev/null || \
    pip install -r requirements-compat.txt -q || \
    pip install -r requirements.txt -q

    deactivate
    cd ..
    print_success "Python 依赖安装完成"
}

install_node_deps() {
    print_step "安装 Node.js 依赖..."

    if ! command -v node &>/dev/null; then
        print_error "Node.js 未安装"
        return 1
    fi

    print_info "Node.js 版本: $(node --version)"
    print_info "npm 版本: $(npm --version)"

    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        print_info "安装 npm 包..."
        npm install --legacy-peer-deps
    fi

    cd ..
    print_success "Node.js 依赖安装完成"
}

init_directories() {
    print_step "初始化项目目录..."
    mkdir -p "$DATA_DIR"/{books,index,static,logs,cache,backups,versions}
    print_success "目录创建完成"
}

init_env_file() {
    print_step "检查 .env 文件..."
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        local secret_key=$(python -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "changeme")
        cat > "$SCRIPT_DIR/.env" << EOF
SECRET_KEY=$secret_key
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://localhost:6379
ACCESS_TOKEN_EXPIRE_MINUTES=1440
BCRYPT_ROUNDS=12
PASSWORD_MIN_LENGTH=6
EOF
        print_success ".env 文件已创建"
    else
        print_info ".env 文件已存在"
    fi
}

setup_redis() {
    print_step "检查 Redis..."

    if ! command -v redis-server &>/dev/null; then
        print_info "安装 Redis..."
        if command -v pkg &>/dev/null; then
            pkg install -y redis 2>/dev/null || true
        elif command -v apt &>/dev/null; then
            sudo apt-get install -y redis-server
        fi
    fi

    if command -v redis-server &>/dev/null; then
        print_info "启动 Redis..."
        if command -v pgrep &>/dev/null && pgrep redis-server > /dev/null; then
            print_info "Redis 已在运行"
        else
            redis-server --daemonize yes --port 6379 2>/dev/null || \
            nohup redis-server --port 6379 > "$DATA_DIR/logs/redis.log" 2>&1 &
            sleep 2
        fi

        if command -v redis-cli &>/dev/null; then
            if redis-cli ping &>/dev/null; then
                print_success "Redis 运行正常"
            else
                print_warn "Redis 启动失败，将使用内存缓存模式"
            fi
        fi
    else
        print_warn "Redis 未安装，将使用内存缓存模式"
        print_info "应用仍可正常运行，只是无法持久化缓存"
    fi
}

start_backend() {
    print_step "启动后端服务..."

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        print_info "创建虚拟环境..."
        python -m venv venv
    fi

    source venv/bin/activate

    mkdir -p "$DATA_DIR/logs"

    print_info "启动 uvicorn..."
    nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 \
        > "$DATA_DIR/logs/backend.log" 2>&1 &
    local pid=$!
    echo $pid > uvicorn.pid

    print_info "后端 PID: $pid"

    print_info "等待服务就绪..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/api/health &>/dev/null; then
            print_success "后端服务已就绪"
            break
        fi
        sleep 1
    done

    deactivate
    cd ..
}

start_frontend() {
    print_step "启动前端服务..."

    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        print_info "安装前端依赖..."
        npm install --legacy-peer-deps
    fi

    print_info "启动 Vite 开发服务器..."
    nohup npm run dev > "$DATA_DIR/logs/frontend.log" 2>&1 &
    local pid=$!
    echo $pid > vite.pid

    print_info "前端 PID: $pid"

    cd ..
}

start_all() {
    print_banner
    check_termux
    check_prereq

    init_directories
    init_env_file
    setup_redis
    start_backend
    start_frontend

    echo ""
    print_success "═══════════════════════════════════════════════════"
    print_success "  Novel Reader 已启动!"
    print_success "═══════════════════════════════════════════════════"
    echo ""
    print_info "访问地址:"
    print_info "  前端: http://localhost:5173"
    print_info "  API:  http://localhost:8000/docs"
    print_info "  日志: $DATA_DIR/logs/"
    echo ""
    print_info "停止服务: ./deploy-termux.sh stop"
}

stop_services() {
    print_step "停止服务..."

    if [ -f "$BACKEND_DIR/uvicorn.pid" ]; then
        local pid=$(cat "$BACKEND_DIR/uvicorn.pid")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            print_info "后端服务已停止 (PID: $pid)"
        fi
        rm -f "$BACKEND_DIR/uvicorn.pid"
    fi

    if [ -f "$FRONTEND_DIR/vite.pid" ]; then
        local pid=$(cat "$FRONTEND_DIR/vite.pid")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            print_info "前端服务已停止 (PID: $pid)"
        fi
        rm -f "$FRONTEND_DIR/vite.pid"
    fi

    print_success "所有服务已停止"
}

show_status() {
    print_banner
    print_step "服务状态"
    echo ""

    if [ -f "$BACKEND_DIR/uvicorn.pid" ]; then
        local pid=$(cat "$BACKEND_DIR/uvicorn.pid")
        if kill -0 "$pid" 2>/dev/null; then
            print_success "后端: 运行中 (PID: $pid)"
        else
            print_error "后端: 未运行 (PID 文件过期)"
        fi
    else
        print_error "后端: 未运行"
    fi

    if [ -f "$FRONTEND_DIR/vite.pid" ]; then
        local pid=$(cat "$FRONTEND_DIR/vite.pid")
        if kill -0 "$pid" 2>/dev/null; then
            print_success "前端: 运行中 (PID: $pid)"
        else
            print_error "前端: 未运行 (PID 文件过期)"
        fi
    else
        print_error "前端: 未运行"
    fi

    echo ""

    if curl -s http://localhost:8000/api/health &>/dev/null; then
        print_success "API: 运行中"
    else
        print_error "API: 未响应"
    fi

    if curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 2>/dev/null | grep -q "200"; then
        print_success "前端: 运行中"
    else
        print_error "前端: 未响应"
    fi

    if command -v redis-cli &>/dev/null; then
        echo ""
        if redis-cli ping &>/dev/null; then
            print_success "Redis: 运行中"
        else
            print_warn "Redis: 未运行"
        fi
    fi
}

show_logs() {
    print_step "查看日志 (Ctrl+C 退出)"
    if [ -d "$DATA_DIR/logs" ]; then
        tail -f "$DATA_DIR/logs"/*.log
    else
        print_warn "日志目录不存在"
    fi
}

show_help() {
    print_banner
    cat << EOF
用法: ./deploy-termux.sh [command]

命令:
  install     安装所有依赖
  start       启动服务
  stop        停止服务
  status      查看服务状态
  logs        查看日志
  restart     重启服务
  help        显示帮助

示例:
  ./deploy-termux.sh install   # 安装依赖
  ./deploy-termux.sh start    # 启动服务
  ./deploy-termux.sh status    # 查看状态

环境要求:
  - Termux (Android)
  - Python 3.10+
  - Node.js 18+

Termux 特殊说明:
  - 无需 root 权限
  - 使用 pkg 安装系统包
  - 端口默认: 8000 (后端), 5173 (前端)

首次使用:
  1. pkg update && pkg upgrade
  2. ./deploy-termux.sh install
  3. ./deploy-termux.sh start

文档: https://github.com/lobster-xiaozhua/novel-reader
EOF
}

install_all() {
    print_banner
    check_termux
    check_prereq
    install_prereq
    setup_python
    init_directories
    init_env_file
    install_python_deps
    install_node_deps

    echo ""
    print_success "═══════════════════════════════════════════════════"
    print_success "  安装完成!"
    print_success "═══════════════════════════════════════════════════"
    echo ""
    print_info "下一步: ./deploy-termux.sh start"
}

case "${1:-}" in
    install)
        install_all
        ;;
    start)
        start_all
        ;;
    stop)
        print_banner
        stop_services
        ;;
    restart)
        print_banner
        stop_services
        sleep 2
        start_all
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        print_error "未知命令: $1"
        show_help
        exit 1
        ;;
esac
