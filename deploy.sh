#!/bin/bash

# Novel Reader 统一部署入口
# 自动检测平台并选择合适的部署方式
# 支持: Windows (PowerShell), Linux, macOS, Termux (Android)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

detect_platform() {
    if [ -d "/data/data/com.termux/files/usr" ]; then
        echo "termux"
        return
    fi
    
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OS" == "Windows_NT" ]]; then
        echo "windows"
        return
    fi
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
        return
    fi
    
    echo "linux"
}

print_banner() {
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}Novel Reader - 统一部署入口${NC}                   ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════╝${NC}"
    echo ""
}

show_help() {
    print_banner
    cat << EOF
用法: ./deploy.sh [command]

命令:
  install    安装并配置环境（自动检测平台）
  start      启动服务
  stop       停止服务
  restart    重启服务
  status     查看状态
  deps       安装依赖
  mirror     配置镜像源
  help       显示此帮助

支持平台:
  • Windows 10/11 (PowerShell)
  • Linux (Debian/Ubuntu/CentOS/Fedora/Arch)
  • macOS
  • Android (Termux)

示例:
  ./deploy.sh install    # 首次安装
  ./deploy.sh start      # 启动服务
  ./deploy.sh status     # 查看状态
EOF
}

main() {
    local platform=$(detect_platform)
    local command="${1:-help}"

    print_banner
    print_info "检测到平台: $platform"

    case "$platform" in
        windows)
            print_info "使用 PowerShell 脚本..."
            if [ -f "start.ps1" ]; then
                powershell.exe -ExecutionPolicy Bypass -File "$SCRIPT_DIR/start.ps1" "$command"
            else
                print_error "start.ps1 脚本不存在"
                exit 1
            fi
            ;;
        
        termux)
            print_info "使用 Termux 安装脚本..."
            if [ -f "install-termux.sh" ]; then
                bash "$SCRIPT_DIR/install-termux.sh" "$command"
            else
                print_error "install-termux.sh 脚本不存在"
                exit 1
            fi
            ;;
        
        linux|macos)
            print_info "使用 Linux/macOS 脚本..."
            if [ -f "start.sh" ]; then
                bash "$SCRIPT_DIR/start.sh" "$command"
            else
                print_error "start.sh 脚本不存在"
                exit 1
            fi
            ;;
        
        *)
            print_error "无法识别的平台: $platform"
            show_help
            exit 1
            ;;
    esac
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
