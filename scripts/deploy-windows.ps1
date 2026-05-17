# Novel Reader 跨平台部署脚本 - Windows PowerShell
# 支持: Windows 10/11 (PowerShell 5.1+), WSL2, Docker Desktop
# 用法: .\deploy.ps1 [command]

param(
    [string]$Command = ""
)

$ErrorActionPreference = "Continue"

$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Cyan"
$Cyan = "Cyan"

$PROJECT_NAME = "novel-reader"
$PROJECT_DIR = $PSScriptRoot
$BACKEND_DIR = Join-Path $PROJECT_DIR "backend"
$FRONTEND_DIR = Join-Path $PROJECT_DIR "frontend"
$DATA_DIR = Join-Path $PROJECT_DIR "data"
$REQUIREMENTS_FILE = Join-Path $BACKEND_DIR "requirements.txt"

function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor $Blue }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor $Green }
function Write-Warning { param($msg) Write-Host "[WARN] $msg" -ForegroundColor $Yellow }
function Write-Error { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor $Red }
function Write-Header { param($msg)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor $Cyan
    Write-Host ("  $msg") -ForegroundColor $Cyan
    Write-Host ("=" * 60) -ForegroundColor $Cyan
}

function Get-Region {
    try {
        $response = Invoke-WebRequest -Uri "https://ipinfo.io/country" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($response.Content -eq "CN") {
            return "china"
        }
    } catch {}
    return "global"
}

function Test-Command { param($cmd)
    $null = Get-Command $cmd -ErrorAction SilentlyContinue
    return $?
}

function Test-Python {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        $version = & python --version 2>&1
        Write-Info "检测到 Python: $version"
        return $true
    }
    $py3 = Get-Command python3 -ErrorAction SilentlyContinue
    if ($py3) {
        Write-Info "检测到 Python3"
        return $true
    }
    return $false
}

function Test-Docker {
    try {
        $null = docker info 2>$null
        return $?
    } catch {
        return $false
    }
}

function Install-PythonWindows {
    Write-Header "安装 Python"
    $pythonUrl = "https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe"
    $installer = "$env:TEMP\python-installer.exe"
    Write-Warning "正在下载 Python 3.11..."
    try {
        Invoke-WebRequest -Uri $pythonUrl -OutFile $installer -UseBasicParsing
        Write-Info "运行安装程序..."
        Start-Process -FilePath $installer -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
        Write-Success "Python 安装完成"
    } catch {
        Write-Error "Python 安装失败: $_"
        Write-Info "请手动下载: https://www.python.org/downloads/"
    }
}

function Install-SystemDeps {
    Write-Header "安装系统依赖"
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Info "使用 winget 安装依赖..."
        winget install --id Python.Python.3.11 -e --silent --accept-source-agreements --accept-package-agreements 2>$null
        winget install --id OpenJS.NodeJS.LTS -e --silent --accept-source-agreements --accept-package-agreements 2>$null
    } elseif (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Info "使用 Chocolatey 安装依赖..."
        choco install python311 nodejs-lts -y 2>$null
    } else {
        Write-Warning "未找到包管理器，请手动安装 Python 和 Node.js"
        Write-Info "下载 Python: https://www.python.org/downloads/"
        Write-Info "下载 Node.js: https://nodejs.org/"
    }
}

function Set-PipMirror {
    $region = Get-Region
    if ($region -eq "china") {
        Write-Info "配置 pip 镜像源 (阿里云)..."
        $pipDir = "$env:APPDATA\pip"
        if (-not (Test-Path $pipDir)) {
            New-Item -ItemType Directory -Force -Path $pipDir | Out-Null
        }
        @"
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 120
trusted-host = mirrors.aliyun.com
pypi.tuna.tsinghua.edu.cn
"@ | Out-File -FilePath "$pipDir\pip.ini" -Encoding UTF8
        Write-Success "pip 镜像配置完成"
    }
}

function Set-NpmMirror {
    $region = Get-Region
    if ($region -eq "china") {
        Write-Info "配置 npm 镜像源..."
        npm config set registry https://registry.npmmirror.com
        Write-Success "npm 镜像配置完成"
    }
}

