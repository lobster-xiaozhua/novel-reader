#!/bin/bash
# deploy-linux.sh - Linux 部署脚本
# 用于主流 Linux 发行版 (Ubuntu/Debian/CentOS/Fedora/Arch)
# 用法: bash deploy-linux.sh [命令]
#
# 命令:
#   install    安装所有依赖
#   start      启动服务
#   stop       停止服务
#   restart    重启服务
#   status     查看状态
#   update     更新项目
#   help       显示帮助

set -e

PROJECT_NAME="novel-reader"
PROJECT_DIR="${DEPLOY_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
DATA_DIR="$PROJECT_DIR/data"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

detect_linux() {
    if [ "$(uname)" = "Linux" ] && [ -z "$ANDROID_ROOT" ]; then
        return 0
    fi
    return 1
}

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_step() { echo -e "${CYAN}[→]${NC} $1"; }

print_banner() {
    echo ""
    echo -e "${MAGENTA}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}  ${CYAN}Novel Reader - Linux 部署脚本${NC}                ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}  ${CYAN}支持 Ubuntu/Debian/CentOS/Fedora/Arch${NC}        ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╚═══════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_linux() {
    if ! detect_linux; then
        log_error "此脚本仅适用于标准 Linux 环境"
        log_info "在 Linux 上运行: bash deploy-linux.sh"
        exit 1
    fi
    log_info "检测到 Linux 环境: $(uname -sr)"
}

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

setup_pip_mirror() {
    log_step "配置 pip 镜像..."

    local country="global"
    if command -v curl &> /dev/null; then
        country=$(curl -s --max-time 3 "https://ipinfo.io/country" 2>/dev/null || echo "global")
    fi

    if [ "$country" = "CN" ]; then
        mkdir -p "$HOME/.pip"
        cat > "$HOME/.pip/pip.conf" << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 60
[install]
trusted-host = mirrors.aliyun.com
EOF
        log_success "pip 镜像: 阿里云"
    else
        log_info "使用官方 pip 源"
    fi
}

install_system_deps_apt() {
    log_step "安装系统依赖 (APT)..."

    sudo apt-get update -qq

    local packages=(
        python3 python3-pip python3-venv
        git curl wget
        redis-server
        build-essential
    )

    sudo apt-get install -y -qq "${packages[@]}"

    if ! command -v node &> /dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y -qq nodejs
    fi

    log_success "系统依赖安装完成"
}

install_system_deps_yum() {
    log_step "安装系统依赖 (YUM)..."

    local packages=(
        python3 python3-pip python3-venv
        git curl wget
        redis
        gcc gcc-c++
    )

    sudo yum install -y -q "${packages[@]}"

    if ! command -v node &> /dev/null; then
        curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
        sudo yum install -y -q nodejs
    fi

    log_success "系统依赖安装完成"
}

install_system_deps_dnf() {
    log_step "安装系统依赖 (DNF)..."

    local packages=(
        python3 python3-pip python3-venv
        git curl wget
        redis
        gcc gcc-c++ make
    )

    sudo dnf install -y -q "${packages[@]}"

    if ! command -v node &> /dev/null; then
        curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
        sudo dnf install -y -q nodejs
    fi

    log_success "系统依赖安装完成"
}

install_system_deps_pacman() {
    log_step "安装系统依赖 (Pacman)..."

    sudo pacman -Sy --noconfirm

    local packages=(
        python python-pip python-virtualenv
        git curl wget
        redis
        base-devel
    )

    sudo pacman -S --noconfirm "${packages[@]}"

    if ! command -v node &> /dev/null; then
        sudo pacman -S --noconfirm nodejs npm
    fi

    log_success "系统依赖安装完成"
}

install_system_deps() {
    local distro=$(detect_distro)

    case "$distro" in
        ubuntu|debian|linuxmint|pop)
            install_system_deps_apt
            ;;
        centos|rhel|rocky|alma)
            install_system_deps_yum
            ;;
        fedora)
            install_system_deps_dnf
            ;;
        arch|manjaro|endeavouros)
            install_system_deps_pacman
            ;;
        *)
            log_warning "未知发行版，尝试 APT..."
            install_system_deps_apt
            ;;
    esac
}

