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
SCRIPTS_DIR="scripts"
MODE=""
ACTION=""
SYS_TYPE=""
IS_TERMUX=0
TERMUX_HOME=""
ORIGINAL_DIR=""
RUN_DIR=""
MIRROR_CONFIGURED=0

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
    command -v "$1" &> /dev/null
}

detect_system() {
    if [ -d "/data/data/com.termux" ] || echo "$PREFIX" | grep -q "com.termux" 2>/dev/null; then
        SYS_TYPE="termux"
        IS_TERMUX=1
        TERMUX_HOME="$HOME"
        print_info "系统识别: Android Termux"
    elif [ "$(uname -s)" = "Darwin" ]; then
        SYS_TYPE="macos"
        print_info "系统识别: macOS"
    else
        SYS_TYPE="linux"
        print_info "系统识别: Linux"
    fi
}

is_on_shared_storage() {
    local abs_path
    abs_path="$(cd "$(dirname "$0")" && pwd)"
    case "$abs_path" in
        /sdcard/*|/storage/emulated/*|/mnt/media_rw/*|/storage/*/Android/data/com.termux/files/*)
            return 0
            ;;
        *)
            if [ "$IS_TERMUX" -eq 1 ]; then
                case "$abs_path" in
                    /data/data/com.termux/files/home/*)
                        return 1
                        ;;
                    *)
                        return 0
                        ;;
                esac
            fi
            return 1
            ;;
    esac
}

migrate_to_internal() {
    local src_dir
    src_dir="$(cd "$(dirname "$0")" && pwd)"
    local target_dir="$TERMUX_HOME/novel-reader"

    if [ "$src_dir" = "$target_dir" ] || [ "$src_dir" = "$target_dir" ]; then
        print_info "项目已在内部存储中"
        RUN_DIR="$target_dir"
        return 0
    fi

    if [ -d "$target_dir" ]; then
        print_info "内部存储已存在项目副本，同步更新..."
        rsync -a --delete --exclude='data/' --exclude='.env' --exclude='node_modules/' --exclude='venv/' --exclude='__pycache__/' --exclude='.git/' "$src_dir/" "$target_dir/" 2>/dev/null || {
            print_info "rsync 不可用，使用 cp 同步..."
            cp -r "$src_dir/backend" "$src_dir/frontend" "$src_dir/start.sh" "$src_dir/docker-compose.yml" "$src_dir/.env.example" "$target_dir/" 2>/dev/null || true
        }
    else
        print_info "复制项目到内部存储: $target_dir"
        mkdir -p "$target_dir"
        cp -r "$src_dir"/* "$target_dir/" 2>/dev/null || true
        cp -r "$src_dir"/.* "$target_dir/" 2>/dev/null || true
    fi

    if [ ! -d "$target_dir/data" ] && [ -d "$src_dir/data" ]; then
        cp -r "$src_dir/data" "$target_dir/" 2>/dev/null || true
    fi

    if [ -f "$src_dir/.env" ] && [ ! -f "$target_dir/.env" ]; then
        cp "$src_dir/.env" "$target_dir/"
    fi

    RUN_DIR="$target_dir"
    print_success "项目已迁移到内部存储: $target_dir"
    print_warning "后续操作将在内部存储目录执行"
}

ensure_storage_permission() {
    if [ ! -d "$HOME/storage" ]; then
        print_warning "Termux 存储权限未设置"
        print_info "正在请求存储权限..."
        termux-setup-storage 2>/dev/null || {
            print_warning "无法自动获取存储权限，请手动执行: termux-setup-storage"
        }
    fi
}

install_deps_termux() {
    print_header "安装 Termux 系统依赖"

    print_info "更新包管理器..."
    pkg update -y 2>/dev/null && pkg upgrade -y 2>/dev/null || true

    local pkgs="python python-dev nodejs build-essential ca-certificates clang make cmake"
    local need_install=""

    for pkg_name in $pkgs; do
        if ! pkg list-installed 2>/dev/null | grep -q "^$pkg_name/"; then
            need_install="$need_install $pkg_name"
        fi
    done

    if [ -n "$need_install" ]; then
        print_info "安装缺失的包:$need_install"
        pkg install -y $need_install 2>/dev/null || {
            print_warning "部分包安装失败，尝试逐个安装..."
            for pkg_name in $need_install; do
                pkg install -y "$pkg_name" 2>/dev/null || print_warning "  $pkg_name 安装失败"
            done
        }
    fi

    print_info "升级 pip..."
    python -m pip install --upgrade pip 2>/dev/null || pip install --upgrade pip 2>/dev/null || true

    print_success "Termux 系统依赖安装完成"
}

install_deps_linux() {
    print_header "安装 Linux 系统依赖"

    if check_command apt-get; then
        local pkgs="python3 python3-pip python3-venv nodejs npm"
        local need_install=""

        for pkg_name in $pkgs; do
            if ! check_command "$pkg_name" && ! dpkg -l "$pkg_name" &>/dev/null; then
                need_install="$need_install $pkg_name"
            fi
        done

        if [ -n "$need_install" ]; then
            print_info "安装缺失的包:$need_install"
            sudo apt-get update -qq
            sudo apt-get install -y $need_install 2>/dev/null || {
                print_warning "部分包安装失败，请手动安装"
            }
        fi
    elif check_command yum; then
        local pkgs="python3 python3-pip nodejs npm"
        for pkg_name in $pkgs; do
            if ! check_command "$pkg_name"; then
                sudo yum install -y "$pkg_name" 2>/dev/null || true
            fi
        done
    elif check_command dnf; then
        local pkgs="python3 python3-pip nodejs npm"
        for pkg_name in $pkgs; do
            if ! check_command "$pkg_name"; then
                sudo dnf install -y "$pkg_name" 2>/dev/null || true
            fi
        done
    elif check_command pacman; then
        local pkgs="python python-pip nodejs npm"
        for pkg_name in $pkgs; do
            if ! check_command "$pkg_name"; then
                sudo pacman -S --noconfirm "$pkg_name" 2>/dev/null || true
            fi
        done
    else
        print_warning "未识别的包管理器，请手动安装: Python 3.10+, Node.js 18+"
    fi

    print_success "Linux 系统依赖安装完成"
}

install_deps_macos() {
    print_header "安装 macOS 系统依赖"

    if ! check_command brew; then
        print_warning "Homebrew 未安装"
        print_info "请访问 https://brew.sh 安装后重试"
        return 1
    fi

    local pkgs="python3 node"
    for pkg_name in $pkgs; do
        if ! check_command "$pkg_name"; then
            brew install "$pkg_name" 2>/dev/null || true
        fi
    done

    print_success "macOS 系统依赖安装完成"
}

install_system_deps() {
    case "$SYS_TYPE" in
        termux) install_deps_termux ;;
        linux)  install_deps_linux ;;
        macos)  install_deps_macos ;;
    esac
}

configure_mirrors() {
    if [ "$MIRROR_CONFIGURED" -eq 1 ]; then
        return 0
    fi

    local mirror_script="$RUN_DIR/$SCRIPTS_DIR/mirror-selector.sh"
    if [ ! -f "$mirror_script" ]; then
        mirror_script="$(cd "$(dirname "$0")" && pwd)/$SCRIPTS_DIR/mirror-selector.sh"
    fi

    if [ -f "$mirror_script" ]; then
        source "$mirror_script"
        configure_all_mirrors "$SYS_TYPE"
        MIRROR_CONFIGURED=1
    else
        print_warning "镜像选择脚本不存在，使用默认源"
    fi
}

check_python() {
    local py_cmd=""
    if check_command python3; then
        py_cmd="python3"
    elif check_command python; then
        py_cmd="python"
    fi

    if [ -z "$py_cmd" ]; then
        print_error "Python 未安装"
        return 1
    fi

    local py_version
    py_version=$($py_cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
    local py_major py_minor
    py_major=$(echo "$py_version" | cut -d'.' -f1)
    py_minor=$(echo "$py_version" | cut -d'.' -f2)

    if [ "$py_major" -lt 3 ] || ([ "$py_major" -eq 3 ] && [ "$py_minor" -lt 10 ]); then
        print_error "Python 版本过低 ($py_version)，需要 3.10+"
        return 1
    fi

    PYTHON_CMD="$py_cmd"
    print_info "Python 版本: $py_version ($py_cmd)"
    return 0
}

check_node() {
    if ! check_command node; then
        print_warning "Node.js 未安装，前端将不可用"
        return 1
    fi

    local node_version
    node_version=$(node --version 2>/dev/null | cut -d'v' -f2 | cut -d'.' -f1)
    if [ -n "$node_version" ] && [ "$node_version" -lt 18 ]; then
        print_warning "Node.js 版本过低，建议 18+"
    fi
    return 0
}

check_docker() {
    if [ "$IS_TERMUX" -eq 1 ]; then
        print_error "Termux 不支持 Docker，请使用本地模式"
        return 1
    fi
    if ! docker info &> /dev/null; then
        print_error "Docker 未运行，请先启动 Docker"
        return 1
    fi
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
        local secret
        if check_command openssl; then
            secret=$(openssl rand -hex 32)
        else
            secret="docker-$(date +%s)-$RANDOM$RANDOM$RANDOM"
        fi
        cat > .env << EOF
SECRET_KEY=$secret
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
        local secret
        if check_command openssl; then
            secret=$(openssl rand -hex 32)
        else
            secret="local-$(date +%s)-$RANDOM$RANDOM$RANDOM"
        fi
        local redis_url="redis://localhost:6379"
        if [ "$IS_TERMUX" -eq 1 ]; then
            redis_url="redis://localhost:6379"
        fi
        cat > .env << EOF
SECRET_KEY=$secret
DEBUG=true
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=$redis_url
EOF
        print_success ".env 文件已创建"
    else
        if grep -q "redis://redis:6379" .env 2>/dev/null; then
            print_warning "检测到 .env 中 REDIS_URL 为 Docker 内部地址 (redis://redis:6379)"
            print_info "本地模式需要使用 redis://localhost:6379"
            if [ ! -t 0 ]; then
                sed -i 's|redis://redis:6379|redis://localhost:6379|g' .env
                print_success "REDIS_URL 已自动修改为本地地址"
            else
                read -p "是否自动修改? (Y/n): " confirm
                if [[ ! $confirm =~ ^[Nn]$ ]]; then
                    sed -i 's|redis://redis:6379|redis://localhost:6379|g' .env
                    print_success "REDIS_URL 已修改为本地地址"
                fi
            fi
        fi
    fi
}

setup_python_env() {
    print_header "配置 Python 环境"

    if ! check_python; then
        print_error "Python 不可用，请先安装"
        return 1
    fi

    cd "$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        print_info "创建 Python 虚拟环境..."
        $PYTHON_CMD -m venv venv
        if [ $? -ne 0 ]; then
            print_error "venv 创建失败"
            if [ "$IS_TERMUX" -eq 1 ]; then
                print_warning "Termux 提示: 确保项目在内部存储中 (非 /sdcard/)"
            fi
            return 1
        fi
    fi

    source venv/bin/activate

    print_info "安装 Python 依赖..."
    if [ "$IS_TERMUX" -eq 1 ]; then
        pip install --upgrade pip 2>/dev/null || true

        print_info "Termux 策略: 优先安装预编译 wheel..."
        local pure_pkgs="fastapi uvicorn sqlalchemy aiosqlite redis pydantic pydantic-settings python-jose passlib python-multipart beautifulsoup4 tenacity pydantic-core starlette typing-extensions annotated-types anyio idna sniffio"
        pip install --only-binary :all: $pure_pkgs 2>/dev/null || {
            print_info "部分纯 Python 包无预编译 wheel，使用源码安装..."
            pip install $pure_pkgs 2>/dev/null || true
        }

        print_info "安装 C 扩展包 (可能需要编译)..."
        pip install --only-binary :all: aiohttp 2>/dev/null || {
            print_warning "aiohttp 无预编译 wheel，从源码编译 (较慢)..."
            pip install aiohttp 2>/dev/null || {
                print_warning "aiohttp 安装失败，使用 httpx 替代"
                pip install httpx 2>/dev/null || true
            }
        }

        pip install --only-binary :all: psutil 2>/dev/null || {
            print_warning "psutil 无预编译 wheel，尝试编译..."
            pip install psutil 2>/dev/null || print_warning "psutil 安装失败（非致命，功能降级）"
        }

        pip install --only-binary :all: python-magic 2>/dev/null || {
            print_warning "python-magic 无预编译 wheel，尝试编译..."
            pip install python-magic 2>/dev/null || print_warning "python-magic 安装失败（非致命，文件类型检测降级）"
        }

        pip install bcrypt cryptography 2>/dev/null || {
            print_warning "bcrypt/cryptography 安装失败，尝试降级版本..."
            pip install "cryptography<43" 2>/dev/null || true
            pip install "bcrypt<4.1" 2>/dev/null || true
        }
    else
        pip install -q -r requirements.txt
    fi

    cd "$RUN_DIR"
    print_success "Python 环境配置完成"
}

start_backend_local() {
    print_header "启动后端服务 (本地)"

    setup_python_env || return 1

    cd "$BACKEND_DIR"
    source venv/bin/activate

    local extra_args=""
    if [ "$IS_TERMUX" -eq 1 ]; then
        extra_args="--workers 1 --limit-concurrency 50"
        print_info "Termux 优化: 单 worker + 限制并发"
    fi

    print_info "启动后端服务..."
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload $extra_args &
    BACKEND_PID=$!
    echo "$BACKEND_PID" > "$RUN_DIR/.backend.pid"

    cd "$RUN_DIR"

    print_info "等待后端服务就绪..."
    for i in $(seq 1 30); do
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

    if ! check_node; then
        print_warning "Node.js 不可用，跳过前端"
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
    echo "$FRONTEND_PID" > "$RUN_DIR/.frontend.pid"

    cd "$RUN_DIR"
    print_success "前端开发服务已启动 (PID: $FRONTEND_PID)"
}

build_frontend() {
    print_header "构建前端"

    if ! check_node; then
        print_error "Node.js 未安装"
        return 1
    fi

    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        print_info "安装前端依赖..."
        npm install
    fi

    print_info "构建生产版本..."
    npm run build

    cd "$RUN_DIR"
    print_success "前端构建完成"
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
    for i in $(seq 1 30); do
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

stop_services_docker() {
    print_header "停止服务 (Docker)"

    if ! check_docker; then return 1; fi

    print_info "停止所有容器..."
    docker-compose down
    print_success "所有服务已停止"
}

stop_services_local() {
    print_header "停止服务 (本地)"

    local pid_file="$RUN_DIR/.backend.pid"
    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            print_success "后端服务已停止 (PID: $pid)"
        else
            print_warning "后端进程已不存在 (PID: $pid)"
        fi
        rm -f "$pid_file"
    else
        local pid
        pid=$(lsof -ti:8000 2>/dev/null || true)
        if [ -n "$pid" ]; then
            kill "$pid" 2>/dev/null || true
            print_success "后端服务已停止 (PID: $pid)"
        else
            print_info "后端服务未在运行"
        fi
    fi

    pid_file="$RUN_DIR/.frontend.pid"
    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            print_success "前端服务已停止 (PID: $pid)"
        else
            print_warning "前端进程已不存在 (PID: $pid)"
        fi
        rm -f "$pid_file"
    else
        local pid
        pid=$(lsof -ti:5173 2>/dev/null || true)
        if [ -n "$pid" ]; then
            kill "$pid" 2>/dev/null || true
            print_success "前端服务已停止 (PID: $pid)"
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
    local log_dir="$RUN_DIR/$DATA_DIR/logs"
    if [ -d "$log_dir" ] && [ "$(ls -A "$log_dir" 2>/dev/null)" ]; then
        print_info "日志目录: $log_dir"
        local latest_log
        latest_log=$(ls -t "$log_dir"/*.log 2>/dev/null | head -1)
        if [ -n "$latest_log" ]; then
            print_info "最新日志: $latest_log"
            tail -f "$latest_log"
        fi
    else
        print_info "暂无日志文件"
    fi
}

clean_data() {
    print_header "清理数据"
    print_warning "此操作将删除所有数据，包括书籍、用户、阅读进度等！"

    if [ ! -t 0 ]; then
        print_error "非交互终端，无法确认，操作已取消"
        return 1
    fi

    read -p "确认继续? (y/N): " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        if [ "$MODE" = "local" ]; then
            stop_services_local
        else
            stop_services_docker
        fi
        print_info "删除数据目录..."
        rm -rf "$RUN_DIR/$DATA_DIR"
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

    cd "$RUN_DIR/$BACKEND_DIR"

    if [ ! -d "venv" ]; then
        print_info "创建虚拟环境..."
        $PYTHON_CMD -m venv venv
    fi

    source venv/bin/activate

    print_info "安装测试依赖..."
    pip install -q pytest pytest-asyncio httpx

    print_info "运行测试..."
    pytest tests/ -v --tb=short || true

    cd "$RUN_DIR"
}

start_all_docker() {
    print_header "启动 Novel Reader (Docker 模式)"

    if [ "$IS_TERMUX" -eq 1 ]; then
        print_error "Termux 不支持 Docker，请使用: ./start.sh local"
        return 1
    fi

    check_command docker || { print_error "Docker 未安装"; return 1; }
    check_command docker-compose || check_command docker || { print_error "Docker Compose 未安装"; return 1; }
    check_node || print_warning "Node.js 未安装，前端可能无法构建"

    configure_mirrors

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
    print_header "启动 Novel Reader (本地模式 | $SYS_TYPE)"

    if [ "$IS_TERMUX" -eq 1 ]; then
        ensure_storage_permission
        if is_on_shared_storage; then
            print_warning "项目位于共享存储区 (不支持执行 Python)"
            print_info "正在迁移到内部存储..."
            migrate_to_internal
            cd "$RUN_DIR"
        else
            RUN_DIR="$(pwd)"
        fi
    else
        RUN_DIR="$(pwd)"
    fi

    install_system_deps
    configure_mirrors

    check_python || { print_error "Python 不可用，请安装后重试"; return 1; }
    check_node || print_warning "Node.js 未安装，前端将不可用"

    create_directories
    check_env_local

    if [ "$IS_TERMUX" -eq 1 ]; then
        print_info "Termux 优化: Redis 非必需，未安装时自动降级为无缓存模式"
        print_info "Termux 优化: 单 worker 模式，降低内存占用"
    else
        print_info "提示: Redis 非必需，未安装时自动降级为无缓存模式"
    fi

    start_backend_local
    start_frontend_local

    print_header "服务已启动 (本地模式 | $SYS_TYPE)"

    local frontend_port=5173
    echo -e "${GREEN}📖 前端页面:${NC} http://localhost:$frontend_port"
    echo -e "${GREEN}🔧 API 文档:${NC} http://localhost:8000/docs"
    echo -e "${GREEN}💓 健康检查:${NC} http://localhost:8000/api/health"
    echo ""
    echo -e "${YELLOW}常用命令:${NC}"
    echo "  ./start.sh local stop     - 停止服务"
    echo "  ./start.sh local status   - 查看状态"
    echo "  ./start.sh local logs     - 查看日志"
    echo ""

    if [ "$IS_TERMUX" -eq 1 ]; then
        echo -e "${YELLOW}Termux 提示:${NC}"
        echo "  项目运行在: $RUN_DIR"
        echo "  原始代码在共享存储时，启动时已自动同步到内部存储"
        echo "  修改共享存储的代码后，重新启动即可自动同步"
        echo "  建议使用 tmux 保持后台运行: pkg install tmux"
    else
        echo -e "${YELLOW}提示:${NC}"
        echo "  本地模式后端使用 --reload，修改代码自动重启"
        echo "  前端使用 Vite 开发服务器，支持热更新"
    fi
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
Novel Reader 启动脚本 (自动识别系统)

用法: ./start.sh <模式> [命令]

系统自动识别:
  Termux   - Android Termux 环境 (自动优化)
  Linux    - 桌面 Linux / 服务器
  macOS    - macOS

模式:
  docker    Docker 模式 (Termux 不支持)
  local     本地模式 (所有系统通用)

命令:
  (无)      启动所有服务 (自动安装依赖)
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
  ./start.sh local           # 本地模式启动 (自动安装依赖)
  ./start.sh local stop      # 本地模式停止
  ./start.sh local status    # 本地模式查看状态

Termux 专项优化:
  - 自动检测共享存储并迁移到内部存储
  - 自动安装 build-essential 等编译依赖
  - 跳过不可用的可选依赖 (python-magic 等)
  - 单 worker + 限制并发，降低内存占用
  - 自动降级无 Redis 模式

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
            MODE="local"
            ACTION="$1"
            ;;
        "")
            MODE="local"
            ACTION=""
            ;;
        *)
            print_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac

    if [ "$IS_TERMUX" -eq 1 ] && [ "$MODE" = "docker" ]; then
        print_warning "Termux 不支持 Docker，自动切换为本地模式"
        MODE="local"
    fi
}

run_action() {
    case "$ACTION" in
        stop)
            if [ "$MODE" = "local" ]; then stop_services_local; else stop_services_docker; fi
            ;;
        restart)
            restart_services
            ;;
        build)
            rebuild_all
            ;;
        logs)
            if [ "$MODE" = "local" ]; then show_logs_local; else show_logs_docker; fi
            ;;
        status)
            if [ "$MODE" = "local" ]; then show_status_local; else show_status_docker; fi
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
            if [ "$MODE" = "local" ]; then start_all_local; else start_all_docker; fi
            ;;
        *)
            print_error "未知命令: $ACTION"
            show_help
            exit 1
            ;;
    esac
}

detect_system

RUN_DIR="$(pwd)"

parse_args "$@"
run_action
