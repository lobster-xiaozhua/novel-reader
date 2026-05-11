# Novel Reader 跨平台部署脚本 (Windows PowerShell)
# 支持 Docker Desktop 或 WSL2
# 版本: 1.0.0

param(
    [Parameter(Position=0)]
    [ValidateSet("install", "start", "stop", "restart", "status", "logs", "deps", "docker", "wsl", "help")]
    [string]$Command = "",
    [switch]$SkipMirror,
    [switch]$UseWSL
)

$ErrorActionPreference = "Stop"
$ScriptVersion = "1.0.0"

$PROJECT_NAME = "novel-reader"
$BACKEND_DIR = Join-Path $PSScriptRoot "backend"
$FRONTEND_DIR = Join-Path $PSScriptRoot "frontend"
$DATA_DIR = Join-Path $PSScriptRoot "data"

$colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Cyan"
    Cyan = "Cyan"
    Magenta = "Magenta"
}

function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor $colors.Blue }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor $colors.Green }
function Write-Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor $colors.Yellow }
function Write-Err { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor $colors.Red }
function Write-Step { param($msg) Write-Host "[>] $msg" -ForegroundColor $colors.Cyan }

function Write-Banner {
    Write-Host ""
    Write-Host "════════════════════════════════════════════════════" -ForegroundColor $colors.Magenta
    Write-Host "  Novel Reader 跨平台部署 (Windows) v$ScriptVersion" -ForegroundColor $colors.Magenta
    Write-Host "════════════════════════════════════════════════════" -ForegroundColor $colors.Magenta
    Write-Host ""
}

function Test-Command { param([string]$cmd) $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue) }

function Test-Docker {
    try { $null = docker info 2>$null; return $true } catch { return $false }
}

function Test-WSL {
    try { $null = wsl --status 2>$null; return $true } catch { return $false }
}

function Get-SystemRegion {
    try {
        $response = Invoke-WebRequest -Uri "https://ipinfo.io/country" -UseBasicParsing -TimeoutSec 3
        if ($response.Content -trim -eq "CN") { return "CN" }
    } catch {}
    return "GLOBAL"
}

function Set-PyMirror {
    Write-Step "配置 Python pip 镜像源..."
    $pipDir = "$env:APPDATA\pip"
    if (-not (Test-Path $pipDir)) { New-Item -ItemType Directory -Force -Path $pipDir | Out-Null }
    @"
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 120
trusted-host = mirrors.aliyun.com

[install]
prefer-binary = true
only-binary = :all:
"@ | Out-File -FilePath "$pipDir\pip.ini" -Encoding UTF8
    Write-Success "pip 镜像: 阿里云"
}

function Set-NpmMirror {
    Write-Step "配置 npm 镜像源..."
    npm config set registry https://registry.npmmirror.com 2>$null
    npm config set prefix "$env:USERPROFILE\.npm-global" 2>$null
    Write-Success "npm 镜像: npmmirror.com"
}

function Set-DockerMirror {
    Write-Step "配置 Docker 镜像加速..."
    $dockerDir = "$env:USERPROFILE\.docker"
    if (-not (Test-Path $dockerDir)) { New-Item -ItemType Directory -Force -Path $dockerDir | Out-Null }
    @"
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ],
  "builder": { "gc": { "enabled": true, "defaultKeepStorage": "20GB" } },
  "features": { "buildkit": true }
}
"@ | Out-File -FilePath "$dockerDir\daemon.json" -Encoding UTF8
    Write-Success "Docker 镜像加速已配置 (重启 Docker Desktop 生效)"
}

function Initialize-Project {
    Write-Step "初始化项目目录..."
    @("books", "index", "static", "logs", "cache", "backups", "versions") | ForEach-Object {
        $path = Join-Path $DATA_DIR $_
        if (-not (Test-Path $path)) { New-Item -ItemType Directory -Force -Path $path | Out-Null }
    }
    Write-Success "目录创建完成"
}

