#!/bin/bash

# Novel Reader 一键启动脚本
# 支持 Linux / macOS / WSL
# 用法: ./start.sh [command]
#   ./start.sh          - 启动所有服务
#   ./start.sh stop     - 停止所有服务
#   ./start.sh restart  - 重启所有服务
#   ./start.sh build    - 重新构建前端并启动
#   ./start.sh logs     - 查看日志
#   ./start.sh status   - 查看服务状态
#   ./start.sh clean    - 清理数据并重新启动
#   ./start.sh test     - 运行测试

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目配置
PROJECT_NAME="novel-reader"
FRONTEND_DIR="frontend"
BACKEND_DIR="backend"
DATA_DIR="data"

# 打印带颜色的信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 未安装，请先安装"
        return 1
    fi
    return 0
}

# 检查 Docker 是否运行
check_docker() {
    if ! docker info &> /dev/null; then
        print_error "Docker 未运行，请先启动 Docker"
        return 1
    fi
    return 0
}

# 检查 Node.js
check_node() {
    if ! command -v node &> /dev/null; then
        print_error "Node.js 未安装"
        print_info "请访问 https://nodejs.org/ 下载安装"
        return 1
    fi
    
    NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 18 ]; then
        print_warning "Node.js 版本过低，建议 18+"
    fi
    return 0
}

# 创建必要目录
create_directories() {
    print_info "创建数据目录..."
    mkdir -p "$DATA_DIR"/{books,index,static,logs,cache}
    print_success "目录创建完成"
}

# 检查环境文件
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

# 启动后端服务
start_backend() {
    print_header "启动后端服务"
    
    if ! check_docker; then
        return 1
    fi
    
    print_info "启动 Docker 容器..."
    docker-compose up -d redis
    
    # 等待 Redis 启动
    print_info "等待 Redis 启动..."
    sleep 3
    
    # 检查后端容器是否已在运行
    if docker-compose ps | grep -q "novel-reader-backend"; then
        print_warning "后端容器已在运行"
    else
        print_info "启动后端容器..."
        docker-compose up -d backend
    fi
    
    # 等待后端启动
    print_info "等待后端服务就绪..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            print_success "后端服务已就绪"
            return 0
        fi
        sleep 1
    done
    
    print_warning "后端服务启动较慢，请稍后检查"
    return 0
}

# 构建前端
build_frontend() {
    print_header "构建前端"
    
    if ! check_node; then
        return 1
    fi
    
    cd "$FRONTEND_DIR"
    
    if [ ! -d "node_modules" ]; then
        print_info "安装前端依赖..."
        npm install
    fi
    
    print_info "构建生产版本..."
    npm run build
    
    cd ..
    print_success "前端构建完成"
}

# 启动前端服务
start_frontend() {
    print_header "启动前端服务"
    
    if ! check_docker; then
        return 1
    fi
    
    # 检查前端构建文件
    if [ ! -d "$FRONTEND_DIR/dist" ] || [ ! -f "$FRONTEND_DIR/dist/index.html" ]; then
        print_warning "前端构建文件不存在，开始构建..."
        build_frontend
    fi
    
    print_info "启动前端容器..."
    docker-compose up -d frontend
    
    print_success "前端服务已启动"
}

# 停止所有服务
stop_services() {
    print_header "停止服务"
    
    if ! check_docker; then
        return 1
    fi
    
    print_info "停止所有容器..."
    docker-compose down
    
    print_success "所有服务已停止"
}

# 查看状态
show_status() {
    print_header "服务状态"
    
    if ! check_docker; then
        return 1
    fi
    
    echo -e "${CYAN}容器状态:${NC}"
    docker-compose ps
    
    echo ""
    echo -e "${CYAN}健康检查:${NC}"
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        print_success "后端 API: 运行中"
    else
        print_error "后端 API: 未响应"
    fi
    
    if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|301\|302"; then
        print_success "前端页面: 运行中"
    else
        print_error "前端页面: 未响应"
    fi
}

# 查看日志
show_logs() {
    print_header "查看日志"
    
    if ! check_docker; then
        return 1
    fi
    
    echo -e "${CYAN}按 Ctrl+C 退出日志查看${NC}"
    docker-compose logs -f
}

# 清理数据
clean_data() {
    print_header "清理数据"
    
    print_warning "此操作将删除所有数据，包括书籍、用户、阅读进度等！"
    read -p "确认继续? (y/N): " confirm
    
    if [[ $confirm =~ ^[Yy]$ ]]; then
        stop_services
        print_info "删除数据目录..."
        rm -rf "$DATA_DIR"
        create_directories
        print_success "数据已清理"
        
        read -p "是否重新启动服务? (Y/n): " restart
        if [[ ! $restart =~ ^[Nn]$ ]]; then
            start_all
        fi
    else
        print_info "操作已取消"
    fi
}

# 运行测试
run_tests() {
    print_header "运行测试"
    
    cd "$BACKEND_DIR"
    
    if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
        print_info "创建虚拟环境..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    
    print_info "安装测试依赖..."
    pip install -q pytest pytest-asyncio httpx
    
    print_info "运行测试..."
    pytest tests/ -v --tb=short
    
    deactivate
    cd ..
}

# 启动所有服务
start_all() {
    print_header "启动 Novel Reader"
    
    # 检查依赖
    check_command docker
    check_command docker-compose
    check_command node
    
    # 初始化
    create_directories
    check_env
    
    # 启动服务
    start_backend
    start_frontend
    
    # 显示访问信息
    print_header "服务已启动"
    echo -e "${GREEN}📖 前端页面:${NC} http://localhost"
    echo -e "${GREEN}🔧 API 文档:${NC} http://localhost:8000/docs"
    echo -e "${GREEN}💓 健康检查:${NC} http://localhost:8000/api/health"
    echo ""
    echo -e "${YELLOW}常用命令:${NC}"
    echo "  ./start.sh stop     - 停止服务"
    echo "  ./start.sh restart  - 重启服务"
    echo "  ./start.sh logs     - 查看日志"
    echo "  ./start.sh status   - 查看状态"
}

# 重启服务
restart_services() {
    print_header "重启服务"
    stop_services
    sleep 2
    start_all
}

# 重新构建并启动
rebuild_all() {
    print_header "重新构建并启动"
    stop_services
    build_frontend
    start_all
}

# 显示帮助
show_help() {
    cat << EOF
Novel Reader 一键启动脚本

用法: ./start.sh [command]

命令:
  (无)      启动所有服务
  stop      停止所有服务
  restart   重启所有服务
  build     重新构建前端并启动
  logs      查看服务日志
  status    查看服务状态
  clean     清理所有数据并重新启动
  test      运行后端测试
  help      显示此帮助信息

示例:
  ./start.sh          # 首次启动
  ./start.sh stop     # 停止服务
  ./start.sh restart  # 重启服务
  ./start.sh logs     # 查看日志

访问地址:
  前端: http://localhost
  API:  http://localhost:8000
  文档: http://localhost:8000/docs
EOF
}

# 主逻辑
case "${1:-}" in
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    build)
        rebuild_all
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    clean)
        clean_data
        ;;
    test)
        run_tests
        ;;
    help|--help|-h)
        show_help
        ;;
    "")
        start_all
        ;;
    *)
        print_error "未知命令: $1"
        show_help
        exit 1
        ;;
esac
