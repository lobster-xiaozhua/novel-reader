# Novel Reader 跨平台部署脚本 (Windows PowerShell)
# 用法: .\deploy.ps1 [mode]
#
# 模式:
#   local      本地模式 (Docker Desktop)
#   wsl        WSL2 模式 (推荐中国用户)
#   native     原生模式 (不使用 Docker)

param(
    [string]$Mode = "local"
)

$PROJECT_NAME = "novel-reader"
$BACKEND_DIR = "backend"
$FRONTEND_DIR = "frontend"
$DATA_DIR = "data"

$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Cyan"

function Print-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor $Blue }
function Print-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor $Green }
function Print-Warning { param($msg) Write-Host "[WARN] $msg" -ForegroundColor $Yellow }
function Print-Error { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor $Red }
function Print-Header { param($msg)
    Write-Host ""
    Write-Host ("══════════════════════════════════════════════════════") -ForegroundColor Cyan
    Write-Host ("  $msg") -ForegroundColor Cyan
    Write-Host ("══════════════════════════════════════════════════════") -ForegroundColor Cyan
}

function Test-Command { param($cmd)
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        return $false
    }
    return $true
}

function Get-Region {
    try {
        $response = Invoke-WebRequest -Uri "https://ipinfo.io/country" -UseBasicParsing -TimeoutSec 3
        if ($response.Content -eq "CN") {
            return "china"
        }
    } catch {}
    return "global"
}

function Set-Mirrors {
    $region = Get-Region

    if ($region -eq "china") {
        Print-Info "检测到中国地区，配置国内镜像源..."

        $pipDir = "$env:APPDATA\pip"
        if (-not (Test-Path $pipDir)) {
            New-Item -ItemType Directory -Force -Path $pipDir | Out-Null
        }
        @"
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 120
retries = 5

[install]
trusted-host = mirrors.aliyun.com
             pypi.tuna.tsinghua.edu.cn
"@ | Out-File -FilePath "$pipDir\pip.ini" -Encoding UTF8
        Print-Success "pip 镜像: 阿里云"

        npm config set registry https://registry.npmmirror.com
        Print-Success "npm 镜像: npmmirror.com"

        $dockerDir = "$env:USERPROFILE\.docker"
        if (-not (Test-Path $dockerDir)) {
            New-Item -ItemType Directory -Force -Path $dockerDir | Out-Null
        }
        @"
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me",
    "https://dockerproxy.cn"
  ]
}
"@ | Out-File -FilePath "$dockerDir\daemon.json" -Encoding UTF8
        Print-Success "Docker 镜像加速已配置"
    } else {
        Print-Info "使用官方源"
    }
}

function New-DataDirectories {
    Print-Info "创建数据目录..."
    @("books", "index", "static", "logs", "cache", "backups") | ForEach-Object {
        New-Item -ItemType Directory -Force -Path "$DATA_DIR\$_" | Out-Null
    }
    Print-Success "目录创建完成"
}

function Test-EnvFile {
    if (-not (Test-Path ".env")) {
        Print-Info "创建 .env 配置文件..."
        $secretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
        @"
SECRET_KEY=$secretKey
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://redis:6379
DATA_DIR=./data
BOOKS_DIR=./data/books
INDEX_DIR=./data/index
STATIC_DIR=./data/static
LOGS_DIR=./data/logs
CACHE_DIR=./data/cache
"@ | Out-File -FilePath ".env" -Encoding UTF8
        Print-Success ".env 文件已创建"
    }
}

function Install-PythonDeps-Local {
    Print-Info "安装 Python 依赖 (本地模式)..."

    Set-Location $BACKEND_DIR

    if (-not (Test-Path "venv")) {
        Print-Info "创建 Python 虚拟环境..."
        python -m venv venv
    }

    & .\venv\Scripts\Activate.ps1

    Print-Info "升级 pip..."
    pip install --upgrade pip

    Print-Info "安装依赖 (使用兼容版本)..."
    if (Test-Path "requirements-compat.txt") {
        pip install -r requirements-compat.txt
    } else {
        pip install -r requirements.txt
    }

    deactivate
    Set-Location ..
    Print-Success "Python 依赖安装完成"
}

function Install-NodeDeps-Local {
    Print-Info "安装 Node.js 依赖 (本地模式)..."

    Set-Location $FRONTEND_DIR
    npm install
    Set-Location ..

    Print-Success "Node.js 依赖安装完成"
}

function Start-Redis-Local {
    Print-Info "检查 Redis..."
    if (Test-Command "redis-server") {
        Print-Info "启动 Redis..."
        redis-server --daemonize yes --port 6379 --maxmemory 64mb --maxmemory-policy allkeys-lru
    } else {
        Print-Warning "Redis 未安装，尝试使用 Docker..."
        if (Test-Command "docker") {
            docker run -d --name novel-reader-redis -p 6379:6379 redis:7-alpine --maxmemory 64mb --maxmemory-policy allkeys-lru
        } else {
            Print-Warning "Redis 不可用，禁用缓存功能"
        }
    }
}

function Start-Backend-Local {
    Print-Info "启动后端服务 (原生模式)..."

    Set-Location $BACKEND_DIR

    if (-not (Test-Path "venv")) {
        python -m venv venv
    }

    & .\venv\Scripts\Activate.ps1

    $env:DATABASE_URL = "sqlite+aiosqlite:///data/novel.db"
    $env:REDIS_URL = "redis://localhost:6379"
    $env:PYTHONDONTWRITEBYTECODE = "1"

    Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000" -WindowStyle Hidden

    deactivate
    Set-Location ..

    Print-Info "等待后端启动..."
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                Print-Success "后端服务已就绪"
                return
            }
        } catch {}
        Start-Sleep -Seconds 1
    }
    Print-Warning "后端启动较慢，请稍后检查"
}