create_directories() {
    log_step "创建目录结构..."
    mkdir -p "$DATA_DIR"/{books,index,static,logs,cache,backups,versions}
    log_success "目录创建完成"
}

setup_env() {
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        log_info "创建环境配置文件..."
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

        cat > "$PROJECT_DIR/.env" << EOF
SECRET_KEY=$SECRET_KEY
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
        log_success ".env 文件已创建"
    else
        log_info ".env 文件已存在"
    fi
}

install_python_deps() {
    log_step "安装 Python 依赖..."

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        log_info "创建虚拟环境..."
        python3 -m venv venv
    fi

    source venv/bin/activate

    pip install --upgrade pip -q
    pip install -r requirements.txt -q

    deactivate
    cd ..
    log_success "Python 依赖安装完成"
}

install_nodejs_deps() {
    log_step "安装 Node.js 依赖..."

    if ! command -v node &> /dev/null; then
        log_error "Node.js 未安装"
        return 1
    fi

    cd "$FRONTEND_DIR"

    npm config set registry https://registry.npmmirror.com 2>/dev/null || true
    npm install

    cd ..
    log_success "Node.js 依赖安装完成"
}

start_redis() {
    log_step "启动 Redis..."

    if command -v redis-server &> /dev/null; then
        if pgrep -x redis-server > /dev/null 2>&1; then
            log_info "Redis 已在运行"
        else
            mkdir -p "$DATA_DIR/redis"
            if command -v sudo &> /dev/null; then
                sudo redis-server --daemonize yes --dir "$DATA_DIR/redis" --port 6379 2>/dev/null || true
            else
                redis-server --daemonize yes --dir "$DATA_DIR/redis" --port 6379 2>/dev/null || true
            fi
            sleep 1
            if pgrep -x redis-server > /dev/null 2>&1; then
                log_success "Redis 已启动"
            else
                log_warning "Redis 启动失败，继续..."
            fi
        fi
    else
        log_warning "Redis 未安装"
    fi
}

stop_redis() {
    if pgrep -x redis-server > /dev/null 2>&1; then
        if command -v sudo &> /dev/null; then
            sudo pkill -x redis-server 2>/dev/null || true
        else
            pkill -x redis-server 2>/dev/null || true
        fi
        log_info "Redis 已停止"
    fi
}

start_backend() {
    log_step "启动后端服务..."

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        install_python_deps
    fi

    source venv/bin/activate

    if [ -f "uvicorn.pid" ] && kill -0 $(cat uvicorn.pid) 2>/dev/null; then
        log_info "后端已在运行"
    else
        export PYTHONPATH="$PROJECT_DIR/backend"
        export PYTHONDONTWRITEBYTECODE=1
        nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$DATA_DIR/logs/backend.log" 2>&1 &
        echo $! > uvicorn.pid
        log_success "后端已启动 (PID: $(cat uvicorn.pid))"
    fi

    deactivate
    cd ..
}

stop_backend() {
    if [ -f "$BACKEND_DIR/uvicorn.pid" ]; then
        kill $(cat "$BACKEND_DIR/uvicorn.pid") 2>/dev/null || true
        rm -f "$BACKEND_DIR/uvicorn.pid"
        log_info "后端已停止"
    fi
}

start_frontend() {
    log_step "启动前端服务..."

    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        install_nodejs_deps
    fi

    if [ -f "vite.pid" ] && kill -0 $(cat vite.pid) 2>/dev/null; then
        log_info "前端已在运行"
    else
        if [ ! -f "dist/index.html" ]; then
            log_info "构建前端..."
            npm run build
        fi
        nohup npm run dev > "$DATA_DIR/logs/frontend.log" 2>&1 &
        echo $! > vite.pid
        log_success "前端已启动 (PID: $(cat vite.pid))"
    fi

    cd ..
}

