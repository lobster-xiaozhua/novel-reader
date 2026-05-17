#!/bin/bash
# Novel Reader - Android/Termux 部署脚本
# 支持: Termux (Android)
# 要求: Termux 最新版本, Python 3.10+
# 交互逻辑对齐 Windows PowerShell 版本

# 不设置 set -e，避免单个命令失败导致整个脚本退出
# 改为在每个关键步骤后手动检查返回值

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERR]${NC} $1"; }
log_header() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

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
    if command -v "$1" &> /dev/null; then
        return 0
    fi
    return 1
}

get_python_cmd() {
    if check_command python3; then
        echo "python3"
    elif check_command python; then
        echo "python"
    else
        echo ""
    fi
}

detect_region() {
    if check_command curl; then
        COUNTRY=$(curl -s --max-time 3 "https://ipinfo.io/country" 2>/dev/null || echo "unknown")
        if [ "$COUNTRY" = "CN" ]; then
            echo "china"
            return
        fi
    fi
    echo "global"
}

termux_setup_storage() {
    if is_termux; then
        log_info "配置 Termux 存储访问..."
        termux-setup-storage 2>/dev/null || true
    fi
}

setup_mirrors() {
    log_header "配置镜像源"
    local region=$(detect_region)

    if [ "$region" = "china" ]; then
        log_info "检测到中国地区，配置国内镜像..."

        mkdir -p ~/.pip
        cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 120
[install]
trusted-host = mirrors.aliyun.com
EOF
        log_success "pip 镜像: 阿里云"

        npm config set registry https://registry.npmmirror.com 2>/dev/null || true
        log_success "npm 镜像: npmmirror.com"
    else
        log_info "海外地区，使用官方源"
    fi
}

install_termux_deps() {
    log_header "安装系统依赖"

    if ! is_termux; then
        log_warning "未检测到 Termux 环境，跳过系统依赖安装"
        return 0
    fi

    log_info "更新包列表..."
    pkg update -y || apt update -y || {
        log_warning "包列表更新失败，继续尝试安装..."
    }

    log_info "安装系统依赖 (逐个安装，忽略失败)..."

    # 逐个安装，避免一个包失败导致全部失败
    local packages="python python-pip clang make cmake git redis openssl"
    for pkg in $packages; do
        log_info "安装 $pkg ..."
        pkg install -y "$pkg" > /dev/null 2>&1 || {
            log_warning "$pkg 安装失败或已存在，继续..."
        }
    done

    # 可选包（可能不存在）
    local optional_packages="python-dev libjpeg-turbo-dev zlib-dev nodejs-lts libmagic tur-repo libjpeg-turbo"
    for pkg in $optional_packages; do
        log_info "尝试安装可选包 $pkg ..."
        pkg install -y "$pkg" > /dev/null 2>&1 || {
            log_warning "$pkg 不可用，跳过"
        }
    done

    # 如果 nodejs-lts 安装失败，尝试 nodejs
    if ! check_command node; then
        log_info "尝试安装 nodejs ..."
        pkg install -y nodejs > /dev/null 2>&1 || {
            log_warning "nodejs 安装失败"
        }
    fi

    log_success "系统依赖安装完成"
}

create_directories() {
    log_header "创建数据目录"

    for dir in books index static logs cache backups versions; do
        mkdir -p "$DATA_DIR/$dir"
        log_success "data/$dir"
    done
}

create_env_file() {
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        log_header "创建 .env 配置文件"

        local python_cmd=$(get_python_cmd)
        if [ -z "$python_cmd" ]; then
            log_error "未找到 Python，无法生成密钥"
            return 1
        fi

        local secret_key=$($python_cmd -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null)
        if [ -z "$secret_key" ]; then
            secret_key=$(openssl rand -hex 32 2>/dev/null || date +%s%N | sha256sum | head -c 64)
        fi

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

    local python_cmd=$(get_python_cmd)
    if [ -z "$python_cmd" ]; then
        log_error "Python 未安装"
        return 1
    fi

    log_info "使用 Python: $python_cmd"

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        log_info "创建虚拟环境..."
        $python_cmd -m venv venv || {
            log_error "虚拟环境创建失败"
            cd "$SCRIPT_DIR"
            return 1
        }
    fi

    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    elif [ -f "venv/bin/activate.csh" ]; then
        source venv/bin/activate.csh
    else
        log_error "找不到虚拟环境激活脚本"
        cd "$SCRIPT_DIR"
        return 1
    fi

    log_info "升级 pip..."
    pip install --upgrade pip || {
        log_warning "pip 升级失败，继续..."
    }

    log_info "安装 Python 包 (这可能需要几分钟，在移动设备上可能更长)..."
    log_warning "提示: 如果安装失败，Termux 可能需要额外的编译工具"

    if [ -f "$PYTHON_DEPS_FILE" ]; then
        pip install --no-cache-dir -r "$PYTHON_DEPS_FILE" || {
            log_warning "部分依赖安装失败，尝试安装预编译版本..."
            pip install --only-binary=:all: -r "$PYTHON_DEPS_FILE" || {
                log_warning "预编译版本也失败，继续..."
            }
        }
    else
        log_warning "requirements.txt 不存在，跳过 Python 依赖安装"
    fi

    deactivate 2>/dev/null || true
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

    if [ ! -f "package.json" ]; then
        log_error "package.json 不存在"
        cd "$SCRIPT_DIR"
        return 1
    fi

    log_info "安装 npm 包..."
    npm install || {
        log_warning "npm install 失败，尝试 --legacy-peer-deps..."
        npm install --legacy-peer-deps || {
            log_warning "npm 安装失败，尝试使用 yarn..."
            if check_command yarn; then
                yarn install
            else
                log_error "所有包管理器都失败"
            fi
        }
    }

    cd "$SCRIPT_DIR"

    log_success "Node.js 依赖安装完成"
}