function Start-Frontend-Local {
    Print-Info "启动前端服务 (原生模式)..."

    Set-Location $FRONTEND_DIR

    if (-not (Test-Path "node_modules")) {
        Print-Info "安装前端依赖..."
        npm install
    }

    Start-Process -FilePath "npm" -ArgumentList "run", "dev", "--", "--host", "0.0.0.0", "--port", "80" -WindowStyle Hidden

    Set-Location ..
    Print-Success "前端服务已启动"
}

function Test-Docker {
    try {
        $null = docker info 2>$null
        return $true
    } catch {
        return $false
    }
}

function Test-WSL {
    if (Test-Command "wsl") {
        try {
            $null = wsl --list 2>$null
            return $true
        } catch {
            return $false
        }
    }
    return $false
}

function Deploy-Local {
    Print-Header "Docker Desktop 本地部署"

    if (-not (Test-Docker)) {
        Print-Error "Docker Desktop 未安装或未运行"
        Print-Info "请访问 https://docker.com/download 下载安装"
        return
    }

    Set-Mirrors
    New-DataDirectories
    Test-EnvFile

    Print-Info "启动 Docker 服务..."
    docker-compose up -d redis
    Start-Sleep -Seconds 3
    docker-compose up -d backend
    docker-compose up -d frontend

    Print-Info "等待服务启动..."
    for ($i = 1; $i -le 60; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                Print-Success "服务已就绪"
                break
            }
        } catch {}
        Start-Sleep -Seconds 1
    }

    Print-Success "部署完成!"
    Write-Host ""
    Write-Host "  前端页面: http://localhost" -ForegroundColor Green
    Write-Host "  API 文档: http://localhost:8000/docs" -ForegroundColor Green
    Write-Host ""
}

function Deploy-WSL {
    Print-Header "WSL2 部署模式"

    if (-not (Test-WSL)) {
        Print-Error "WSL2 未安装"
        Print-Info "请运行: wsl --install"
        Print-Info "然后在 WSL 中运行: ./deploy.sh"
        return
    }

    Print-Info "检测到 WSL2，准备在 WSL 中部署..."

    wsl -- bash -c "cd /mnt/`$(wslpath '$PWD' | tr -d '\r') && chmod +x deploy.sh && ./deploy.sh"

    Print-Success "请在 WSL 终端中查看部署状态"
}

function Deploy-Native {
    Print-Header "原生模式部署 (无 Docker)"

    Set-Mirrors
    New-DataDirectories
    Test-EnvFile

    Install-PythonDeps-Local
    Install-NodeDeps-Local

    Start-Redis-Local
    Start-Backend-Local
    Start-Frontend-Local

    Print-Success "部署完成!"
    Write-Host ""
    Write-Host "  前端页面: http://localhost" -ForegroundColor Green
    Write-Host "  API 文档: http://localhost:8000/docs" -ForegroundColor Green
    Write-Host ""
    Print-Warning "注意: 原生模式需要手动启动服务"
}

function Show-Status {
    Print-Header "服务状态"

    if (Test-Docker) {
        Write-Host "Docker 容器:" -ForegroundColor Cyan
        docker-compose ps
    }

    Write-Host "`n健康检查:" -ForegroundColor Cyan
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Print-Success "后端 API: 运行中"
        }
    } catch {
        Print-Error "后端 API: 未响应"
    }

    try {
        $code = Invoke-WebRequest -Uri "http://localhost" -UseBasicParsing -TimeoutSec 2 | Select-Object -ExpandProperty StatusCode
        if ($code -in @(200, 301, 302)) {
            Print-Success "前端页面: 运行中"
        }
    } catch {
        Print-Error "前端页面: 未响应"
    }
}

function Stop-All {
    Print-Header "停止服务"

    if (Test-Docker) {
        Print-Info "停止 Docker 容器..."
        docker-compose down
    }

    Get-Process | Where-Object { $_.Name -match "uvicorn|python.*main|vite|npm.*dev" } | Stop-Process -Force -ErrorAction SilentlyContinue

    if (Test-Command "redis-cli") {
        redis-cli shutdown 2>$null
    }

    Print-Success "所有服务已停止"
}

function Show-Help {
    @"
Novel Reader 跨平台部署脚本 (Windows)

用法: .\deploy.ps1 [mode]

模式:
  local     Docker Desktop 模式 (默认)
  wsl       WSL2 模式 (推荐中国用户)
  native    原生模式 (不使用 Docker)

命令:
  .\deploy.ps1           部署 (默认 Docker 模式)
  .\deploy.ps1 local      Docker Desktop 模式
  .\deploy.ps1 wsl        WSL2 模式
  .\deploy.ps1 native     原生模式
  .\deploy.ps1 status     查看状态
  .\deploy.ps1 stop       停止服务
  .\deploy.ps1 help       显示帮助

访问地址:
  前端: http://localhost
  API:  http://localhost:8000/docs
"@
}

switch ($Mode) {
    "local" { Deploy-Local }
    "wsl" { Deploy-WSL }
    "native" { Deploy-Native }
    "status" { Show-Status }
    "stop" { Stop-All }
    "help" { Show-Help }
    default {
        if ($Mode -match "^(stop|status|help)$") {
            & "$PSCommandPath" $Mode
        } else {
            Deploy-Local
        }
    }
}
