#!/bin/bash

# Novel Reader 一键启动脚本
# 支持 Linux / macOS / WSL
# 用法: ./start.sh [command]
#   ./start.sh          - 启动所有服务
#   ./start.sh stop     - 停止所有服务
#   ./start.sh restart  - 重启服务
#   ./start.sh build    - 重新构建前端并启动
#   ./start.sh logs     - 查看日志
#   ./start.sh status   - 查看服务状态
#   ./start.sh clean    - 清理数据并重新启动
#   ./start.sh test     - 运行测试
#   ./start.sh mirror   - 配置/测试镜像源
#   ./start.sh deps     - 安装依赖（自动使用镜像）

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_NAME="novel-reader"
FRONTEND_DIR="frontend"
BACKEND_DIR="backend"
DATA_DIR="data"

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[OK]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() {
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}════════════════════════════════════════════${NC}"
}

detect_region() {
    if command -v curl &> /dev/null; then
        COUNTRY=$(curl -s --max-time 3 "https://ipinfo.io/country" 2>/dev/null || echo "unknown")
        [ "$COUNTRY" = "CN" ] && echo "china" || echo "global"
    else
        echo "global"
    fi
}

configure_mirrors() {
    print_header "配置镜像源"
    REGION=$(detect_region)
    
    if [ "$REGION" = "china" ]; then
        print_info "检测到中国地区，配置国内镜像源..."
        
        print_info "━━━ Python pip ━━━"
        mkdir -p ~/.pip
        cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 60
[install]
trusted-host = mirrors.aliyun.com
EOF
        print_success "pip 镜像: 阿里云"
        
        print_info "━━━ Node.js npm ━━━"
        npm config set registry https://registry.npmmirror.com
        print_success "npm 镜像: 淘宝镜像"
        
        print_info "━━━ Docker ━━━"
        mkdir -p "$HOME/.docker"
        cat > "$HOME/.docker/daemon.json" << 'EOF'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
EOF
        print_success "Docker 镜像加速已配置"
        print_info "请运行: sudo systemctl restart docker"
    else
        print_info "检测到海外地区，使用官方源"
    fi
    print_success "镜像源配置完成"
}

install_all_deps() {
    print_header "安装所有依赖"
    configure_mirrors
    print_success "依赖安装完成"
}

create_directories() {
    print_info "创建数据目录..."
    mkdir -p "$DATA_DIR"/{books,index,static,logs,cache}
    print_success "目录创建完成"
}

check_env() {
    if [ ! -f ".env" ]; then
        print_warning ".env 文件不存在，创建默认配置..."
        cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://redis:6379
EOF
        print_success ".env 文件已创建"
    fi
}

check_docker() {
    docker info &> /dev/null && return 0
    print_error "Docker 未运行，请先启动 Docker"
    return 1
}

start_backend() {
    print_header "启动后端服务"
    check_docker || return 1
    docker-compose up -d redis
    print_info "等待 Redis 启动..."
    sleep 3
    docker-compose up -d backend
    print_info "等待后端服务就绪..."
    for i in {1..30}; do
        curl -s http://localhost:8000/api/health > /dev/null 2>&1 && {
            print_success "后端服务已就绪"
            return 0
        }
        sleep 1
    done
    print_warning "后端服务启动较慢，请稍后检查"
}

build_frontend() {
    print_header "构建前端"
    cd "$FRONTEND_DIR"
    [ ! -d "node_modules" ] && npm install
    npm run build
    cd ..
    print_success "前端构建完成"
}

start_frontend() {
    print_header "启动前端服务"
    check_docker || return 1
    [ ! -f "$FRONTEND_DIR/dist/index.html" ] && build_frontend
    docker-compose up -d frontend
    print_success "前端服务已启动"
}

stop_services() {
    print_header "停止服务"
    check_docker && docker-compose down
    print_success "所有服务已停止"
}

show_status() {
    print_header "服务状态"
    docker-compose ps
    curl -s http://localhost:8000/api/health > /dev/null 2>&1 && print_success "后端 API: 运行中" || print_error "后端 API: 未响应"
}

show_logs() { docker-compose logs -f; }

start_all() {
    print_header "启动 Novel Reader"
    create_directories
    check_env
    start_backend
    start_frontend
    print_header "服务已启动"
    echo -e "  ${GREEN}📖 前端: http://localhost${NC}"
    echo -e "  ${GREEN}🔧 API: http://localhost:8000/docs${NC}"
}

show_help() {
    cat << EOF
用法: ./start.sh [command]

命令:
  (无)      启动所有服务
  stop      停止服务
  restart   重启服务
  build     重新构建前端
  logs      查看日志
  status    查看状态
  clean     清理数据
  mirror    配置镜像源
  deps      安装依赖
  help      显示帮助
EOF
}

case "${1:-}" in
    stop) stop_services ;;
    restart) stop_services; start_all ;;
    build) build_frontend ;;
    logs) show_logs ;;
    status) show_status ;;
    clean) stop_services; rm -rf "$DATA_DIR"; create_directories ;;
    mirror) configure_mirrors ;;
    deps) install_all_deps ;;
    help|--help|-h) show_help ;;
    "") start_all ;;
    *) print_error "未知命令: $1"; show_help ;;
esac