function Install-PythonDeps {
    Write-Header "安装 Python 依赖"
    if (-not (Test-Python)) {
        Write-Error "Python 未安装"
        Install-SystemDeps
        return
    }
    if (-not (Test-Path $REQUIREMENTS_FILE)) {
        Write-Error "requirements.txt 不存在: $REQUIREMENTS_FILE"
        return
    }
    Set-PipMirror
    Push-Location $BACKEND_DIR
    if (-not (Test-Path "venv")) {
        Write-Info "创建虚拟环境..."
        python -m venv venv
    }
    Write-Info "激活虚拟环境..."
    & .\venv\Scripts\Activate.ps1
    Write-Info "升级 pip..."
    python -m pip install --upgrade pip
    Write-Info "安装依赖 (纯 Python 版本，无编译)..."
    python -m pip install -r requirements.txt
    & deactivate
    Pop-Location
    Write-Success "Python 依赖安装完成"
}

function Install-NodeDeps {
    Write-Header "安装 Node.js 依赖"
    if (-not (Test-Command "node")) {
        Write-Error "Node.js 未安装"
        return
    }
    Set-NpmMirror
    Push-Location $FRONTEND_DIR
    if (-not (Test-Path "package.json")) {
        Write-Error "package.json 不存在"
        Pop-Location
        return
    }
    Write-Info "安装 npm 包..."
    npm install
    Pop-Location
    Write-Success "Node.js 依赖安装完成"
}

function Install-RedisDocker {
    Write-Header "安装 Redis (Docker)"
    if (Test-Docker) {
        $redisRunning = docker ps -a | Select-String "redis"
        if ($redisRunning) {
            Write-Info "Redis 容器已存在"
        } else {
            Write-Info "拉取 Redis 镜像..."
            docker pull redis:7-alpine
            Write-Info "启动 Redis 容器..."
            docker run -d --name novel-reader-redis -p 6379:6379 redis:7-alpine redis-server --appendonly yes --maxmemory 64mb --maxmemory-policy allkeys-lru
        }
        Write-Success "Redis (Docker) 安装完成"
    } else {
        Write-Error "Docker 未安装或未运行"
    }
}

function New-DataDirectories {
    Write-Header "创建数据目录"
    $dirs = @("books", "index", "static", "logs", "cache", "backups", "versions")
    foreach ($dir in $dirs) {
        $path = Join-Path $DATA_DIR $dir
        if (-not (Test-Path $path)) {
            New-Item -ItemType Directory -Force -Path $path | Out-Null
            Write-Info "创建: $path"
        }
    }
    Write-Success "数据目录创建完成"
}

function Test-EnvFile {
    $envFile = Join-Path $PROJECT_DIR ".env"
    if (-not (Test-Path $envFile)) {
        Write-Info "创建 .env 配置文件..."
        $secretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
        @"
SECRET_KEY=$secretKey
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://localhost:6379
"@ | Out-File -FilePath $envFile -Encoding UTF8
        Write-Success ".env 文件已创建"
    }
}

function Install-All {
    Write-Header "完整安装"
    Install-SystemDeps
    Install-PythonDeps
    Install-NodeDeps
    New-DataDirectories
    Test-EnvFile
    if (Test-Docker) {
        Install-RedisDocker
    }
    Write-Header "安装完成"
    Write-Success "Novel Reader 环境配置完成!"
}

function Start-Local {
    Write-Header "启动服务 (本地模式)"
    if (-not (Test-Python)) {
        Write-Error "Python 未安装，请先运行 .\deploy.ps1 install"
        return
    }
    if (-not (Test-Command "node")) {
        Write-Error "Node.js 未安装，请先运行 .\deploy.ps1 install"
        return
    }
    Test-EnvFile
    New-DataDirectories
    Write-Info "启动后端..."
    Push-Location $BACKEND_DIR
    if (-not (Test-Path "venv")) {
        python -m venv venv
    }
    & .\venv\Scripts\Activate.ps1
    Start-Process -FilePath "uvicorn" -ArgumentList "app.main:app --host 0.0.0.0 --port 8000 --reload" -NoNewWindow
    Start-Sleep -Seconds 2
    & deactivate
    Pop-Location
    Write-Info "启动前端..."
    Push-Location $FRONTEND_DIR
    Start-Process -FilePath "npm" -ArgumentList "run dev" -NoNewWindow
    Pop-Location
    Write-Success "服务已启动"
    Write-Host ""
    Write-Host "  访问地址:" -ForegroundColor $Green
    Write-Host "  前端: http://localhost"
    Write-Host "  API:  http://localhost:8000/docs"
}

