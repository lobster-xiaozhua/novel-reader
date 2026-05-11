# Novel Reader 跨平台部署脚本 - Windows PowerShell
# 支持 Docker Desktop / WSL2 / 本地安装
# 用法:
#   .\deploy.ps1              - 交互式菜单
#   .\deploy.ps1 docker        - Docker 部署
#   .\deploy.ps1 wsl          - WSL2 部署
#   .\deploy.ps1 local        - 本地安装
#   .\deploy.ps1 termux       - Termux 安装 (通过 WSL)
#   .\deploy.ps1 status       - 查看状态
#   .\deploy.ps1 uninstall    - 卸载

param(
    [string]$Command = ""
)

$ErrorActionPreference = "Continue"
$PROJECT_NAME = "novel-reader"
$PROJECT_DIR = $PSScriptRoot
$BACKEND_DIR = Join-Path $PROJECT_DIR "backend"
$FRONTEND_DIR = Join-Path $PROJECT_DIR "frontend"
$DATA_DIR = Join-Path $PROJECT_DIR "data"
$INSTALL_MARKER = Join-Path $PROJECT_DIR ".installed"

$ColRed = "Red"
$ColGreen = "Green"
$ColYellow = "Yellow"
$ColBlue = "Cyan"
$ColMagenta = "Magenta"

function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor $ColBlue }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor $ColGreen }
function Write-Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor $ColYellow }
function Write-Err { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor $ColRed }
function Write-Header { param($msg)
    Write-Host ""
    Write-Host ("══════ $msg ═════=") -ForegroundColor $ColMagenta
}

function Test-Command($cmd) {
    try {
        $null = Get-Command $cmd -ErrorAction Stop
        return $true
    } catch { return $false }
}

function Get-Region {
    try {
        $r = Invoke-WebRequest -Uri "https://ipinfo.io/country" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($r.Content -trim -eq "CN") { return "china" }
    } catch {}
    return "global"
}

function Set-Mirrors-Windows {
    Write-Header "配置镜像源"
    $region = Get-Region

    if ($region -eq "china") {
        Write-Info "检测到中国地区，配置镜像..."

        $pipDir = "$env:APPDATA\pip"
        if (-not (Test-Path $pipDir)) { New-Item -ItemType Directory -Force -Path $pipDir | Out-Null }
        @"
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 120

[install]
trusted-host = mirrors.aliyun.com
             pypi.tuna.tsinghua.edu.cn
"@ | Out-File -FilePath "$pipDir\pip.ini" -Encoding UTF8
        Write-Success "pip: 阿里云"

        try {
            npm config set registry https://registry.npmmirror.com
            Write-Success "npm: npmmirror.com"
        } catch { Write-Warn "npm 配置失败" }

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
        Write-Success "Docker 镜像加速已配置"
    } else {
        Write-Info "使用官方源"
    }
}

function New-DataDirs {
    Write-Info "创建数据目录..."
    $dirs = @("books", "index", "static", "logs", "cache", "backups", "versions")
    foreach ($d in $dirs) {
        $path = Join-Path $DATA_DIR $d
        if (-not (Test-Path $path)) { New-Item -ItemType Directory -Force -Path $path | Out-Null }
    }
    Write-Success "目录创建完成"
}

function Test-EnvFile {
    $envFile = Join-Path $PROJECT_DIR ".env"
    if (-not (Test-Path $envFile)) {
        Write-Info "创建 .env 配置文件..."
        $secret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
        @"
SECRET_KEY=$secret
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///$($DATA_DIR.Replace('\','/'))/novel.db
REDIS_URL=redis://localhost:6379
DATA_DIR=$DATA_DIR
BOOKS_DIR=$DATA_DIR\books
INDEX_DIR=$DATA_DIR\index
STATIC_DIR=$DATA_DIR\static
LOGS_DIR=$DATA_DIR\logs
CACHE_DIR=$DATA_DIR\cache
"@ | Out-File -FilePath $envFile -Encoding UTF8
        Write-Success ".env 已创建"
    }
}

function Install-PythonDeps-Windows($venvPath) {
    $python = if ($venvPath) { Join-Path $venvPath "Scripts\python.exe" } else { "python" }
    $pip = if ($venvPath) { Join-Path $venvPath "Scripts\pip.exe" } else { "pip" }

    Write-Info "升级 pip..."
    & $pip install --upgrade pip --quiet

    $reqFile = Join-Path $BACKEND_DIR "requirements-pure-python.txt"
    if (-not (Test-Path $reqFile)) { $reqFile = Join-Path $BACKEND_DIR "requirements.txt" }

    Write-Info "安装 Python 依赖..."
    & $pip install -r $reqFile --quiet

    Write-Success "Python 依赖安装完成"
}

