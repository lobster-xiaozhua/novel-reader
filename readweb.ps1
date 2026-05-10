# readweb - Novel Reader 项目管理命令行工具 (Windows PowerShell)
# 用法: .\readweb.ps1 <command> [options]

param(
    [string]$Command = "",
    [string]$Arg = ""
)

$VERSION = "1.0.0"
$PROJECT_NAME = "novel-reader"

function Write-Log { param($type, $msg)
    $color = switch ($type) { "info" { "Cyan" } "success" { "Green" } "warning" { "Yellow" } "error" { "Red" } "step" { "Magenta" } }
    Write-Host "[$($type.ToUpper())] $msg" -ForegroundColor $color
}

function Show-Banner {
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════╗" -ForegroundColor Magenta
    Write-Host "║  Novel Reader - 项目管理工具                      ║" -ForegroundColor Magenta
    Write-Host "║  版本: $VERSION                                      ║" -ForegroundColor Magenta
    Write-Host "╚═══════════════════════════════════════════════════╝" -ForegroundColor Magenta
    Write-Host ""
}

function Show-Help {
    Show-Banner
    @"
用法: .\readweb.ps1 <command>

命令:
  start      启动项目（自动配置环境、构建、运行）
  stop       停止所有服务
  restart    重启服务
  update     更新项目（git pull + 重建）
  status     查看服务状态
  logs       查看日志
  deps       安装/更新依赖
  mirror     配置镜像源
  clean      清理环境
  doctor     环境检查
  backup     备份数据
  restore    恢复数据
  version    显示版本信息
  help       显示帮助

示例:
  .\readweb.ps1 start          # 首次启动
  .\readweb.ps1 update         # 更新项目
  .\readweb.ps1 logs backend  # 查看后端日志
  .\readweb.ps1 doctor        # 检查环境
  .\readweb.ps1 backup        # 备份数据
"@
}

function Show-Version {
    Write-Host "Novel Reader 项目管理工具 v$VERSION"
    Write-Host ""
    Write-Host "Docker: $(docker --version 2>$null || '未安装')"
    Write-Host "Node.js: $(node --version 2>$null || '未安装')"
    Write-Host "Python: $(python --version 2>$null || '未安装')"
}

function Test-Environment {
    Write-Log "step" "检查运行环境..."
    $errors = 0

    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Log "error" "Docker 未安装"
        $errors++
    } elseif (-not (docker info 2>$null)) {
        Write-Log "error" "Docker 未运行"
        $errors++
    } else {
        Write-Log "success" "Docker: $(docker --version | Select-String -Pattern '\d+\.\d+' -AllMatches | ForEach-Object { $_.Matches.Value })"
    }

    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Write-Log "warning" "Node.js 未安装"
    } else {
        Write-Log "success" "Node.js: $(node --version)"
    }

    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Log "warning" "Python 未安装"
    } else {
        Write-Log "success" "Python: $(python --version)"
    }

    if ($errors -gt 0) {
        Write-Log "error" "环境检查失败 ($errors 个错误)"
        return $false
    }
    Write-Log "success" "环境检查通过"
    return $true
}

function Set-Mirrors {
    Write-Log "step" "配置镜像源..."

    try {
        $country = (Invoke-WebRequest -Uri "https://ipinfo.io/country" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue).Content
    } catch {
        $country = "global"
    }

    if ($country -eq "CN") {
        Write-Log "info" "检测到中国地区，配置国内镜像..."

        $pipDir = "$env:APPDATA\pip"
        if (-not (Test-Path $pipDir)) { New-Item -ItemType Directory -Force -Path $pipDir | Out-Null }
        @"
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 60
[install]
trusted-host = mirrors.aliyun.com
"@ | Out-File -FilePath "$pipDir\pip.ini" -Encoding UTF8
        Write-Log "success" "pip 镜像: 阿里云"

        npm config set registry https://registry.npmmirror.com 2>$null
        Write-Log "success" "npm 镜像: npmmirror.com"

        $dockerDir = "$env:USERPROFILE\.docker"
        if (-not (Test-Path $dockerDir)) { New-Item -ItemType Directory -Force -Path $dockerDir | Out-Null }
        @"
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
"@ | Out-File -FilePath "$dockerDir\daemon.json" -Encoding UTF8
        Write-Log "success" "Docker 镜像加速: 已配置"
    }
}

