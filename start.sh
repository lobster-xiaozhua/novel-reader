#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
DIM='\033[2m'
BOLD='\033[1m'

STEP_NUM=0
TOTAL_STEPS=6

_timer_start=0
timer_start() { _timer_start=${SECONDS}; }
timer_elapsed() { echo $((SECONDS - _timer_start)); }
fmt_duration() {
    local s=$1
    if [ $s -lt 60 ]; then printf "%ds" $s
    else printf "%dm%ds" $((s/60)) $((s%60)); fi
}

log_info()    { echo -e "  ${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "  ${GREEN}✓${NC} $1"; }
log_warn()    { echo -e "  ${YELLOW}⚠${NC} $1"; }
log_error()   { echo -e "  ${RED}✗${NC} $1"; }
log_detail()  { echo -e "  ${DIM}→ $1${NC}"; }

log_step() {
    ((STEP_NUM++)) || true
    echo ""
    echo -e "${BOLD}${CYAN}[${STEP_NUM}/${TOTAL_STEPS}]${NC} ${BOLD}$1${NC}"
    timer_start
}

step_done() {
    local elapsed=$(fmt_duration $(timer_elapsed))
    echo -e "  ${GREEN}✓${NC} ${DIM}完成 (${elapsed})${NC}"
}

print_banner() {
    echo ""
    echo -e "${MAGENTA}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}  ${CYAN}Novel Reader v2.0 - 高性能小说阅读器${NC}        ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╚═══════════════════════════════════════════════════╝${NC}"
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
    log_step "环境检查"
    local errors=0

    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        ((errors++))
    else
        log_success "Python $(python3 --version | cut -d' ' -f2)"
    fi

    if ! command -v node &> /dev/null; then
        log_error "Node.js 未安装"
        ((errors++))
    else
        log_success "Node $(node --version)"
    fi

    if [ $errors -gt 0 ]; then
        log_error "环境检查失败"
        exit 1
    fi
    step_done
}

install_python_deps() {
    source venv/bin/activate

    if python -c "import django, ninja, granian" 2>/dev/null; then
        log_success "Python 依赖已就绪，跳过安装"
        return 0
    fi

    log_info "从阿里云 PyPI 镜像安装..."
    if [ ! -f requirements.txt ]; then
        log_error "requirements.txt 不存在"
        exit 1
    fi

    local pkg_count
    pkg_count=$(grep -cE '^[^#]' requirements.txt 2>/dev/null || echo "?")
    log_detail "共 ${pkg_count} 个依赖项"

    local install_output
    install_output=$(pip install -r requirements.txt \
        -i https://mirrors.aliyun.com/pypi/simple/ \
        --trusted-host mirrors.aliyun.com 2>&1) || {
        log_error "pip 安装失败"
        echo "$install_output" | grep -iE "error|failed|cannot" | head -5 | while read -r line; do
            log_error "  $line"
        done
        exit 1
    }

    local installed
    installed=$(echo "$install_output" | grep -c "Successfully installed" || true)
    if [ "$installed" -gt 0 ]; then
        local pkgs
        pkgs=$(echo "$install_output" | grep "Successfully installed" | sed 's/Successfully installed //')
        log_success "已安装: ${pkgs:0:80}..."
    fi

    if python -c "import django" 2>/dev/null; then
        return 0
    else
        log_error "Python 依赖验证失败，请检查网络或镜像源"
        exit 1
    fi
}

install_node_deps() {
    if [ ! -f frontend/package.json ]; then
        return 0
    fi

    if [ -d "frontend/node_modules" ] && [ -d "frontend/node_modules/react" ]; then
        log_success "Node 依赖已就绪，跳过安装"
        return 0
    fi

    if [ -d "frontend/node_modules" ]; then
        log_warn "Node 依赖目录损坏，正在清理并重新安装..."
        rm -rf frontend/node_modules
    fi

    log_info "从阿里云 npm 镜像安装..."
    cd frontend

    local install_output
    install_output=$(npm install --registry https://registry.npmmirror.com 2>&1) || {
        cd ..
        log_error "npm 安装失败"
        echo "$install_output" | grep -iE "ERR|error|ECONNREFUSED" | head -5 | while read -r line; do
            log_error "  $line"
        done
        exit 1
    }

    local added
    added=$(echo "$install_output" | grep -oE 'added [0-9]+ packages' || true)
    if [ -n "$added" ]; then
        log_success "$added"
    fi
    cd ..

    if [ -d "frontend/node_modules/react" ]; then
        return 0
    else
        log_error "Node 依赖安装失败"
        exit 1
    fi
}

install_deps() {
    log_step "安装依赖"
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_success "虚拟环境已创建"
    fi

    log_info "Python 依赖..."
    install_python_deps
    log_info "Node 依赖..."
    install_node_deps
    step_done
}

migrate_db() {
    log_step "数据库迁移"
    source venv/bin/activate

    local output
    output=$(python manage.py migrate 2>&1) || {
        log_error "数据库迁移失败"
        echo "$output" | tail -5 | while read -r line; do
            log_error "  $line"
        done
        exit 1
    }

    local applied
    applied=$(echo "$output" | grep -c "Applying\|OK" || true)
    if [ "$applied" -gt 0 ]; then
        echo "$output" | grep "Applying" | while read -r line; do
            log_detail "$line"
        done
    else
        log_detail "无待执行的迁移"
    fi
    step_done
}

create_superuser() {
    log_step "初始化管理员"
    source venv/bin/activate

    local result
    result=$(python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    import secrets, string
    pwd = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
    User.objects.create_superuser('admin', 'admin@example.com', pwd)
    print(f'CREATED:admin:{pwd}')
else:
    print('EXISTS:admin')
" 2>&1) || true

    if [[ "$result" == CREATED:* ]]; then
        local pwd="${result#CREATED:admin:}"
        log_success "管理员账号: admin / $pwd"
        log_warn "请妥善保存此密码！"
    else
        log_success "管理员账号已存在: admin"
    fi
    step_done
}

build_frontend() {
    log_step "构建前端"
    if [ ! -d "frontend/node_modules" ]; then
        install_node_deps
    fi

    cd frontend
    local output
    output=$(npm run build 2>&1) || {
        cd ..
        log_error "前端构建失败"
        echo "$output" | grep -iE "error|failed" | head -5 | while read -r line; do
            log_error "  $line"
        done
        exit 1
    }

    local build_time
    build_time=$(echo "$output" | grep -oE 'built in [0-9]+ms' || true)
    local chunk_count
    chunk_count=$(echo "$output" | grep -cE "^dist/" || true)
    log_detail "${chunk_count} 个文件, ${build_time}"
    cd ..
    step_done
}

start_server() {
    local port="${1:-8000}"
    source venv/bin/activate

    log_step "启动服务"
    local static_output
    static_output=$(python manage.py collectstatic --noinput 2>&1) || true
    local static_count
    static_count=$(echo "$static_output" | grep -oE '[0-9]+ static files' || true)
    log_detail "静态文件: ${static_count}"

    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  🚀 服务已启动!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${GREEN}📖${NC} 访问地址:  ${BOLD}http://localhost:${port}${NC}"
    echo -e "  ${GREEN}🔧${NC} Admin 后台: http://localhost:${port}/admin"
    echo -e "  ${GREEN}📋${NC} API 文档:   http://localhost:${port}/api/v1/docs/"
    echo ""
    echo -e "  ${DIM}按 Ctrl+C 停止服务${NC}"
    echo ""

    exec granian novel_reader.asgi:application \
        --host 0.0.0.0 --port "$port" \
        --interface asgi --workers 1
}

cmd_start() {
    print_banner
    check_env
    install_deps
    migrate_db
    create_superuser
    build_frontend
    start_server 8000
}

cmd_dev() {
    TOTAL_STEPS=4
    print_banner
    check_env
    install_deps
    migrate_db
    create_superuser

    local mem_mb=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)
    if [ "$mem_mb" -gt 0 ] && [ "$mem_mb" -lt 1500 ]; then
        log_warn "可用内存 ${mem_mb}MB，不足同时运行 Django + Vite"
        log_info "切换为低内存模式：构建前端 → 启动后端"
        build_frontend
        start_server 8000
    else
        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  🛠️  开发模式启动!${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "  ${GREEN}📖${NC} 前端: ${BOLD}http://localhost:5173${NC}"
        echo -e "  ${GREEN}🔧${NC} 后端: http://localhost:8000"
        echo ""

        source venv/bin/activate
        python manage.py runserver 0.0.0.0:8000 &
        cd frontend && exec npm run dev
    fi
}

cmd_stop() {
    log_step "停止服务"
    local pids=$(pgrep -f "granian|manage.py runserver|vite" || true)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill 2>/dev/null || true
        log_success "服务已停止"
    else
        log_warn "服务未运行"
    fi
}

cmd_status() {
    log_step "服务状态"
    if pgrep -f "granian" > /dev/null; then
        log_success "Granian 服务: 运行中 (PID: $(pgrep -f "granian" | head -1))"
        log_detail "http://localhost:8000"
    elif pgrep -f "manage.py runserver" > /dev/null; then
        log_success "Django 开发服务器: 运行中 (PID: $(pgrep -f "manage.py runserver" | head -1))"
        log_detail "http://localhost:8000"
    else
        log_warn "服务未运行"
    fi
}

cmd_migrate() {
    TOTAL_STEPS=3
    check_env
    install_deps
    migrate_db
}

cmd_build() {
    TOTAL_STEPS=3
    check_env
    install_deps
    build_frontend
    source venv/bin/activate
    python manage.py collectstatic --noinput 2>&1 | tail -1
    step_done
    log_success "构建完成"
}

main() {
    local command="${1:-start}"
    case "$command" in
        start)   cmd_start ;;
        dev)     cmd_dev ;;
        stop)    cmd_stop ;;
        restart) cmd_stop; sleep 1; cmd_start ;;
        status)  cmd_status ;;
        migrate) cmd_migrate ;;
        build)   cmd_build ;;
        help|--help|-h) show_help ;;
        *) log_error "未知命令: $command"; show_help; exit 1 ;;
    esac
}

main "$@"
