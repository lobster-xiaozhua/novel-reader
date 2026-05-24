#!/bin/bash
set -e

cd "$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_step() { echo -e "\n${CYAN}[→]${NC} ${BOLD}$1${NC}"; }
log_detail() { echo -e "  ${DIM}└─ $1${NC}"; }

SEPARATOR() { echo -e "${DIM}───────────────────────────────────────────────────${NC}"; }

SPINNER_FRAMES=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
_SP_PID="" _SP_MSG="" _SP_START=0

_spin_start() {
    _SP_MSG="$1"; _SP_START=$(date +%s)
    ( while true; do
        local e=$(($(date +%s)-_SP_START)) m=$((e/60)) s=$((e%60))
        printf "\r  ${CYAN}%s${NC} %s  ${DIM}[%02d:%02d]${NC}   " "${SPINNER_FRAMES[$((SECONDS%10))]}" "$_SP_MSG" "$m" "$s"
        sleep 0.08
    done ) & _SP_PID=$!
}

_spin_stop() {
    local ok="${1:-true}"
    [ -n "$_SP_PID" ] && kill "$_SP_PID" 2>/dev/null; wait "$_SP_PID" 2>/dev/null || true; _SP_PID=""
    local e=$(($(date +%s)-_SP_START)) m=$((e/60)) s=$((e%60))
    if [ "$ok" = "true" ]; then
        printf "\r  ${GREEN}✓${NC} %s  ${DIM}[%02d:%02d]${NC}                              \n" "$_SP_MSG" "$m" "$s"
    else
        printf "\r  ${RED}✗${NC} %s  ${DIM}[%02d:%02d]${NC}                              \n" "$_SP_MSG" "$m" "$s"
    fi
}

run_spin() {
    local desc="$1"; shift
    local tmp=$(mktemp /tmp/novel-XXXXXX.log)
    _spin_start "$desc"
    if "$@" &> "$tmp"; then
        _spin_stop true
        tail -3 "$tmp" 2>/dev/null | while IFS= read -r l; do [ -n "$l" ] && log_detail "$l"; done
        rm -f "$tmp"; return 0
    else
        _spin_stop false
        log_error "命令失败，日志:"; head -20 "$tmp" | while IFS= read -r l; do echo -e "  ${RED}$l${NC}"; done
        rm -f "$tmp"; return 1
    fi
}

print_banner() {
    echo ""
    echo -e "${MAGENTA}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}  ${CYAN}Novel Reader v2.0 - 高性能小说阅读器${NC}        ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╚═══════════════════════════════════════════════════╝${NC}"
    echo ""
}

show_help() {
    print_banner
    cat << EOF
用法: ./start.sh <command>

命令:
  start      启动项目（默认）
  stop       停止服务
  restart    重启服务
  status     查看服务状态
  migrate    执行数据库迁移
  build      构建前端
  dev        开发模式（前后端分离）
  help       显示此帮助

示例:
  ./start.sh start          # 启动生产服务
  ./start.sh dev            # 开发模式
  ./start.sh build          # 构建前端
EOF
}

check_env() {
    log_step "检查运行环境"
    SEPARATOR
    local errors=0

    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        log_detail "请安装 Python 3.12+ : https://www.python.org/downloads/"
        ((errors++))
    else
        local py_ver=$(python3 --version | cut -d' ' -f2)
        log_success "Python  ${py_ver}"
        log_detail "路径: $(which python3)"
    fi

    if ! command -v node &> /dev/null; then
        log_error "Node.js 未安装"
        log_detail "请安装 Node.js 20+ : https://nodejs.org/"
        ((errors++))
    else
        local node_ver=$(node --version)
        log_success "Node   ${node_ver}"
        log_detail "路径: $(which node)"
        if command -v npm &> /dev/null; then
            log_detail "npm    $(npm --version)"
        fi
    fi

    if command -v redis-cli &> /dev/null; then
        local redis_ok=$(redis-cli ping 2>/dev/null || echo "FAIL")
        if [ "$redis_ok" = "PONG" ]; then
            log_success "Redis  在线"
        else
            log_warning "Redis  未运行 (爬虫功能不可用)"
        fi
    else
        log_warning "Redis  未安装 (爬虫功能不可用)"
        log_detail "安装: apt install redis-server 或 docker run redis"
    fi

    local mem_total=$(awk '/MemTotal/ {printf "%.0f", $2/1024}' /proc/meminfo 2>/dev/null || echo 0)
    local mem_avail=$(awk '/MemAvailable/ {printf "%.0f", $2/1024}' /proc/meminfo 2>/dev/null || echo 0)
    if [ "$mem_total" -gt 0 ]; then
        log_detail "内存   ${mem_avail}MB 可用 / ${mem_total}MB 总计"
    fi

    local disk_free=$(df -h . | awk 'NR==2 {print $4}' 2>/dev/null || echo "unknown")
    log_detail "磁盘   ${disk_free} 可用"

    if [ $errors -gt 0 ]; then
        echo ""
        log_error "环境检查失败，请安装缺失的依赖后重试"
        exit 1
    fi
    echo ""
    log_success "环境检查通过"
}