function Initialize-Directories {
    Write-Log "step" "创建目录结构..."
    @("books", "index", "static", "logs", "cache", "backups", "versions") | ForEach-Object {
        New-Item -ItemType Directory -Force -Path "data\$_" | Out-Null
    }
    Write-Log "success" "目录创建完成"
}

function Initialize-Env {
    if (-not (Test-Path ".env")) {
        Write-Log "info" "创建环境配置文件..."
        $key = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
        @"
SECRET_KEY=$key
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://redis:6379
"@ | Out-File -FilePath ".env" -Encoding UTF8
        Write-Log "success" ".env 文件已创建"
    }
}

function Start-Services {
    Show-Banner
    Write-Log "step" "启动 Novel Reader..."

    if (-not (Test-Environment)) { return }

    Set-Mirrors
    Initialize-Directories
    Initialize-Env

    Write-Log "step" "启动服务..."
    docker-compose up -d redis
    Start-Sleep -Seconds 2
    docker-compose up -d backend frontend

    Write-Log "step" "等待服务就绪..."
    for ($i = 1; $i -le 30; $i++) {
        try {
            $r = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 1 -ErrorAction SilentlyContinue
            if ($r.StatusCode -eq 200) {
                Write-Log "success" "后端服务已就绪"
                break
            }
        } catch { }
        Start-Sleep -Seconds 1
    }

    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  项目已启动!" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "  📖 前端页面:  http://localhost" -ForegroundColor Green
    Write-Host "  🔧 API 文档:   http://localhost:8000/docs" -ForegroundColor Green
    Write-Host ""
}

function Stop-Services {
    Write-Log "step" "停止服务..."
    docker-compose down 2>$null
    Write-Log "success" "服务已停止"
}

function Update-Project {
    Show-Banner
    Write-Log "step" "更新项目..."

    if (-not (Test-Path ".git")) {
        Write-Log "error" "不是 git 仓库，无法更新"
        return
    }

    Write-Log "step" "拉取最新代码..."
    git pull origin main

    Write-Log "step" "重启服务..."
    docker-compose up -d --force-recreate backend frontend

    Write-Log "success" "项目更新完成!"
}

function Get-Status {
    Write-Log "step" "服务状态"
    Write-Host ""
    docker-compose ps

    Write-Host ""
    Write-Log "info" "健康检查:"
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { Write-Log "success" "后端 API: 运行中" }
    } catch { Write-Log "error" "后端 API: 未响应" }
}

function Show-Logs {
    param([string]$Service = "")
    if ($Service) {
        Write-Log "info" "查看 $Service 日志 (Ctrl+C 退出)"
        docker-compose logs -f $Service
    } else {
        Write-Log "info" "查看所有日志 (Ctrl+C 退出)"
        docker-compose logs -f
    }
}

function Backup-Data {
    Write-Log "step" "备份数据..."

    $backupDir = "data\backups"
    if (-not (Test-Path $backupDir)) { New-Item -ItemType Directory -Force -Path $backupDir | Out-Null }

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupFile = "$backupDir\backup_$timestamp.zip"

    Compress-Archive -Path "data\books", "data\db.json", "data\settings.json" -DestinationPath $backupFile -Force 2>$null

    Write-Log "success" "备份已保存: $backupFile"
}

switch ($Command) {
    "start" { Start-Services }
    "stop" { Stop-Services }
    "restart" { Stop-Services; Start-Services }
    "update" { Update-Project }
    "status" { Get-Status }
    "logs" { Show-Logs -Service $Arg }
    "deps" { Set-Mirrors; Write-Log "success" "依赖配置完成" }
    "mirror" { Set-Mirrors; Write-Log "success" "镜像配置完成" }
    "clean" { Stop-Services; Remove-Item -Recurse -Force "data\logs", "data\cache" -ErrorAction SilentlyContinue; Write-Log "success" "清理完成" }
    "doctor" { Test-Environment }
    "backup" { Backup-Data }
    "restore" { Write-Log "info" "用法: .\readweb.ps1 restore <备份文件>" }
    "version" { Show-Version }
    "help" { Show-Help }
    "" { Show-Help }
    default { Write-Log "error" "未知命令: $Command"; Write-Host "运行 '.\readweb.ps1 help' 查看帮助" }
}
