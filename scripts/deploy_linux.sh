#!/bin/bash
# Novel Reader - Linux 部署脚本
# 支持: Ubuntu / Debian / CentOS / Fedora / Arch 等主流发行版

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_header() { echo -e "\n${CYAN}═══ $1 ═══${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="novel-reader"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DATA_DIR="$SCRIPT_DIR/data"
PYTHON_DEPS_FILE="$BACKEND_DIR/requirements.txt"

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "${ID:-unknown}"
    elif [ -f /etc/redhat-release ]; then
        echo "rhel"
    else
        echo "unknown"
    fi
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

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 未安装"
        return 1
    fi
    return 0
}

install_system_deps() {
    log_header "安装系统依赖"

    local distro=$(detect_distro)
    local region=$(detect_region)

    log_info "检测到发行版: $distro"

    case "$distro" in
        ubuntu|debian|linuxmint|pop)
            export DEBIAN_FRONTEND=noninteractive
            sudo apt-get update -qq
            sudo apt-get install -y -qq \
                python3 python3-venv python3-pip \
                nodejs npm \
                redis-server \
                curl wget git \
                build-essential libmagic1 \
                > /dev/null 2>&1
            log_success "系统依赖安装完成 (apt)"
            ;;
        fedora|rhel|centos|rocky|alma)
            sudo dnf install -y -q \
                python3 python3-pip python3-virtualenv \
                nodejs npm \
                redis \
                curl wget git \
                libmagic \
                > /dev/null 2>&1
            log_success "系统依赖安装完成 (dnf)"
            ;;
        arch|manjaro|endeavouros)
            sudo pacman -Sy --noconfirm \
                python python-pip \
                nodejs npm \
                redis \
                curl wget git \
                base-devel \
                > /dev/null 2>&1
            log_success "系统依赖安装完成 (pacman)"
            ;;
        alpine)
            apk add --no-cache \
                python3 py3-pip \
                nodejs npm \
                redis \
                curl wget git \
                libmagic \
                build-base \
                > /dev/null 2>&1
            log_success "系统依赖安装完成 (apk)"
            ;;
        *)
            log_warning "未知发行版，请手动安装以下依赖:"
            log_warning "  - Python 3.8+"
            log_warning "  - Node.js 16+"
            log_warning "  - Redis"
            ;;
    esac
}

setup_mirrors() {
    log_header "配置镜像源"

    local region=$(detect_region)

    if [ "$region" = "china" ]; then
        log_info "检测到中国地区，配置国内镜像..."

        mkdir -p ~/.pip
        cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com.com/pypi/simple/
timeout = 120
extra-index-url = https://pypi.tuna.tsinghua.edu.cn/simple

[install]
trusted-host =
    mirrors.aliyun.com
    pypi.tuna.tsinghua.edu.cn
EOF
        log_success "pip 镜像: 阿里云"

        npm config set registry https://registry.npmmirror.com
        log_success "npm 镜像: npmmirror.com"

        if command -v apt-get &> /dev/null; then
            sudo bash -c 'cat > /etc/apt/sources.list.d/docker.list << "EOSOURCES"
deb https://mirrors.aliyun.com/docker-ce/linux/$OS/$OS_ID $(lsb_release -cs) stable
EOSOURCES'
            log_success "apt 镜像: 阿里云"
        fi

    else
        log_info "海外地区，使用官方源"
    fi
}

create_directories() {
    log_header "创建目录结构"

    for dir in books index static logs cache backups versions; do
        mkdir -p "$DATA_DIR/$dir"
        log_success "data/$dir"
    done
}

create_env_file() {
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        log_header "创建 .env 配置文件"

        local secret_key=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")

        cat > "$SCRIPT_DIR/.env" << EOF
SECRET_KEY=$secret_key
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://localhost:6379
DATA_DIR=data
BOOKS_DIR=data/books
INDEX_DIR=data/index
STATIC_DIR=data/static
LOGS_DIR=data/logs
CACHE_DIR=data/cache
BCRYPT_ROUNDS=12
PASSWORD_MIN_LENGTH=6
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7
EOF
        log_success ".env 文件已创建"
    else
        log_info ".env 文件已存在"
    fi
}

install_python_deps() {
    log_header "安装 Python 依赖"

    if ! check_command python3; then
        log_error "Python3 未安装"
        return 1
    fi

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        log_info "创建虚拟环境..."
        python3 -m venv venv
    fi

    source venv/bin/activate

    log_info "升级 pip..."
    pip install --upgrade pip -q

    log_info "安装 Python 包 (这可能需要几分钟)..."
    pip install -r "$PYTHON_DEPS_FILE"

    deactivate
    cd "$SCRIPT_DIR"

    log_success "Python 依赖安装完成"
}

install_node_deps() {
    log_header "安装 Node.js 依赖"

    if ! check_command node; then
        log_error "Node.js 未安装"
        return 1
    fi

    cd "$FRONTEND_DIR"
    npm install --legacy-peer-deps
    cd "$SCRIPT_DIR"

    log_success "Node.js 依赖安装完成"
}

start_redis() {
    log_header "启动 Redis"

    if command -v redis-server &> /dev/null; then
        if ! pgrep redis-server > /dev/null; then
            redis-server --daemonize yes --maxmemory 64mb --maxmemory-policy allkeys-lru
            log_success "Redis 已启动"
        else
            log_info "Redis 已在运行"
        fi
    else
        log_warning "Redis 未安装，SQLite 模式将自动启用"
    fi
}

