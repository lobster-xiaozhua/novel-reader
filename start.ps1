param(
    [string]$Mode = "",
    [string]$Command = ""
)

$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Cyan"
$Cyan = "Cyan"

$PROJECT_NAME = "novel-reader"
$FRONTEND_DIR = "frontend"
$BACKEND_DIR = "backend"
$DATA_DIR = "data"

function Print-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor $Blue }
function Print-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor $Green }
function Print-Warning { param($msg) Write-Host "[WARN] $msg" -ForegroundColor $Yellow }
function Print-Error { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor $Red }
function Print-Header { param($msg)
    Write-Host "========================================" -ForegroundColor $Cyan
    Write-Host "  $msg" -ForegroundColor $Cyan
    Write-Host "========================================" -ForegroundColor $Cyan
}

function Test-Command { param($cmd)
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Print-Error "$cmd 未安装"
        return $false
    }
    return $true
}

function Test-Docker {
    try {
        $null = docker info 2>$null
        return $true
    } catch {
        Print-Error "Docker 未运行，请先启动 Docker Desktop"
        return $false
    }
}

function Test-Python {
    $pythonCmd = $null
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCmd = "python"
    } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3"
    }

    if (-not $pythonCmd) {
        Print-Error "Python 3 未安装，请先安装 Python 3.10+"
        return $false
    }

    $version = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $parts = $version.Split('.')
    $major = [int]$parts[0]
    $minor = [int]$parts[1]

    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
        Print-Error "Python 版本过低 ($version)，需要 3.10+"
        return $false
    }

    Print-Info "Python 版本: $version"
    return $true
}

function New-DataDirectories {
    Print-Info "创建数据目录..."
    @("books", "index", "static", "logs", "cache") | ForEach-Object {
        New-Item -ItemType Directory -Force -Path "$DATA_DIR\$_" | Out-Null
    }
    Print-Success "目录创建完成"
}

function Test-EnvFileDocker {
    if (-not (Test-Path ".env")) {
        Print-Warning ".env 文件不存在，创建 Docker 模式默认配置..."
        $secretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
        @"
SECRET_KEY=$secretKey
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://redis:6379
"@ | Out-File -FilePath ".env" -Encoding UTF8
        Print-Success ".env 文件已创建"
    }
}

function Test-EnvFileLocal {
    if (-not (Test-Path ".env")) {
        Print-Warning ".env 文件不存在，创建本地模式默认配置..."
        $secretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
        @"
SECRET_KEY=$secretKey
DEBUG=true
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://localhost:6379
"@ | Out-File -FilePath ".env" -Encoding UTF8
        Print-Success ".env 文件已创建"
    } else {
        $envContent = Get-Content ".env" -Raw
        if ($envContent -match "redis://redis:6379") {
            Print-Warning "检测到 .env 中 REDIS_URL 为 Docker 内部地址 (redis://redis:6379)"
            Print-Info "本地模式需要使用 redis://localhost:6379"
            $confirm = Read-Host "是否自动修改? (Y/n)"
            if ($confirm -notmatch "^[Nn]$") {
                $envContent = $envContent -replace "redis://redis:6379", "redis://localhost:6379"
                $envContent | Out-File -FilePath ".env" -Encoding UTF8
                Print-Success "REDIS_URL 已修改为本地地址"
            }
        }
    }
}

function Start-BackendDocker {
    Print-Header "启动后端服务 (Docker)"
    if (-not (Test-Docker)) { return }

    Print-Info "启动 Docker 容器..."
    docker-compose up -d redis

    Print-Info "等待 Redis 启动..."
    Start-Sleep -Seconds 3

    $backendRunning = docker-compose ps | Select-String "novel-reader-backend"
    if ($backendRunning) {
        Print-Warning "后端容器已在运行"
    } else {
        Print-Info "启动后端容器..."
        docker-compose up -d backend
    }

    Print-Info "等待后端服务就绪..."
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
    Print-Warning "后端服务启动较慢，请稍后检查"
}