start_redis() {
    log_header "启动 Redis"

    if check_command redis-server; then
        if ! pgrep redis-server > /dev/null 2>&1; then
            redis-server --daemonize yes --port 6379 --maxmemory 32mb --maxmemory-policy allkeys-lru || {
                log_warning "Redis 启动失败"
            }
            sleep 1
            if pgrep redis-server > /dev/null 2>&1; then
                log_success "Redis 已启动"
            else
                log_warning "Redis 启动失败，SQLite 模式将自动启用"
            fi
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
        cd "$SCRIPT_DIR"
        return 1
    fi

    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        log_error "找不到虚拟环境激活脚本"
        cd "$SCRIPT_DIR"
        return 1
    fi

    if [ ! -d "$DATA_DIR/logs" ]; then
        mkdir -p "$DATA_DIR/logs"
    fi

    log_info "启动后端..."
    # Termux 中 nohup 可能有问题，使用直接后台运行
    uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$DATA_DIR/logs/backend.log" 2>&1 &
    local pid=$!
    echo $pid > uvicorn.pid

    deactivate 2>/dev/null || true
    cd "$SCRIPT_DIR"

    sleep 2
    if kill -0 $pid 2>/dev/null; then
        log_success "后端服务已启动 (PID: $pid)"
    else
        log_error "后端启动失败，请检查日志: $DATA_DIR/logs/backend.log"
        return 1
    fi
}

start_frontend() {
    log_header "启动前端服务"

    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        log_error "Node.js 依赖未安装，请先运行安装步骤"
        cd "$SCRIPT_DIR"
        return 1
    fi

    if [ ! -d "$DATA_DIR/logs" ]; then
        mkdir -p "$DATA_DIR/logs"
    fi

    export NODE_OPTIONS="--max-old-space-size=512"

    log_info "启动前端..."
    # Termux 中 nohup 可能有问题，使用直接后台运行
    npm run dev > "$DATA_DIR/logs/frontend.log" 2>&1 &
    local pid=$!
    echo $pid > vite.pid

    cd "$SCRIPT_DIR"

    sleep 2
    if kill -0 $pid 2>/dev/null; then
        log_success "前端服务已启动 (PID: $pid)"
    else
        log_error "前端启动失败，请检查日志: $DATA_DIR/logs/frontend.log"
        return 1
    fi
}

stop_services() {
    log_header "停止服务"

    if [ -f "$BACKEND_DIR/uvicorn.pid" ]; then
        local pid=$(cat "$BACKEND_DIR/uvicorn.pid")
        kill $pid 2>/dev/null || true
        rm -f "$BACKEND_DIR/uvicorn.pid"
        log_success "后端已停止"
    fi

    if [ -f "$FRONTEND_DIR/vite.pid" ]; then
        local pid=$(cat "$FRONTEND_DIR/vite.pid")
        kill $pid 2>/dev/null || true
        rm -f "$FRONTEND_DIR/vite.pid"
        log_success "前端已停止"
    fi

    log_success "所有服务已停止"
}