install_python_deps() {
    log_step "安装 Python 依赖"
    SEPARATOR
    source venv/bin/activate

    local mirror="https://mirrors.aliyun.com/pypi/simple/"
    log_detail "镜像源: ${mirror}"
    log_detail "虚拟环境: $(realpath venv 2>/dev/null || echo 'venv/')"

    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt 不存在"; return 1
    fi

    local pkg_count=$(grep -c "^[^#]" requirements.txt 2>/dev/null || echo "?")
    log_detail "从 requirements.txt 安装 (${pkg_count} 个依赖)"

    run_spin "升级 pip" pip install --upgrade pip -i "$mirror"
    run_spin "安装 Python 依赖 (${pkg_count} 个)" pip install -r requirements.txt -i "$mirror"

    local pip_list=$(pip list --format=columns 2>/dev/null | tail -n +3 | wc -l)
    log_detail "环境中已安装 ${pip_list} 个包"
    echo ""
    log_success "Python 依赖安装完成"
}

install_node_deps() {
    log_step "安装 Node 依赖"
    SEPARATOR

    local mirror="https://registry.npmmirror.com"
    log_detail "镜像源: ${mirror}"
    cd frontend

    if [ -f "node_modules/.package-lock.json" ]; then
        local pkg_count=$(ls -1 node_modules 2>/dev/null | wc -l)
        cd ..
        log_success "Node 依赖已存在且完整 (${pkg_count} 个包)，跳过安装"
        return
    fi

    if [ -d "node_modules" ]; then
        local pkg_count=$(ls -1 node_modules 2>/dev/null | wc -l)
        log_warning "node_modules 不完整 (${pkg_count} 个包)，重新安装"
        rm -rf node_modules
    fi

    if [ -f "package-lock.json" ]; then
        log_detail "从 package-lock.json 安装 (确定性构建)"
        run_spin "安装 Node 依赖 (npm ci)" npm ci --registry "$mirror"
    elif [ -f "package.json" ]; then
        log_detail "从 package.json 安装"
        run_spin "安装 Node 依赖 (npm install)" npm install --registry "$mirror"
    fi

    cd ..
    echo ""
    log_success "Node 依赖安装完成"
}

install_deps() {
    log_step "安装项目依赖"
    SEPARATOR
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_success "Python 虚拟环境已创建"
        log_detail "位置: $(realpath venv)"
    else
        log_detail "虚拟环境已存在，跳过创建"
    fi
    install_python_deps
    if [ -f "frontend/package.json" ]; then
        install_node_deps
    fi
}

migrate_db() {
    log_step "执行数据库迁移"
    SEPARATOR
    source venv/bin/activate

    local db_path="data/db.sqlite3"
    if [ -f "$db_path" ]; then
        log_detail "数据库: $(realpath $db_path 2>/dev/null || echo $db_path)"
        local db_size=$(du -h "$db_path" 2>/dev/null | cut -f1)
        log_detail "大小: ${db_size}"
    else
        log_detail "首次迁移，将创建新数据库"
    fi

    run_spin "执行数据库迁移" python manage.py migrate
    echo ""
    log_success "数据库迁移完成"
}

