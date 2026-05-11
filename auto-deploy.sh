#!/bin/bash

# Novel Reader 跨平台统一部署入口
# 自动检测平台并选择合适的部署方式
# 用法:
#   ./auto-deploy.sh              - 自动检测并部署
#   ./auto-deploy.sh --status    - 查看状态
#   ./auto-deploy.sh --help       - 显示帮助

set -e

PROJECT_NAME="novel-reader"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR="$PROJECT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[OK]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_err() { echo -e "${RED}[ERROR]${NC} $1"; }

detect_platform() {
    local platform="unknown"
    local os=$(uname -s)
    local distro=""

    case "$os" in
        Linux*)
            if [ -n "$TERMUX_VERSION" ] || [ -d "$PREFIX" ]; then
                platform="termux"
                distro="Android/Termux"
            elif [ -f /etc/os-release ]; then
                . /etc/os-release
                distro="$NAME"
                if command -v apt-get &> /dev/null; then
                    platform="linux-apt"
                elif command -v yum &> /dev/null; then
                    platform="linux-yum"
                elif command -v dnf &> /dev/null; then
                    platform="linux-dnf"
                elif command -v pacman &> /dev/null; then
                    platform="linux-pacman"
                else
                    platform="linux"
                fi
            else
                platform="linux"
                distro="Linux"
            fi
            ;;
        Darwin*)
            platform="macos"
            distro="macOS"
            ;;
        MINGW*|MSYS*|CYGWIN*)
            platform="windows"
            distro="Windows"
            ;;
        *)
            platform="unknown"
            distro="$os"
            ;;
    esac

    echo "$platform:$distro"
}

check_docker() {
    if command -v docker &> /dev/null && docker info &> /dev/null; then
        return 0
    fi
    return 1
}

check_wsl() {
    if grep -qiE "microsoft|wsl" /proc/version 2>/dev/null; then
        return 0
    fi
    return 1
}

show_banner() {
    echo ""
    echo -e "${MAGENTA}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}  ${CYAN}Novel Reader - 跨平台自动部署工具${NC}              ${MAGENTA}║${NC}"
    echo -e "${MAGENTA}╚═══════════════════════════════════════════════════╝${NC}"
    echo ""
}

show_platform_info() {
    local info=$(detect_platform)
    local platform="${info%%:*}"
    local distro="${info##*:}"

    echo -e "  ${CYAN}操作系统:${NC} $distro"
    echo -e "  ${CYAN}平台类型:${NC} $platform"

    if check_docker; then
        echo -e "  ${GREEN}Docker:${NC} 已安装"
    else
        echo -e "  ${YELLOW}Docker:${NC} 未安装"
    fi

    if check_wsl; then
        echo -e "  ${CYAN}WSL2:${NC} 检测到"
    fi

    echo ""
}

deploy_auto() {
    show_banner
    echo -e "${MAGENTA}[自动检测]${NC} 检测系统环境..."
    echo ""

    local info=$(detect_platform)
    local platform="${info%%:*}"
    local distro="${info##*:}"

    show_platform_info

    case "$platform" in
        termux)
            print_info "检测到 Android/Termux 环境"
            echo -e "  运行 ${CYAN}./deploy-termux.sh${NC}"
            echo ""
            read -p "是否继续? (Y/n): " confirm
            if [[ "$confirm" =~ ^[Nn]$ ]]; then
                exit 0
            fi
            echo ""
            bash "$SCRIPT_DIR/deploy-termux.sh" local
            ;;
        macos)
            print_info "检测到 macOS 环境"
            if check_docker; then
                print_info "Docker 可用，使用 Docker 部署"
                bash "$SCRIPT_DIR/deploy.sh" docker
            else
                print_info "Docker 不可用，使用本地部署"
                bash "$SCRIPT_DIR/deploy.sh" local
            fi
            ;;
        linux-apt|linux-yum|linux-dnf|linux-pacman|linux)
            print_info "检测到 Linux 环境 ($distro)"
            if check_docker; then
                print_info "Docker 可用，使用 Docker 部署"
                bash "$SCRIPT_DIR/deploy.sh" docker
            else
                print_info "Docker 不可用，使用本地部署"
                bash "$SCRIPT_DIR/deploy.sh" local
            fi
            ;;
        windows)
            print_info "检测到 Windows 环境"
            if check_wsl; then
                print_info "WSL2 可用，使用 WSL 部署"
                print_info "请在 WSL 终端中运行: bash ./deploy.sh"
            else
                print_info "使用 PowerShell 部署"
                print_info "请运行: .\deploy.ps1"
            fi
            ;;
        *)
            print_err "不支持的平台: $distro"
            echo ""
            print_info "请根据您的平台手动选择部署脚本:"
            echo "  Windows:  .\deploy.ps1"
            echo "  Linux:    ./deploy.sh"
            echo "  Termux:   ./deploy-termux.sh"
            exit 1
            ;;
    esac
}

show_status_all() {
    show_banner
    local info=$(detect_platform)
    local platform="${info%%:*}"

    case "$platform" in
        termux)
            bash "$SCRIPT_DIR/deploy-termux.sh" status
            ;;
        windows)
            powershell -ExecutionPolicy Bypass -File "$SCRIPT_DIR/deploy.ps1" status
            ;;
        *)
            bash "$SCRIPT_DIR/deploy.sh" status
            ;;
    esac
}

show_help() {
    cat << EOF
Novel Reader 跨平台统一部署入口

用法: ./auto-deploy.sh [command]

命令:
  (无参数)      自动检测平台并部署
  --status      查看服务状态
  --stop        停止服务
  --help        显示帮助

支持的平台:
  - Windows 10/11 (PowerShell)
  - Windows + WSL2 (Bash)
  - Linux (apt/yum/dnf/pacman)
  - macOS
  - Android + Termux

部署方式:
  1. Docker 部署 (推荐) - 如果 Docker 可用
  2. 本地部署 - 使用 Python + Node.js

自动检测逻辑:
  - 检测到 Docker → 使用 Docker 部署
  - 检测到 Termux → 使用 Termux 专用脚本
  - 其他情况 → 使用本地部署

示例:
  ./auto-deploy.sh              # 自动部署
  ./auto-deploy.sh --status     # 查看状态
  ./auto-deploy.sh --stop      # 停止服务

或直接使用平台专用脚本:
  .\deploy.ps1                  # Windows PowerShell
  ./deploy.sh                   # Linux/macOS
  ./deploy-termux.sh            # Android Termux
EOF
}

case "${1:-}" in
    --status|-s)
        show_status_all
        ;;
    --stop|-t)
        bash "$SCRIPT_DIR/deploy.sh" stop 2>/dev/null || true
        ;;
    --help|-h)
        show_banner
        show_help
        ;;
    "")
        deploy_auto
        ;;
    *)
        print_err "未知参数: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