function Install-NodeDeps-Windows {
    Write-Info "安装 Node.js 依赖..."
    Set-Location $FRONTEND_DIR
    npm install
    Set-Location $PROJECT_DIR
    Write-Success "Node.js 依赖安装完成"
}

function Install-Python-Windows {
    if (Test-Command "python") {
        Write-Info "Python 已安装: $(python --version)"
        return $true
    }

    Write-Warn "Python 未安装"
    Write-Info "请选择安装方式:"
    Write-Info "  1. 访问 https://python.org/downloads 下载 Python 3.11"
    Write-Info "  2. 或使用 winget: winget install Python.Python.3.11"
    Write-Info "  3. 或使用 Chocolatey: choco install python311"
    return $false
}

function Deploy-Docker-Windows {
    Write-Header "Docker 部署"

    if (-not (Test-Command "docker")) {
        Write-Err "Docker 未安装"
        Write-Info "请访问 https://docs.docker.com/desktop/install/windows-install/ 下载 Docker Desktop"
        return $false
    }

    try {
        $null = docker info 2>$null
    } catch {
        Write-Err "Docker 未运行，请先启动 Docker Desktop"
        return $false
    }

    if (-not (Test-Command "docker-compose")) {
        Write-Info "安装 docker-compose..."
        docker compose version | Out-Null
    }

    Set-Mirrors-Windows
    New-DataDirs
    Test-EnvFile

    Write-Info "构建并启动服务..."
    Set-Location $PROJECT_DIR

    docker-compose up -d redis
    Start-Sleep -Seconds 3
    docker-compose up -d backend

    if (Test-Path (Join-Path $FRONTEND_DIR "dist\index.html")) {
        docker-compose up -d frontend
    }

    Write-Info "等待服务就绪..."
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $r = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) {
                Write-Success "后端服务已就绪"
                break
            }
        } catch {}
        Start-Sleep -Seconds 1
    }

    Write-Success "Docker 部署完成!"
    Write-Host "  前端: http://localhost"
    Write-Host "  API:  http://localhost:8000/docs"

    return $true
}

function Deploy-WSL {
    Write-Header "WSL2 部署"

    if (-not (Test-Command "wsl")) {
        Write-Err "WSL2 未安装"
        Write-Info "请在 PowerShell 中运行: wsl --install"
        return $false
    }

    Write-Info "检测 WSL 发行版..."
    $distros = wsl --list --quiet
    if (-not $distros) {
        Write-Err "没有找到 WSL 发行版"
        Write-Info "请运行: wsl --install -d ubuntu"
        return $false
    }

    Write-Info "将使用 WSL 进行部署，请确保 WSL 中已安装 Python 和 Node.js"
    Write-Info "在 WSL 终端中运行: ./start.sh"

    return $true
}

function Deploy-Local-Windows {
    Write-Header "本地部署 (Windows)"

    if (-not (Install-Python-Windows)) { return $false }

    if (-not (Test-Command "node")) {
        Write-Err "Node.js 未安装"
        Write-Info "请访问 https://nodejs.org/ 下载安装"
        return $false
    }

    Set-Mirrors-Windows
    New-DataDirs
    Test-EnvFile

    $venvPath = Join-Path $BACKEND_DIR "venv"
    if (-not (Test-Path $venvPath)) {
        Write-Info "创建 Python 虚拟环境..."
        python -m venv $venvPath
    }

    Install-PythonDeps-Windows $venvPath
    Install-NodeDeps-Windows

    Write-Success "本地部署完成!"
    Write-Host ""
    Write-Host "启动服务:"
    Write-Host "  后端: cd $BACKEND_DIR; .\venv\Scripts\Activate.ps1; uvicorn main:app --reload"
    Write-Host "  前端: cd $FRONTEND_DIR; npm run dev"
    Write-Host ""
    Write-Host "或使用一键启动: .\start.ps1"

    "windows-local" | Out-File -FilePath $INSTALL_MARKER -Encoding UTF8
    return $true
}

function Deploy-Termux-Windows {
    Write-Header "Termux 部署说明 (通过 WSL)"
    Write-Info "请在 Termux (Android) 中运行以下命令:"
    Write-Host ""
    Write-Host "  # 安装 Termux 后，在 Termux 中运行:"
    Write-Host "  pkg update && pkg install proot-distro"
    Write-Host "  proot-distro install ubuntu"
    Write-Host "  proot-distro login ubuntu"
    Write-Host "  # 然后在 Ubuntu 中克隆项目并运行 ./deploy.sh"
    Write-Host ""
    Write-Info "或者直接在 Termux 中使用项目根目录的 deploy-termux.sh"
}

