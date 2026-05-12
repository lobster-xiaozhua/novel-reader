# Novel Reader - Windows 统一部署入口脚本 (PowerShell)
# 自动检测并选择合适的部署方式

param(
    [switch]$UseWSL,
    [switch]$SkipDocker,
    [switch]$NoInstall,
    [string]$Command = ""
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$SCRIPT_DIR = $PSScriptRoot
$SCRIPTS_DIR = Join-Path $SCRIPT_DIR "scripts"

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

$Colors = @{
    Info = "Cyan"
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Header = "Magenta"
}

function Show-Banner {
    Clear-Host
    Write-ColorOutput @"

╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   ██████╗ ███████╗███████╗██╗██████╗ ██╗ █████╗ ███╗   ██╗      ║
║   ██╔══██╗██╔════╝██╔════╝██║██╔══██╗██║██╔══██╗████╗  ██║      ║
║   ██████╔╝█████╗  ███████╗██║██████╔╝██║███████║██╔██╗ ██║      ║
║   ██╔══██╗██╔══╝  ╚════██║██║██╔══██╗██║██╔══██║██║╚██╗██║      ║
║   ██║  ██║███████╗███████║██║██║  ██║██║██║  ██║██║ ╚████║      ║
║   ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝      ║
║              统一跨平台部署脚本 (Windows PowerShell)             ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝

"@ $Colors.Header
}

function Test-WSL {
    if (Test-Path "/proc/version" -PathType Leaf) {
        $content = Get-Content "/proc/version" -Raw -ErrorAction SilentlyContinue
        if ($content -match "Microsoft|WSL") {
            return $true
        }
    }
    return $false
}

function Test-Termux {
    return (Test-Path "$env:PREFIX" -PathType Container)
}

function Show-Help {
    Show-Banner
    @"
用法: .\deploy.ps1 [command] [options]

命令:
  install     安装所有依赖
  start       启动服务
  stop        停止服务
  restart     重启服务
  status      查看服务状态
  logs        查看日志
  docker      使用 Docker 模式启动
  help        显示帮助

选项:
  -UseWSL      使用 WSL2 模式 (如果可用)
  -SkipDocker  跳过 Docker 模式，使用本地模式
  -NoInstall   跳过依赖安装

示例:
  .\deploy.ps1          # 交互式部署
  .\deploy.ps1 install  # 安装依赖
  .\deploy.ps1 start    # 启动服务
  .\deploy.ps1 docker   # Docker 模式启动

Windows 部署说明:
  1. PowerShell 5.1+ (Windows 10/11 自带)
  2. 支持 Docker Desktop 或 WSL2
  3. 推荐使用 Windows Terminal 运行

"@
}

function Main {
    $cmd = $Command.Trim()
    if ([string]::IsNullOrEmpty($cmd)) {
        $cmd = $args[0]
    }

    if ($cmd -eq "help" -or $cmd -eq "-h" -or $cmd -eq "--help") {
        Show-Help
        return
    }

    Show-Banner

    Write-ColorOutput "[INFO] 检测运行环境..." $Colors.Info

    if (Test-Termux) {
        Write-ColorOutput "[INFO] 检测到 Termux 环境，请使用 Bash 脚本:" $Colors.Warning
        Write-ColorOutput "[INFO] 运行: bash deploy.sh" $Colors.Info
        return
    }

    if (Test-WSL -and -not $UseWSL) {
        Write-ColorOutput "[INFO] 检测到 WSL 环境，建议使用:" $Colors.Warning
        Write-ColorOutput "[INFO]   bash deploy.sh    # 使用 Bash 脚本" $Colors.Info
        Write-ColorOutput "[INFO] 或: .\deploy.ps1 -UseWSL    # 使用 WSL" $Colors.Info
        Write-ColorOutput "" $Colors.Info
    }

    if ($UseWSL) {
        Write-ColorOutput "[INFO] 使用 WSL2 模式..." $Colors.Info
        bash "$SCRIPTS_DIR/deploy_linux.sh" $args
        return
    }

    Write-ColorOutput "[INFO] 使用 Windows PowerShell 部署脚本..." $Colors.Info
    & "$SCRIPTS_DIR\deploy_windows.ps1" @args
}

Main