create_superuser() {
    log_step "初始化管理员账户"
    SEPARATOR
    source venv/bin/activate
    local result=$(python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    import secrets, string
    pwd = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
    User.objects.create_superuser('admin', 'admin@example.com', pwd)
    print(f'CREATED:admin:{pwd}')
else:
    print('EXISTS')
" 2>/dev/null)

    if [[ "$result" == "EXISTS" ]]; then
        log_detail "管理员账户 admin 已存在，跳过创建"
    elif [[ "$result" == "CREATED:"* ]]; then
        local creds="${result#CREATED:}"
        local user="${creds%%:*}"
        local pass="${creds#*:}"
        echo ""
        log_warning "新管理员账户已创建"
        echo -e "  ${BOLD}用户名:${NC} ${user}"
        echo -e "  ${BOLD}密码:${NC}   ${pass}"
        echo -e "  ${YELLOW}请妥善保存此密码！${NC}"
        echo ""
    fi
    log_success "管理员账户就绪"
}

build_frontend() {
    log_step "构建前端应用"
    SEPARATOR
    log_detail "框架: React 19 + Vite + Tailwind CSS 4"
    log_detail "输出: frontend/dist/"

    cd frontend
    if [ ! -f "node_modules/.package-lock.json" ]; then
        cd ..
        log_warning "node_modules 不完整，先安装依赖"
        install_node_deps
        cd frontend
    fi
    run_spin "Vite 构建中" npm run build
    cd ..

    local js_size=$(du -h frontend/dist/static/js/main.js 2>/dev/null | cut -f1 || echo "?")
    local css_size=$(du -h frontend/dist/static/css/main.css 2>/dev/null | cut -f1 || echo "?")
    log_detail "JS  ${js_size}  →  static/js/main.js"
    log_detail "CSS ${css_size}  →  static/css/main.css"
    echo ""
    log_success "前端构建完成"
}

cmd_start() {
    print_banner
    check_env
    install_deps
    migrate_db
    create_superuser
    build_frontend

    source venv/bin/activate
    log_step "收集静态文件"
    run_spin "收集静态文件" python manage.py collectstatic --noinput
    log_success "静态文件收集完成"

    log_step "启动 Granian ASGI 服务器"
    SEPARATOR
    log_detail "服务器: Granian (ASGI, Rust 运行时)"
    log_detail "监听:   0.0.0.0:8000"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  🚀 服务已启动!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${GREEN}📖${NC} 访问地址:  ${CYAN}http://localhost:8000${NC}"
    echo -e "  ${GREEN}🔧${NC} Admin 后台: ${CYAN}http://localhost:8000/admin${NC}"
    echo -e "  ${GREEN}📋${NC} API 文档:   ${CYAN}http://localhost:8000/api/v1/docs/${NC}"
    echo ""
    echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
    echo ""

    granian novel_reader.asgi:application --host 0.0.0.0 --port 8000 --interface asgi --workers 1
}

cmd_dev() {
    print_banner
    check_env
    install_deps
    migrate_db
    create_superuser

    local mem_mb=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)
    if [ "$mem_mb" -gt 0 ] && [ "$mem_mb" -lt 1500 ]; then
        log_warning "可用内存 ${mem_mb}MB，不足同时运行 Django + Vite"
        log_step "切换为低内存模式：构建前端 → 启动后端"
        build_frontend
        source venv/bin/activate
        run_spin "收集静态文件" python manage.py collectstatic --noinput

        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  🚀 低内存开发模式启动!${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "  ${GREEN}📖${NC} 访问地址: ${CYAN}http://localhost:8000${NC}"
        echo -e "  ${YELLOW}⚠${NC}  前端变更需重新 ${CYAN}./start.sh build${NC}"
        echo ""

        granian novel_reader.asgi:application --host 0.0.0.0 --port 8000 --interface asgi --workers 1
    else
        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  🚀 开发模式启动!${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "  ${GREEN}📖${NC} 前端: ${CYAN}http://localhost:5173${NC}  (Vite HMR)"
        echo -e "  ${GREEN}🔧${NC} 后端: ${CYAN}http://localhost:8000${NC}  (Django runserver)"
        echo -e "  ${GREEN}📋${NC} API:  ${CYAN}http://localhost:8000/api/v1/docs/${NC}"
        echo ""
        echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
        echo ""

        source venv/bin/activate
        python manage.py runserver 0.0.0.0:8000 &
        cd frontend && npm run dev
    fi
}

cmd_stop() {
    log_step "停止服务"
    SEPARATOR
    local pids=$(pgrep -f "granian\|manage.py runserver\|vite" || true)
    if [ -n "$pids" ]; then
        for pid in $pids; do
            local cmd=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
            log_detail "终止进程 PID=$pid ($cmd)"
        done
        echo "$pids" | xargs kill 2>/dev/null || true
        sleep 1
        log_success "服务已停止"
    else
        log_warning "没有正在运行的服务"
    fi
}

cmd_status() {
    log_step "服务状态"
    SEPARATOR
    local found=0
    if pgrep -f "granian" > /dev/null; then
        log_success "Granian 服务: 运行中"
        log_detail "PID:  $(pgrep -f "granian")"
        log_detail "地址: http://localhost:8000"
        found=1
    fi
    if pgrep -f "manage.py runserver" > /dev/null; then
        log_success "Django 开发服务器: 运行中"
        log_detail "PID:  $(pgrep -f "manage.py runserver")"
        log_detail "地址: http://localhost:8000"
        found=1
    fi
    if pgrep -f "vite" > /dev/null; then
        log_success "Vite 开发服务器: 运行中"
        log_detail "PID:  $(pgrep -f "vite")"
        log_detail "地址: http://localhost:5173"
        found=1
    fi
    if [ $found -eq 0 ]; then
        log_warning "没有正在运行的服务"
        log_detail "使用 ./start.sh start 或 ./start.sh dev 启动"
    fi
}

cmd_migrate() {
    check_env
    install_deps
    migrate_db
}

cmd_build() {
    check_env
    install_deps
    build_frontend
    source venv/bin/activate
    log_step "收集静态文件"
    run_spin "收集静态文件" python manage.py collectstatic --noinput
    log_success "构建完成"
}

main() {
    local command="${1:-start}"
    case "$command" in
        start) cmd_start ;;
        dev) cmd_dev ;;
        stop) cmd_stop ;;
        restart) cmd_stop; sleep 1; cmd_start ;;
        status) cmd_status ;;
        migrate) cmd_migrate ;;
        build) cmd_build ;;
        help|--help|-h) show_help ;;
        *) log_error "未知命令: $command"; show_help; exit 1 ;;
    esac
}

main "$@"
