#!/bin/bash
# Novel Reader 跨平台部署脚本 - Linux
# 支持: Ubuntu/Debian/CentOS/Fedora/Arch
# 用法: ./deploy-linux.sh [command]

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

check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

get_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif [ -f /etc/arch-release ]; then
        echo "arch"
    elif [ -f /etc/redhat-release ]; then
        echo "rhel"
    else
        echo "unknown"
    fi
}

get_region() {
    if command -v curl &> /dev/null; then
        COUNTRY=$(curl -s --max-time 3 "https://ipinfo.io/country" 2>/dev/null || echo "unknown")
        if [ "$COUNTRY" = "CN" ]; then
            echo "china"
            return
        fi
    fi
    echo "global"
}

install_system_deps() {
    header "安装系统依赖"
    local distro=$(get_distro)
    case "$distro" in
        ubuntu|debian|linuxmint|pop)
            info "检测到 Debian/Ubuntu 系统"
            if check_command apt-get; then
                sudo apt-get update -qq
                sudo apt-get install -y python3 python3-venv python3-pip
                if ! check_command node; then
                    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
                    sudo apt-get install -y nodejs
                fi
                sudo apt-get install -y redis-server build-essential curl file git
            fi
            ;;
        fedora|rhel|centos|rocky|alma)
            info "检测到 RHEL/Fedora 系统"
            if check_command dnf; then
                sudo dnf install -y python3 python3-pip nodejs npm redis
            elif check_command yum; then
                sudo yum install -y python3 python3-pip nodejs npm redis
            fi
            ;;
        arch|manjaro)
            info "检测到 Arch Linux 系统"
            if check_command pacman; then
                sudo pacman -Sy --noconfirm python python-pip nodejs npm redis base-devel
            fi
            ;;
        alpine)
            info "检测到 Alpine Linux 系统"
            if check_command apk; then
                sudo apk add python3 py3-pip nodejs npm redis build-base
            fi
            ;;
        *)
            warning "无法识别 Linux 发行版: $distro"
            info "请手动安装: Python 3.8+, Node.js 16+, Redis"
            ;;
    esac
    success "系统依赖安装完成"
}

set_pip_mirror() {
    local region=$(get_region)
    if [ "$region" = "china" ]; then
        info "配置 pip 镜像源 (阿里云)..."
        mkdir -p ~/.pip
        cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 120
trusted-host = mirrors.aliyun.com
EOF
        success "pip 镜像配置完成"
    fi
}

set_npm_mirror() {
    local region=$(get_region)
    if [ "$region" = "china" ]; then
        info "配置 npm 镜像源..."
        npm config set registry https://registry.npmmirror.com
        success "npm 镜像配置完成"
    fi
}

install_python_deps() {
    header "安装 Python 依赖"
    if ! check_command python3 && ! check_command python; then
        error "Python 未安装"
        return 1
    fi
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        error "requirements.txt 不存在"
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
    info "安装 npm 包..."
    npm install
    cd "$SCRIPT_DIR"
    success "Node.js 依赖安装完成"
}

install_redis() {
    header "安装 Redis"
    local distro=$(get_distro)
    if check_command docker && docker info &> /dev/null; then
        info "使用 Docker 安装 Redis..."
        if ! docker ps -a | grep -q novel-reader-redis; then
            docker pull redis:7-alpine
            docker run -d --name novel-reader-redis -p 6379:6379 redis:7-alpine redis-server --appendonly yes --maxmemory 64mb --maxmemory-policy allkeys-lru
        fi
        success "Redis (Docker) 安装完成"
        return 0
    fi
    case "$distro" in
        ubuntu|debian|linuxmint|pop)
            sudo apt-get update -qq && sudo apt-get install -y redis-server
            ;;
        fedora|rhel|centos)
            if check_command dnf; then sudo dnf install -y redis; fi
            ;;
        arch|manjaro)
            if check_command pacman; then sudo pacman -Sy --noconfirm redis; fi
            ;;
    esac
    if check_command redis-server; then
        redis-server --daemonize yes --maxmemory 64mb --maxmemory-policy allkeys-lru
        success "Redis 安装完成"
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
        local secret_key=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
        cat > "$env_file" << EOF
SECRET_KEY=$secret_key
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://localhost:6379
EOF
        success ".env 文件已创建"
    fi
}

install_all() {
    header "完整安装"
    install_system_deps
    install_redis
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
    info "启动后端..."
    cd "$BACKEND_DIR"
    if [ ! -d "venv" ]; then python3 -m venv venv; fi
    source venv/bin/activate
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../data/logs/backend.log 2>&1 &
    echo $! > uvicorn.pid
    deactivate
    cd "$SCRIPT_DIR"
    info "启动前端..."
    cd "$FRONTEND_DIR"
    nohup npm run dev > ../data/logs/frontend.log 2>&1 &
    echo $! > vite.pid
    cd "$SCRIPT_DIR"
    success "服务已启动"
    echo ""
    echo -e "  访问地址:"
    echo "  前端: http://localhost"
    echo "  API:  http://localhost:8000/docs"
}

start_docker() {
    header "启动服务 (Docker 模式)"
    if ! check_command docker || ! docker info &> /dev/null; then
        error "Docker 未安装或未运行"
        return 1
    fi
    cd "$SCRIPT_DIR"
    docker-compose up -d
    sleep 5
    success "Docker 服务已启动"
    echo ""
    echo "  前端: http://localhost"
    echo "  API:  http://localhost:8000/docs"
}

stop_docker() {
    header "停止 Docker 服务"
    cd "$SCRIPT_DIR"
    docker-compose down
    success "Docker 服务已停止"
}

show_status() {
    header "服务状态"
    if check_command docker && docker info &> /dev/null; then
        docker-compose ps
    fi
    echo ""
    curl -s http://localhost:8000/api/health > /dev/null 2>&1 && success "后端 API: 运行中" || error "后端 API: 未响应"
    curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null | grep -q "200" && success "前端页面: 运行中" || error "前端页面: 未响应"
}

show_help() {
    cat << EOF
Novel Reader 跨平台部署脚本 (Linux)

用法: ./deploy-linux.sh [command]

命令:
  install       完整安装所有依赖
  python        仅安装 Python 依赖
  node          仅安装 Node.js 依赖
  redis         安装 Redis
  start         启动服务 (本地模式)
  docker        启动服务 (Docker 模式)
  stop          停止 Docker 服务
  status        查看服务状态
  mirror        配置镜像源
  help          显示此帮助信息

示例:
  ./deploy-linux.sh install    # 完整安装
  ./deploy-linux.sh start      # 启动本地服务
  ./deploy-linux.sh docker     # Docker 模式

支持的发行版:
  - Ubuntu / Debian / Linux Mint
  - Fedora / RHEL / CentOS / Rocky
  - Arch Linux / Manjaro
  - Alpine Linux

自动检测:
  - 中国大陆自动使用阿里云/清华镜像
  - 所有 Python 包使用纯 Python 版本，无需编译
EOF
}

case "${1:-}" in
    install) install_all ;;
    python) install_python_deps ;;
    node) install_node_deps ;;
    redis) install_redis ;;
    start) start_local ;;
    docker) start_docker ;;
    stop) stop_docker ;;
    status) show_status ;;
    mirror) set_pip_mirror; set_npm_mirror ;;
    help|--help|-h|"") show_help ;;
    *) error "未知命令: $1"; show_help; exit 1 ;;
esac