function Start-FrontendDocker {
    Print-Header "启动前端服务 (Docker)"
    if (-not (Test-Docker)) { return }

    if (-not (Test-Path "$FRONTEND_DIR\dist\index.html")) {
        Print-Warning "前端构建文件不存在，开始构建..."
        Build-Frontend
    }

    Print-Info "启动前端容器..."
    docker-compose up -d frontend
    Print-Success "前端服务已启动"
}

function Start-BackendLocal {
    Print-Header "启动后端服务 (本地)"
    if (-not (Test-Python)) { return }

    Push-Location $BACKEND_DIR

    if (-not (Test-Path "venv")) {
        Print-Info "创建 Python 虚拟环境..."
        python -m venv venv
    }

    & .\venv\Scripts\Activate.ps1

    Print-Info "安装 Python 依赖..."
    pip install -q -r requirements.txt

    Print-Info "启动后端服务..."
    $proc = Start-Process -FilePath "uvicorn" -ArgumentList "main:app --host 0.0.0.0 --port 8000 --reload" -PassThru -NoNewWindow
    $proc.Id | Out-File -FilePath "..\.backend.pid" -Encoding UTF8

    Pop-Location

    Print-Info "等待后端服务就绪..."
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                Print-Success "后端服务已就绪 (PID: $($proc.Id))"
                return
            }
        } catch {}
        Start-Sleep -Seconds 1
    }
    Print-Warning "后端服务启动较慢，请稍后检查"
}

function Start-FrontendLocal {
    Print-Header "启动前端服务 (本地)"
    if (-not (Test-Command "node")) {
        Print-Warning "Node.js 未安装，跳过前端启动"
        Print-Info "后端 API 仍可访问: http://localhost:8000/docs"
        return
    }

    Push-Location $FRONTEND_DIR

    if (-not (Test-Path "node_modules")) {
        Print-Info "安装前端依赖..."
        npm install
    }

    Print-Info "启动前端开发服务器..."
    $proc = Start-Process -FilePath "npm" -ArgumentList "run dev" -PassThru
    $proc.Id | Out-File -FilePath "..\.frontend.pid" -Encoding UTF8

    Pop-Location
    Print-Success "前端开发服务已启动 (PID: $($proc.Id))"
}

function Build-Frontend {
    Print-Header "构建前端"
    if (-not (Test-Command "node")) {
        Print-Error "Node.js 未安装，请访问 https://nodejs.org/ 下载"
        return
    }

    Push-Location $FRONTEND_DIR

    if (-not (Test-Path "node_modules")) {
        Print-Info "安装前端依赖..."
        npm install
    }

    Print-Info "构建生产版本..."
    npm run build

    Pop-Location
    Print-Success "前端构建完成"
}

function Stop-ServicesDocker {
    Print-Header "停止服务 (Docker)"
    if (-not (Test-Docker)) { return }
    Print-Info "停止所有容器..."
    docker-compose down
    Print-Success "所有服务已停止"
}

function Stop-ServicesLocal {
    Print-Header "停止服务 (本地)"

    if (Test-Path ".backend.pid") {
        $pid = Get-Content ".backend.pid"
        try {
            $proc = Get-Process -Id $pid -ErrorAction Stop
            Stop-Process -Id $pid -Force
            Print-Success "后端服务已停止 (PID: $pid)"
        } catch {
            Print-Warning "后端进程已不存在 (PID: $pid)"
        }
        Remove-Item ".backend.pid" -Force -ErrorAction SilentlyContinue
    } else {
        $proc = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess
        if ($proc) {
            Stop-Process -Id $proc -Force
            Print-Success "后端服务已停止 (PID: $proc)"
        } else {
            Print-Info "后端服务未在运行"
        }
    }

    if (Test-Path ".frontend.pid") {
        $pid = Get-Content ".frontend.pid"
        try {
            $proc = Get-Process -Id $pid -ErrorAction Stop
            Stop-Process -Id $pid -Force
            Print-Success "前端服务已停止 (PID: $pid)"
        } catch {
            Print-Warning "前端进程已不存在 (PID: $pid)"
        }
        Remove-Item ".frontend.pid" -Force -ErrorAction SilentlyContinue
    } else {
        $proc = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess
        if ($proc) {
            Stop-Process -Id $proc -Force
            Print-Success "前端服务已停止 (PID: $proc)"
        } else {
            Print-Info "前端服务未在运行"
        }
    }
}

