#!/bin/bash
# Novel Reader - Linux 部署脚本
# 支持 apt/yum/dnf/pacman/zypper 等包管理器

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

show_help() {
    cat << EOF
用法: ./deploy.sh [选项]

选项:
  -d, --docker      使用 Docker 部署 (默认)
  -n, --native      原生 Python 部署
  -p, --python VERSION   指定 Python 版本 (如 3.10, 3.11)
  -h, --help        显示此帮助信息

示例:
  ./deploy.sh              # 使用 Docker 部署
  ./deploy.sh -n           # 原生部署
  ./deploy.sh -p 3.11      # 使用 Python 3.11 原生部署
EOF
}

detect_package_manager() {
    if command -v apt-get &> /dev/null; then echo "apt"
    elif command -v yum &> /dev/null; then echo "yum"
    elif command -v dnf &> /dev/null; then echo "dnf"
    elif command -v pacman &> /dev/null; then echo "pacman"
    elif command -v zypper &> /dev/null; then echo "zypper"
    else echo "unknown"
    fi
}

install_deps_apt() {
    log_info "安装系统依赖 (apt)..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv git curl build-essential libffi-dev libssl-dev libmagic1 nginx docker.io docker-compose || sudo apt-get install -y docker-compose
    log_success "系统依赖安装完成"
}

install_deps_yum() {
    log_info "安装系统依赖 (yum)..."
    sudo yum install -y python3 python3-pip python3-devel gcc gcc-c++ make libffi-devel openssl-devel file nginx docker || true
    sudo pip3 install docker-compose || true
    log_success "系统依赖安装完成"
}

install_deps_dnf() {
    log_info "安装系统依赖 (dnf)..."
    sudo dnf install -y python3 python3-pip python3-devel gcc gcc-c++ make libffi-devel openssl-devel file-devel nginx docker docker-compose
    log_success "系统依赖安装完成"
}

install_deps_pacman() {
    log_info "安装系统依赖 (pacman)..."
    sudo pacman -Sy --noconfirm python python-pip base-devel libffi openssl file nginx docker docker-compose
    log_success "系统依赖安装完成"
}

install_deps_zypper() {
    log_info "安装系统依赖 (zypper)..."
    sudo zypper install -y python3 python3-pip python3-devel gcc gcc-c++ make libffi-devel libopenssl-devel file nginx docker docker-compose
    log_success "系统依赖安装完成"
}

install_system_deps() {
    local pm=$(detect_package_manager)
    log_info "检测到包管理器: $pm"
    case $pm in
        apt) install_deps_apt ;;
        yum) install_deps_yum ;;
        dnf) install_deps_dnf ;;
        pacman) install_deps_pacman ;;
        zypper) install_deps_zypper ;;
        *) log_warn "未检测到支持的包管理器，请手动安装依赖" ;;
    esac
}

deploy_docker() {
    log_info "使用 Docker 部署..."
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        install_system_deps
        if ! command -v docker &> /dev/null; then log_error "Docker 安装失败"; exit 1; fi
    fi
    log_success "Docker: $(docker --version)"
    if command -v systemctl &> /dev/null; then
        sudo systemctl start docker 2>/dev/null || true
        sudo systemctl enable docker 2>/dev/null || true
    fi
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        if [ -f "$PROJECT_ROOT/.env.example" ]; then cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"; fi
    fi
    COMPOSE_CMD="docker compose"
    if ! docker compose version &> /dev/null; then COMPOSE_CMD="docker-compose"; fi
    cd "$PROJECT_ROOT" && $COMPOSE_CMD up -d --build
    if [ $? -eq 0 ]; then
        log_success "服务启动成功!"
        log_info "访问 http://localhost:3000 查看前端"
        log_info "API 文档: http://localhost:8000/docs"
    else log_error "服务启动失败"; exit 1; fi
}

deploy_native() {
    log_info "原生 Python 部署..."
    local python_cmd="python3"
    if ! command -v python3 &> /dev/null; then
        python_cmd="python"
        if ! command -v python &> /dev/null; then
            log_error "Python 未安装"
            install_system_deps
            if ! command -v python3 &> /dev/null; then log_error "Python 安装失败"; exit 1; fi
        fi
    fi
    log_success "Python: $($python_cmd --version)"
    VENV_PATH="$PROJECT_ROOT/venv"
    if [ ! -d "$VENV_PATH" ]; then
        log_info "创建虚拟环境..."
        $python_cmd -m venv "$VENV_PATH"
        log_success "虚拟环境已创建"
    fi
    source "$VENV_PATH/bin/activate"
    log_info "升级 pip..."
    pip install --upgrade pip
    log_info "安装 Python 依赖..."
    pip install -r "$PROJECT_ROOT/backend/requirements.txt"
    if [ $? -ne 0 ]; then log_error "依赖安装失败"; exit 1; fi
    log_success "依赖安装完成"
    for dir in books index static logs cache; do mkdir -p "$PROJECT_ROOT/data/$dir"; done
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        if [ -f "$PROJECT_ROOT/.env.example" ]; then cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"; log_success "请编辑 .env 文件设置密钥"; fi
    fi
    log_success "原生部署配置完成"
}

main() {
    local deployment_mode="docker"
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--docker) deployment_mode="docker" ; shift ;;
            -n|--native) deployment_mode="native" ; shift ;;
            -h|--help) show_help; exit 0 ;;
            *) log_error "未知选项: $1"; exit 1 ;;
        esac
    done
    echo ""
    echo -e "${CYAN}  ╔═══════════════════════════════════╗${NC}"
    echo -e "${CYAN}  ║   Novel Reader 部署脚本 (Linux)   ║${NC}"
    echo -e "${CYAN}  ╚═══════════════════════════════════╝${NC}"
    echo ""
    log_info "检测到平台: Linux"
    log_info "部署模式: $deployment_mode"
    if [ "$deployment_mode" == "docker" ]; then deploy_docker; else deploy_native; fi
    echo ""
    log_success "部署完成!"
}
main "$@"
