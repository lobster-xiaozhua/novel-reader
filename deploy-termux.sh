#!/bin/bash

# Novel Reader Android/Termux 部署脚本
# 用法: ./deploy-termux.sh [command]
#
# 命令:
#   install     安装依赖
#   start       启动服务
#   stop        停止服务
#   status      查看状态
#   update      更新项目
#   help        显示帮助

set -e

PROJECT_NAME="novel-reader"
PROJECT_DIR="$HOME/storage/shared/novel-reader"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
DATA_DIR="$PROJECT_DIR/data"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_header() { echo -e "\n${CYAN}════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}════════════════════════════════════════════════${NC}\n"; }

check_termux() {
    if [ ! -d "$PREFIX" ]; then
        print_error "此脚本仅适用于 Termux (Android)"
        exit 1
    fi
    print_info "检测到 Termux 环境"
}

detect_china() {
    if command -v curl &> /dev/null; then
        COUNTRY=$(curl -s --max-time 3 "https://ipinfo.io/country" 2>/dev/null || echo "unknown")
        if [ "$COUNTRY" = "CN" ]; then
            echo "china"
            return
        fi
    fi
    echo "global"
}

setup_mirrors() {
    print_info "配置 Termux 镜像源..."
    REGION=$(detect_china)

    if [ "$REGION" = "china" ]; then
        print_info "检测到中国地区，配置国内镜像..."

        if [ -f "$PREFIX/etc/apt/sources.list" ]; then
            print_info "配置 Termux 镜像..."
            echo "https://mirrors.ustc.edu.cn/termux/apt/termux-main" > "$PREFIX/etc/apt/sources.list"
            print_success "Termux 镜像: USTC"
        fi

        mkdir -p ~/.pip
        cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 120
retries = 5

[install]
trusted-host = mirrors.aliyun.com
             pypi.tuna.tsinghua.edu.cn
EOF
        print_success "pip: 阿里云镜像"

        npm config set registry https://registry.npmmirror.com 2>/dev/null || true
        print_success "npm: npmmirror.com"
    else
        print_info "使用官方源"
    fi
}

install_system_deps() {
    print_header "安装系统依赖 (Termux)"

    print_info "更新包列表..."
    pkg update -y

    print_info "安装基础工具..."
    pkg install -y python python-pip nodejs-lts npm git curl wget termux-services

    print_info "安装 Python 开发工具..."
    pkg install -y python-dev clang make

    print_info "配置 Python..."
    python -m pip install --upgrade pip

    print_success "系统依赖安装完成"
}

create_directories() {
    if [ ! -d "$PROJECT_DIR" ]; then
        print_info "项目目录不存在，需要先克隆项目"
        print_info "请在 Termux 中运行:"
        echo "  cd ~/storage/shared"
        echo "  git clone https://github.com/lobster-xiaozhua/novel-reader.git"
        exit 1
    fi

    print_info "创建数据目录..."
    mkdir -p "$DATA_DIR"/{books,index,static,logs,cache,backups}
    print_success "目录创建完成"
}

check_env() {
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        print_info "创建 .env 配置文件..."
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        cat > "$PROJECT_DIR/.env" << EOF
SECRET_KEY=$SECRET_KEY
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://localhost:6379
DATA_DIR=./data
BOOKS_DIR=./data/books
INDEX_DIR=./data/index
STATIC_DIR=./data/static
LOGS_DIR=./data/logs
CACHE_DIR=./data/cache
EOF
        print_success ".env 文件已创建"
    fi
}

install_python_deps() {
    print_header "安装 Python 依赖 (Termux)"

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        print_info "创建 Python 虚拟环境..."
        python -m venv venv
    fi

    source venv/bin/activate

    print_info "安装依赖 (兼容版本)..."
    if [ -f "requirements-compat.txt" ]; then
        pip install --no-cache-dir -r requirements-compat.txt
    else
        pip install --no-cache-dir -r requirements.txt
    fi

    deactivate
    cd ..
    print_success "Python 依赖安装完成"
}

install_node_deps() {
    print_header "安装 Node.js 依赖 (Termux)"

    cd "$FRONTEND_DIR"

    print_info "安装 npm 包..."
    npm install

    cd ..
    print_success "Node.js 依赖安装完成"
}

start_redis() {
    print_info "启动 Redis..."

    if command -v redis-server &> /dev/null; then
        if ! pgrep -x redis-server > /dev/null; then
            redis-server --daemonize yes --port 6379 --maxmemory 64mb --maxmemory-policy allkeys-lru
            print_success "Redis 已启动"
        else
            print_info "Redis 已在运行"
        fi
    else
        print_warning "Redis 未安装，禁用缓存功能"
        print_info "可选: pkg install redis"
    fi
}