function Show-StatusDocker {
    Print-Header "服务状态 (Docker)"
    if (-not (Test-Docker)) { return }

    Write-Host "容器状态:" -ForegroundColor $Cyan
    docker-compose ps

    Write-Host "`n健康检查:" -ForegroundColor $Cyan
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

function Show-StatusLocal {
    Print-Header "服务状态 (本地)"

    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Print-Success "后端 API: 运行中 (http://localhost:8000)"
        }
    } catch {
        Print-Error "后端 API: 未响应"
    }

    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -TimeoutSec 2
        Print-Success "前端页面: 运行中 (http://localhost:5173)"
    } catch {
        Print-Warning "前端页面: 未响应"
    }
}

function Show-LogsDocker {
    Print-Header "查看日志 (Docker)"
    if (-not (Test-Docker)) { return }
    Write-Host "按 Ctrl+C 退出日志查看" -ForegroundColor $Cyan
    docker-compose logs -f
}

function Show-LogsLocal {
    Print-Header "查看日志 (本地)"
    $logDir = "$DATA_DIR\logs"
    if ((Test-Path $logDir) -and (Get-ChildItem $logDir -File -ErrorAction SilentlyContinue)) {
        Print-Info "日志目录: $logDir"
        Get-ChildItem $logDir | Format-Table Name, Length, LastWriteTime
        $latestLog = Get-ChildItem "$logDir\*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latestLog) {
            Print-Info "最新日志: $($latestLog.FullName)"
            Get-Content $latestLog.FullName -Tail 50 -Wait
        }
    } else {
        Print-Info "暂无日志文件"
    }
}

function Clear-Data {
    Print-Header "清理数据"
    Print-Warning "此操作将删除所有数据！"
    $confirm = Read-Host "确认继续? (y/N)"

    if ($confirm -match "^[Yy]$") {
        if ($Mode -eq "local") {
            Stop-ServicesLocal
        } else {
            Stop-ServicesDocker
        }
        Print-Info "删除数据目录..."
        Remove-Item -Recurse -Force $DATA_DIR -ErrorAction SilentlyContinue
        New-DataDirectories
        Print-Success "数据已清理"

        $restart = Read-Host "是否重新启动服务? (Y/n)"
        if ($restart -notmatch "^[Nn]$") {
            if ($Mode -eq "local") {
                Start-AllLocal
            } else {
                Start-AllDocker
            }
        }
    } else {
        Print-Info "操作已取消"
    }
}

function Run-Tests {
    Print-Header "运行测试"
    Push-Location $BACKEND_DIR

    if (-not (Test-Path "venv")) {
        Print-Info "创建虚拟环境..."
        python -m venv venv
    }

    & .\venv\Scripts\Activate.ps1

    Print-Info "安装测试依赖..."
    pip install -q pytest pytest-asyncio httpx

    Print-Info "运行测试..."
    pytest tests/ -v --tb=short

    deactivate
    Pop-Location
}

function Start-AllDocker {
    Print-Header "启动 Novel Reader (Docker 模式)"

    Test-Command "docker"
    Test-Command "docker-compose"
    Test-Command "node"

    New-DataDirectories
    Test-EnvFileDocker

    Start-BackendDocker
    Start-FrontendDocker

    Print-Header "服务已启动 (Docker 模式)"
    Write-Host "📖 前端页面: http://localhost" -ForegroundColor $Green
    Write-Host "🔧 API 文档: http://localhost:8000/docs" -ForegroundColor $Green
    Write-Host "💓 健康检查: http://localhost:8000/api/health" -ForegroundColor $Green
    Write-Host ""
    Write-Host "常用命令:" -ForegroundColor $Yellow
    Write-Host "  .\start.ps1 docker stop     - 停止服务"
    Write-Host "  .\start.ps1 docker restart  - 重启服务"
    Write-Host "  .\start.ps1 docker logs     - 查看日志"
    Write-Host "  .\start.ps1 docker status   - 查看状态"
}

