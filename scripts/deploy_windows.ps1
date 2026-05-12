# Novel Reader - Windows 部署脚本
# 支持: Windows 10/11, PowerShell 5.1+
# 模式: Docker Desktop 或 WSL2

param(
    [switch]$UseWSL,
    [switch]$SkipDocker,
    [switch]$NoInstall
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

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

$SCRIPT_DIR = $PSScriptRoot
$PROJECT_NAME = "novel-reader"
$BACKEND_DIR = "$SCRIPT_DIR\backend"
$FRONTEND_DIR = "$SCRIPT_DIR\frontend"
$DATA_DIR = "$SCRIPT_DIR\data"
$PYTHON_DEPS_FILE = "$BACKEND_DIR\requirements.txt"

function Test-WSL {
    if ($IsLinux -or $IsMacOS) { return $true }
    if (Test-Path "/proc/version" -PathType Leaf) {
        $content = Get-Content "/proc/version" -Raw -ErrorAction SilentlyContinue
        if ($content -match "Microsoft|WSL") { return $true }
    }
    return $false
}

function Test-Termux {
    return (Test-Path "$env:PREFIX" -PathType Container)
}

function Get-Region {
    try {
        $response = Invoke-WebRequest -Uri "https://ipinfo.io/country" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.Content.Trim() -eq "CN") {
            return "china"
        }
    } catch {}
    return "global"
}

function Test-PythonInstalled {
    try {
        $version = python --version 2>$null
        if ($version) {
            Write-ColorOutput "[OK] Python 已安装: $version" $Colors.Success
            return $true
        }
    } catch {
        try {
            $version = python3 --version 2>$null
            if ($version) {
                Write-ColorOutput "[OK] Python 已安装: $version" $Colors.Success
                return $true
            }
        } catch {}
    }
    return $false
}

function Test-DockerInstalled {
    try {
        $null = docker --version 2>$null
        $null = docker info 2>$null
        Write-ColorOutput "[OK] Docker 已安装并运行" $Colors.Success
        return $true
    } catch {
        Write-ColorOutput "[INFO] Docker 未安装或未运行" $Colors.Info
        return $false
    }
}

function Test-NodeInstalled {
    try {
        $version = node --version 2>$null
        if ($version) {
            Write-ColorOutput "[OK] Node.js 已安装: $version" $Colors.Success
            return $true
        }
    } catch {}
    return $false
}

function Set-Mirrors {
    Write-ColorOutput "`n=== 配置镜像源 ===" $Colors.Header

    $region = Get-Region

    if ($region -eq "china") {
        Write-ColorOutput "[INFO] 检测到中国地区，配置国内镜像..." $Colors.Info

        $pipDir = "$env:APPDATA\pip"
        if (-not (Test-Path $pipDir)) {
            New-Item -ItemType Directory -Force -Path $pipDir | Out-Null
        }
        @"
[global]
index-url = https://mirrors.aliyun.com.com/pypi/simple/
timeout = 120
extra-index-url = https://pypi.tuna.tsinghua.edu.cn/simple

[install]
trusted-host =
    mirrors.aliyun.com
    pypi.tuna.tsinghua.edu.cn
"@ | Out-File -FilePath "$pipDir\pip.ini" -Encoding UTF8
        Write-ColorOutput "[OK] pip 镜像: 阿里云" $Colors.Success

        npm config set registry https://registry.npmmirror.com --location user 2>$null
        Write-ColorOutput "[OK] npm 镜像: npmmirror.com" $Colors.Success

        $dockerDir = "$env:USERPROFILE\.docker"
        if (-not (Test-Path $dockerDir)) {
            New-Item -ItemType Directory -Force -Path $dockerDir | Out-Null
        }
        @"
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
"@ | Out-File -FilePath "$dockerDir\daemon.json" -Encoding UTF8
        Write-ColorOutput "[OK] Docker 镜像加速已配置" $Colors.Success
        Write-ColorOutput "[INFO] 如需生效，请在 Docker Desktop 中重启 Docker" $Colors.Warning

    } else {
        Write-ColorOutput "[INFO] 海外地区，使用官方源" $Colors.Info
    }
}

function New-ProjectDirectories {
    Write-ColorOutput "`n=== 创建目录结构 ===" $Colors.Header

    $dirs = @("books", "index", "static", "logs", "cache", "backups", "versions")
    foreach ($dir in $dirs) {
        $path = "$DATA_DIR\$dir"
        if (-not (Test-Path $path)) {
            New-Item -ItemType Directory -Force -Path $path | Out-Null
            Write-ColorOutput "[OK] 创建: data/$dir" $Colors.Success
        }
    }
}

