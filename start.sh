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
TOTAL_STEPS=8

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
    echo -e "${MAGENTA}║${NC}  ${DIM}PG + Redis + DiskCache + 液态玻璃 UI${NC}          ${MAGENTA}║${NC}"
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
  services   启动基础设施（PG/Redis/ES）
  help       显示此帮助

示例:
  ./start.sh start          # 启动生产服务
  ./start.sh services       # 仅启动 PG + Redis
  ./start.sh dev            # 开发模式
  ./start.sh build          # 构建前端
EOF
}

# ─── Infrastructure ───

_ensure_postgres() {
    log_info "PostgreSQL 未运行，正在检查..."

    # 尝试直接启动已有实例
    if command -v pg_ctlcluster &>/dev/null; then
        local cluster
        cluster=$(pg_lsclusters -h 2>/dev/null | head -1 | awk '{print $1, $2}')
        if [ -n "$cluster" ]; then
            log_info "尝试启动 PostgreSQL 集群 ($cluster)..."
            if pg_ctlcluster $cluster start 2>/dev/null; then
                sleep 2
                if pg_isready -q 2>/dev/null; then
                    log_success "PostgreSQL 已启动"
                    _setup_postgres_user_and_db
                    return 0
                fi
            fi
        fi
    fi

    # 尝试 pg_ctl 直接启动
    if command -v pg_ctl &>/dev/null; then
        log_info "尝试 pg_ctl 启动..."
        local pgdata=""
        for d in /var/lib/postgresql/*/main /var/lib/pgsql/*/data /usr/local/var/postgres; do
            [ -f "$d/PG_VERSION" ] && pgdata="$d" && break
        done
        if [ -n "$pgdata" ]; then
            su - postgres -c "pg_ctl -D $pgdata -l $pgdata/logfile start" 2>/dev/null && {
                sleep 2
                pg_isready -q 2>/dev/null && log_success "PostgreSQL 已启动" && return 0
            }
        fi
    fi

    # 自动安装 PostgreSQL
    log_info "PostgreSQL 未安装，开始自动安装..."
    if command -v apt-get &>/dev/null; then
        log_info "使用 apt 安装 PostgreSQL..."
        apt-get update -qq >/dev/null 2>&1 && \
        apt-get install -y -qq postgresql postgresql-contrib >/dev/null 2>&1 || {
            log_error "PostgreSQL 安装失败"
            log_info "请手动执行: sudo apt-get install postgresql postgresql-contrib"
            return 1
        }
    elif command -v pkg &>/dev/null; then
        log_info "Termux 环境，使用 pkg 安装 PostgreSQL..."
        pkg install -y postgresql 2>/dev/null || {
            log_error "PostgreSQL 安装失败"
            log_info "请手动执行: pkg install postgresql"
            return 1
        }
    elif command -v yum &>/dev/null; then
        log_info "使用 yum 安装 PostgreSQL..."
        yum install -y postgresql-server postgresql-contrib >/dev/null 2>&1 || {
            log_error "PostgreSQL 安装失败"
            return 1
        }
        # 首次安装需要初始化
        if command -v postgresql-setup &>/dev/null; then
            postgresql-setup --initdb --unit postgresql 2>/dev/null || true
        fi
    elif command -v dnf &>/dev/null; then
        log_info "使用 dnf 安装 PostgreSQL..."
        dnf install -y postgresql-server postgresql-contrib >/dev/null 2>&1 || {
            log_error "PostgreSQL 安装失败"
            return 1
        }
    else
        log_error "不支持的包管理器，无法自动安装 PostgreSQL"
        log_info "请手动安装 PostgreSQL 15+ 后重试"
        return 1
    fi

    log_success "PostgreSQL 安装完成"

    # 初始化并启动
    _start_postgres_after_install
}

