# deploy-windows.ps1 - Windows 部署脚本
# 用于 Windows 10/11 (PowerShell)
# 用法: .\deploy-windows.ps1 [命令]
#
# 命令:
#   install    安装所有依赖
#   start      启动服务
#   stop       停止服务
#   restart    重启服务
#   status     查看状态
#   update     更新项目
#   docker     使用 Docker Desktop 部署
#   wsl        使用 WSL2 部署
#   help       显示帮助

param(
    [string]$Command = ""
)

$PROJECT_NAME = "novel-reader"
$PROJECT_DIR = $PSScriptRoot
$BACKEND_DIR = Join-Path $PROJECT_DIR "backend"
$FRONTEND_DIR = Join-Path $PROJECT_DIR "frontend"
$DATA_DIR = Join-Path $PROJECT_DIR "data"

$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Cyan"
$Cyan = "Cyan"

function log_info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor $Blue }
function log_success { param($msg) Write-Host "[OK] $msg" -ForegroundColor $Green }
function log_warning { param($msg) Write-Host "[WARN] $msg" -ForegroundColor $Yellow }
function log_error { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor $Red }
function log_step { param($msg) Write-Host "[->] $msg" -ForegroundColor $Cyan }

function print_banner {
    Write-Host ""
    Write-Host "========================================================" -ForegroundColor Magenta
    Write-Host "  Novel Reader - Windows 部署脚本" -ForegroundColor Cyan
    Write-Host "  支持 Windows 10/11 / PowerShell / Docker Desktop" -ForegroundColor Cyan
    Write-Host "========================================================" -ForegroundColor Magenta
    Write-Host ""
}

function test_command { param($cmd)
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        log_error "$cmd 未安装"
        return $false
    }
    return $true
}

function test_docker {
    try {
        $null = docker info 2>$null
        return $true
    } catch {
        return $false
    }
}

function test_wsl {
    try {
        $wsl = wsl --status 2>$null
        return $?
    } catch {
        return $false
    }
}

function get_region {
    try {
        $response = Invoke-WebRequest -Uri "https://ipinfo.io/country" -UseBasicParsing -TimeoutSec 3
        if ($response.Content -eq "CN") {
            return "china"
        }
    } catch {}
    return "global"
}

function set_pip_mirror {
    log_step "配置 pip 镜像..."

    $region = get_region

    $pipDir = "$env:APPDATA\pip"
    if (-not (Test-Path $pipDir)) {
        New-Item -ItemType Directory -Force -Path $pipDir | Out-Null
    }

    if ($region -eq "china") {
        @"
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 60
[install]
trusted-host = mirrors.aliyun.com
"@ | Out-File -FilePath "$pipDir\pip.ini" -Encoding UTF8
        log_success "pip 镜像: 阿里云"
    } else {
        log_info "使用官方 pip 源"
    }
}

function set_npm_mirror {
    $region = get_region
    if ($region -eq "china") {
        npm config set registry https://registry.npmmirror.com
        log_success "npm 镜像: npmmirror.com"
    }
}

function install_python_deps {
    log_step "安装 Python 依赖..."

    if (-not (test_command "python")) {
        return
    }

    Set-Location $BACKEND_DIR

    if (-not (Test-Path "venv")) {
        log_info "创建虚拟环境..."
        python -m venv venv
    }

    & .\venv\Scripts\Activate.ps1

    pip install --upgrade pip -q
    pip install -r requirements.txt -q

    deactivate
    Set-Location $PROJECT_DIR

    log_success "Python 依赖安装完成"
}

function install_nodejs_deps {
    log_step "安装 Node.js 依赖..."

    if (-not (test_command "node")) {
        return
    }

    Set-Location $FRONTEND_DIR
    set_npm_mirror
    npm install
    Set-Location $PROJECT_DIR

    log_success "Node.js 依赖安装完成"
}

function create_directories {
    log_step "创建目录结构..."
    $dirs = @("books", "index", "static", "logs", "cache", "backups", "versions")
    foreach ($dir in $dirs) {
        $path = Join-Path $DATA_DIR $dir
        if (-not (Test-Path $path)) {
            New-Item -ItemType Directory -Force -Path $path | Out-Null
        }
    }
    log_success "目录创建完成"
}

function setup_env {
    $envFile = Join-Path $PROJECT_DIR ".env"
    if (-not (Test-Path $envFile)) {
        log_info "创建环境配置文件..."
        $secretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object { [char]$_ })

        @"
SECRET_KEY=$secretKey
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///$DATA_DIR/novel.db
REDIS_URL=redis://localhost:6379
DATA_DIR=$DATA_DIR
BOOKS_DIR=$DATA_DIR\books
INDEX_DIR=$DATA_DIR\index
STATIC_DIR=$DATA_DIR\static
LOGS_DIR=$DATA_DIR\logs
CACHE_DIR=$DATA_DIR\cache
"@ | Out-File -FilePath $envFile -Encoding UTF8

        log_success ".env 文件已创建"
    } else {
        log_info ".env 文件已存在"
    }
}

