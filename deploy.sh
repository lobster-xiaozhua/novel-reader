#!/bin/bash
# Novel Reader - 统一跨平台部署入口脚本
# 自动检测操作系统并选择合适的部署方式

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[✓]${NC} $1"; }
echo_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
echo_error() { echo -e "${RED}[✗]${NC} $1"; }
echo_header() { echo -e "\n${CYAN}═══ $1 ═══${NC}"; }

detect_os() {
    if [ -d "$PREFIX" ] && [ -d "$HOME" ] && [[ "$PREFIX" == *"com.termux"* ]]; then
        echo "termux"
        return
    fi

    if [ "$(uname)" = "Darwin" ]; then
        echo "macos"
        return
    fi

    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [ "$ID" = "alpine" ]; then
            echo "alpine"
            return
        elif [ "$ID" = "android" ]; then
            echo "android"
            return
        fi
    fi

    if [ -f /proc/version ]; then
        if grep -qi "Microsoft\|WSL" /proc/version 2>/dev/null; then
            echo "wsl"
            return
        fi
    fi

    if command -v apt-get &> /dev/null; then
        echo "debian"
        return
    fi

    if command -v dnf &> /dev/null; then
        echo "fedora"
        return
    fi

    if command -v pacman &> /dev/null; then
        echo "arch"
        return
    fi

    echo "linux"
}

show_banner() {
    echo ""
    echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}                                                              ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}   ${CYAN}██████╗ ███████╗███████╗██╗██████╗ ██╗ █████╗ ███╗   ██╗${MAGENTA}  ║${NC}"
    echo -e "${MAGENTA}║${NC}   ${CYAN}██╔══██╗██╔════╝██╔════╝██║██╔══██╗██║██╔══██╗████╗  ██║${MAGENTA}  ║${NC}"
    echo -e "${MAGENTA}║${NC}   ${CYAN}██████╔╝█████╗  ███████╗██║██████╔╝██║███████║██╔██╗ ██║${MAGENTA}  ║${NC}"
    echo -e "${MAGENTA}║${NC}   ${CYAN}██╔══██╗██╔══╝  ╚════██║██║██╔══██╗██║██╔══██║██║╚██╗██║${MAGENTA}  ║${NC}"
    echo -e "${MAGENTA}║${NC}   ${CYAN}██║  ██║███████╗███████║██║██║  ██║██║██║  ██║██║ ╚████║${MAGENTA}  ║${NC}"
    echo -e "${MAGENTA}║${NC}   ${CYAN}╚═╝  ╚═╝╚══════╝╚══════╝╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝${MAGENTA}  ║${NC}"
    echo -e "${MAGENTA}║${NC}   ${CYAN}                统一跨平台部署脚本${NC}                         ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}║${NC}                                                              ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

show_help() {
    show_banner
    cat << EOF
用法: ./deploy.sh [command] [options]

命令:
  install     安装所有依赖
  start      启动服务
  stop       停止服务
  restart    重启服务
  status     查看服务状态
  logs       查看日志
  docker     使用 Docker 模式启动
  help       显示帮助

自动检测:
  脚本会自动检测您的操作系统并选择合适的部署方式:
  - Termux (Android) → deploy_termux.sh
  - Linux (Debian/Ubuntu) → deploy_linux.sh
  - Linux (Fedora/RHEL) → deploy_linux.sh
  - Linux (Arch) → deploy_linux.sh
  - macOS → deploy_linux.sh
  - WSL → deploy_linux.sh

示例:
  ./deploy.sh          # 交互式部署
  ./deploy.sh install  # 安装依赖
  ./deploy.sh start    # 启动服务
  ./deploy.sh docker   # Docker 模式启动

EOF
}

main() {
    local os_type=$(detect_os)

    if [ "$1" = "help" ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
        show_help
        return 0
    fi

    show_banner

    echo_info "检测到操作系统: ${CYAN}$os_type${NC}"

    case "$os_type" in
        termux)
            echo_info "使用 Termux 部署脚本..."
            bash "$SCRIPTS_DIR/deploy_termux.sh" "$@"
            ;;
        wsl)
            echo_info "检测到 WSL 环境，使用 Linux 部署脚本..."
            echo_info "提示: 也可以使用 Windows 的 PowerShell 脚本"
            echo ""
            bash "$SCRIPTS_DIR/deploy_linux.sh" "$@"
            ;;
        macos)
            echo_info "检测到 macOS，使用 Linux 部署脚本..."
            bash "$SCRIPTS_DIR/deploy_linux.sh" "$@"
            ;;
        debian|alpine|arch|fedora|linux)
            echo_info "使用 Linux 部署脚本..."
            bash "$SCRIPTS_DIR/deploy_linux.sh" "$@"
            ;;
        *)
            echo_warning "未知操作系统，尝试使用 Linux 部署脚本..."
            bash "$SCRIPTS_DIR/deploy_linux.sh" "$@"
            ;;
    esac
}

main "$@"
