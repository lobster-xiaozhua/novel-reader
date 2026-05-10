#!/bin/bash

# Novel Reader 一键启动脚本
# 支持 Linux / macOS / WSL
# 用法: ./start.sh [command]

set -e

PROJECT_NAME="novel-reader"
FRONTEND_DIR="frontend"
BACKEND_DIR="backend"
DATA_DIR="data"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALLED_FILE="$SCRIPT_DIR/.installed"

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
print_step() { echo -e "${CYAN}[→]${NC} $1"; }

print_banner() {
    echo ""
    echo -e "${MAGENTA}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}  ${CYAN}Novel Reader - 一键启动${NC}                        ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╚═══════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 未安装"
        return 1
    fi
    return 0
}

check_node() {
    if ! command -v node &> /dev/null; then
        print_error "Node.js 未安装"
        print_info "请访问 https://nodejs.org/ 下载安装"
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
    print_step "配置镜像源..."

    REGION=$(detect_region)

    if [ "$REGION" = "china" ]; then
        print_info "检测到中国地区，配置国内镜像..."

        mkdir -p ~/.pip
        cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 60
[install]
trusted-host = mirrors.aliyun.com
EOF
        print_success "pip: 阿里云镜像"

        npm config set registry https://registry.npmmirror.com 2>/dev/null || true
        print_success "npm: npmmirror.com"

        mkdir -p ~/.docker
        cat > ~/.docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
EOF
        print_success "Docker: 镜像加速已配置"
    else
        print_info "使用官方源"
    fi
}

create_directories() {
    mkdir -p "$DATA_DIR"/{books,index,static,logs,cache,backups,versions}
}

check_env() {
    if [ ! -f ".env" ]; then
        print_info "创建环境配置文件..."
        cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://localhost:6379
EOF
        print_success ".env 已创建"
    fi
}

install_python_deps() {
    print_step "安装 Python 依赖..."

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi

    source venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    deactivate
    cd ..
    print_success "Python 依赖安装完成"
}

install_node_deps() {
    print_step "安装 Node.js 依赖..."

    cd "$FRONTEND_DIR"
    npm install
    cd ..
    print_success "Node.js 依赖安装完成"
}

setup_global() {
    print_step "配置全局命令..."

    local bin_dir="/usr/local/bin"
    local installed=false

    if [ -w "$bin_dir" ] || sudo ls "$bin_dir" &>/dev/null; then
        if [ -f "$SCRIPT_DIR/readweb" ]; then
            sudo ln -sf "$SCRIPT_DIR/readweb" "$bin_dir/readweb" 2>/dev/null || \
            ln -sf "$SCRIPT_DIR/readweb" "$bin_dir/readweb" 2>/dev/null || true
            print_success "readweb 已安装到 PATH"
            installed=true
        fi

        if [ -f "$SCRIPT_DIR/update.sh" ]; then
            sudo ln -sf "$SCRIPT_DIR/update.sh" "$bin_dir/update.sh" 2>/dev/null || \
            ln -sf "$SCRIPT_DIR/update.sh" "$bin_dir/update.sh" 2>/dev/null || true
            print_success "update.sh 已安装到 PATH"
            installed=true
        fi

        if [ "$installed" = true ]; then
            echo "$PROJECT_NAME" > "$INSTALLED_FILE"
            echo ""
            print_success "全局命令配置完成!"
            echo -e "${YELLOW}以后可直接使用:${NC}"
            echo "  readweb start    # 启动项目"
            echo "  readweb update   # 更新项目"
            echo "  readweb help     # 查看帮助"
            echo ""
        fi
    else
        print_warning "无法写入 $bin_dir，跳过全局安装"
        print_info "可手动运行: sudo ln -s $SCRIPT_DIR/readweb $bin_dir/"
    fi
}