function Show-Status-Windows {
    Write-Header "服务状态"

    if (Test-Command "docker") {
        try {
            $null = docker info 2>$null
            Write-Host "Docker 容器:" -ForegroundColor $ColBlue
            docker-compose ps 2>$null
        } catch {}
    }

    Write-Host "`n健康检查:" -ForegroundColor $ColBlue
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { Write-Success "后端 API: 运行中" }
    } catch { Write-Err "后端 API: 未响应" }

    try {
        $r = Invoke-WebRequest -Uri "http://localhost" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -in @(200, 301, 302)) { Write-Success "前端页面: 运行中" }
    } catch { Write-Err "前端页面: 未响应" }
}

function Stop-Services-Windows {
    Write-Header "停止服务"
    if (Test-Command "docker") {
        try {
            $null = docker info 2>$null
            Set-Location $PROJECT_DIR
            docker-compose down
            Write-Success "Docker 服务已停止"
        } catch {
            Write-Info "Docker 未运行或服务未启动"
        }
    }

    Get-Process uvicorn -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Get-Process node -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*vite*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Success "本地服务已停止"
}

function Uninstall-Windows {
    Write-Header "卸载"
    Write-Warn "此操作将删除虚拟环境和安装标记!"

    Stop-Services-Windows

    $venvPath = Join-Path $BACKEND_DIR "venv"
    if (Test-Path $venvPath) {
        Remove-Item -Recurse -Force $venvPath
        Write-Success "已删除虚拟环境"
    }

    if (Test-Path $INSTALL_MARKER) {
        Remove-Item -Force $INSTALL_MARKER
        Write-Success "已删除安装标记"
    }

    Write-Success "卸载完成"
}

function Show-Menu {
    Write-Host ""
    Write-Host ("═══════════════════════════════════════════") -ForegroundColor $ColMagenta
    Write-Host ("  Novel Reader - 跨平台部署工具") -ForegroundColor $ColMagenta
    Write-Host ("═══════════════════════════════════════════") -ForegroundColor $ColMagenta
    Write-Host ""
    Write-Host "1. Docker Desktop 部署        (推荐，有 Docker 的用户)"
    Write-Host "2. WSL2 部署                  (Linux 子系统)"
    Write-Host "3. 本地安装                   (无 Docker，纯 Windows)"
    Write-Host "4. Termux 部署说明            (Android)"
    Write-Host ""
    Write-Host "s. 查看状态"
    Write-Host "m. 配置镜像源"
    Write-Host "u. 卸载"
    Write-Host "q. 退出"
    Write-Host ""
    Write-Host ("═══════════════════════════════════════════") -ForegroundColor $ColMagenta
    Write-Host ""
}

function Show-Help-Windows {
    @"
Novel Reader 跨平台部署脚本 (Windows PowerShell)

用法: .\deploy.ps1 [command]

命令:
  docker      Docker Desktop 部署 (推荐)
  wsl         WSL2 部署
  local       本地安装 (纯 Windows)
  termux      Termux 部署说明
  status      查看服务状态
  mirror      配置镜像源
  uninstall   卸载
  help        显示帮助

示例:
  .\deploy.ps1           # 显示交互式菜单
  .\deploy.ps1 docker     # Docker 部署
  .\deploy.ps1 local     # 本地安装
  .\deploy.ps1 status    # 查看状态

支持平台:
  Windows 10/11 + Docker Desktop
  Windows 10/11 + WSL2
  Windows 10/11 (本地 Python + Node.js)
  Android + Termux (使用 deploy-termux.sh)
  Linux (使用 deploy.sh)
"@
}

switch ($Command.ToLower()) {
    "docker" { Deploy-Docker-Windows }
    "wsl" { Deploy-WSL }
    "local" { Deploy-Local-Windows }
    "termux" { Deploy-Termux-Windows }
    "status" { Show-Status-Windows }
    "stop" { Stop-Services-Windows }
    "mirror" { Set-Mirrors-Windows }
    "uninstall" { Uninstall-Windows }
    "help" { Show-Help-Windows }
    "q" { exit 0 }
    "" {
        Show-Menu
        $choice = Read-Host "请选择 (1-4, s, m, u, q)"
        switch ($choice) {
            "1" { Deploy-Docker-Windows }
            "2" { Deploy-WSL }
            "3" { Deploy-Local-Windows }
            "4" { Deploy-Termux-Windows }
            "s" { Show-Status-Windows }
            "m" { Set-Mirrors-Windows }
            "u" { Uninstall-Windows }
            "q" { exit 0 }
        }
    }
    default {
        Write-Err "未知命令: $Command"
        Show-Help-Windows
        exit 1
    }
}
