#!/bin/bash
# Novel Reader - Android/Termux 部署脚本
# 支持: Termux (Android)
# 要求: Termux 最新版本, Python 3.10+

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

TERMUX_PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
TERMUX_HOME="${HOME:-/data/data/com.termux/files/home}"

is_termux() {
    [ -d "$TERMUX_PREFIX" ] && [ -d "$TERMUX_HOME" ]
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

termux_setup_storage() {
    if is_termux; then
        log_info "配置 Termux 存储访问..."
        termux-setup-storage 2>/dev/null || true
    fi
}

install_termux_deps() {
    log_header "安装 Termux 依赖"

    if ! is_termux; then
        log_warning "未检测到 Termux 环境，跳过系统依赖安装"
        return 0
    fi

    log_info "更新包列表..."
    pkg update -y 2>/dev/null || apt update -y

    log_info "安装系统依赖..."
    pkg install -y \
        python \
        python-pip \
        python-dev \
        libjpeg-turbo-dev \
        zlib-dev \
        clang \
        make \
        cmake \
        git \
        redis \
        nodejs-lts \
        openssl \
        libmagic \
        > /dev/null 2>&1

    log_info "安装 Termux specific packages..."
    pkg install -y \
        tur-repo \
        libjpeg-turbo \
        > /dev/null 2>&1 || true

    log_success "Termux 依赖安装完成"
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

        local secret_key=$(python3 -c "import secrets; print(secrets.token_hex(32))")

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

    log_info "安装 Python 包 (这可能需要几分钟，在移动设备上可能更长)..."
    log_warning "提示: 如果安装失败，Termux 可能需要额外的编译工具"

    pip install --no-cache-dir -r "$PYTHON_DEPS_FILE" 2>&1 || {
        log_warning "部分依赖安装失败，尝试安装预编译版本..."
        pip install --only-binary=:all: -r "$PYTHON_DEPS_FILE" 2>&1 || true
    }

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

    if ! npm install --legacy-peer-deps 2>&1; then
        log_warning "npm 安装失败，尝试使用 yarn..."
        if check_command yarn; then
            yarn install
        fi
    fi

    cd "$SCRIPT_DIR"

    log_success "Node.js 依赖安装完成"
}

start_redis() {
    log_header "启动 Redis"

    if check_command redis-server; then
        if ! pgrep redis-server > /dev/null; then
            redis-server --daemonize yes --port 6379 --maxmemory 32mb --maxmemory-policy allkeys-lru
            log_success "Redis 已启动"
        else
            log_info "Redis 已在运行"
        fi
    else
        log_warning "Redis 未安装，SQLite 模式将自动启用"
        log_info "提示: pkg install redis 安装 Redis"
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

    export NODE_OPTIONS="--max-old-space-size=512"

    nohup npm run dev > "$DATA_DIR/logs/frontend.log" 2>&1 &
    echo $! > vite.pid

    cd "$SCRIPT_DIR"

    log_success "前端服务已启动 (PID: $(cat $FRONTEND_DIR/vite.pid))"
}

stop_services() {
    log_header "停止服务"

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

setup_global_commands() {
    log_header "配置全局命令"

    if [ -d "$TERMUX_PREFIX/bin" ] && [ -w "$TERMUX_PREFIX/bin" ]; then
        local bin_dir="$TERMUX_PREFIX/bin"

        if [ -f "$SCRIPT_DIR/readweb" ]; then
            ln -sf "$SCRIPT_DIR/readweb" "$bin_dir/readweb"
            log_success "readweb → $bin_dir/readweb"
        fi

        if [ -f "$SCRIPT_DIR/update.sh" ]; then
            ln -sf "$SCRIPT_DIR/update.sh" "$bin_dir/update.sh"
            log_success "update.sh → $bin_dir/update.sh"
        fi

        log_success "全局命令配置完成!"
        echo ""
        echo -e "${YELLOW}请重新打开 Termux 或运行:${NC}"
        echo "  hash -r"
        echo ""
        echo -e "${YELLOW}以后可直接使用:${NC}"
        echo "  readweb start    # 启动项目"
        echo "  readweb update   # 更新项目"
        echo ""
    else
        log_warning "无法写入 $TERMUX_PREFIX/bin，跳过全局命令配置"
    fi
}

show_help() {
    cat << EOF

Novel Reader - Android/Termux 部署脚本

用法: bash deploy_termux.sh [command]

命令:
  install     安装所有依赖 (首次运行必须)
  start       启动服务
  stop        停止服务
  restart     重启服务
  status      查看服务状态
  logs        查看日志
  global      配置全局命令 (readweb)
  help        显示帮助

示例:
  bash deploy_termux.sh install    # 安装依赖
  bash deploy_termux.sh start      # 启动服务

Termux 特别提示:
  1. 首次使用需要授予存储权限: termux-setup-storage
  2. 如果遇到编译错误，运行: pkg install python-dev clang make cmake
  3. 建议在稳定的网络环境下安装依赖

访问地址:
  前端: http://localhost
  API:  http://localhost:8000/docs

EOF
}

main() {
    local cmd="${1:-help}"

    if is_termux; then
        echo ""
        echo -e "${MAGENTA}╔══════════════════════════════════════════════════════╗${NC}"
        echo -e "${MAGENTA}║${NC}  ${CYAN}Novel Reader - Termux 部署脚本${NC}                  ${MAGENTA}║${NC}"
        echo -e "${MAGENTA}║${NC}  ${YELLOW}Android 移动端优化版${NC}                             ${MAGENTA}║${NC}"
        echo -e "${MAGENTA}╚══════════════════════════════════════════════════════╝${NC}"
        echo ""
    else
        echo ""
        echo -e "${MAGENTA}╔══════════════════════════════════════════════════════╗${NC}"
        echo -e "${MAGENTA}║${NC}  ${CYAN}Novel Reader - Linux 部署脚本${NC}                    ${MAGENTA}║${NC}"
        echo -e "${MAGENTA}╚══════════════════════════════════════════════════════╝${NC}"
        echo ""
    fi

    case "$cmd" in
        install)
            termux_setup_storage
            install_termux_deps
            create_directories
            create_env_file
            install_python_deps
            install_node_deps
            setup_global_commands
            ;;
        start)
            create_directories
            create_env_file
            start_backend
            start_frontend

            echo ""
            echo -e "${GREEN}═════════════════════════════════════════════════════${NC}"
            echo -e "${GREEN}  服务已启动!${NC}"
            echo -e "${GREEN}═════════════════════════════════════════════════════${NC}"
            echo ""
            echo -e "  ${GREEN}📖${NC} 前端:  http://localhost"
            echo -e "  ${GREEN}🔧${NC} API:   http://localhost:8000/docs"
            echo ""
            echo -e "${YELLOW}提示: 如果在手机浏览器访问，使用 http://localhost:3000${NC}"
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
        global)
            setup_global_commands
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