_start_postgres_after_install() {
    # 查找 pg_ctlcluster 或 pg_ctl
    if command -v pg_ctlcluster &>/dev/null; then
        local cluster
        cluster=$(pg_lsclusters -h 2>/dev/null | head -1 | awk '{print $1, $2}')
        if [ -n "$cluster" ]; then
            log_info "启动 PostgreSQL ($cluster)..."
            pg_ctlcluster $cluster start 2>/dev/null || true
        fi
    elif command -v pg_ctl &>/dev/null; then
        local pgdata=""
        for d in /var/lib/postgresql/*/main /var/lib/pgsql/*/data /usr/local/var/postgres ~/.termux/postgresql/data; do
            [ -f "$d/PG_VERSION" ] && pgdata="$d" && break
        done
        if [ -n "$pgdata" ]; then
            su - postgres -c "pg_ctl -D $pgdata -l $pgdata/logfile start" 2>/dev/null || \
                pg_ctl -D "$pgdata" -l "$pgdata/logfile" start 2>/dev/null || true
        fi
    elif command -v pg-ctl &>/dev/null; then
        # Termux
        pg_ctl -D ${PREFIX:-/data/data/com.termux/files/usr}/var/postgresql start 2>/dev/null || true
    fi

    sleep 3

    if pg_isready -q 2>/dev/null; then
        log_success "PostgreSQL 已启动"
        _setup_postgres_user_and_db
        return 0
    else
        log_error "PostgreSQL 启动失败"
        log_info "请检查: pg_ctlcluster <version> <cluster> start"
        return 1
    fi
}

_setup_postgres_user_and_db() {
    local pg_user="${PG_USER:-novel_user}"
    local pg_pass="${PG_PASS:-novel_pass}"
    local pg_db="${PG_DB:-novel_reader}"

    # 检查用户是否已存在
    local user_exists
    user_exists=$(su - postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='$pg_user'\"" 2>/dev/null || echo "")

    if [ "$user_exists" != "1" ]; then
        log_info "创建 PostgreSQL 用户: $pg_user"
        su - postgres -c "psql -c \"CREATE USER $pg_user WITH PASSWORD '$pg_pass' CREATEDB;\"" 2>/dev/null || {
            log_warn "创建用户失败，可能权限不足，尝试使用 sudo"
            sudo -u postgres psql -c "CREATE USER $pg_user WITH PASSWORD '$pg_pass' CREATEDB;" 2>/dev/null || \
                log_warn "无法创建 PostgreSQL 用户，请手动创建"
        }
    fi

    # 检查数据库是否存在
    local db_exists
    db_exists=$(su - postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='$pg_db'\"" 2>/dev/null || echo "")

    if [ "$db_exists" != "1" ]; then
        log_info "创建数据库: $pg_db"
        su - postgres -c "psql -c \"CREATE DATABASE $pg_db OWNER $pg_user;\"" 2>/dev/null || \
            sudo -u postgres psql -c "CREATE DATABASE $pg_db OWNER $pg_user;" 2>/dev/null || \
            log_warn "无法创建数据库，请手动创建"
    fi

    log_success "PostgreSQL 用户和数据库已就绪"
}

start_infra() {
    log_step "启动基础设施"

    # PostgreSQL
    if pg_isready -q 2>/dev/null; then
        log_success "PostgreSQL 已运行"
    else
        _ensure_postgres || {
            log_error "PostgreSQL 无法启动，系统无法运行"
            log_info "这是一个硬性依赖，请手动安装后重试"
            exit 1
        }
    fi

    # Redis
    if redis-cli ping 2>/dev/null | grep -q PONG; then
        log_success "Redis 已运行"
    else
        log_info "启动 Redis..."
        redis-server --daemonize yes --maxmemory 256mb --maxmemory-policy allkeys-lru 2>/dev/null && \
            log_success "Redis 已启动" || \
            log_warn "Redis 启动失败，将使用 DiskCache 模式"
    fi

    # Elasticsearch (optional)
    if curl -sf http://localhost:9200 > /dev/null 2>&1; then
        log_success "Elasticsearch 已运行"
        ES_AVAILABLE=true
    else
        if command -v elasticsearch &> /dev/null || [ -d "/usr/share/elasticsearch" ]; then
            log_info "启动 Elasticsearch..."
            systemctl start elasticsearch 2>/dev/null || \
                /usr/share/elasticsearch/bin/elasticsearch -d 2>/dev/null || \
                log_warn "Elasticsearch 启动失败"
            sleep 5
            if curl -sf http://localhost:9200 > /dev/null 2>&1; then
                log_success "Elasticsearch 已运行"
                ES_AVAILABLE=true
            else
                log_warn "Elasticsearch 未就绪，搜索将降级为数据库模式"
            fi
        else
            log_detail "Elasticsearch 未安装，搜索使用 PostgreSQL LIKE 模式"
        fi
    fi

    step_done
}