function start_redis {
    log_step "启动 Redis..."

    if (test_command "redis-server") {
        if (-not (Get-Process redis-server -ErrorAction SilentlyContinue)) {
            $redisDir = Join-Path $DATA_DIR "redis"
            if (-not (Test-Path $redisDir)) {
                New-Item -ItemType Directory -Force -Path $redisDir | Out-Null
            }
            Start-Process -FilePath "redis-server" -ArgumentList "--daemonize yes --dir $redisDir --port 6379" -WindowStyle Hidden
            Start-Sleep -Seconds 2
        }
        if (Get-Process redis-server -ErrorAction SilentlyContinue) {
            log_success "Redis 已启动"
        } else {
            log_warning "Redis 启动失败，继续..."
        }
    } else {
        log_warning "Redis 未安装"
    }
}

function stop_redis {
    $redisProc = Get-Process redis-server -ErrorAction SilentlyContinue
    if ($redisProc) {
        Stop-Process -Name redis-server -Force -ErrorAction SilentlyContinue
        log_info "Redis 已停止"
    }
}

function start_backend {
    log_step "启动后端服务..."

    Set-Location $BACKEND_DIR

    if (-not (Test-Path "venv")) {
        install_python_deps
    }

    & .\venv\Scripts\Activate.ps1

    $pidFile = "uvicorn.pid"
    $logFile = Join-Path $DATA_DIR "logs\backend.log"

    if ((Test-Path $pidFile) -and (Get-Content $pidFile -ErrorAction SilentlyContinue | ForEach-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue })) {
        log_info "后端已在运行"
    } else {
        $env:PYTHONPATH = "$PROJECT_DIR\backend"
        $env:PYTHONDONTWRITEBYTECODE = "1"

        Start-Process -FilePath "python" -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000" -NoNewWindow -RedirectStandardOutput $logFile -WindowStyle Hidden
        Start-Sleep -Seconds 2

        log_success "后端已启动"
    }

    deactivate
    Set-Location $PROJECT_DIR
}

function stop_backend {
    $pidFile = Join-Path $BACKEND_DIR "uvicorn.pid"
    if (Test-Path $pidFile) {
        $pids = Get-Content $pidFile -ErrorAction SilentlyContinue
        foreach ($pid in $pids) {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        log_info "后端已停止"
    }

    Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*uvicorn*" } | Stop-Process -Force -ErrorAction SilentlyContinue
}

function start_frontend {
    log_step "启动前端服务..."

    Set-Location $FRONTEND_DIR

    if (-not (Test-Path "node_modules")) {
        install_nodejs_deps
    }

    $pidFile = "vite.pid"
    $logFile = Join-Path $DATA_DIR "logs\frontend.log"

    if ((Test-Path $pidFile) -and (Get-Content $pidFile -ErrorAction SilentlyContinue | ForEach-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue })) {
        log_info "前端已在运行"
    } else {
        if (-not (Test-Path "dist\index.html")) {
            log_info "构建前端..."
            npm run build
        }
        Start-Process -FilePath "npm" -ArgumentList "run dev" -NoNewWindow -RedirectStandardOutput $logFile -WindowStyle Hidden
        Start-Sleep -Seconds 2
        log_success "前端已启动"
    }

    Set-Location $PROJECT_DIR
}

function stop_frontend {
    $pidFile = Join-Path $FRONTEND_DIR "vite.pid"
    if (Test-Path $pidFile) {
        $pids = Get-Content $pidFile -ErrorAction SilentlyContinue
        foreach ($pid in $pids) {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        log_info "前端已停止"
    }

    Get-Process node -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*vite*" } | Stop-Process -Force -ErrorAction SilentlyContinue
}

function cmd_install {
    print_banner
    log_step "开始安装..."

    create_directories
    setup_env
    set_pip_mirror
    install_python_deps
    install_nodejs_deps

    echo ""
    echo "========================================================" -ForegroundColor Green
    echo "  安装完成!" -ForegroundColor Green
    echo "========================================================" -ForegroundColor Green
    echo ""
    echo "下一步:" -ForegroundColor Yellow
    echo "  .\deploy-windows.ps1 start   # 启动服务"
    echo "  .\deploy-windows.ps1 status  # 查看状态"
    echo ""
}

function cmd_start {
    print_banner
    log_step "启动 Novel Reader..."

    create_directories
    setup_env
    start_redis
    start_backend
    start_frontend

    log_info "等待服务就绪..."
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                log_success "后端服务已就绪"
                break
            }
        } catch {}
        Start-Sleep -Seconds 1
    }

    echo ""
    echo "========================================================" -ForegroundColor Green
    echo "  服务已启动!" -ForegroundColor Green
    echo "========================================================" -ForegroundColor Green
    echo ""
    echo "  前端页面: http://localhost:5173" -ForegroundColor Green
    echo "  API 文档:  http://localhost:8000/docs" -ForegroundColor Green
    echo "  健康检查:  http://localhost:8000/api/health" -ForegroundColor Green
    echo ""
}

