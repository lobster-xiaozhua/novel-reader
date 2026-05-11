#!/bin/bash

# Novel Reader 跨平台部署脚本 (Linux/macOS/WSL)
# 用法: ./deploy.sh [mode]
#
# 模式:
#   docker     Docker 模式 (默认)
#   native     原生模式

set -e

PROJECT_NAME="novel-reader"
BACKEND_DIR="backend"
FRONTEND_DIR="frontend"
DATA_DIR="data"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_header() { echo -e "\n${CYAN}════════════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}════════════════════════════════════════════════════════${NC}\n"; }

check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 未安装"
        return 1
    fi
    return 0
}

detect_region() {
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
    print_info "配置镜像源..."
    REGION=$(detect_region)

    if [ "$REGION" = "china" ]; then
        print_info "检测到中国地区，配置国内镜像..."

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

        if command -v docker &> /dev/null; then
            mkdir -p ~/.docker
            cat > ~/.docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me",
    "https://dockerproxy.cn"
  ]
}
EOF
            print_success "Docker: 镜像加速已配置"
        fi
    else
        print_info "使用官方源"
    fi
}

create_directories() {
    print_info "创建数据目录..."
    mkdir -p "$DATA_DIR"/{books,index,static,logs,cache,backups}
    print_success "目录创建完成"
}

check_env() {
    if [ ! -f ".env" ]; then
        print_info "创建 .env 配置文件..."
        if command -v openssl &> /dev/null; then
            SECRET_KEY=$(openssl rand -hex 32)
        else
            SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        fi
        cat > .env << EOF
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

install_system_deps() {
    print_info "安装系统依赖..."

    if command -v apt-get &> /dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y -qq python3 python3-venv python3-pip \
            nodejs npm redis-server curl git file libmagic1
        print_success "系统依赖安装完成 (apt)"
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3 python3-pip nodejs npm \
            redis curl git file-devel
        print_success "系统依赖安装完成 (yum)"
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3 python3-pip nodejs npm \
            redis curl git file-devel
        print_success "系统依赖安装完成 (dnf)"
    elif command -v pacman &> /dev/null; then
        sudo pacman -Sy --noconfirm python python-pip nodejs npm \
            redis curl git base-devel file
        print_success "系统依赖安装完成 (pacman)"
    elif command -v apk &> /dev/null; then
        apk add --no-cache python3 py3-pip nodejs npm redis curl git file
        print_success "系统依赖安装完成 (apk)"
    else
        print_warning "无法自动安装系统依赖，请手动安装"
    fi
}

install_python_deps_native() {
    print_info "安装 Python 依赖 (原生模式)..."

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        print_info "创建 Python 虚拟环境..."
        python3 -m venv venv
    fi

    source venv/bin/activate

    print_info "升级 pip..."
    pip install --upgrade pip

    print_info "安装依赖..."
    if [ -f "requirements-compat.txt" ]; then
        pip install -r requirements-compat.txt
    else
        pip install -r requirements.txt
    fi

    deactivate
    cd ..
    print_success "Python 依赖安装完成"
}

install_node_deps_native() {
    print_info "安装 Node.js 依赖 (原生模式)..."

    cd "$FRONTEND_DIR"
    npm install
    cd ..

    print_success "Node.js 依赖安装完成"
}

start_redis_native() {
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
    fi
}

start_backend_native() {
    print_info "启动后端服务 (原生模式)..."

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

start_frontend_native() {
    print_info "启动前端服务 (原生模式)..."

    cd "$FRONTEND_DIR"
    nohup npm run dev -- --host 0.0.0.0 --port 80 > ../data/logs/frontend.log 2>&1 &
    echo $! > vite.pid
    cd ..

    print_success "前端服务已启动"
}

deploy_docker() {
    print_header "Docker 模式部署"

    if ! check_command docker; then
        print_error "Docker 未安装，请先安装 Docker"
        print_info "访问 https://docs.docker.com/get-docker/"
        return 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker 未运行，请先启动 Docker"
        return 1
    fi

    setup_mirrors
    create_directories
    check_env

    print_info "启动 Docker 服务..."
    docker-compose up -d redis
    sleep 3
    docker-compose up -d backend
    docker-compose up -d frontend

    print_info "等待服务启动..."
    for i in {1..60}; do
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            print_success "服务已就绪"
            break
        fi
        sleep 1
    done

    print_success "部署完成!"
    echo ""
    echo -e "  ${GREEN}📖${NC} 前端页面: http://localhost"
    echo -e "  ${GREEN}🔧${NC} API 文档:  http://localhost:8000/docs"
    echo ""
}

deploy_native() {
    print_header "原生模式部署 (无 Docker)"

    setup_mirrors
    create_directories
    check_env
    install_system_deps

    install_python_deps_native
    install_node_deps_native

    start_redis_native
    start_backend_native
    start_frontend_native

    print_success "部署完成!"
    echo ""
    echo -e "  ${GREEN}📖${NC} 前端页面: http://localhost"
    echo -e "  ${GREEN}🔧${NC} API 文档:  http://localhost:8000/docs"
    echo ""
    print_warning "注意: 原生模式需要手动启动服务"
}

show_status() {
    print_header "服务状态"

    if command -v docker &> /dev/null && docker info &> /dev/null; then
        echo -e "${CYAN}[Docker 容器]${NC}"
        docker-compose ps
    else
        echo -e "${CYAN}[原生模式]${NC}"

        if pgrep -x uvicorn > /dev/null; then
            print_success "后端: 运行中"
        else
            print_error "后端: 未运行"
        fi

        if pgrep -f "vite|npm run dev" > /dev/null; then
            print_success "前端: 运行中"
        else
            print_error "前端: 未运行"
        fi
    fi

    echo ""
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        print_success "API: 运行中"
    else
        print_error "API: 未响应"
    fi

    if curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null | grep -qE "^(200|301|302)"; then
        print_success "前端: 运行中"
    else
        print_error "前端: 未响应"
    fi
}

stop_all() {
    print_header "停止服务"

    if command -v docker &> /dev/null && docker info &> /dev/null; then
        print_info "停止 Docker 容器..."
        docker-compose down
    fi

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

show_help() {
    cat << EOF
Novel Reader 跨平台部署脚本 (Linux/macOS/WSL)

用法: ./deploy.sh [mode]

模式:
  docker     Docker 模式 (默认)
  native     原生模式 (不使用 Docker)

命令:
  ./deploy.sh           部署 (默认 Docker 模式)
  ./deploy.sh docker     Docker 模式
  ./deploy.sh native     原生模式
  ./deploy.sh status     查看状态
  ./deploy.sh stop       停止服务
  ./deploy.sh help       显示帮助

访问地址:
  前端: http://localhost
  API:  http://localhost:8000/docs
EOF
}

case "${1:-}" in
    docker)
        deploy_docker
        ;;
    native)
        deploy_native
        ;;
    status)
        show_status
        ;;
    stop)
        stop_all
        ;;
    help|--help|-h)
        show_help
        ;;
    "")
        deploy_docker
        ;;
    *)
        print_error "未知模式: $1"
        show_help
        exit 1
        ;;
esac
