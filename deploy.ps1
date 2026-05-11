# Novel Reader 统一部署入口 (Windows)
# 自动检测平台并选择合适的部署方式
# 支持: Windows PowerShell, WSL2, Termux

param(
    [string]$Command = "help"
)

$SCRIPT_DIR = $PWD.Path

function Detect-Platform {
    # 检测 Termux
    if (Test-Path "/data/data/com.termux/files/usr") {
        return "termux"
    }
    
    # 检测 WSL
    if ($env:WSL_DISTRO_NAME) {
        return "wsl"
    }
    
    # 检测 Windows
    if ($env:OS -eq "Windows_NT") {
        return "windows"
    }
    
    return "unknown"
}

function Show-Help {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Novel Reader - 统一部署入口" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "用法: .\deploy.ps1 [command]"
    Write-Host ""
    Write-Host "命令:"
    Write-Host "  install    安装并配置环境（自动检测平台）"
    Write-Host "  start      启动服务"
    Write-Host "  stop       停止服务"
    Write-Host "  restart    重启服务"
    Write-Host "  status     查看状态"
    Write-Host "  deps       安装依赖"
    Write-Host "  mirror     配置镜像源"
    Write-Host "  help       显示此帮助"
    Write-Host ""
    Write-Host "支持平台:"
    Write-Host "  • Windows 10/11 (PowerShell + Docker)"
    Write-Host "  • Windows Subsystem for Linux (WSL2)"
    Write-Host "  • Android (Termux)"
    Write-Host ""
    Write-Host "示例:"
    Write-Host "  .\deploy.ps1 install    # 首次安装"
    Write-Host "  .\deploy.ps1 start      # 启动服务"
    Write-Host "  .\deploy.ps1 status     # 查看状态"
}

function Main {
    $platform = Detect-Platform
    
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Novel Reader - 统一部署入口" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "[INFO] 检测到平台: $platform" -ForegroundColor Blue

    switch ($platform) {
        "wsl" {
            Write-Host "[INFO] 使用 WSL2 模式..." -ForegroundColor Blue
            if (Test-Path "start.sh") {
                & bash -c "./start.sh $Command"
            } else {
                Write-Host "[ERROR] start.sh 脚本不存在" -ForegroundColor Red
                exit 1
            }
        }
        "termux" {
            Write-Host "[INFO] 使用 Termux 模式..." -ForegroundColor Blue
            if (Test-Path "install-termux.sh") {
                & bash -c "./install-termux.sh $Command"
            } else {
                Write-Host "[ERROR] install-termux.sh 脚本不存在" -ForegroundColor Red
                exit 1
            }
        }
        "windows" {
            Write-Host "[INFO] 使用 Windows PowerShell 模式..." -ForegroundColor Blue
            if (Test-Path "start.ps1") {
                & .\start.ps1 $Command
            } else {
                Write-Host "[ERROR] start.ps1 脚本不存在" -ForegroundColor Red
                exit 1
            }
        }
        default {
            Write-Host "[ERROR] 无法识别的平台: $platform" -ForegroundColor Red
            Show-Help
            exit 1
        }
    }
}

if ($args.Count -gt 0) {
    $Command = $args[0]
}

if ($Command -eq "help" -or $Command -eq "--help" -or $Command -eq "-h") {
    Show-Help
    exit 0
}

Main