function cmd_stop {
    log_step "停止服务..."
    stop_backend
    stop_frontend
    stop_redis
    log_success "所有服务已停止"
}

function cmd_restart {
    cmd_stop
    Start-Sleep -Seconds 2
    cmd_start
}

function cmd_status {
    log_step "服务状态"
    Write-Host ""

    $backendRunning = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*uvicorn*" }
    if ($backendRunning) {
        log_success "后端服务: 运行中"
    } else {
        log_error "后端服务: 未运行"
    }

    $frontendRunning = Get-Process node -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*vite*" }
    if ($frontendRunning) {
        log_success "前端服务: 运行中"
    } else {
        log_error "前端服务: 未运行"
    }

    $redisRunning = Get-Process redis-server -ErrorAction SilentlyContinue
    if ($redisRunning) {
        log_success "Redis: 运行中"
    } else {
        log_warning "Redis: 未运行"
    }

    Write-Host ""
    log_info "健康检查:"
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            log_success "后端 API: 运行中"
        }
    } catch {
        log_error "后端 API: 未响应"
    }
}

function cmd_docker {
    print_banner
    log_step "使用 Docker Desktop 部署..."

    if (-not (test_docker)) {
        log_error "Docker Desktop 未运行，请先启动"
        return
    }

    log_step "配置 Docker 镜像..."
    set_pip_mirror

    log_step "启动 Docker 服务..."
    docker-compose up -d redis
    Start-Sleep -Seconds 3
    docker-compose up -d backend frontend

    log_info "等待服务就绪..."
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                log_success "后端服务已就绪"
                break
            }
        } catch {}
        Start-Sleep -Seconds 1
    }

    echo ""
    echo "========================================================" -ForegroundColor Green
    echo "  Docker 服务已启动!" -ForegroundColor Green
    echo "========================================================" -ForegroundColor Green
    echo ""
    echo "  前端页面: http://localhost" -ForegroundColor Green
    echo "  API 文档:  http://localhost:8000/docs" -ForegroundColor Green
    echo ""
}

function cmd_wsl {
    print_banner
    log_step "使用 WSL2 部署..."

    if (-not (test_wsl)) {
        log_error "WSL2 未安装"
        log_info "请运行: wsl --install"
        return
    }

    log_info "在 WSL2 中运行 Linux 部署脚本..."
    wsl bash -c "cd /mnt/$($PROJECT_DIR -replace ':','' -replace '\\','/') && bash deploy-linux.sh install"

    echo ""
    echo "========================================================" -ForegroundColor Green
    echo "  WSL2 部署完成!" -ForegroundColor Green
    echo "========================================================" -ForegroundColor Green
    echo ""
    echo "  在 WSL2 终端中运行:" -ForegroundColor Yellow
    echo "    bash deploy-linux.sh start  # 启动服务"
    echo ""
}

function show_help {
    print_banner
    @"
用法: .\deploy-windows.ps1 <command>

命令:
  \${GREEN}install\${NC}    安装所有依赖（首次运行）
  \${GREEN}start\${NC}       本地模式启动服务
  \${GREEN}stop\${NC}        停止服务
  \${GREEN}restart\${NC}     重启服务
  \${GREEN}status\${NC}      查看服务状态
  \${GREEN}docker\${NC}      使用 Docker Desktop 部署
  \${GREEN}wsl\${NC}         使用 WSL2 部署
  \${GREEN}update\${NC}      更新项目
  \${GREEN}help\${NC}        显示帮助

部署方式:
  1. 本地模式 (默认): 直接使用本地 Python/Node.js
  2. Docker Desktop:  使用 Docker 容器
  3. WSL2:            使用 Linux 子系统

环境要求:
  - Windows 10/11
  - Python 3.11+
  - Node.js 18+
  - Redis 6.0+ (可选)

更多信息: https://github.com/lobster-xiaozhua/novel-reader
"@
}

$main = {
    switch ($Command) {
        "install" { cmd_install }
        "start" { cmd_start }
        "stop" { cmd_stop }
        "restart" { cmd_restart }
        "status" { cmd_status }
        "docker" { cmd_docker }
        "wsl" { cmd_wsl }
        "update" {
            log_step "更新项目..."
            if (Test-Path ".git") {
                git pull origin main
                install_python_deps
                cmd_restart
            } else {
                log_error "不是 git 仓库"
            }
        }
        "help" { show_help }
        "" { cmd_install }
        default {
            log_error "未知命令: $Command"
            show_help
            exit 1
        }
    }
}

& $main