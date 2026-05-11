#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DATA_DIR="$SCRIPT_DIR/data"

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

detect_system() {
    if [ -d "$PREFIX" ] && [ -f "$PREFIX/bin/bash" ]; then
        echo "termux"
        return
    fi
    
    if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
        echo "docker"
        return
    fi
    
    if command -v apt-get &> /dev/null; then
        echo "debian"
        return
    fi
    if command -v yum &> /dev/null; then
        echo "redhat"
        return
    fi
    if command -v dnf &> /dev/null; then
        echo "redhat"
        return
    fi
    if command -v pacman &> /dev/null; then
        echo "arch"
        return
    fi
    if command -v apk &> /dev/null; then
        echo "alpine"
        return
    fi
    if command -v brew &> /dev/null; then
        echo "macos"
        return
    fi
    
    echo "unknown"
}

detect_china() {
    if command -v curl &> /dev/null; then
        COUNTRY=$(curl -s --max-time 3 "https://ipinfo.io/country" 2>/dev/null || echo "unknown")
        [ "$COUNTRY" = "CN" ] && echo "china" || echo "global"
    else
        echo "global"
    fi
}

setup_mirrors() {
    REGION=$(detect_china)
    if [ "$REGION" = "china" ]; then
        mkdir -p ~/.pip
        cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 120

[install]
trusted-host = mirrors.aliyun.com
EOF
        npm config set registry https://registry.npmmirror.com 2>/dev/null || true
    fi
}

create_directories() {
    mkdir -p "$DATA_DIR"/{books,index,static,logs,cache,backups}
}

check_env() {
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null) || \
                     SECRET_KEY=$(openssl rand -hex 32 2>/dev/null) || \
                     SECRET_KEY="dev-secret-key-$(date +%s)"
        cat > "$SCRIPT_DIR/.env" << EOF
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
        print_success ".env 已创建"
    fi
}

install_termux_deps() {
    print_header "安装 Termux 依赖"
    
    print_info "更新包列表..."
    pkg update -y
    
    print_info "安装基础工具..."
    pkg install -y python python-pip nodejs-lts npm git curl wget
    
    setup_mirrors
    
    create_directories
    check_env
    
    cd "$BACKEND_DIR"
    
    if [ ! -d "venv" ]; then
        python -m venv venv
    fi
    
    source venv/bin/activate
    
    print_info "安装 Python 依赖 (仅使用预编译包)..."
    pip install --upgrade pip setuptools wheel
    pip install --only-binary=:all: \
        fastapi==0.110.0 \
        uvicorn[standard]==0.27.1 \
        sqlalchemy==2.0.27 \
        aiosqlite==0.19.0 \
        redis==5.0.1 \
        "pydantic==2.6.1" \
        pydantic-settings==2.1.0 \
        python-multipart==0.0.9 \
        beautifulsoup4==4.12.3 \
        tenacity==8.2.3 \
        rich==13.7.0 \
        "python-jose[cryptography]==3.3.0" \
        pycryptodome==3.20.0 \
        passlib==1.7.4 \
        bcrypt==4.1.2 \
        aiohttp==3.9.3 \
        httpx==0.27.0
    
    deactivate
    cd "$SCRIPT_DIR"
    
    cd "$FRONTEND_DIR"
    npm install
    cd "$SCRIPT_DIR"
    
    print_success "依赖安装完成"
}

install_docker_deps() {
    print_header "Docker 模式"
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装"
        exit 1
    fi
    
    if ! docker info &> /dev/null 2>&1; then
        print_error "Docker 未运行"
        exit 1
    fi
    
    setup_mirrors
    create_directories
    check_env
    
    print_info "构建并启动服务..."
    docker-compose up -d
    
    print_success "服务已启动"
    print_info "前端: http://localhost"
    print_info "API:  http://localhost:8000/docs"
}

install_native_deps() {
    print_header "原生模式安装"
    
    SYSTEM=$(detect_system)
    setup_mirrors
    create_directories
    check_env
    
    case "$SYSTEM" in
        debian)
            sudo apt-get update -qq
            sudo apt-get install -y python3 python3-venv python3-pip nodejs npm redis-server curl git
            ;;
        redhat)
            sudo yum install -y python3 python3-pip nodejs npm redis curl git
            ;;
        arch)
            sudo pacman -Sy --noconfirm python python-pip nodejs npm redis curl git
            ;;
        alpine)
            apk add --no-cache python3 py3-pip nodejs npm redis curl git
            ;;
        macos)
            [ ! -f /usr/local/bin/brew ] && brew install python node redis
            ;;
    esac
    
    cd "$BACKEND_DIR"
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    
    print_info "安装 Python 依赖..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    deactivate
    cd "$SCRIPT_DIR"
    
    cd "$FRONTEND_DIR"
    npm install
    cd "$SCRIPT_DIR"
    
    print_success "依赖安装完成"
}

