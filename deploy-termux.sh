#!/bin/bash
# Novel Reader - Android/Termux 部署脚本

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_termux() {
    if [ ! -d "/data/data/com.termux/files/usr" ]; then
        log_error "此脚本需要在 Termux 环境中运行"
        exit 1
    fi
    log_success "检测到 Termux 环境"
}

check_storage_permission() {
    if [ ! -d "$HOME/storage" ]; then
        log_info "请求存储权限..."
        termux-setup-storage
        sleep 2
    fi
}

main() {
    echo ""
    echo -e "${CYAN}  ╔═══════════════════════════════════════╗${NC}"
    echo -e "${CYAN}  ║  Novel Reader 部署脚本 (Termux)     ║${NC}"
    echo -e "${CYAN}  ╚═══════════════════════════════════════╝${NC}"
    echo ""
    check_termux
    check_storage_permission
    log_info "更新包列表..."
    pkg update -y
    log_info "安装系统依赖..."
    pkg install -y python python-pip git curl wget openssl libffi rust clang make libiconv
    log_success "系统依赖安装完成"
    log_info "创建 Python 虚拟环境..."
    if [ ! -d "$PROJECT_ROOT/venv" ]; then
        python -m venv "$PROJECT_ROOT/venv"
        log_success "虚拟环境已创建"
    fi
    source "$PROJECT_ROOT/venv/bin/activate"
    log_info "安装 Python 依赖..."
    pip install --upgrade pip setuptools wheel
    pip install fastapi==0.104.1 uvicorn[standard]==0.24.0 sqlalchemy[asyncio]==2.0.23 aiosqlite==0.19.0 redis==5.0.1 pydantic==2.5.2 pydantic-settings==2.1.0 python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4 python-multipart==0.0.6 aiohttp==3.9.1 beautifulsoup4==4.12.2 tenacity==8.2.3 python-magic==0.4.27 rich==13.7.0
    log_success "Python 依赖安装完成"
    mkdir -p "$PROJECT_ROOT/data"/{books,index,static,logs,cache}
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        if [ -f "$PROJECT_ROOT/.env.example" ]; then cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"; fi
    fi
    echo ""
    log_success "Termux 部署完成!"
    echo "启动服务: cd $PROJECT_ROOT && source venv/bin/activate && cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000"
}
main "$@"