function New-EnvFile {
    $envPath = "$SCRIPT_DIR\.env"

    if (-not (Test-Path $envPath)) {
        Write-ColorOutput "`n=== 创建 .env 配置文件 ===" $Colors.Header

        $chars = @()
        0..9 + 'a'..'f' | ForEach-Object { $chars += [char]$_ }
        $secretKey = -join ($chars | Get-Random -Count 64)

        @"
SECRET_KEY=$secretKey
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://localhost:6379
DATA_DIR=data
BOOKS_DIR=data/books
INDEX_DIR=data/index
STATIC_DIR=data/static
LOGS_DIR=data/logs
CACHE_DIR=data/cache
BCRYPT_ROUNDS=12
PASSWORD_MIN_LENGTH=6
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7
"@ | Out-File -FilePath $envPath -Encoding UTF8

        Write-ColorOutput "[OK] .env 文件已创建" $Colors.Success
    } else {
        Write-ColorOutput "[INFO] .env 文件已存在" $Colors.Info
    }
}

function Install-PythonDependencies {
    Write-ColorOutput "`n=== 安装 Python 依赖 ===" $Colors.Header

    if (-not (Test-PythonInstalled)) {
        Write-ColorOutput "[ERROR] Python 未安装" $Colors.Error
        Write-ColorOutput "[INFO] 请访问 https://www.python.org/downloads/ 下载安装" $Colors.Info
        return $false
    }

    $venvDir = "$BACKEND_DIR\venv"

    if (-not (Test-Path $venvDir)) {
        Write-ColorOutput "[INFO] 创建虚拟环境..." $Colors.Info
        Push-Location $BACKEND_DIR
        python -m venv venv
        Pop-Location
    }

    Write-ColorOutput "[INFO] 激活虚拟环境并安装依赖..." $Colors.Info
    Write-ColorOutput "[INFO] 这可能需要几分钟，请耐心等待..." $Colors.Info

    $pipCmd = "$BACKEND_DIR\venv\Scripts\pip.exe"

    try {
        & $pipCmd install --upgrade pip --quiet
        & $pipCmd install -r $PYTHON_DEPS_FILE

        Write-ColorOutput "[OK] Python 依赖安装完成" $Colors.Success
        return $true
    } catch {
        Write-ColorOutput "[ERROR] Python 依赖安装失败: $_" $Colors.Error
        return $false
    }
}

function Install-NodeDependencies {
    Write-ColorOutput "`n=== 安装 Node.js 依赖 ===" $Colors.Header

    if (-not (Test-NodeInstalled)) {
        Write-ColorOutput "[ERROR] Node.js 未安装" $Colors.Error
        Write-ColorOutput "[INFO] 请访问 https://nodejs.org/ 下载安装 (建议 LTS 版本)" $Colors.Info
        return $false
    }

    Push-Location $FRONTEND_DIR
    try {
        npm install --legacy-peer-deps
        Write-ColorOutput "[OK] Node.js 依赖安装完成" $Colors.Success
        Pop-Location
        return $true
    } catch {
        Write-ColorOutput "[ERROR] Node.js 依赖安装失败: $_" $Colors.Error
        Pop-Location
        return $false
    }
}

function Start-DockerMode {
    Write-ColorOutput "`n=== Docker 模式启动 ===" $Colors.Header

    if (-not (Test-DockerInstalled)) {
        Write-ColorOutput "[ERROR] Docker 未安装，无法使用 Docker 模式" $Colors.Error
        Write-ColorOutput "[INFO] 请访问 https://www.docker.com/products/docker-desktop/ 下载安装" $Colors.Info
        return $false
    }

    Write-ColorOutput "[INFO] 启动 Redis..." $Colors.Info
    docker-compose up -d redis

    Start-Sleep -Seconds 3

    Write-ColorOutput "[INFO] 启动后端..." $Colors.Info
    docker-compose up -d backend

    Write-ColorOutput "[INFO] 启动前端..." $Colors.Info
    docker-compose up -d frontend

    Write-ColorOutput "[OK] Docker 服务启动完成" $Colors.Success
    return $true
}

