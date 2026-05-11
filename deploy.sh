#!/bin/bash

# Novel Reader 跨平台部署脚本 - Linux/macOS
# 支持 apt/yum/dnf/pacman 等包管理器
# 用法:
#   ./deploy.sh              - 交互式菜单
#   ./deploy.sh docker       - Docker 部署
#   ./deploy.sh local        - 本地安装
#   ./deploy.sh termux       - Termux 安装说明
#   ./deploy.sh status       - 查看状态
#   ./deploy.sh uninstall    - 卸载

set -e

PROJECT_NAME="novel-reader"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DATA_DIR="$SCRIPT_DIR/data"
INSTALL_MARKER="$SCRIPT_DIR/.installed"

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
print_err() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() { echo -e "\n${MAGENTA}══════ $1 ══════${NC}"; }

check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_err "$1 未安装"
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
    print_header "配置镜像源"
    REGION=$(detect_region)

    if [ "$REGION" = "china" ]; then
        print_info "检测到中国地区，配置镜像..."

        mkdir -p ~/.pip
        cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 120
[install]
trusted-host = mirrors.aliyun.com
EOF
        print_success "pip: 阿里云镜像"

        if command -v npm &> /dev/null; then
            npm config set registry https://registry.npmmirror.com 2>/dev/null || true
            print_success "npm: npmmirror.com"
        fi

        if command -v docker &> /dev/null; then
            mkdir -p ~/.docker
            cat > ~/.docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
EOF
            print_success "Docker 镜像加速已配置"
        fi
    else
        print_info "使用官方源"
    fi
}

create_dirs() {
    print_info "创建数据目录..."
    mkdir -p "$DATA_DIR"/{books,index,static,logs,cache,backups,versions}
    print_success "目录创建完成"
}

test_env() {
    if [ ! -f ".env" ]; then
        print_info "创建 .env 配置文件..."
        if command -v openssl &> /dev/null; then
            SECRET=$(openssl rand -hex 32)
        else
            SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        fi
        cat > .env << EOF
SECRET_KEY=$SECRET
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
        print_success ".env 已创建"
    fi
}

install_system_deps() {
    print_header "安装系统依赖"

    if command -v apt-get &> /dev/null; then
        print_info "检测到 Debian/Ubuntu"
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv \
            nodejs npm curl git build-essential redis-server
        print_success "系统依赖安装完成 (apt)"
    elif command -v yum &> /dev/null; then
        print_info "检测到 RHEL/CentOS"
        sudo yum install -y python3 python3-pip python3-devel \
            nodejs npm curl git gcc gcc-c++ make redis
        print_success "系统依赖安装完成 (yum)"
    elif command -v dnf &> /dev/null; then
        print_info "检测到 Fedora/DNF"
        sudo dnf install -y python3 python3-pip python3-devel \
            nodejs npm curl git gcc gcc-c++ make redis
        print_success "系统依赖安装完成 (dnf)"
    elif command -v pacman &> /dev/null; then
        print_info "检测到 Arch Linux"
        sudo pacman -Sy --noconfirm python python-pip python-venv \
            nodejs npm base-devel redis
        print_success "系统依赖安装完成 (pacman)"
    else
        print_warn "无法检测包管理器，请手动安装: python3, pip, nodejs, npm, redis"
    fi
}

install_python_deps() {
    print_header "安装 Python 依赖"
    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        print_info "创建 Python 虚拟环境..."
        python3 -m venv venv
    fi

    source venv/bin/activate
    pip install --upgrade pip -q

    if [ -f "requirements-pure-python.txt" ]; then
        pip install -r requirements-pure-python.txt -q
    else
        pip install -r requirements.txt -q
    fi

    deactivate
    cd ..
    print_success "Python 依赖安装完成"
}

install_node_deps() {
    print_header "安装 Node.js 依赖"
    cd "$FRONTEND_DIR"
    npm install
    cd ..
    print_success "Node.js 依赖安装完成"
}

install_redis() {
    print_header "安装 Redis"

    if command -v redis-cli &> /dev/null; then
        print_info "Redis 已安装"
    else
        install_system_deps
    fi

    if command -v systemctl &> /dev/null; then
        sudo systemctl start redis-server 2>/dev/null || \
        sudo systemctl start redis 2>/dev/null || \
        redis-server --daemonize yes 2>/dev/null || true
        print_info "Redis 服务已启动"
    else
        redis-server --daemonize yes 2>/dev/null || true
        print_info "Redis 已启动"
    fi
}

deploy_docker() {
    print_header "Docker 部署"

    if ! check_command "docker"; then
        print_info "请安装 Docker: https://docs.docker.com/get-docker/"
        return 1
    fi

    if ! docker info &> /dev/null; then
        print_err "Docker 未运行"
        return 1
    fi

    if ! check_command "docker-compose"; then
        docker compose version &> /dev/null || {
            print_err "docker-compose 未安装"
            return 1
        }
    fi

    setup_mirrors
    create_dirs
    test_env

    print_info "构建并启动服务..."
    cd "$PROJECT_DIR"
    docker-compose up -d redis
    sleep 3
    docker-compose up -d backend

    if [ -f "$FRONTEND_DIR/dist/index.html" ]; then
        docker-compose up -d frontend
    fi

    print_info "等待服务就绪..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            print_success "后端服务已就绪"
            break
        fi
        sleep 1
    done

    print_success "Docker 部署完成!"
    echo ""
    echo -e "  ${GREEN}前端:${NC} http://localhost"
    echo -e "  ${GREEN}API:${NC}  http://localhost:8000/docs"

    echo "docker" > "$INSTALL_MARKER"
    return 0
}