show_status() {
    log_header "服务状态"

    echo ""
    echo -e "${CYAN}[本地服务]${NC}"

    if [ -f "$BACKEND_DIR/uvicorn.pid" ]; then
        local pid=$(cat "$BACKEND_DIR/uvicorn.pid")
        if kill -0 $pid 2>/dev/null; then
            log_success "后端: 运行中 (PID: $pid)"
        else
            log_error "后端: 未运行 (PID 文件存在但进程不存在)"
            rm -f "$BACKEND_DIR/uvicorn.pid"
        fi
    else
        log_error "后端: 未运行"
    fi

    if [ -f "$FRONTEND_DIR/vite.pid" ]; then
        local pid=$(cat "$FRONTEND_DIR/vite.pid")
        if kill -0 $pid 2>/dev/null; then
            log_success "前端: 运行中 (PID: $pid)"
        else
            log_error "前端: 未运行 (PID 文件存在但进程不存在)"
            rm -f "$FRONTEND_DIR/vite.pid"
        fi
    else
        log_error "前端: 未运行"
    fi

    echo ""

    if check_command curl; then
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
    else
        log_warning "curl 未安装，跳过 HTTP 健康检查"
    fi
}

show_logs() {
    if [ -d "$DATA_DIR/logs" ]; then
        local log_files=$(find "$DATA_DIR/logs" -name "*.log" 2>/dev/null)
        if [ -n "$log_files" ]; then
            tail -f $log_files 2>/dev/null || echo "暂无日志"
        else
            echo "暂无日志文件"
        fi
    else
        echo "日志目录不存在"
    fi
}

setup_global_commands() {
    log_header "配置全局命令"

    if [ -d "$TERMUX_PREFIX/bin" ] && [ -w "$TERMUX_PREFIX/bin" ]; then
        local bin_dir="$TERMUX_PREFIX/bin"

        if [ -f "$SCRIPT_DIR/readweb" ]; then
            ln -sf "$SCRIPT_DIR/readweb" "$bin_dir/readweb"
            log_success "readweb -> $bin_dir/readweb"
        fi

        if [ -f "$SCRIPT_DIR/update.sh" ]; then
            ln -sf "$SCRIPT_DIR/update.sh" "$bin_dir/update.sh"
            log_success "update.sh -> $bin_dir/update.sh"
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
  install     完整安装所有依赖 (首次运行必须)
  python      仅安装 Python 依赖
  node        仅安装 Node.js 依赖
  redis       安装 Redis (本地方式)
  start       启动服务 (本地模式)
  docker      启动服务 (Docker 模式)
  stop        停止服务
  status      查看服务状态
  logs        查看日志
  mirror      配置镜像源
  global      配置全局命令 (readweb)
  help        显示帮助

示例:
  bash deploy_termux.sh install    # 安装依赖
  bash deploy_termux.sh start      # 启动服务
  bash deploy_termux.sh docker     # 启动 Docker 服务

Termux 特别提示:
  1. 首次使用需要授予存储权限: termux-setup-storage
  2. 如果遇到编译错误，运行: pkg install python-dev clang make cmake
  3. 建议在稳定的网络环境下安装依赖
  4. 如果某个包安装失败，脚本会继续尝试其他包

访问地址:
  前端: http://localhost
  API:  http://localhost:8000/docs

EOF
}

main() {
    local cmd="${1:-help}"

    if is_termux; then
        echo ""
        echo -e "${MAGENTA}=======================================================${NC}"
        echo -e "  ${CYAN}Novel Reader - Termux 部署脚本${NC}"
        echo -e "  ${YELLOW}Android 移动端优化版${NC}"
        echo -e "${MAGENTA}=======================================================${NC}"
        echo ""
    else
        echo ""
        echo -e "${MAGENTA}=======================================================${NC}"
        echo -e "  ${CYAN}Novel Reader - Linux 部署脚本${NC}"
        echo -e "${MAGENTA}=======================================================${NC}"
        echo ""
    fi

    case "$cmd" in
        install)
            termux_setup_storage
            setup_mirrors
            install_termux_deps
            create_directories
            create_env_file
            install_python_deps
            install_node_deps
            setup_global_commands
            ;;
        python)
            install_python_deps
            ;;
        node)
            install_node_deps
            ;;
        redis)
            start_redis
            ;;
        start)
            create_directories
            create_env_file
            start_redis
            start_backend
            start_frontend

            echo ""
            echo -e "${GREEN}=======================================================${NC}"
            echo -e "${GREEN}  服务已启动!${NC}"
            echo -e "${GREEN}=======================================================${NC}"
            echo ""
            echo -e "  ${GREEN}[OK]${NC} 前端:  http://localhost"
            echo -e "  ${GREEN}[OK]${NC} API:   http://localhost:8000/docs"
            echo ""
            echo -e "${YELLOW}提示: 如果在手机浏览器访问，使用 http://localhost:3000${NC}"
            ;;
        docker)
            log_error "Docker 模式在 Termux 上不可用"
            log_info "请使用本地模式: bash deploy_termux.sh start"
            ;;
        stop)
            stop_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        mirror)
            setup_mirrors
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