function Start-AllLocal {
    Print-Header "启动 Novel Reader (本地模式)"

    Test-Python
    Test-Command "node"

    New-DataDirectories
    Test-EnvFileLocal

    Print-Info "提示: Redis 非必需，未安装时自动降级为无缓存模式"

    Start-BackendLocal
    Start-FrontendLocal

    Print-Header "服务已启动 (本地模式)"
    Write-Host "📖 前端页面: http://localhost:5173" -ForegroundColor $Green
    Write-Host "🔧 API 文档: http://localhost:8000/docs" -ForegroundColor $Green
    Write-Host "💓 健康检查: http://localhost:8000/api/health" -ForegroundColor $Green
    Write-Host ""
    Write-Host "常用命令:" -ForegroundColor $Yellow
    Write-Host "  .\start.ps1 local stop     - 停止服务"
    Write-Host "  .\start.ps1 local status   - 查看状态"
    Write-Host "  .\start.ps1 local logs     - 查看日志"
    Write-Host ""
    Write-Host "提示:" -ForegroundColor $Yellow
    Write-Host "  本地模式后端使用 --reload，修改代码自动重启"
    Write-Host "  前端使用 Vite 开发服务器，支持热更新"
}

function Show-Help {
    @"
Novel Reader 启动脚本 (Windows)

用法: .\start.ps1 <模式> [命令]

模式:
  docker    Docker 模式 (需要 Docker Desktop)
  local     本地模式 (直接运行 Python + Node.js)

命令:
  (无)      启动所有服务
  stop      停止所有服务
  restart   重启所有服务
  build     重新构建并启动
  logs      查看服务日志
  status    查看服务状态
  clean     清理所有数据并重新启动
  test      运行后端测试
  help      显示此帮助信息

示例:
  .\start.ps1 docker          # Docker 模式启动
  .\start.ps1 docker stop     # Docker 模式停止
  .\start.ps1 local           # 本地模式启动
  .\start.ps1 local stop      # 本地模式停止
  .\start.ps1 local status    # 本地模式查看状态

Docker 模式访问地址:
  前端: http://localhost
  API:  http://localhost:8000
  文档: http://localhost:8000/docs

本地模式访问地址:
  前端: http://localhost:5173
  API:  http://localhost:8000
  文档: http://localhost:8000/docs
"@
}

if ($Mode -eq "" -and $Command -eq "") {
    $Mode = "docker"
    $Command = ""
} elseif ($Mode -in @("docker", "local")) {
    # Mode already set, Command is optional second param
} elseif ($Mode -in @("stop", "restart", "build", "logs", "status", "clean", "test", "help")) {
    $Command = $Mode
    $Mode = "docker"
}

switch ("$Mode|$Command") {
    "docker|"       { Start-AllDocker }
    "docker|stop"   { Stop-ServicesDocker }
    "docker|restart" { Stop-ServicesDocker; Start-Sleep -Seconds 2; Start-AllDocker }
    "docker|build"  { Stop-ServicesDocker; Build-Frontend; Start-AllDocker }
    "docker|logs"   { Show-LogsDocker }
    "docker|status" { Show-StatusDocker }
    "docker|clean"  { Clear-Data }
    "docker|test"   { Run-Tests }
    "local|"        { Start-AllLocal }
    "local|stop"    { Stop-ServicesLocal }
    "local|restart" { Stop-ServicesLocal; Start-Sleep -Seconds 2; Start-AllLocal }
    "local|build"   { Stop-ServicesLocal; Start-AllLocal }
    "local|logs"    { Show-LogsLocal }
    "local|status"  { Show-StatusLocal }
    "local|clean"   { Clear-Data }
    "local|test"    { Run-Tests }
    default {
        if ($Command -eq "help" -or $Mode -eq "help") {
            Show-Help
        } else {
            Print-Error "未知命令: $Mode $Command"
            Show-Help
            exit 1
        }
    }
}