function Start-LocalMode {
    Write-ColorOutput "`n=== 本地模式启动 ===" $Colors.Header

    $venvActivate = "$BACKEND_DIR\venv\Scripts\Activate.ps1"

    if (-not (Test-Path $venvActivate)) {
        Write-ColorOutput "[ERROR] Python 虚拟环境未配置，请先运行安装步骤" $Colors.Error
        return $false
    }

    Write-ColorOutput "[INFO] 启动后端服务..." $Colors.Info
    $backendLog = "$DATA_DIR\logs\backend.log"
    if (-not (Test-Path $backendLog)) {
        New-Item -ItemType File -Force -Path $backendLog | Out-Null
    }

    Push-Location $BACKEND_DIR
    & .\venv\Scripts\Activate.ps1
    Start-Process -FilePath "uvicorn" -ArgumentList "app.main:app --host 0.0.0.0 --port 8000" -NoNewWindow -RedirectStandardOutput $backendLog -RedirectStandardError "$DATA_DIR\logs\backend_error.log"
    Pop-Location

    Start-Sleep -Seconds 3

    Write-ColorOutput "[INFO] 启动前端服务..." $Colors.Info
    $frontendLog = "$DATA_DIR\logs\frontend.log"
    if (-not (Test-Path $frontendLog)) {
        New-Item -ItemType File -Force -Path $frontendLog | Out-Null
    }

    Push-Location $FRONTEND_DIR
    Start-Process -FilePath "npm" -ArgumentList "run dev" -NoNewWindow -RedirectStandardOutput $frontendLog -RedirectStandardError "$DATA_DIR\logs\frontend_error.log"
    Pop-Location

    Write-ColorOutput "[OK] 本地服务启动完成" $Colors.Success
    return $true
}

function Stop-Services {
    Write-ColorOutput "`n=== 停止服务 ===" $Colors.Header

    if (Test-DockerInstalled) {
        Write-ColorOutput "[INFO] 停止 Docker 容器..." $Colors.Info
        docker-compose down 2>$null
    }

    Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "vite" } | Stop-Process -Force

    Write-ColorOutput "[OK] 服务已停止" $Colors.Success
}

function Main {
    Clear-Host
    Write-ColorOutput @"

╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║           Novel Reader - Windows 部署脚本                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

"@ $Colors.Header

    Write-ColorOutput "[INFO] 检测运行环境..." $Colors.Info

    if (Test-Termux) {
        Write-ColorOutput "[INFO] 检测到 Termux 环境，请使用 Bash 脚本部署" $Colors.Warning
        Write-ColorOutput "[INFO] 运行: bash deploy.sh" $Colors.Info
        return
    }

    if (Test-WSL -and -not $UseWSL) {
        Write-ColorOutput "[INFO] 建议在 WSL 环境中运行 Bash 脚本" $Colors.Warning
        Write-ColorOutput "[INFO] 或运行: bash deploy.sh" $Colors.Info
    }

    Write-ColorOutput "`n=== 检查系统依赖 ===" $Colors.Header
    $pythonOk = Test-PythonInstalled
    $nodeOk = Test-NodeInstalled
    $dockerOk = Test-DockerInstalled

    if (-not $NoInstall) {
        Set-Mirrors
        New-ProjectDirectories
        New-EnvFile

        if ($pythonOk) {
            Install-PythonDependencies
        } else {
            Write-ColorOutput "[WARN] Python 未安装，跳过 Python 依赖安装" $Colors.Warning
        }

        if ($nodeOk) {
            Install-NodeDependencies
        } else {
            Write-ColorOutput "[WARN] Node.js 未安装，跳过前端依赖安装" $Colors.Warning
        fi
    }

    Write-ColorOutput "`n=== 启动服务 ===" $Colors.Header

    if ($dockerOk -and -not $SkipDocker) {
        Start-DockerMode
    } elseif ($pythonOk -and $nodeOk) {
        Start-LocalMode
    } else {
        Write-ColorOutput "[ERROR] 无法启动服务，请安装必要的依赖" $Colors.Error
        return
    }

    Write-ColorOutput "`n=== 检查服务状态 ===" $Colors.Header
    Start-Sleep -Seconds 5

    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-ColorOutput "[OK] 后端服务运行中: http://localhost:8000" $Colors.Success
        }
    } catch {
        Write-ColorOutput "[INFO] 后端服务可能还在启动中" $Colors.Info
    }

    Write-ColorOutput @"

╔══════════════════════════════════════════════════════════════╗
║                    部署完成!                                  ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║   前端页面:  http://localhost                                ║
║   API 文档:  http://localhost:8000/docs                      ║
║                                                              ║
║   常用命令:                                                  ║
║     .\start.ps1 stop     - 停止服务                          ║
║     .\start.ps1 restart - 重启服务                          ║
║     .\start.ps1 logs     - 查看日志                          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

"@ $Colors.Success
}

Main
