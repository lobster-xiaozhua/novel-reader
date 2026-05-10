#!/bin/bash

set -e

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
MODE=""

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[OK]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 未安装，请先安装"
        return 1
    fi
    return 0
}

check_docker() {
    if ! docker info &> /dev/null; then
        print_error "Docker 未运行，请先启动 Docker"
        return 1
    fi
    return 0
}

check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Python 3 未安装，请先安装 Python 3.10+"
        return 1
    fi

    PY_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d'.' -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d'.' -f2)

    if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
        print_error "Python 版本过低 ($PY_VERSION)，需要 3.10+"
        return 1
    fi

    print_info "Python 版本: $PY_VERSION"
    return 0
}

create_directories() {
    print_info "创建数据目录..."
    mkdir -p "$DATA_DIR"/{books,index,static,logs,cache}
    print_success "目录创建完成"
}

check_env_docker() {
    if [ ! -f ".env" ]; then
        print_warning ".env 文件不存在，创建 Docker 模式默认配置..."
        cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://redis:6379
EOF
        print_success ".env 文件已创建"
    fi
}

check_env_local() {
    if [ ! -f ".env" ]; then
        print_warning ".env 文件不存在，创建本地模式默认配置..."
        cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=true
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://localhost:6379
EOF
        print_success ".env 文件已创建"
    else
        if grep -q "redis://redis:6379" .env 2>/dev/null; then
            print_warning "检测到 .env 中 REDIS_URL 为 Docker 内部地址 (redis://redis:6379)"
            print_info "本地模式需要使用 redis://localhost:6379"
            read -p "是否自动修改? (Y/n): " confirm
            if [[ ! $confirm =~ ^[Nn]$ ]]; then
                sed -i 's|redis://redis:6379|redis://localhost:6379|g' .env
                print_success "REDIS_URL 已修改为本地地址"
            fi
        fi
    fi
}

