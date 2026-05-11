#!/bin/bash

# Novel Reader 跨平台部署脚本 (Linux/macOS)
# 支持 apt/yum/dnf/pacman 等包管理器
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
    echo -e "${MAGENTA}║  Novel Reader 跨平台部署 (Linux) v${SCRIPT_VERSION}          ║${NC}"
    echo -e "${MAGENTA}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
}

command_exists() {
    command -v "$1" &> /dev/null
}

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        case "$ID" in
            ubuntu|debian|linuxmint|elementary)
                echo "debian"
                ;;
            fedora|rhel|centos|rocky|alma)
                echo "rhel"
                ;;
            arch|manjaro|endeavouros)
                echo "arch"
                ;;
            opensuse|suse)
                echo "suse"
                ;;
            alpine)
                echo "alpine"
                ;;
            termux)
                echo "termux"
                ;;
            *)
                echo "unknown"
                ;;
        esac
    else
        echo "unknown"
    fi
}

detect_region() {
    if command_exists curl; then
        COUNTRY=$(curl -s --max-time 3 "https://ipinfo.io/country" 2>/dev/null || echo "unknown")
        if [ "$COUNTRY" = "CN" ]; then
            echo "CN"
            return
        fi
    fi
    echo "GLOBAL"
}

set_pip_mirror() {
    print_step "配置 pip 镜像源..."
    mkdir -p ~/.pip
    cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 120

[install]
prefer-binary = true
only-binary = :all:
trusted-host = mirrors.aliyun.com
EOF
    print_success "pip 镜像: 阿里云"
}

set_npm_mirror() {
    print_step "配置 npm 镜像源..."
    npm config set registry https://registry.npmmirror.com 2>/dev/null || true
    npm config set prefix ~/.npm-global 2>/dev/null || true
    print_success "npm 镜像: npmmirror.com"
}

set_docker_mirror() {
    print_step "配置 Docker 镜像加速..."
    mkdir -p ~/.docker
    cat > ~/.docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ],
  "builder": {
    "gc": {
      "enabled": true,
      "defaultKeepStorage": "20GB"
    }
  }
}
EOF
    print_success "Docker 镜像加速已配置"
}

install_system_deps_debian() {
    print_step "安装系统依赖 (Debian/Ubuntu)..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
        python3 python3-venv python3-pip \
        nodejs npm \
        libmagic1 \
        git curl wget
    print_success "系统依赖安装完成"
}

install_system_deps_rhel() {
    print_step "安装系统依赖 (RHEL/CentOS)..."
    if command_exists dnf; then
        sudo dnf install -y \
            python3 python3-pip \
            nodejs npm \
            file-devel \
            git curl wget
    else
        sudo yum install -y \
            python3 python3-pip \
            nodejs npm \
            file-devel \
            git curl wget
    fi
    print_success "系统依赖安装完成"
}

install_system_deps_arch() {
    print_step "安装系统依赖 (Arch/Manjaro)..."
    sudo pacman -Sy --noconfirm \
        python python-pip \
        nodejs npm \
        libmagic \
        git curl wget
    print_success "系统依赖安装完成"
}

install_system_deps_suse() {
    print_step "安装系统依赖 (openSUSE)..."
    sudo zypper install -y \
        python3 python3-pip \
        nodejs npm \
        file-devel \
        git curl wget
    print_success "系统依赖安装完成"
}

install_system_deps_alpine() {
    print_step "安装系统依赖 (Alpine)..."
    apk add --no-cache \
        python3 py3-pip \
        nodejs npm \
        libmagic \
        git curl wget
    print_success "系统依赖安装完成"
}

install_system_deps() {
    local os_type=$(detect_os)

    case "$os_type" in
        debian)
            install_system_deps_debian
            ;;
        rhel)
            install_system_deps_rhel
            ;;
        arch)
            install_system_deps_arch
            ;;
        suse)
            install_system_deps_suse
            ;;
        alpine)
            install_system_deps_alpine
            ;;
        termux)
            print_info "Termux 环境，使用 pkg 安装依赖..."
            ;;
        *)
            print_warn "无法检测操作系统，请手动安装依赖"
            print_info "需要: python3, nodejs, npm, libmagic, git"
            ;;
    esac
}

init_directories() {
    print_step "初始化项目目录..."
    mkdir -p "$DATA_DIR"/{books,index,static,logs,cache,backups,versions}
    print_success "目录创建完成"
}

init_env_file() {
    print_step "检查 .env 文件..."
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        local secret_key
        if command_exists python3; then
            secret_key=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "changeme")
        else
            secret_key="changeme"
        fi
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

install_python_deps() {
    print_step "安装 Python 依赖..."

    if ! command_exists python3; then
        print_error "Python3 未安装"
        return 1
    fi

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        print_info "创建虚拟环境..."
        python3 -m venv venv
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

    if ! command_exists node; then
        print_error "Node.js 未安装"
        return 1
    fi

    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        print_info "安装 npm 包..."
        npm install --legacy-peer-deps
    fi

    cd ..
    print_success "Node.js 依赖安装完成"
}

start_docker_stack() {
    print_step "启动 Docker 服务..."

    if ! command_exists docker; then
        print_error "Docker 未安装"
        return 1
    fi

    if ! docker info &>/dev/null; then
        print_error "Docker 未运行，请启动 Docker"
        return 1
    fi

    init_directories
    init_env_file

    print_info "启动 Redis..."
    docker-compose up -d redis
    sleep 3

    print_info "启动后端..."
    docker-compose up -d backend

    print_info "等待后端就绪..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/api/health &>/dev/null; then
            print_success "后端服务已就绪"
            break
        fi
        sleep 1
    done

    print_info "启动前端..."
    if [ ! -f "$FRONTEND_DIR/dist/index.html" ]; then
        print_info "构建前端..."
        cd "$FRONTEND_DIR"
        [ ! -d "node_modules" ] && npm install --legacy-peer-deps
        npm run build
        cd ..
    fi
    docker-compose up -d frontend

    print_success "所有服务已启动"
}