function Start-Docker {
    Write-Header "启动服务 (Docker 模式)"
    if (-not (Test-Docker)) {
        Write-Error "Docker 未安装或未运行"
        return
    }
    Push-Location $PROJECT_DIR
    Write-Info "构建并启动容器..."
    docker-compose up -d
    Write-Info "等待服务启动..."
    Start-Sleep -Seconds 5
    Pop-Location
    Write-Success "Docker 服务已启动"
    Write-Host ""
    Write-Host "  访问地址:" -ForegroundColor $Green
    Write-Host "  前端: http://localhost"
    Write-Host "  API:  http://localhost:8000/docs"
}

function Stop-Docker {
    Write-Header "停止 Docker 服务"
    if (Test-Docker) {
        docker-compose down
        Write-Success "Docker 服务已停止"
    }
}

function Show-Status {
    Write-Header "服务状态"
    if (Test-Docker) {
        Write-Host "Docker 容器:" -ForegroundColor $Cyan
        docker-compose ps
    }
    Write-Host ""
    Write-Host "健康检查:" -ForegroundColor $Cyan
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Success "后端 API: 运行中"
        }
    } catch {
        Write-Error "后端 API: 未响应"
    }
    try {
        $response = Invoke-WebRequest -Uri "http://localhost" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        Write-Success "前端页面: 运行中"
    } catch {
        Write-Error "前端页面: 未响应"
    }
}

function Show-Logs {
    Write-Header "查看日志"
    $logDir = Join-Path $DATA_DIR "logs"
    if (Test-Path $logDir) {
        $logFiles = Get-ChildItem -Path $logDir -Filter "*.log" -ErrorAction SilentlyContinue
        if ($logFiles) {
            Write-Info "正在显示日志 (按 Ctrl+C 退出)..."
            Get-Content -Path "$logDir\*.log" -Wait -Tail 50
        } else {
            Write-Warning "暂无日志文件"
        }
    } else {
        Write-Warning "日志目录不存在"
    }
}

function Show-Help {
    @"
Novel Reader 跨平台部署脚本 (Windows PowerShell)

用法: .\deploy.ps1 [command]

命令:
  install       完整安装所有依赖 (首次运行必须)
  python        仅安装 Python 依赖
  node          仅安装 Node.js 依赖
  redis         安装 Redis (Docker 方式)
  start         启动服务 (本地模式)
  docker        启动服务 (Docker 模式)
  stop          停止 Docker 服务
  status        查看服务状态
  logs          查看日志
  mirror        配置镜像源
  help          显示此帮助信息

示例:
  .\deploy.ps1            # 显示帮助
  .\deploy.ps1 install    # 完整安装
  .\deploy.ps1 start      # 启动本地服务
  .\deploy.ps1 docker     # 启动 Docker 服务

环境要求:
  - Windows 10/11 或 WSL2
  - Python 3.8+ 或 Docker Desktop
  - Node.js 16+ (本地模式)
  - Git (可选)

自动检测:
  - 中国大陆自动使用阿里云/清华镜像
  - 自动检测 Docker 或本地模式
  - 所有 Python 包使用纯 Python 版本，无需编译
"@
}

switch ($Command.ToLower()) {
    "install" { Install-All }
    "python" { Install-PythonDeps }
    "node" { Install-NodeDeps }
    "redis" { Install-RedisDocker }
    "start" { Start-Local }
    "docker" { Start-Docker }
    "stop" { Stop-Docker }
    "status" { Show-Status }
    "logs" { Show-Logs }
    "mirror" { Set-PipMirror; Set-NpmMirror }
    "help" { Show-Help }
    "" { Show-Help }
    default {
        Write-Error "未知命令: $Command"
        Show-Help
        exit 1
    }
}