check_env() {
    log_step "环境检查"
    local errors=0

    # 检测 Termux 环境
    IS_TERMUX=false
    if [ -d "/data/data/com.termux" ] || [ -n "${TERMUX_VERSION:-}" ] || [ "$(uname -o 2>/dev/null)" = "Android" ]; then
        IS_TERMUX=true
        log_info "检测到 Termux 环境"
    fi

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
        local node_ver=$(node --version)
        log_success "Node ${node_ver}"

        # Termux 下检测 Node 兼容性
        if [ "$IS_TERMUX" = true ]; then
            local node_path=$(which node)
            if [[ "$node_path" == *".nvm"* ]]; then
                log_warn "当前 Node 通过 nvm 安装，在 Termux 下可能不兼容"
                log_info "建议执行: nvm uninstall $(nvm current) && pkg install nodejs-lts"
            fi

            if ! node -e "console.log('ok')" 2>/dev/null; then
                log_error "Node.js 无法正常运行 (Illegal instruction?)"
                log_info "修复方法:"
                log_detail "1. nvm uninstall $(nvm current 2>/dev/null || echo '版本')"
                log_detail "2. pkg install nodejs-lts"
                log_detail "3. 重新运行 ./start.sh"
                ((errors++))
            fi
        fi
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

    # 如果已有构建产物，跳过
    if [ -f "frontend/dist/index.html" ]; then
        log_success "前端已构建，跳过（删除 frontend/dist 可强制重建）"
        return 0
    fi

    if [ ! -d "frontend/node_modules" ] || [ ! -d "frontend/node_modules/react" ]; then
        install_node_deps
    fi

    cd frontend

    # 显示前端环境信息
    log_detail "Node: $(node --version) | npm: $(npm --version)"
    log_detail "工作目录：$(pwd)"

    # 内存检查
    local mem_mb=0
    if [ -f "/proc/meminfo" ]; then
        mem_mb=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)
    fi
    log_detail "可用内存: ${mem_mb}MB"

    # Termux / 低内存环境优化
    local build_cmd="./node_modules/.bin/vite build"
    local node_opts=""

    if [ "$IS_TERMUX" = true ]; then
        log_info "Termux 环境：优化构建配置"
        # 限制 Node 堆内存，防止 OOM
        if [ "$mem_mb" -gt 0 ] && [ "$mem_mb" -lt 2048 ]; then
            local heap_mb=$((mem_mb * 70 / 100))
            node_opts="--max-old-space-size=${heap_mb}"
            log_detail "内存限制: ${heap_mb}MB (--max-old-space-size)"
        fi
    fi

    export NODE_OPTIONS="${node_opts}"

    local output
    local start_time=$SECONDS
    output=$($build_cmd 2>&1)
    local exit_code=$?
    local build_seconds=$((SECONDS - start_time))

    unset NODE_OPTIONS

    if [ $exit_code -ne 0 ]; then
        # 检测 OOM / 内存不足
        if echo "$output" | grep -qiE "OOM|out of memory|Cannot allocate|killed"; then
            cd ..
            log_error "内存不足，前端构建失败"
            log_info "解决方案:"
            log_detail "1. 关闭其他应用释放内存后重试"
            log_detail "2. 使用预构建版本: 从仓库拉取 frontend/dist/"
            log_detail "3. 在电脑上构建后拷贝 dist/ 到手机"
            exit 1
        fi

        # 检测 Illegal instruction 错误
        if echo "$output" | grep -qiE "Illegal instruction|SIGILL"; then
            cd ..
            log_error "Node.js 与当前 CPU 不兼容 (Illegal instruction)"
            log_info "修复方法:"
            log_detail "1. 卸载 nvm Node: nvm uninstall $(nvm current 2>/dev/null || echo '版本')"
            log_detail "2. 安装 Termux 原生 Node: pkg install nodejs-lts"
            log_detail "3. 清理并重建: cd frontend && rm -rf node_modules && npm install"
            log_detail "4. 重新运行: ./start.sh"
            exit 1
        fi

        cd ..
        log_error "前端构建失败 (退出码：$exit_code, 耗时：${build_seconds}s)"
        echo ""

        # 输出完整日志（不截断）
        echo -e "${DIM}===== 完整构建日志 =====${NC}"
        echo "$output"
        echo -e "${DIM}===== 日志结束 =====${NC}"
        echo ""

        # 常见错误诊断
        if echo "$output" | grep -qiE "ENOENT|Cannot find module|Module not found"; then
            log_error "诊断：缺少依赖模块"
            log_detail "建议：cd frontend && rm -rf node_modules && npm install && npm run build"
        elif echo "$output" | grep -qiE "SyntaxError|Unexpected token"; then
            log_error "诊断：代码语法错误"
            log_detail "建议：检查最近修改的 TypeScript/JSX 文件"
        elif echo "$output" | grep -qiE "Type.*error|TS[0-9]+"; then
            log_error "诊断：TypeScript 类型错误"
            log_detail "建议：cd frontend && npx tsc --noEmit 查看详细信息"
        elif echo "$output" | grep -qiE "EACCES|permission denied"; then
            log_error "诊断：权限不足"
            log_detail "建议：sudo chown -R $USER:$USER frontend/"
        else
            log_error "诊断：未知错误，请查看上方完整日志"
            log_detail "建议：cd frontend && rm -rf node_modules dist && npm install && npm run build"
        fi

        exit 1
    fi

    local build_time
    build_time=$(echo "$output" | grep -oE 'built in [0-9]+ms' || echo "耗时 ${build_seconds}s")
    local chunk_count
    chunk_count=$(echo "$output" | grep -cE "^dist/" || true)

    # 显示构建产物大小
    local total_size
    if command -v du &> /dev/null; then
        total_size=$(du -sh dist/ 2>/dev/null | cut -f1 || echo "?")
        log_detail "${chunk_count} 个文件，${build_time}, 总大小：${total_size}"
    else
        log_detail "${chunk_count} 个文件，${build_time}"
    fi

    cd ..

    # 同步 index.html 到 Django 模板（自动更新 JS/CSS 引用）
    if [ -f "frontend/dist/index.html" ]; then
        python3 -c "
