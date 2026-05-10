# Novel Reader 一键启动脚本 (Windows PowerShell)
# 用法: .\start.ps1 [command]
#   .\start.ps1          - 启动所有服务
#   .\start.ps1 stop     - 停止所有服务
#   .\start.ps1 restart  - 重启所有服务
#   .\start.ps1 build    - 重新构建前端并启动
#   .\start.ps1 logs     - 查看日志
#   .\start.ps1 status   - 查看服务状态
#   .\start.ps1 clean    - 清理数据并重新启动
#   .\start.ps1 test     - 运行测试

param(
    [string]$Command = ""
)

# 颜色定义
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Cyan"
$Cyan = "Cyan"

# 项目配置
$PROJECT_NAME = "novel-reader"
$FRONTEND_DIR = "frontend"
$BACKEND_DIR = "backend"
$DATA_DIR = "data"

# 打印函数
function Print-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor $Blue }
function Print-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor $Green }
function Print-Warning { param($msg) Write-Host "[WARN] $msg" -ForegroundColor $Yellow }
function Print-Error { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor $Red }
function Print-Header { param($msg)
    Write-Host "========================================" -ForegroundColor $Cyan
    Write-Host "  $msg" -ForegroundColor $Cyan
    Write-Host "========================================" -ForegroundColor $Cyan
}

# 检查命令
function Test-Command { param($cmd)
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Print-Error "$cmd 未安装"
        return $false
    }
    return $true
}

# 检查 Docker
function Test-Docker {
    try {
        $null = docker info 2>$null
        return $true
    } catch {
        Print-Error "Docker 未运行，请先启动 Docker Desktop"
        return $false
    }
}

# 创建目录
function New-DataDirectories {
    Print-Info "创建数据目录..."
    @("books", "index", "static", "logs", "cache") | ForEach-Object {
        New-Item -ItemType Directory -Force -Path "$DATA_DIR\$_" | Out-Null
    }
    Print-Success "目录创建完成"
}

# 检查环境文件
function Test-EnvFile {
    if (-not (Test-Path ".env")) {
        Print-Warning ".env 文件不存在，创建默认配置..."
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

# 启动后端
function Start-Backend {
    Print-Header "启动后端服务"
    
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

# 构建前端
function Build-Frontend {
    Print-Header "构建前端"
    
    if (-not (Test-Command "node")) {
        Print-Error "Node.js 未安装，请访问 https://nodejs.org/ 下载"
        return
    }
    
    Set-Location $FRONTEND_DIR
    
    if (-not (Test-Path "node_modules")) {
        Print-Info "安装前端依赖..."
        npm install
    }
    
    Print-Info "构建生产版本..."
    npm run build
    
    Set-Location ..
    Print-Success "前端构建完成"
}

# 启动前端
function Start-Frontend {
    Print-Header "启动前端服务"
    
    if (-not (Test-Docker)) { return }
    
    if (-not (Test-Path "$FRONTEND_DIR\dist\index.html")) {
        Print-Warning "前端构建文件不存在，开始构建..."
        Build-Frontend
    }
    
    Print-Info "启动前端容器..."
    docker-compose up -d frontend
    Print-Success "前端服务已启动"
}

# 停止服务
function Stop-Services {
    Print-Header "停止服务"
    if (-not (Test-Docker)) { return }
    Print-Info "停止所有容器..."
    docker-compose down
    Print-Success "所有服务已停止"
}

# 查看状态
function Show-Status {
    Print-Header "服务状态"
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

# 查看日志
function Show-Logs {
    Print-Header "查看日志"
    if (-not (Test-Docker)) { return }
    Write-Host "按 Ctrl+C 退出日志查看" -ForegroundColor $Cyan
    docker-compose logs -f
}

# 清理数据
function Clear-Data {
    Print-Header "清理数据"
    Print-Warning "此操作将删除所有数据！"
    $confirm = Read-Host "确认继续? (y/N)"
    
    if ($confirm -match "^[Yy]$") {
        Stop-Services
        Print-Info "删除数据目录..."
        Remove-Item -Recurse -Force $DATA_DIR -ErrorAction SilentlyContinue
        New-DataDirectories
        Print-Success "数据已清理"
        
        $restart = Read-Host "是否重新启动服务? (Y/n)"
        if ($restart -notmatch "^[Nn]$") {
            Start-All
        }
    } else {
        Print-Info "操作已取消"
    }
}

# 运行测试
function Run-Tests {
    Print-Header "运行测试"
    Set-Location $BACKEND_DIR
    
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
    Set-Location ..
}

# 启动所有服务
function Start-All {
    Print-Header "启动 Novel Reader"
    
    Test-Command "docker"
    Test-Command "docker-compose"
    Test-Command "node"
    
    New-DataDirectories
    Test-EnvFile
    
    Start-Backend
    Start-Frontend
    
    Print-Header "服务已启动"
    Write-Host "📖 前端页面: http://localhost" -ForegroundColor $Green
    Write-Host "🔧 API 文档: http://localhost:8000/docs" -ForegroundColor $Green
    Write-Host "💓 健康检查: http://localhost:8000/api/health" -ForegroundColor $Green
    Write-Host ""
    Write-Host "常用命令:" -ForegroundColor $Yellow
    Write-Host "  .\start.ps1 stop     - 停止服务"
    Write-Host "  .\start.ps1 restart  - 重启服务"
    Write-Host "  .\start.ps1 logs     - 查看日志"
    Write-Host "  .\start.ps1 status   - 查看状态"
}

# 重启服务
function Restart-Services {
    Print-Header "重启服务"
    Stop-Services
    Start-Sleep -Seconds 2
    Start-All
}

# 重新构建
function Rebuild-All {
    Print-Header "重新构建并启动"
    Stop-Services
    Build-Frontend
    Start-All
}

# 显示帮助
function Show-Help {
    @"
Novel Reader 一键启动脚本 (Windows)

用法: .\start.ps1 [command]

命令:
  (无)      启动所有服务
  stop      停止所有服务
  restart   重启所有服务
  build     重新构建前端并启动
  logs      查看服务日志
  status    查看服务状态
  clean     清理所有数据并重新启动
  test      运行后端测试
  help      显示此帮助信息

示例:
  .\start.ps1          # 首次启动
  .\start.ps1 stop     # 停止服务
  .\start.ps1 restart  # 重启服务
  .\start.ps1 logs     # 查看日志

访问地址:
  前端: http://localhost
  API:  http://localhost:8000
  文档: http://localhost:8000/docs
"@
}

# 主逻辑
switch ($Command) {
    "stop" { Stop-Services }
    "restart" { Restart-Services }
    "build" { Rebuild-All }
    "logs" { Show-Logs }
    "status" { Show-Status }
    "clean" { Clear-Data }
    "test" { Run-Tests }
    "help" { Show-Help }
    "" { Start-All }
    default {
        Print-Error "未知命令: $Command"
        Show-Help
        exit 1
    }
}