start_termux_services() {
    print_header "启动 Termux 服务"
    
    if ! pgrep -x redis-server > /dev/null 2>&1; then
        if command -v redis-server &> /dev/null; then
            redis-server --daemonize yes --port 6379 --maxmemory 64mb --maxmemory-policy allkeys-lru 2>/dev/null || true
        fi
    fi
    
    cd "$BACKEND_DIR"
    
    if [ ! -d "venv" ]; then
        python -m venv venv
    fi
    
    source venv/bin/activate
    
    export DATABASE_URL="sqlite+aiosqlite:///data/novel.db"
    export REDIS_URL="redis://localhost:6379"
    export PYTHONDONTWRITEBYTECODE=1
    
    nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 > ../data/logs/backend.log 2>&1 &
    echo $! > uvicorn.pid
    
    deactivate
    cd "$SCRIPT_DIR"
    
    cd "$FRONTEND_DIR"
    nohup npm run dev -- --host 0.0.0.0 --port 8080 > ../data/logs/frontend.log 2>&1 &
    echo $! > vite.pid
    cd "$SCRIPT_DIR"
    
    print_info "等待服务启动..."
    for i in {1..30}; do
        curl -s http://localhost:8000/api/health > /dev/null 2>&1 && break
        sleep 1
    done
    
    print_success "服务已启动"
    print_info "前端: http://localhost:8080"
    print_info "API:  http://localhost:8000/docs"
}

start_native_services() {
    print_header "启动原生服务"
    
    if ! pgrep -x redis-server > /dev/null 2>&1; then
        if command -v redis-server &> /dev/null; then
            redis-server --daemonize yes --port 6379 --maxmemory 64mb --maxmemory-policy allkeys-lru 2>/dev/null || true
        fi
    fi
    
    cd "$BACKEND_DIR"
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    
    export DATABASE_URL="sqlite+aiosqlite:///data/novel.db"
    export REDIS_URL="redis://localhost:6379"
    export PYTHONDONTWRITEBYTECODE=1
    
    nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 > ../data/logs/backend.log 2>&1 &
    echo $! > uvicorn.pid
    
    deactivate
    cd "$SCRIPT_DIR"
    
    cd "$FRONTEND_DIR"
    nohup npm run dev -- --host 0.0.0.0 --port 80 > ../data/logs/frontend.log 2>&1 &
    echo $! > vite.pid
    cd "$SCRIPT_DIR"
    
    print_info "等待服务启动..."
    for i in {1..30}; do
        curl -s http://localhost:8000/api/health > /dev/null 2>&1 && break
        sleep 1
    done
    
    print_success "服务已启动"
    print_info "前端: http://localhost"
    print_info "API:  http://localhost:8000/docs"
}

stop_services() {
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
    
    docker-compose down 2>/dev/null || true
    
    if command -v redis-cli &> /dev/null; then
        redis-cli shutdown 2>/dev/null || true
    fi
    
    print_success "所有服务已停止"
}

show_status() {
    print_header "服务状态"
    
    SYSTEM=$(detect_system)
    echo "系统: $SYSTEM"
    
    case "$SYSTEM" in
        docker)
            docker-compose ps 2>/dev/null || print_info "Docker 未运行"
            ;;
        termux)
            pgrep -f "uvicorn" > /dev/null && print_success "后端: 运行中" || print_error "后端: 未运行"
            pgrep -f "vite" > /dev/null && print_success "前端: 运行中" || print_error "前端: 未运行"
            ;;
        *)
            pgrep -x uvicorn > /dev/null && print_success "后端: 运行中" || print_error "后端: 未运行"
            pgrep -f "vite|npm" > /dev/null && print_success "前端: 运行中" || print_error "前端: 未运行"
            ;;
    esac
    
    echo ""
    curl -s http://localhost:8000/api/health > /dev/null 2>&1 && print_success "API: 运行中" || print_error "API: 未响应"
}

show_help() {
    cat << EOF
Novel Reader 智能启动脚本

用法: ./start.sh [command]

命令:
  install     自动检测系统并安装依赖
  start       启动所有服务
  stop        停止所有服务
  status      查看服务状态

自动检测支持:
  - Termux (Android)
  - Docker
  - Linux (Debian/RHEL/Arch/Alpine)
  - macOS

示例:
  ./start.sh install   # 安装依赖
  ./start.sh start    # 启动服务
  ./start.sh status   # 查看状态
EOF
}

main() {
    SYSTEM=$(detect_system)
    print_info "检测到系统: $SYSTEM"
    
    case "${1:-}" in
        install)
            case "$SYSTEM" in
                termux) install_termux_deps ;;
                docker) install_docker_deps ;;
                *) install_native_deps ;;
            esac
            ;;
        start)
            case "$SYSTEM" in
                termux) start_termux_services ;;
                docker)
                    docker-compose up -d
                    print_success "Docker 服务已启动"
                    ;;
                *) start_native_services ;;
            esac
            ;;
        stop)
            stop_services
            ;;
        status)
            show_status
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
}

main "$@"
