#!/bin/bash
set -e

cd "$(dirname "$0")"

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
log_step() { echo -e "${CYAN}[→]${NC} $1"; }

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
    log_step "检查环境..."
    local errors=0

    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        ((errors++))
    else
        log_success "Python: $(python3 --version | cut -d' ' -f2)"
    fi

    if ! command -v node &> /dev/null; then
        log_error "Node.js 未安装"
        ((errors++))
    else
        log_success "Node: $(node --version)"
    fi

    if [ $errors -gt 0 ]; then
        log_error "环境检查失败"
        exit 1
    fi
    log_success "环境检查通过"
}

install_deps() {
    log_step "安装依赖..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_success "虚拟环境已创建"
    fi
    source venv/bin/activate
    log_info "使用阿里云 PyPI 镜像..."
    pip install -q --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/
    pip install -q -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
    log_success "Python 依赖安装完成"

    if [ -f "frontend/package.json" ]; then
        cd frontend
        if [ ! -d "node_modules" ]; then
            log_info "使用阿里云 npm 镜像..."
            npm ci --prefer-offline --registry https://registry.npmmirror.com 2>/dev/null || npm install --registry https://registry.npmmirror.com
        fi
        cd ..
        log_success "Node 依赖安装完成"
    fi
}

migrate_db() {
    log_step "执行数据库迁移..."
    source venv/bin/activate
    python manage.py migrate
    log_success "数据库迁移完成"
}

create_superuser() {
    log_step "创建超级用户..."
    source venv/bin/activate
    python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    import secrets, string
    pwd = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
    User.objects.create_superuser('admin', 'admin@example.com', pwd)
    print(f'Superuser created: admin / {pwd}')
    print('请妥善保存此密码！')
else:
    print('Superuser admin already exists')
" 2>/dev/null || true
}

build_frontend() {
    log_step "构建前端..."
    cd frontend
    npm run build
    cd ..
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
    python manage.py collectstatic --noinput 2>/dev/null || true

    log_step "启动 Granian ASGI 服务器..."
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  服务已启动!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${GREEN}📖${NC} 访问地址:  http://localhost:8000"
    echo -e "  ${GREEN}🔧${NC} Admin 后台: http://localhost:8000/admin"
    echo -e "  ${GREEN}📋${NC} API 文档:   http://localhost:8000/api/v1/docs/"
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
        python manage.py collectstatic --noinput 2>/dev/null || true

        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  低内存开发模式启动!${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "  ${GREEN}📖${NC} 访问地址: http://localhost:8000"
        echo -e "  ${YELLOW}⚠${NC}  前端变更需重新 ${CYAN}./start.sh build${NC}"
        echo ""

        granian novel_reader.asgi:application --host 0.0.0.0 --port 8000 --interface asgi --workers 1
    else
        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  开发模式启动!${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "  ${GREEN}📖${NC} 前端: http://localhost:5173"
        echo -e "  ${GREEN}🔧${NC} 后端: http://localhost:8000"
        echo ""

        source venv/bin/activate
        python manage.py runserver 0.0.0.0:8000 &
        cd frontend && npm run dev
    fi
}

cmd_stop() {
    log_step "停止服务..."
    local pids=$(pgrep -f "granian\|manage.py runserver\|vite" || true)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill 2>/dev/null || true
        log_success "服务已停止"
    else
        log_warning "服务未运行"
    fi
}

cmd_status() {
    log_step "服务状态"
    if pgrep -f "granian" > /dev/null; then
        log_success "Granian 服务: 运行中"
        echo "  PID: $(pgrep -f "granian")"
        echo "  地址: http://localhost:8000"
    elif pgrep -f "manage.py runserver" > /dev/null; then
        log_success "Django 开发服务器: 运行中"
        echo "  PID: $(pgrep -f "manage.py runserver")"
        echo "  地址: http://localhost:8000"
    else
        log_error "服务: 未运行"
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
    python manage.py collectstatic --noinput 2>/dev/null || true
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