start_backend() {
    print_header "启动后端服务"

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        python -m venv venv
    fi

    source venv/bin/activate

    export DATABASE_URL="sqlite+aiosqlite:///data/novel.db"
    export REDIS_URL="redis://localhost:6379"
    export PYTHONDONTWRITEBYTECODE=1
    export TERMUX=1

    nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 > ../data/logs/backend.log 2>&1 &
    echo $! > uvicorn.pid

    deactivate
    cd ..

    print_info "等待后端启动..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            print_success "后端服务已就绪"
            return
        fi
        sleep 1
    done
    print_warning "后端启动较慢，请稍后检查"
}

start_frontend() {
    print_header "启动前端服务"

    cd "$FRONTEND_DIR"

    nohup npm run dev -- --host 0.0.0.0 --port 8080 > ../data/logs/frontend.log 2>&1 &
    echo $! > vite.pid

    cd ..

    print_success "前端服务已启动"
}

do_install() {
    print_header "安装 Novel Reader (Termux)"

    check_termux
    setup_mirrors
    install_system_deps
    create_directories
    check_env
    install_python_deps
    install_node_deps

    print_success "安装完成!"
    echo ""
    echo -e "${GREEN}下一步:${NC}"
    echo "  ./deploy-termux.sh start   # 启动服务"
    echo ""
}

do_start() {
    print_header "启动 Novel Reader (Termux)"

    check_termux

    if [ ! -d "$PROJECT_DIR" ]; then
        print_error "项目目录不存在"
        print_info "请先运行: ./deploy-termux.sh install"
        exit 1
    fi

    create_directories
    check_env
    start_redis
    start_backend
    start_frontend

    print_success "服务已启动!"
    echo ""
    echo -e "  ${GREEN}📖${NC} 前端页面: http://localhost:8080"
    echo -e "  ${GREEN}🔧${NC} API 文档:  http://localhost:8000/docs"
    echo ""
    print_warning "注意: 服务在后台运行，关闭 Termux 会停止服务"
}

do_stop() {
    print_header "停止服务"

    if [ -f "$BACKEND_DIR/uvicorn.pid" ]; then
        kill $(cat "$BACKEND_DIR/uvicorn.pid") 2>/dev/null || true
        rm -f "$BACKEND_DIR/uvicorn.pid"
    fi

    if [ -f "$FRONTEND_DIR/vite.pid" ]; then
        kill $(cat "$FRONTEND_DIR/vite.pid") 2>/dev/null || true
        rm -f "$FRONTEND_DIR/vite.pid"
    fi

    pkill -f "uvicorn" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true

    if command -v redis-cli &> /dev/null; then
        redis-cli shutdown 2>/dev/null || true
    fi

    print_success "所有服务已停止"
}

do_status() {
    print_header "服务状态"

    echo -e "${CYAN}[原生模式 - Termux]${NC}"

    if pgrep -f "uvicorn" > /dev/null; then
        print_success "后端: 运行中"
    else
        print_error "后端: 未运行"
    fi

    if pgrep -f "vite" > /dev/null; then
        print_success "前端: 运行中"
    else
        print_error "前端: 未运行"
    fi

    echo ""
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        print_success "API: 运行中"
    else
        print_error "API: 未响应"
    fi

    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 2>/dev/null | grep -qE "^(200|301|302)"; then
        print_success "前端: 运行中"
    else
        print_error "前端: 未响应"
    fi
}

do_update() {
    print_header "更新项目"

    if [ ! -d "$PROJECT_DIR" ]; then
        print_error "项目目录不存在"
        exit 1
    fi

    cd "$PROJECT_DIR"
    git pull origin main

    print_info "重新安装依赖..."
    cd "$BACKEND_DIR"
    if [ -d "venv" ]; then
        source venv/bin/activate
        pip install --upgrade -r requirements-compat.txt
        deactivate
    fi

    cd "$FRONTEND_DIR"
    npm install

    print_success "更新完成!"
}

show_help() {
    cat << EOF
Novel Reader Android/Termux 部署脚本

用法: ./deploy-termux.sh [command]

命令:
  install     安装所有依赖
  start       启动服务
  stop        停止服务
  status      查看状态
  update      更新项目
  help        显示帮助

首次使用:
  1. pkg install git
  2. cd ~/storage/shared
  3. git clone https://github.com/lobster-xiaozhua/novel-reader.git
  4. cd novel-reader
  5. ./deploy-termux.sh install
  6. ./deploy-termux.sh start

访问地址 (在手机浏览器中):
  前端: http://localhost:8080
  API:  http://localhost:8000/docs

注意:
  - 需要授予 Termux 存储权限: termux-setup-storage
  - 服务在后台运行，关闭 Termux 会停止服务
  - 建议保持 Termux 在后台运行
EOF
}

case "${1:-}" in
    install)
        do_install
        ;;
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    status)
        do_status
        ;;
    update)
        do_update
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
