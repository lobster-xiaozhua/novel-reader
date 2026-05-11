#!/bin/bash
# deploy.sh - 跨平台统一部署入口
# 自动检测平台并选择合适的部署脚本
# 用法: bash deploy.sh [命令] [选项]
#
# 命令:
#   install    安装所有依赖
#   start      启动服务
#   stop       停止服务
#   restart    重启服务
#   status     查看状态
#   update     更新项目
#   help       显示帮助

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
    echo -e "${MAGENTA}║${NC}  ${CYAN}Novel Reader - 跨平台部署工具${NC}                 ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╚═══════════════════════════════════════════════════╝${NC}"
    echo ""
}

detect_platform() {
    local platform="unknown"

    if [ -n "$ANDROID_ROOT" ] || [ -d "$PREFIX" ] && [ -w "$PREFIX/bin" ]; then
        platform="termux"
    elif [ "$(uname)" = "Darwin" ]; then
        platform="macos"
    elif [ "$(uname)" = "Linux" ]; then
        platform="linux"
    elif [[ "$OS" == *"Windows"* ]] || [ -n "$windir" ]; then
        platform="windows"
    fi

    echo "$platform"
}

get_script_name() {
    local platform="$1"

    case "$platform" in
        termux)
            echo "deploy-termux.sh"
            ;;
        linux|macos)
            echo "deploy-linux.sh"
            ;;
        windows)
            echo "deploy-windows.ps1"
            ;;
        *)
            echo "deploy-linux.sh"
            ;;
    esac
}

check_dependencies() {
    log_step "检查系统依赖..."

    local missing=()

    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        missing+=("Python")
    fi

    if ! command -v git &> /dev/null; then
        missing+=("Git")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "缺少必要的依赖: ${missing[*]}"
        log_info "请先安装这些依赖"
        return 1
    fi

    local python_version=$(python3 --version 2>/dev/null || python --version 2>/dev/null | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [ -n "$python_version" ]; then
        log_success "Python: $(python3 --version 2>/dev/null || python --version 2>/dev/null)"
    fi

    log_success "依赖检查通过"
    return 0
}

main() {
    local command="${1:-}"
    local platform
    local script_name

    platform=$(detect_platform)
    script_name=$(get_script_name "$platform")

    print_banner

    case "$platform" in
        termux)
            echo -e "${CYAN}检测到平台: ${GREEN}Android/Termux${NC}"
            echo -e "${CYAN}将使用脚本: ${GREEN}$script_name${NC}"
            ;;
        linux)
            echo -e "${CYAN}检测到平台: ${GREEN}Linux${NC}"
            echo -e "${CYAN}将使用脚本: ${GREEN}$script_name${NC}"
            ;;
        macos)
            echo -e "${CYAN}检测到平台: ${GREEN}macOS${NC}"
            echo -e "${CYAN}将使用脚本: ${GREEN}$script_name${NC}"
            ;;
        windows)
            echo -e "${CYAN}检测到平台: ${GREEN}Windows${NC}"
            echo -e "${CYAN}将使用脚本: ${GREEN}$script_name${NC}"
            ;;
        *)
            log_warning "无法确定平台，将使用 Linux 脚本"
            script_name="deploy-linux.sh"
            ;;
    esac

    echo ""

    case "$platform" in
        termux|linux|macos)
            if [ ! -f "$SCRIPT_DIR/$script_name" ]; then
                log_error "部署脚本不存在: $script_name"
                exit 1
            fi

            chmod +x "$SCRIPT_DIR/$script_name" 2>/dev/null || true

            if [ "$command" = "help" ] || [ "$command" = "--help" ] || [ "$command" = "-h" ] || [ -z "$command" ]; then
                bash "$SCRIPT_DIR/$script_name" help
            else
                bash "$SCRIPT_DIR/$script_name" "$command" "${@:2}"
            fi
            ;;
        windows)
            if [ ! -f "$SCRIPT_DIR/$script_name" ]; then
                log_error "部署脚本不存在: $script_name"
                exit 1
            fi

            if [ "$command" = "help" ] || [ "$command" = "--help" ] || [ "$command" = "-h" ] || [ -z "$command" ]; then
                powershell -ExecutionPolicy Bypass -File "$SCRIPT_DIR\$script_name" help
            else
                powershell -ExecutionPolicy Bypass -File "$SCRIPT_DIR\$script_name" "$command"
            fi
            ;;
    esac
}

show_help() {
    print_banner
    cat << EOF
Novel Reader - 跨平台统一部署工具

用法: bash deploy.sh <command>

命令:
  \${GREEN}install\${NC}    安装所有依赖（首次运行）
  \${GREEN}start\${NC}       启动服务
  \${GREEN}stop\${NC}        停止服务
  \${GREEN}restart\${NC}     重启服务
  \${GREEN}status\${NC}      查看服务状态
  \${GREEN}update\${NC}      更新项目
  \${GREEN}help\${NC}        显示帮助

支持的平台:
  ✓ Linux (Ubuntu/Debian/CentOS/Fedora/Arch)
  ✓ macOS
  ✓ Android (Termux)
  ✓ Windows (PowerShell)

自动检测:
  脚本会自动检测当前平台并选择合适的部署方式

  - Linux/macOS:    使用 bash deploy-linux.sh
  - Termux:         使用 bash deploy-termux.sh
  - Windows:        使用 PowerShell deploy-windows.ps1

快速开始:
  1. Linux/macOS/Termux:
     bash deploy.sh install   # 安装依赖
     bash deploy.sh start     # 启动服务

  2. Windows:
     .\deploy-windows.ps1 install   # 安装依赖
     .\deploy-windows.ps1 start     # 启动服务

     或使用统一入口:
     powershell -ExecutionPolicy Bypass -File deploy.sh install

环境要求:
  - Python 3.11+
  - Node.js 18+ (可选，用于本地开发)
  - Redis 6.0+ (可选)

更多信息: https://github.com/lobster-xiaozhua/novel-reader
EOF
}

if [ "$1" = "help" ] || [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
else
    main "$@"
fi