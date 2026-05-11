#!/bin/bash
# Novel Reader 统一部署入口脚本
# 自动检测操作系统并选择合适的部署方式
# 用法: ./deploy.sh [command]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="novel-reader"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
header() {
    echo ""
    echo -e "${MAGENTA}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}  ${CYAN}$1${NC}"
    echo -e "${MAGENTA}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_command() {
    command -v "$1" &> /dev/null
}

is_wsl() {
    if grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; then
        return 0
    fi
    return 1
}

is_termux() {
    if [ -d "$PREFIX" ] && [ -w "$PREFIX" ]; then
        return 0
    fi
    return 1
}

get_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if is_wsl; then
            echo "wsl"
        elif is_termux; then
            echo "termux"
        elif [ -f /etc/os-release ]; then
            . /etc/os-release
            echo "$ID"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

show_banner() {
    header "Novel Reader 跨平台部署工具"
    echo -e "  ${CYAN}自动检测操作系统并配置环境${NC}"
    echo ""
    echo -e "  ${GREEN}支持的平台:${NC}"
    echo "    - Windows (PowerShell / WSL2)"
    echo "    - Linux (Ubuntu/Debian/Fedora/Arch 等)"
    echo "    - macOS"
    echo "    - Android/Termux"
    echo ""
    echo -e "  ${GREEN}部署特性:${NC}"
    echo "    - 纯 Python 版本依赖，无需编译"
    echo "    - 自动配置镜像源 (中国/海外)"
    echo "    - Docker 或本地模式自动选择"
    echo ""
}

show_help() {
    show_banner
    cat << EOF
用法: ./deploy.sh [command]

命令:
  install       完整安装所有依赖
  start         启动服务
  stop          停止服务
  status        查看服务状态
  docker        使用 Docker 模式启动
  python        仅安装 Python 依赖
  node          仅安装 Node.js 依赖
  redis         安装 Redis
  mirror        配置镜像源
  help          显示帮助信息

示例:
  ./deploy.sh              # 显示帮助
  ./deploy.sh install      # 完整安装
  ./deploy.sh start        # 启动本地服务
  ./deploy.sh docker      # Docker 模式启动

自动检测:
  平台: $(get_os)
  WSL: $(is_wsl && echo "是" || echo "否")
  Termux: $(is_termux && echo "是" || echo "否")

EOF
}

run_windows() {
    local script="$SCRIPT_DIR/scripts/deploy-windows.ps1"
    if [ -f "$script" ]; then
        powershell -ExecutionPolicy Bypass -File "$script" "$@"
    else
        error "Windows 部署脚本不存在"
        exit 1
    fi
}

run_linux() {
    local script="$SCRIPT_DIR/scripts/deploy-linux.sh"
    if [ -f "$script" ]; then
        bash "$script" "$@"
    else
        error "Linux 部署脚本不存在"
        exit 1
    fi
}

run_termux() {
    local script="$SCRIPT_DIR/scripts/deploy-termux.sh"
    if [ -f "$script" ]; then
        bash "$script" "$@"
    else
        error "Termux 部署脚本不存在"
        exit 1
    fi
}

run_docker_check() {
    if check_command docker && docker info &> /dev/null; then
        return 0
    fi
    return 1
}

install_all() {
    header "完整安装"

    local os=$(get_os)

    case "$os" in
        windows|wsl)
            info "检测到 Windows/WSL 环境"
            run_windows install
            ;;
        termux)
            info "检测到 Termux 环境"
            run_termux install
            ;;
        macos)
            info "检测到 macOS 环境"
            run_linux install
            ;;
        ubuntu|debian|linuxmint|pop|fedora|rhel|centos|rocky|alma|arch|manjaro|alpine|linux)
            info "检测到 Linux 环境: $os"
            run_linux install
            ;;
        *)
            error "不支持的操作系统: $os"
            exit 1
            ;;
    esac

    success "安装完成!"
}

start_services() {
    header "启动服务"

    if run_docker_check; then
        info "检测到 Docker，选择 Docker 模式"
        run_linux docker
    else
        local os=$(get_os)
        case "$os" in
            windows|wsl)
                run_windows start
                ;;
            termux)
                run_termux start
                ;;
            *)
                run_linux start
                ;;
        esac
    fi
}

stop_services() {
    header "停止服务"

    if run_docker_check; then
        run_linux stop
    else
        local os=$(get_os)
        case "$os" in
            termux)
                run_termux stop
                ;;
            *)
                info "本地服务已停止"
                ;;
        esac
    fi
}

show_status() {
    header "服务状态"

    if run_docker_check; then
        run_linux status
    else
        local os=$(get_os)
        case "$os" in
            termux)
                run_termux status
                ;;
            *)
                run_linux status
                ;;
        esac
    fi
}

case "${1:-}" in
    install)
        install_all
        ;;
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    status)
        show_status
        ;;
    docker)
        header "Docker 模式"
        if run_docker_check; then
            run_linux docker
        else
            error "Docker 未安装或未运行"
            exit 1
        fi
        ;;
    python)
        run_linux python
        ;;
    node)
        run_linux node
        ;;
    redis)
        run_linux redis
        ;;
    mirror)
        run_linux mirror
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        error "未知命令: $1"
        show_help
        exit 1
        ;;
esac