function Initialize-EnvFile {
    Write-Step "检查 .env 文件..."
    $envPath = Join-Path $PSScriptRoot ".env"
    if (-not (Test-Path $envPath)) {
        $secretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | ForEach-Object { [char]$_ })
        @"
SECRET_KEY=$secretKey
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://redis:6379
ACCESS_TOKEN_EXPIRE_MINUTES=1440
BCRYPT_ROUNDS=12
PASSWORD_MIN_LENGTH=6
"@ | Out-File -FilePath $envPath -Encoding UTF8
        Write-Success ".env 文件已创建"
    } else { Write-Info ".env 文件已存在" }
}

function Install-PythonDeps {
    Write-Step "安装 Python 依赖..."
    if (-not (Test-Command "python")) { Write-Err "Python 未安装"; return $false }
    Push-Location $BACKEND_DIR
    if (-not (Test-Path "venv")) { Write-Info "创建虚拟环境..."; python -m venv venv }
    & ".\venv\Scripts\Activate.ps1"
    Write-Info "升级 pip..."; pip install --upgrade pip -q
    Write-Info "安装依赖 (使用预编译 wheel)..."
    pip install --only-binary :all: -r requirements-compat.txt 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Warn "尝试混合安装..."; pip install -r requirements-compat.txt -q }
    deactivate; Pop-Location
    Write-Success "Python 依赖安装完成"; return $true
}

function Install-NodeDeps {
    Write-Step "安装 Node.js 依赖..."
    if (-not (Test-Command "node")) { Write-Err "Node.js 未安装"; return $false }
    Push-Location $FRONTEND_DIR
    if (-not (Test-Path "node_modules")) { Write-Info "安装 npm 包..."; npm install --legacy-peer-deps }
    Pop-Location
    Write-Success "Node.js 依赖安装完成"; return $true
}

function Install-Docker {
    Write-Banner; Write-Step "检查 Docker 环境..."
    if (-not (Test-Command "docker")) { Write-Err "Docker 未安装，请从 https://www.docker.com/products/docker-desktop 下载"; return $false }
    if (-not (Test-Docker)) { Write-Warn "Docker 未运行，请启动 Docker Desktop"; return $false }
    Write-Success "Docker 环境就绪"; return $true
}

function Install-WSL {
    Write-Banner; Write-Step "检查 WSL 环境..."
    if (-not (Test-WSL)) { Write-Info "WSL 未安装，运行: wsl --install -d Ubuntu"; return $false }
    Write-Success "WSL 环境就绪"
    Write-Host "  wsl bash ./deploy.sh" -ForegroundColor $colors.Cyan
    return $true
}

function Start-DockerStack {
    Write-Step "启动 Docker 服务..."
    if (-not (Test-Docker)) { Write-Err "Docker 未运行"; return $false }
    Initialize-Project; Initialize-EnvFile
    Write-Info "启动 Redis..."; docker-compose up -d redis; Start-Sleep -Seconds 3
    Write-Info "启动后端..."; docker-compose up -d backend
    Write-Info "等待后端就绪..."
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { Write-Success "后端服务已就绪"; break }
        } catch {}
        Start-Sleep -Seconds 1
    }
    Write-Info "启动前端..."
    if (-not (Test-Path (Join-Path $FRONTEND_DIR "dist\index.html"))) {
        Write-Info "构建前端..."
        Push-Location $FRONTEND_DIR
        if (-not (Test-Path "node_modules")) { npm install --legacy-peer-deps }
        npm run build; Pop-Location
    }
    docker-compose up -d frontend
    Write-Success "所有服务已启动"
}

function Stop-DockerStack { Write-Step "停止 Docker 服务..."; docker-compose down 2>$null; Write-Success "服务已停止" }

function Show-DockerStatus {
    Write-Banner; Write-Step "服务状态"
    if (-not (Test-Docker)) { Write-Warn "Docker 未运行"; return }
    docker-compose ps
    Write-Host ""; Write-Step "健康检查:"
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) { Write-Success "后端 API: 运行中" } else { Write-Err "后端 API: 未响应" }
    } catch { Write-Err "后端 API: 未响应" }
}

function Show-DockerLogs { Write-Step "查看日志 (Ctrl+C 退出)"; docker-compose logs -f }