stop_docker_stack() {
    print_step "停止 Docker 服务..."
    docker-compose down 2>/dev/null || true
    print_success "服务已停止"
}

show_docker_status() {
    print_banner
    print_step "服务状态"
    echo ""

    if ! docker info &>/dev/null; then
        print_warn "Docker 未运行"
        return
    fi

    docker-compose ps

    echo ""
    print_step "健康检查:"

    if curl -s http://localhost:8000/api/health &>/dev/null; then
        print_success "后端 API: 运行中"
    else
        print_error "后端 API: 未响应"
    fi

    if curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null | grep -qE "^(200|301|302)"; then
        print_success "前端页面: 运行中"
    else
        print_error "前端页面: 未响应"
    fi
}

show_docker_logs() {
    print_step "查看日志 (Ctrl+C 退出)"
    docker-compose logs -f
}

start_local() {
    print_step "启动本地服务..."

    init_directories
    init_env_file

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        print_info "创建虚拟环境..."
        python3 -m venv venv
    fi

    source venv/bin/activate

    mkdir -p "$DATA_DIR/logs"

    print_info "启动 uvicorn..."
    nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 \
        > "$DATA_DIR/logs/backend.log" 2>&1 &
    echo $! > uvicorn.pid

    deactivate
    cd ..

    print_success "后端服务已启动"

    print_step "启动前端..."
    cd "$FRONTEND_DIR"
    nohup npm run dev > "$DATA_DIR/logs/frontend.log" 2>&1 &
    echo $! > vite.pid
    cd ..

    print_success "前端服务已启动"
}

stop_local() {
    print_step "停止本地服务..."

    if [ -f "$BACKEND_DIR/uvicorn.pid" ]; then
        kill $(cat "$BACKEND_DIR/uvicorn.pid") 2>/dev/null || true
        rm -f "$BACKEND_DIR/uvicorn.pid"
    fi

    if [ -f "$FRONTEND_DIR/vite.pid" ]; then
        kill $(cat "$FRONTEND_DIR/vite.pid") 2>/dev/null || true
        rm -f "$FRONTEND_DIR/vite.pid"
    fi

    print_success "本地服务已停止"
}

show_local_status() {
    print_banner
    print_step "本地服务状态"
    echo ""

    if [ -f "$BACKEND_DIR/uvicorn.pid" ] && kill -0 $(cat "$BACKEND_DIR/uvicorn.pid") 2>/dev/null; then
        print_success "后端: 运行中 (PID: $(cat $BACKEND_DIR/uvicorn.pid))"
    else
        print_error "后端: 未运行"
    fi

    if [ -f "$FRONTEND_DIR/vite.pid" ] && kill -0 $(cat "$FRONTEND_DIR/vite.pid") 2>/dev/null; then
        print_success "前端: 运行中 (PID: $(cat $FRONTEND_DIR/vite.pid))"
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
}

show_help() {
    print_banner
    cat << EOF
用法: ./deploy.sh [command]

命令:
  install     安装所有依赖
  start       启动服务 (Docker 或本地)
  stop        停止服务
  restart     重启服务
  status      查看服务状态
  logs        查看服务日志
  deps        仅安装依赖
  system      仅安装系统依赖
  help        显示帮助

示例:
  ./deploy.sh              # 交互式启动
  ./deploy.sh install      # 安装依赖
  ./deploy.sh start        # 启动服务
  ./deploy.sh status       # 查看状态

环境要求:
  - Docker (可选，推荐)
  - Python 3.10+
  - Node.js 18+
  - libmagic (Linux)

文档: https://github.com/lobster-xiaozhua/novel-reader
EOF
}

case "${1:-}" in
    install)
        print_banner
        local region=$(detect_region)
        if [ "$region" = "CN" ]; then
            set_pip_mirror
            set_npm_mirror
        fi
        install_system_deps
        init_directories
        init_env_file
        install_python_deps
        install_node_deps
        print_success "安装完成!"
        ;;
    start)
        print_banner
        if command_exists docker && docker info &>/dev/null; then
            start_docker_stack
        else
            print_warn "Docker 未运行，使用本地模式"
            start_local
        fi
        ;;
    stop)
        print_banner
        if command_exists docker && docker info &>/dev/null; then
            stop_docker_stack
        else
            stop_local
        fi
        ;;
    restart)
        print_banner
        if command_exists docker && docker info &>/dev/null; then
            stop_docker_stack
            sleep 2
            start_docker_stack
        else
            stop_local
            sleep 1
            start_local
        fi
        ;;
    status)
        if command_exists docker && docker info &>/dev/null; then
            show_docker_status
        else
            show_local_status
        fi
        ;;
    logs)
        if command_exists docker && docker info &>/dev/null; then
            show_docker_logs
        else
            tail -f "$DATA_DIR/logs"/*.log 2>/dev/null || print_warn "没有日志文件"
        fi
        ;;
    deps)
        print_banner
        local region=$(detect_region)
        if [ "$region" = "CN" ]; then
            set_pip_mirror
            set_npm_mirror
        fi
        init_directories
        install_python_deps
        install_node_deps
        ;;
    system)
        print_banner
        install_system_deps
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