start_backend_docker() {
    print_header "启动后端服务 (Docker)"

    if ! check_docker; then return 1; fi

    print_info "启动 Docker 容器..."
    docker-compose up -d redis

    print_info "等待 Redis 启动..."
    sleep 3

    if docker-compose ps | grep -q "novel-reader-backend"; then
        print_warning "后端容器已在运行"
    else
        print_info "启动后端容器..."
        docker-compose up -d backend
    fi

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

start_frontend_docker() {
    print_header "启动前端服务 (Docker)"

    if ! check_docker; then return 1; fi

    if [ ! -d "$FRONTEND_DIR/dist" ] || [ ! -f "$FRONTEND_DIR/dist/index.html" ]; then
        print_warning "前端构建文件不存在，开始构建..."
        build_frontend
    fi

    print_info "启动前端容器..."
    docker-compose up -d frontend
    print_success "前端服务已启动"
}

start_backend_local() {
    print_header "启动后端服务 (本地)"

    if ! check_python; then return 1; fi

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        print_info "创建 Python 虚拟环境..."
        $PYTHON_CMD -m venv venv
    fi

    source venv/bin/activate

    print_info "安装 Python 依赖..."
    pip install -q -r requirements.txt

    print_info "启动后端服务..."
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!

    echo "$BACKEND_PID" > ../.backend.pid

    cd ..

    print_info "等待后端服务就绪..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            print_success "后端服务已就绪 (PID: $BACKEND_PID)"
            return 0
        fi
        sleep 1
    done

    print_warning "后端服务启动较慢，请稍后检查"
    return 0
}

start_frontend_local() {
    print_header "启动前端服务 (本地)"

    if ! check_command node; then
        print_warning "Node.js 未安装，跳过前端启动"
        print_info "后端 API 仍可访问: http://localhost:8000/docs"
        return 0
    fi

    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        print_info "安装前端依赖..."
        npm install
    fi

    print_info "启动前端开发服务器..."
    npm run dev &
    FRONTEND_PID=$!

    echo "$FRONTEND_PID" > ../.frontend.pid

    cd ..

    print_success "前端开发服务已启动 (PID: $FRONTEND_PID)"
}

build_frontend() {
    print_header "构建前端"

    if ! check_command node; then
        print_error "Node.js 未安装"
        print_info "请访问 https://nodejs.org/ 下载安装"
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

stop_services_docker() {
    print_header "停止服务 (Docker)"

    if ! check_docker; then return 1; fi

    print_info "停止所有容器..."
    docker-compose down

    print_success "所有服务已停止"
}

stop_services_local() {
    print_header "停止服务 (本地)"

    if [ -f ".backend.pid" ]; then
        PID=$(cat .backend.pid)
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            print_success "后端服务已停止 (PID: $PID)"
        else
            print_warning "后端进程已不存在 (PID: $PID)"
        fi
        rm -f .backend.pid
    else
        print_info "未找到后端 PID 文件，尝试按端口查找..."
        PID=$(lsof -ti:8000 2>/dev/null || true)
        if [ -n "$PID" ]; then
            kill "$PID" 2>/dev/null || true
            print_success "后端服务已停止 (PID: $PID)"
        else
            print_info "后端服务未在运行"
        fi
    fi

    if [ -f ".frontend.pid" ]; then
        PID=$(cat .frontend.pid)
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            print_success "前端服务已停止 (PID: $PID)"
        else
            print_warning "前端进程已不存在 (PID: $PID)"
        fi
        rm -f .frontend.pid
    else
        PID=$(lsof -ti:5173 2>/dev/null || true)
        if [ -n "$PID" ]; then
            kill "$PID" 2>/dev/null || true
            print_success "前端服务已停止 (PID: $PID)"
        else
            print_info "前端服务未在运行"
        fi
    fi
}

show_status_docker() {
    print_header "服务状态 (Docker)"

    if ! check_docker; then return 1; fi

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

show_status_local() {
    print_header "服务状态 (本地)"

    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        print_success "后端 API: 运行中 (http://localhost:8000)"
    else
        print_error "后端 API: 未响应"
    fi

    if curl -s -o /dev/null http://localhost:5173 2>/dev/null; then
        print_success "前端页面: 运行中 (http://localhost:5173)"
    else
        print_warning "前端页面: 未响应"
    fi
}

show_logs_docker() {
    print_header "查看日志 (Docker)"

    if ! check_docker; then return 1; fi

    echo -e "${CYAN}按 Ctrl+C 退出日志查看${NC}"
    docker-compose logs -f
}

show_logs_local() {
    print_header "查看日志 (本地)"

    LOG_DIR="$DATA_DIR/logs"
    if [ -d "$LOG_DIR" ] && [ "$(ls -A "$LOG_DIR" 2>/dev/null)" ]; then
        print_info "日志目录: $LOG_DIR"
        ls -la "$LOG_DIR"
        echo ""
        LATEST_LOG=$(ls -t "$LOG_DIR"/*.log 2>/dev/null | head -1)
        if [ -n "$LATEST_LOG" ]; then
            print_info "最新日志: $LATEST_LOG"
            tail -f "$LATEST_LOG"
        fi
    else
        print_info "暂无日志文件"
    fi
}

clean_data() {
    print_header "清理数据"

    print_warning "此操作将删除所有数据，包括书籍、用户、阅读进度等！"
    read -p "确认继续? (y/N): " confirm

    if [[ $confirm =~ ^[Yy]$ ]]; then
        if [ "$MODE" = "local" ]; then
            stop_services_local
        else
            stop_services_docker
        fi
        print_info "删除数据目录..."
        rm -rf "$DATA_DIR"
        create_directories
        print_success "数据已清理"

        read -p "是否重新启动服务? (Y/n): " restart
        if [[ ! $restart =~ ^[Nn]$ ]]; then
            if [ "$MODE" = "local" ]; then
                start_all_local
            else
                start_all_docker
            fi
        fi
    else
        print_info "操作已取消"
    fi
}

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

start_all_docker() {
    print_header "启动 Novel Reader (Docker 模式)"

    check_command docker
    check_command docker-compose
    check_command node

    create_directories
    check_env_docker

    start_backend_docker
    start_frontend_docker

    print_header "服务已启动 (Docker 模式)"
    echo -e "${GREEN}📖 前端页面:${NC} http://localhost"
    echo -e "${GREEN}🔧 API 文档:${NC} http://localhost:8000/docs"
    echo -e "${GREEN}💓 健康检查:${NC} http://localhost:8000/api/health"
    echo ""
    echo -e "${YELLOW}常用命令:${NC}"
    echo "  ./start.sh docker stop     - 停止服务"
    echo "  ./start.sh docker restart  - 重启服务"
    echo "  ./start.sh docker logs     - 查看日志"
    echo "  ./start.sh docker status   - 查看状态"
}

start_all_local() {
    print_header "启动 Novel Reader (本地模式)"

    check_python
    check_command node

    create_directories
    check_env_local

    print_info "提示: Redis 非必需，未安装时自动降级为无缓存模式"

    start_backend_local
    start_frontend_local

    print_header "服务已启动 (本地模式)"
    echo -e "${GREEN}📖 前端页面:${NC} http://localhost:5173"
    echo -e "${GREEN}🔧 API 文档:${NC} http://localhost:8000/docs"
    echo -e "${GREEN}💓 健康检查:${NC} http://localhost:8000/api/health"
    echo ""
    echo -e "${YELLOW}常用命令:${NC}"
    echo "  ./start.sh local stop     - 停止服务"
    echo "  ./start.sh local status   - 查看状态"
    echo "  ./start.sh local logs     - 查看日志"
    echo ""
    echo -e "${YELLOW}提示:${NC}"
    echo "  本地模式后端使用 --reload，修改代码自动重启"
    echo "  前端使用 Vite 开发服务器，支持热更新"
}

restart_services() {
    print_header "重启服务"
    if [ "$MODE" = "local" ]; then
        stop_services_local
    else
        stop_services_docker
    fi
    sleep 2
    if [ "$MODE" = "local" ]; then
        start_all_local
    else
        start_all_docker
    fi
}

rebuild_all() {
    print_header "重新构建并启动"
    if [ "$MODE" = "local" ]; then
        stop_services_local
        start_all_local
    else
        stop_services_docker
        build_frontend
        start_all_docker
    fi
}

show_help() {
    cat << EOF
Novel Reader 启动脚本

用法: ./start.sh <模式> [命令]

模式:
  docker    Docker 模式 (需要 Docker + Docker Compose)
  local     本地模式 (直接运行 Python + Node.js)

命令:
  (无)      启动所有服务
  stop      停止所有服务
  restart   重启所有服务
  build     重新构建并启动
  logs      查看服务日志
  status    查看服务状态
  clean     清理所有数据并重新启动
  test      运行后端测试
  help      显示此帮助信息

示例:
  ./start.sh docker          # Docker 模式启动
  ./start.sh docker stop     # Docker 模式停止
  ./start.sh local           # 本地模式启动
  ./start.sh local stop      # 本地模式停止
  ./start.sh local status    # 本地模式查看状态

Docker 模式访问地址:
  前端: http://localhost
  API:  http://localhost:8000
  文档: http://localhost:8000/docs

本地模式访问地址:
  前端: http://localhost:5173
  API:  http://localhost:8000
  文档: http://localhost:8000/docs
EOF
}

parse_args() {
    case "${1:-}" in
        docker|local)
            MODE="$1"
            ACTION="${2:-}"
            ;;
        stop|restart|build|logs|status|clean|test|help|--help|-h)
            MODE="docker"
            ACTION="$1"
            ;;
        "")
            MODE="docker"
            ACTION=""
            ;;
        *)
            print_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
}

run_action() {
    case "$ACTION" in
        stop)     if [ "$MODE" = "local" ]; then stop_services_local; else stop_services_docker; fi ;;
        restart)  restart_services ;;
        build)    rebuild_all ;;
        logs)     if [ "$MODE" = "local" ]; then show_logs_local; else show_logs_docker; fi ;;
        status)   if [ "$MODE" = "local" ]; then show_status_local; else show_status_docker; fi ;;
        clean)    clean_data ;;
        test)     run_tests ;;
        help|--help|-h) show_help ;;
        "")
            if [ "$MODE" = "local" ]; then start_all_local; else start_all_docker; fi
            ;;
        *)
            print_error "未知命令: $ACTION"
            show_help
            exit 1
            ;;
    esac
}

parse_args "$@"
run_action