function Invoke-LocalStart {
    Write-Step "启动本地服务..."
    Push-Location $BACKEND_DIR
    if (-not (Test-Path "venv")) { Write-Info "创建虚拟环境..."; python -m venv venv }
    & ".\venv\Scripts\Activate.ps1"
    $logDir = Join-Path $PSScriptRoot "data\logs"
    if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
    $logFile = Join-Path $logDir "backend.log"
    Write-Info "启动 uvicorn..."
    Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" -NoNewWindow -RedirectStandardOutput $logFile -RedirectStandardError (Join-Path $logDir "backend_error.log")
    deactivate; Pop-Location
    Write-Success "后端服务已启动"
    Write-Host ""; Write-Info "启动前端开发服务器..."
    Push-Location $FRONTEND_DIR
    Start-Process -FilePath "npm" -ArgumentList "run", "dev" -NoNewWindow; Pop-Location
    Write-Success "前端服务已启动"
}

function Show-Help {
    Write-Banner
    @"
用法: .\deploy.ps1 [command] [options]

命令:
  install     安装所有依赖 (Python + Node.js)
  start       启动服务 (Docker 或本地)
  stop        停止服务
  restart     重启服务
  status      查看服务状态
  logs        查看服务日志
  deps        仅安装依赖
  docker      仅检查/配置 Docker
  wsl         仅检查/配置 WSL
  help        显示帮助

选项:
  -SkipMirror    跳过镜像源配置
  -UseWSL        强制使用 WSL 模式

示例:
  .\deploy.ps1
  .\deploy.ps1 install
  .\deploy.ps1 start
  .\deploy.ps1 -SkipMirror

环境要求:
  - Docker Desktop 4.x+ (推荐)
  - 或 WSL2 + Ubuntu
  - Python 3.10+
  - Node.js 18+

文档: https://github.com/lobster-xiaozhua/novel-reader
"@
}

switch ($Command) {
    "install" {
        Write-Banner
        if (-not $SkipMirror -and (Get-SystemRegion) -eq "CN") { Set-PyMirror; Set-NpmMirror }
        Initialize-Project; Initialize-EnvFile
        Install-PythonDeps; Install-NodeDeps
        Write-Success "安装完成!"
    }
    "start" {
        Write-Banner
        if ($UseWSL) {
            if (Test-WSL) { wsl bash ./deploy.sh } else { Write-Err "WSL 未安装" }
        } elseif (Test-Docker) { Start-DockerStack } else {
            Write-Warn "Docker 未运行，使用本地模式"
            Initialize-Project; Initialize-EnvFile; Invoke-LocalStart
        }
    }
    "stop" { Write-Banner; if (Test-Docker) { Stop-DockerStack } }
    "restart" { Write-Banner; if (Test-Docker) { Stop-DockerStack; Start-Sleep -Seconds 2; Start-DockerStack } }
    "status" { Show-DockerStatus }
    "logs" { Show-DockerLogs }
    "deps" {
        Write-Banner
        if (-not $SkipMirror -and (Get-SystemRegion) -eq "CN") { Set-PyMirror; Set-NpmMirror }
        Initialize-Project; Install-PythonDeps; Install-NodeDeps
    }
    "docker" {
        Write-Banner
        if (-not $SkipMirror -and (Get-SystemRegion) -eq "CN") { Set-DockerMirror }
        Install-Docker
    }
    "wsl" { Write-Banner; Install-WSL }
    "help" { Show-Help }
    "" {
        Write-Banner
        Write-Step "欢迎使用 Novel Reader 跨平台部署工具"
        Write-Host ""
        Write-Host "请选择操作:" -ForegroundColor $colors.Yellow
        Write-Host "  1. install  - 安装依赖"
        Write-Host "  2. start    - 启动服务"
        Write-Host "  3. stop     - 停止服务"
        Write-Host "  4. status   - 查看状态"
        Write-Host "  5. docker   - 配置 Docker"
        Write-Host "  6. help     - 查看帮助"
        Write-Host ""
        Write-Host "示例: .\deploy.ps1 start" -ForegroundColor $colors.Cyan
    }
    default { Write-Err "未知命令: $Command"; Show-Help; exit 1 }
}