deploy_local() {
    print_header "本地部署 (Linux/macOS)"

    if ! check_command "python3"; then
        print_err "Python 3 未安装"
        print_info "请安装 Python 3.11+: https://www.python.org/downloads/"
        return 1
    fi

    if ! check_command "node"; then
        print_err "Node.js 未安装"
        print_info "请安装 Node.js: https://nodejs.org/"
        return 1
    fi

    setup_mirrors
    install_system_deps
    install_redis
    create_dirs
    test_env
    install_python_deps
    install_node_deps

    print_success "本地部署完成!"
    echo ""
    echo -e "${YELLOW}启动服务:${NC}"
    echo "  后端: cd $BACKEND_DIR && source venv/bin/activate && uvicorn main:app --reload"
    echo "  前端: cd $FRONTEND_DIR && npm run dev"
    echo ""
    echo -e "${YELLOW}或使用一键启动:${NC} ./start.sh"

    echo "local" > "$INSTALL_MARKER"
    return 0
}

deploy_termux_info() {
    print_header "Termux 部署说明 (Android)"
    echo ""
    echo -e "${CYAN}请在 Termux 中运行以下命令:${NC}"
    echo ""
    echo "  # 首次安装 Termux 后
  pkg update && pkg upgrade
  pkg install python nodejs-lts git
"
    echo "  # 进入项目目录并运行
  cd /sdcard/novel-reader
  ./deploy-termux.sh
"
    echo ""
    echo -e "${YELLOW}或者直接在 Termux 中:${NC}"
    echo "  git clone https://github.com/lobster-xiaozhua/novel-reader.git
  cd novel-reader
  ./deploy-termux.sh
"
    echo ""
    print_info "详细说明请查看: docs/DEPLOYMENT.md"
}

show_status() {
    print_header "服务状态"

    if command -v docker &> /dev/null && docker info &> /dev/null; then
        echo -e "${CYAN}Docker 容器:${NC}"
        cd "$PROJECT_DIR"
        docker-compose ps 2>/dev/null || echo "  未找到容器"
    fi

    echo ""
    echo -e "${CYAN}健康检查:${NC}"

    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        print_success "后端 API: 运行中"
    else
        print_err "后端 API: 未响应"
    fi

    if curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null | grep -qE "^(200|301|302)"; then
        print_success "前端页面: 运行中"
    else
        print_err "前端页面: 未响应"
    fi

    if command -v redis-cli &> /dev/null; then
        if redis-cli ping > /dev/null 2>&1; then
            print_success "Redis: 运行中"
        else
            print_warn "Redis: 未运行"
        fi
    fi
}

stop_services() {
    print_header "停止服务"

    if command -v docker &> /dev/null && docker info &> /dev/null; then
        cd "$PROJECT_DIR"
        docker-compose down 2>/dev/null && print_success "Docker 服务已停止"
    fi

    pkill -f "uvicorn main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    print_success "本地服务已停止"
}

uninstall() {
    print_header "卸载"
    print_warn "此操作将删除虚拟环境和安装标记!"

    stop_services

    if [ -d "$BACKEND_DIR/venv" ]; then
        rm -rf "$BACKEND_DIR/venv"
        print_success "已删除虚拟环境"
    fi

    if [ -f "$INSTALL_MARKER" ]; then
        rm -f "$INSTALL_MARKER"
        print_success "已删除安装标记"
    fi

    print_success "卸载完成"
}

show_menu() {
    echo ""
    echo -e "${MAGENTA}════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}  Novel Reader - 跨平台部署工具${NC}"
    echo -e "${MAGENTA}════════════════════════════════════════════${NC}"
    echo ""
    echo "1. Docker 部署              (推荐，有 Docker 的用户)"
    echo "2. 本地安装                 (无 Docker)"
    echo "3. Termux 部署说明          (Android)"
    echo ""
    echo "s. 查看状态"
    echo "m. 配置镜像源"
    echo "u. 卸载"
    echo "q. 退出"
    echo ""
    echo -e "${MAGENTA}════════════════════════════════════════════${NC}"
    echo ""
}

show_help() {
    cat << EOF
Novel Reader 跨平台部署脚本 (Linux/macOS)

用法: ./deploy.sh [command]

命令:
  docker      Docker 部署 (推荐)
  local       本地安装
  termux      Termux 部署说明
  status      查看服务状态
  stop        停止服务
  mirror      配置镜像源
  uninstall   卸载
  help        显示帮助

示例:
  ./deploy.sh              # 显示交互式菜单
  ./deploy.sh docker        # Docker 部署
  ./deploy.sh local         # 本地安装
  ./deploy.sh status        # 查看状态

支持平台:
  Linux + Docker
  Linux (本地 Python + Node.js)
  macOS (Docker 或 Homebrew)
  Android + Termux (使用 deploy-termux.sh)
  Windows (使用 deploy.ps1)
EOF
}

case "${1:-}" in
    docker)
        deploy_docker
        ;;
    local)
        deploy_local
        ;;
    termux)
        deploy_termux_info
        ;;
    status)
        show_status
        ;;
    stop)
        stop_services
        ;;
    mirror)
        setup_mirrors
        ;;
    uninstall)
        uninstall
        ;;
    help|--help|-h)
        show_help
        ;;
    "")
        show_menu
        read -p "请选择 (1-3, s, m, u, q): " choice
        case "$choice" in
            1) deploy_docker ;;
            2) deploy_local ;;
            3) deploy_termux_info ;;
            s) show_status ;;
            m) setup_mirrors ;;
            u) uninstall ;;
            q) exit 0 ;;
        esac
        ;;
    *)
        print_err "未知命令: $1"
        show_help
        exit 1
        ;;
esac