start_backend() {
    log_header "启动后端服务"

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        log_error "Python 虚拟环境不存在，请先运行安装步骤"
        return 1
    fi

    source venv/bin/activate

    if [ ! -d "$DATA_DIR/logs" ]; then
        mkdir -p "$DATA_DIR/logs"
    fi

    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$DATA_DIR/logs/backend.log" 2>&1 &
    echo $! > uvicorn.pid

    deactivate
    cd "$SCRIPT_DIR"

    log_success "后端服务已启动 (PID: $(cat $BACKEND_DIR/uvicorn.pid))"
}

start_frontend() {
    log_header "启动前端服务"

    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        log_error "Node.js 依赖未安装，请先运行安装步骤"
        return 1
    fi

    if [ ! -d "$DATA_DIR/logs" ]; then
        mkdir -p "$DATA_DIR/logs"
    fi

    nohup npm run dev > "$DATA_DIR/logs/frontend.log" 2>&1 &
    echo $! > vite.pid

    cd "$SCRIPT_DIR"

    log_success "前端服务已启动 (PID: $(cat $FRONTEND_DIR/vite.pid))"
}

start_docker_mode() {
    log_header "Docker 模式启动"

    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        return 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker 未运行"
        return 1
    fi

    log_info "启动 Redis..."
    docker-compose up -d redis

    sleep 2

    log_info "启动后端..."
    docker-compose up -d backend

    log_info "启动前端..."
    docker-compose up -d frontend

    log_success "Docker 服务启动完成"
}

stop_services() {
    log_header "停止服务"

    if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
        log_info "停止 Docker 容器..."
        docker-compose down 2>/dev/null || true
    fi

    if [ -f "$BACKEND_DIR/uvicorn.pid" ]; then
        kill $(cat "$BACKEND_DIR/uvicorn.pid") 2>/dev/null || true
        rm -f "$BACKEND_DIR/uvicorn.pid"
        log_success "后端已停止"
    fi

    if [ -f "$FRONTEND_DIR/vite.pid" ]; then
        kill $(cat "$FRONTEND_DIR/vite.pid") 2>/dev/null || true
        rm -f "$FRONTEND_DIR/vite.pid"
        log_success "前端已停止"
    fi

    log_success "所有服务已停止"
}

show_status() {
    log_header "服务状态"

    echo ""

    if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
        if docker ps --filter "name=novel-reader" --format "{{.Names}}" | grep -q .; then
            echo "Docker 容器:"
            docker-compose ps
        fi
    fi

    echo ""
    echo -e "${CYAN}[本地服务]${NC}"

    if [ -f "$BACKEND_DIR/uvicorn.pid" ] && kill -0 $(cat "$BACKEND_DIR/uvicorn.pid") 2>/dev/null; then
        log_success "后端: 运行中"
    else
        log_error "后端: 未运行"
    fi

    if [ -f "$FRONTEND_DIR/vite.pid" ] && kill -0 $(cat "$FRONTEND_DIR/vite.pid") 2>/dev/null; then
        log_success "前端: 运行中"
    else
        log_error "前端: 未运行"
    fi

    echo ""

    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        log_success "API: 运行中"
    else
        log_error "API: 未响应"
    fi

    if curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null | grep -qE "^(200|301|302)"; then
        log_success "前端: 运行中"
    else
        log_error "前端: 未响应"
    fi
}

show_help() {
    cat << EOF

Novel Reader - Linux 部署脚本

用法: $0 [command]

命令:
  install     安装所有依赖
  start       启动服务
  stop        停止服务
  restart     重启服务
  status      查看服务状态
  logs        查看日志
  docker      使用 Docker 模式
  mirrors     配置镜像源
  help        显示帮助

示例:
  $0 install     # 安装依赖
  $0 start       # 启动服务
  $0 docker      # Docker 模式启动

访问地址:
  前端: http://localhost
  API:  http://localhost:8000/docs

EOF
}

main() {
    local cmd="${1:-help}"

    echo ""
    echo -e "${MAGENTA}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}  ${CYAN}Novel Reader - Linux 部署脚本${NC}                    ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""

    case "$cmd" in
        install)
            setup_mirrors
            install_system_deps
            create_directories
            create_env_file
            install_python_deps
            install_node_deps
            ;;
        start)
            create_directories
            create_env_file

            if command -v docker &> /dev/null && docker info &> /dev/null 2>&1; then
                start_docker_mode
            else
                start_redis
                start_backend
                start_frontend
            fi

            echo ""
            echo -e "${GREEN}═════════════════════════════════════════════════════${NC}"
            echo -e "${GREEN}  服务已启动!${NC}"
            echo -e "${GREEN}═════════════════════════════════════════════════════${NC}"
            echo ""
            echo -e "  ${GREEN}📖${NC} 前端:  http://localhost"
            echo -e "  ${GREEN}🔧${NC} API:   http://localhost:8000/docs"
            echo ""
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            sleep 2
            $0 start
            ;;
        status)
            show_status
            ;;
        logs)
            if [ -d "$DATA_DIR/logs" ]; then
                tail -f "$DATA_DIR/logs"/*.log 2>/dev/null || echo "暂无日志"
            else
                echo "日志目录不存在"
            fi
            ;;
        docker)
            setup_mirrors
            create_directories
            create_env_file
            start_docker_mode
            ;;
        mirrors)
            setup_mirrors
            ;;
        help|--help|-h|"")
            show_help
            ;;
        *)
            log_error "未知命令: $cmd"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