stop_frontend() {
    if [ -f "$FRONTEND_DIR/vite.pid" ]; then
        kill $(cat "$FRONTEND_DIR/vite.pid") 2>/dev/null || true
        rm -f "$FRONTEND_DIR/vite.pid"
        log_info "前端已停止"
    fi
}

install_all() {
    print_banner
    check_linux
    setup_pip_mirror
    install_system_deps
    create_directories
    setup_env
    install_python_deps
    install_nodejs_deps
    start_redis

    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  安装完成!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}下一步:${NC}"
    echo "  bash deploy-linux.sh start   # 启动服务"
    echo "  bash deploy-linux.sh status  # 查看状态"
    echo ""
}

cmd_start() {
    print_banner
    log_step "启动 Novel Reader..."

    cd "$PROJECT_DIR"

    create_directories
    setup_env
    start_redis
    start_backend
    start_frontend

    log_info "等待服务就绪..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            log_success "后端服务已就绪"
            break
        fi
        sleep 1
    done

    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  服务已启动!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${GREEN}📖${NC} 前端页面:  http://localhost:5173"
    echo -e "  ${GREEN}🔧${NC} API 文档:   http://localhost:8000/docs"
    echo -e "  ${GREEN}💓${NC} 健康检查:   http://localhost:8000/api/health"
    echo ""
}

cmd_stop() {
    log_step "停止服务..."
    stop_backend
    stop_frontend
    stop_redis
    log_success "所有服务已停止"
}

cmd_restart() {
    cmd_stop
    sleep 2
    cmd_start
}

cmd_status() {
    log_step "服务状态"
    echo ""

    if [ -f "$BACKEND_DIR/uvicorn.pid" ] && kill -0 $(cat "$BACKEND_DIR/uvicorn.pid") 2>/dev/null; then
        log_success "后端服务: 运行中 (PID: $(cat "$BACKEND_DIR/uvicorn.pid"))"
    else
        log_error "后端服务: 未运行"
    fi

    if [ -f "$FRONTEND_DIR/vite.pid" ] && kill -0 $(cat "$FRONTEND_DIR/vite.pid") 2>/dev/null; then
        log_success "前端服务: 运行中 (PID: $(cat "$FRONTEND_DIR/vite.pid"))"
    else
        log_error "前端服务: 未运行"
    fi

    if pgrep -x redis-server > /dev/null 2>&1; then
        log_success "Redis: 运行中"
    else
        log_warning "Redis: 未运行"
    fi

    echo ""
    log_info "健康检查:"
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        log_success "后端 API: 运行中"
    else
        log_error "后端 API: 未响应"
    fi
}

show_help() {
    print_banner
    cat << EOF
用法: bash deploy-linux.sh <command>

命令:
  ${GREEN}install${NC}    安装所有依赖（首次运行）
  ${GREEN}start${NC}       启动服务
  ${GREEN}stop${NC}        停止服务
  ${GREEN}restart${NC}     重启服务
  ${GREEN}status${NC}      查看服务状态
  ${GREEN}update${NC}      更新项目
  ${GREEN}help${NC}        显示此帮助

支持的发行版:
  - Ubuntu / Debian / Linux Mint
  - CentOS / RHEL / Rocky Linux / AlmaLinux
  - Fedora
  - Arch Linux / Manjaro / EndeavourOS

环境要求:
  - Linux (x86_64/arm64)
  - Python 3.11+
  - Node.js 18+
  - Redis 6.0+

更多信息: https://github.com/lobster-xiaozhua/novel-reader
EOF
}

main() {
    local command="${1:-}"

    case "$command" in
        install) install_all ;;
        start) cmd_start ;;
        stop) cmd_stop ;;
        restart) cmd_restart ;;
        status) cmd_status ;;
        update)
            log_step "更新项目..."
            cd "$PROJECT_DIR"
            if [ -d ".git" ]; then
                git pull origin main
                install_python_deps
                cmd_restart
            else
                log_error "不是 git 仓库"
                exit 1
            fi
            ;;
        help|--help|-h|"") show_help ;;
        *) log_error "未知命令: $command"; show_help; exit 1 ;;
    esac
}

main "$@"