import re, sys
with open('frontend/dist/index.html', 'r') as f:
    html = f.read()
# 将 /static/ 替换为 {% static '' %} 标签
html = html.replace('src=\"/static/', 'src=\"{% static \\'')
html = html.replace('.js\"></script>', '.js\\' %}\"></script>')
html = html.replace('href=\"/static/', 'href=\"{% static \\'')
html = html.replace('.js\">', '.js\\' %}\">')
html = html.replace('.css\">', '.css\\' %}\">')
# 添加 Django static tag
if '{% load static %}' not in html:
    html = '{% load static %}' + html
with open('templates/index.html', 'w') as f:
    f.write(html)
print('index.html 已同步')
" 2>/dev/null && log_detail "Django 模板已同步"
    fi

    step_done
}

start_server() {
    local port="${1:-8000}"
    source venv/bin/activate

    log_step "启动服务"
    local static_output
    static_output=$(python manage.py collectstatic --noinput --clear 2>&1)
    local static_count
    static_count=$(echo "$static_output" | grep -oE '[0-9]+ static files' || true)
    log_detail "静态文件: ${static_count}"

    # 如果 collectstatic 失败，显示错误
    if [ -z "$static_count" ]; then
        log_warn "静态文件收集异常"
        echo "$static_output" | tail -5 | while IFS= read -r line; do
            log_detail "$line"
        done
    fi

    # 初始化引擎（推荐/搜索/缓存预热）
    log_info "初始化系统引擎..."
    python manage.py init_engines 2>&1 || {
        log_warn "引擎初始化异常，服务仍可运行"
    }

    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  🚀 服务已启动!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${GREEN}📖${NC} 访问地址:  ${BOLD}http://localhost:${port}${NC}"
    echo -e "  ${GREEN}🔧${NC} Admin 后台: http://localhost:${port}/admin"
    echo -e "  ${GREEN}📋${NC} API 文档:   http://localhost:${port}/api/v1/docs/"
    echo -e "  ${GREEN}📊${NC} 性能监控:   http://localhost:${port}/api/v1/health/perf/"
    echo ""
    echo -e "  ${DIM}按 Ctrl+C 停止服务${NC}"
    echo ""

    # 后台预热 API 缓存，避免首次请求慢
    (sleep 3 && curl -sf http://localhost:${port}/api/v1/books/ > /dev/null 2>&1 && \
     curl -sf http://localhost:${port}/api/v1/books/rankings/ > /dev/null 2>&1 && \
     log_detail "API 缓存预热完成") &

    exec granian novel_reader.asgi:application \
        --host 0.0.0.0 --port "$port" \
        --interface asginl --workers 1
}

cmd_start() {
    print_banner
    TOTAL_STEPS=8
    start_infra
    check_env
    install_deps
    migrate_db
    create_superuser
    build_frontend
    start_server 8000
}

cmd_dev() {
    print_banner
    TOTAL_STEPS=5
    start_infra
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

    # PostgreSQL
    if pg_isready -q 2>/dev/null; then
        log_success "PostgreSQL: 运行中"
    else
        log_warn "PostgreSQL: 未运行"
    fi

    # Redis
    if redis-cli ping 2>/dev/null | grep -q PONG; then
        log_success "Redis: 运行中"
    else
        log_warn "Redis: 未运行"
    fi

    # Elasticsearch
    if curl -sf http://localhost:9200 > /dev/null 2>&1; then
        log_success "Elasticsearch: 运行中"
    else
        log_warn "Elasticsearch: 未运行 (搜索将使用 PostgreSQL 模式)"
    fi

    # App
    if pgrep -f "granian" > /dev/null; then
        log_success "Granian 服务: 运行中 (PID: $(pgrep -f "granian" | head -1))"
        log_detail "http://localhost:8000"
    elif pgrep -f "manage.py runserver" > /dev/null; then
        log_success "Django 开发服务器: 运行中 (PID: $(pgrep -f "manage.py runserver" | head -1))"
        log_detail "http://localhost:8000"
    else
        log_warn "应用服务: 未运行"
    fi
}

cmd_migrate() {
    TOTAL_STEPS=4
    print_banner
    start_infra
    check_env
    install_deps
    migrate_db
}

cmd_build() {
    TOTAL_STEPS=4
    print_banner
    check_env
    install_deps
    build_frontend
    source venv/bin/activate
    python manage.py collectstatic --noinput 2>&1 | tail -1
    step_done
    log_success "构建完成"
}

cmd_services() {
    TOTAL_STEPS=1
    print_banner
    start_infra
    echo ""
    echo -e "${GREEN}基础设施已启动:${NC}"
    if pg_isready -q 2>/dev/null; then log_detail "  PostgreSQL: localhost:5432"; fi
    if redis-cli ping 2>/dev/null | grep -q PONG; then log_detail "  Redis: localhost:6379"; fi
    if curl -sf http://localhost:9200 > /dev/null 2>&1; then log_detail "  Elasticsearch: localhost:9200"; fi
}

main() {
    local command="${1:-start}"
    case "$command" in
        start)     cmd_start ;;
        dev)       cmd_dev ;;
        stop)      cmd_stop ;;
        restart)   cmd_stop; sleep 1; cmd_start ;;
        status)    cmd_status ;;
        migrate)   cmd_migrate ;;
        build)     cmd_build ;;
        services)  cmd_services ;;
        help|--help|-h) show_help ;;
        *) log_error "未知命令: $command"; show_help; exit 1 ;;
    esac
}

main "$@"
