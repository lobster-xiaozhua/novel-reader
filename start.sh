#!/bin/bash
set -e

cd "$(dirname "$0")"

# 颜色输出
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
    echo -e "${MAGENTA}║${NC}  ${CYAN}Novel Reader - Django 小说阅读器${NC}                ${MAGENTA}║${NC}"
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
  createsuperuser  创建超级用户
  shell      进入 Django shell
  help       显示此帮助

示例:
  ./start.sh start          # 启动服务
  ./start.sh stop           # 停止服务
  ./start.sh restart        # 重启服务
  ./start.sh migrate        # 数据库迁移
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
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    log_success "依赖安装完成"
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
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin / admin123')
else:
    print('Superuser admin already exists')
" 2>/dev/null || true
}

collect_static() {
    log_step "收集静态文件..."
    source venv/bin/activate
    python manage.py collectstatic --noinput 2>/dev/null || true
}

cmd_start() {
    print_banner
    check_env
    install_deps
    migrate_db
    collect_static
    create_superuser

    log_step "启动 Django 开发服务器..."
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  服务已启动!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${GREEN}📖${NC} 访问地址:  http://localhost:8000"
    echo -e "  ${GREEN}🔧${NC} Admin 后台: http://localhost:8000/admin"
    echo -e "  ${GREEN}👤${NC} 默认账号:  admin / admin123"
    echo ""
    echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
    echo ""

    python manage.py runserver 0.0.0.0:8000
}

cmd_stop() {
    log_step "停止服务..."
    local pids=$(pgrep -f "manage.py runserver" || true)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill 2>/dev/null || true
        log_success "服务已停止"
    else
        log_warning "服务未运行"
    fi
}

cmd_status() {
    log_step "服务状态"
    if pgrep -f "manage.py runserver" > /dev/null; then
        log_success "Django 服务: 运行中"
        echo "  PID: $(pgrep -f "manage.py runserver")"
        echo "  地址: http://localhost:8000"
    else
        log_error "Django 服务: 未运行"
    fi
}

cmd_migrate() {
    check_env
    install_deps
    migrate_db
}

cmd_createsuperuser() {
    check_env
    install_deps
    source venv/bin/activate
    python manage.py createsuperuser
}

cmd_shell() {
    check_env
    install_deps
    source venv/bin/activate
    python manage.py shell
}

main() {
    local command="${1:-start}"
    case "$command" in
        start) cmd_start ;;
        stop) cmd_stop ;;
        restart) cmd_stop; sleep 1; cmd_start ;;
        status) cmd_status ;;
        migrate) cmd_migrate ;;
        createsuperuser) cmd_createsuperuser ;;
        shell) cmd_shell ;;
        help|--help|-h) show_help ;;
        *) log_error "未知命令: $command"; show_help; exit 1 ;;
    esac
}

main "$@"