first_run_setup() {
    if [ ! -f "$INSTALLED_FILE" ]; then
        print_banner
        echo -e "${CYAN}首次运行检测到，自动配置环境...${NC}"
        echo ""

        setup_mirrors
        create_directories
        check_env

        echo ""
        print_step "安装依赖..."
        install_python_deps
        install_node_deps

        echo ""

        if command -v docker &> /dev/null && docker info &> /dev/null; then
            print_info "检测到 Docker，可使用 ./start.sh 启动"
        else
            print_info "检测到本地模式，配置 readweb..."
            setup_global
        fi

        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  环境配置完成!${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${YELLOW}下一步:${NC}"
        echo "  ./start.sh          # 启动项目"
        echo "  ./readweb start     # 或使用 readweb"
        echo ""
        return 0
    fi
    return 1
}

start_backend() {
    if command -v docker &> /dev/null && docker info &> /dev/null; then
        print_step "启动 Docker 服务..."
        docker-compose up -d redis
        sleep 2
        docker-compose up -d backend
    else
        print_step "启动本地后端服务..."
        cd "$BACKEND_DIR"
        if [ ! -d "venv" ]; then
            python3 -m venv venv
        fi
        source venv/bin/activate
        nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > ../data/logs/backend.log 2>&1 &
        echo $! > uvicorn.pid
        deactivate
        cd ..
    fi

    print_step "等待服务就绪..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            print_success "后端服务已就绪"
            return 0
        fi
        sleep 1
    done
    print_warning "后端启动较慢，请稍后检查"
}

start_frontend() {
    if command -v docker &> /dev/null && docker info &> /dev/null; then
        if [ ! -d "$FRONTEND_DIR/dist" ]; then
            print_step "构建前端..."
            cd "$FRONTEND_DIR"
            npm run build
            cd ..
        fi
        docker-compose up -d frontend
    else
        print_step "启动前端服务..."
        cd "$FRONTEND_DIR"
        npm run dev > ../data/logs/frontend.log 2>&1 &
        echo $! > vite.pid
        cd ..
    fi
    print_success "前端服务已启动"
}

stop_services() {
    print_step "停止服务..."

    if command -v docker &> /dev/null && docker info &> /dev/null; then
        docker-compose down 2>/dev/null || true
    else
        [ -f "$BACKEND_DIR/uvicorn.pid" ] && kill $(cat "$BACKEND_DIR/uvicorn.pid") 2>/dev/null || true
        [ -f "$FRONTEND_DIR/vite.pid" ] && kill $(cat "$FRONTEND_DIR/vite.pid") 2>/dev/null || true
        rm -f "$BACKEND_DIR/uvicorn.pid" "$FRONTEND_DIR/vite.pid"
    fi
    print_success "服务已停止"
}

show_status() {
    print_step "服务状态"
    echo ""

    if command -v docker &> /dev/null && docker info &> /dev/null; then
        docker-compose ps
    else
        echo -e "${CYAN}[Local 模式]${NC}"

        [ -f "$BACKEND_DIR/uvicorn.pid" ] && kill -0 $(cat "$BACKEND_DIR/uvicorn.pid") 2>/dev/null && \
            print_success "后端: 运行中" || print_error "后端: 未运行"

        [ -f "$FRONTEND_DIR/vite.pid" ] && kill -0 $(cat "$FRONTEND_DIR/vite.pid") 2>/dev/null && \
            print_success "前端: 运行中" || print_error "前端: 未运行"
    fi

    echo ""
    curl -s http://localhost:8000/api/health > /dev/null 2>&1 && \
        print_success "API: 运行中" || print_error "API: 未响应"

    curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null | grep -q "200" && \
        print_success "前端: 运行中" || print_error "前端: 未响应"
}

show_help() {
    print_banner
    cat << EOF
用法: ./start.sh [command]

命令:
  start      启动项目
  stop       停止服务
  restart    重启服务
  status     查看状态
  logs       查看日志
  deps       安装依赖
  mirror     配置镜像
  global     配置全局命令
  help       显示帮助

示例:
  ./start.sh          # 首次启动
  ./start.sh deps     # 安装依赖
  ./start.sh global   # 配置全局命令

全局命令 (配置后可用):
  readweb start       # 启动项目
  readweb update      # 更新项目
  readweb status      # 查看状态
EOF
}

case "${1:-}" in
    start)
        first_run_setup || true
        create_directories
        check_env
        start_backend
        start_frontend
        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  项目已启动!${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
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
        sleep 1
        ./start.sh start
        ;;
    status)
        show_status
        ;;
    logs)
        tail -f data/logs/*.log 2>/dev/null || docker-compose logs -f
        ;;
    deps)
        setup_mirrors
        install_python_deps
        install_node_deps
        ;;
    mirror)
        setup_mirrors
        ;;
    global)
        setup_global
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
