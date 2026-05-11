# Novel Reader Windows 一键启动脚本
# 用法: .\start.ps1
# 什么都不用管，一键启动，自动更新，自动处理所有问题

param(
    [switch]$SkipUpdate,
    [switch]$Force,
    [switch]$Debug
)

$ErrorActionPreference = "Continue"
if ($Debug) { $ErrorActionPreference = "Continue" }

$Script:ProjectRoot = $PSScriptRoot
$Script:BackendDir = Join-Path $Script:ProjectRoot "backend"
$Script:FrontendDir = Join-Path $Script:ProjectRoot "frontend"
$Script:DataDir = Join-Path $Script:ProjectRoot "data"
$Script:VenvDir = Join-Path $Script:BackendDir "venv"
$Script:PidsDir = Join-Path $Script:ProjectRoot ".pids"

$Red = "Red"; $Green = "Green"; $Yellow = "Yellow"; $Blue = "Cyan"; $Cyan = "Cyan"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor $Blue }
function Write-Success($msg) { Write-Host "[OK] $msg" -ForegroundColor $Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor $Yellow }
function Write-Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor $Red }
function Write-Step($msg) {
    Write-Host ""
    Write-Host "═══ $msg ═══" -ForegroundColor $Cyan
}

function Get-Region {
    try {
        $r = Invoke-WebRequest -Uri "https://ipinfo.io/country" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($r.Content -eq "CN") { return "china" }
    } catch {}
    return "global"
}

function Test-Admin {
    return ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Set-ExecutionPolicy-Bypass {
    $current = Get-ExecutionPolicy -Scope CurrentUser
    if ($current -eq "Restricted" -or $current -eq "Undefined") {
        Write-Info "设置 PowerShell 执行策略..."
        Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force -ErrorAction SilentlyContinue
    }
}

function Initialize-Directories {
    $dirs = @("books", "index", "static", "logs", "cache", "backups")
    foreach ($dir in $dirs) {
        $path = Join-Path $DataDir $dir
        if (-not (Test-Path $path)) {
            New-Item -ItemType Directory -Force -Path $path | Out-Null
        }
    }
    if (-not (Test-Path $Script:PidsDir)) {
        New-Item -ItemType Directory -Force -Path $Script:PidsDir | Out-Null
    }
}

function Initialize-EnvFile {
    $envPath = Join-Path $Script:ProjectRoot ".env"
    if (-not (Test-Path $envPath)) {
        Write-Info "创建配置文件..."
        $key = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
        $content = @"
SECRET_KEY=$key
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://127.0.0.1:6379
DATA_DIR=./data
BOOKS_DIR=./data/books
INDEX_DIR=./data/index
STATIC_DIR=./data/static
LOGS_DIR=./data/logs
CACHE_DIR=./data/cache
"@
        $content | Out-File -FilePath $envPath -Encoding UTF8
        Write-Success "配置文件已创建"
    }
}

function Set-Mirrors {
    $region = Get-Region
    if ($region -eq "china") {
        Write-Info "检测到中国，配置国内镜像..."
        
        $pipDir = "$env:APPDATA\pip"
        if (-not (Test-Path $pipDir)) { New-Item -ItemType Directory -Force -Path $pipDir | Out-Null }
        @"
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 120
[install]
trusted-host = mirrors.aliyun.com
"@ | Out-File -Path "$pipDir\pip.ini" -Encoding UTF8
        
        npm config set registry https://registry.npmmirror.com --location user 2>$null
        Write-Success "镜像源已配置 (阿里云/腾讯)"
    }
}

function Test-Command($cmd) {
    return !!(Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Install-Python {
    if (Test-Command "python") {
        $ver = python --version 2>&1
        Write-Info "Python: $ver"
        return $true
    }
    
    Write-Step "安装 Python"
    
    if (Test-Command "py") {
        Write-Info "使用 py launcher 安装..."
        py -3.11 -m pip --version 2>$null
        if ($?) {
            Write-Success "使用 py launcher"
            return $true
        }
    }
    
    Write-Warn "Python 未安装"
    Write-Info "请选择安装方式:"
    Write-Host "  1. Microsoft Store (推荐, 自动)" -ForegroundColor Yellow
    Write-Host "  2. python.org 下载安装包" -ForegroundColor Yellow
    Write-Host ""
    
    try {
        Write-Host "正在打开 Microsoft Store..." -ForegroundColor Cyan
        Start-Process "ms-windows-store://search/python"
        Start-Sleep 2
    } catch {}
    
    Write-Host ""
    Write-Host "安装 Python 后，请重新运行此脚本" -ForegroundColor Yellow
    return $false
}

function Install-Nodejs {
    if (Test-Command "node") {
        $ver = node --version
        Write-Info "Node.js: v$ver"
        return $true
    }
    
    Write-Step "安装 Node.js"
    Write-Warn "Node.js 未安装"
    Write-Host "请访问 https://nodejs.org 下载安装 LTS 版本" -ForegroundColor Cyan
    
    try {
        Start-Process "https://nodejs.org"
    } catch {}
    
    return $false
}

function Install-RedisOrSkip {
    if (Test-Command "redis-server") {
        return "native"
    }
    
    if (Test-Command "memurai") {
        return "memurai"
    }
    
    Write-Warn "Redis 未安装，将禁用缓存功能"
    return "none"
}

function Install-PythonDeps {
    Set-Step "安装 Python 依赖"
    
    Set-Mirrors
    
    if (-not (Test-Path $Script:VenvDir)) {
        Write-Info "创建虚拟环境..."
        python -m venv venv
        if (-not $?) {
            Write-Err "虚拟环境创建失败"
            return $false
        }
    }
    
    $pip = Join-Path $Script:VenvDir "Scripts\pip.exe"
    if (-not (Test-Path $pip)) {
        Write-Err "虚拟环境损坏，重新创建..."
        Remove-Item -Recurse -Force $Script:VenvDir -ErrorAction SilentlyContinue
        python -m venv venv
        $pip = Join-Path $Script:VenvDir "Scripts\pip.exe"
    }
    
    Write-Info "升级 pip..."
    & $pip install --upgrade pip --quiet 2>$null
    
    Write-Info "安装项目依赖..."
    $deps = @(
        "fastapi==0.110.0",
        "uvicorn[standard]==0.27.1",
        "sqlalchemy==2.0.27",
        "aiosqlite==0.19.0",
        "redis==5.0.1",
        "pydantic==2.6.1",
        "pydantic-settings==2.1.0",
        "python-multipart==0.0.9",
        "beautifulsoup4==4.12.3",
        "tenacity==8.2.3",
        "rich==13.7.0",
        "python-jose[cryptography]==3.3.0",
        "pycryptodome==3.20.0",
        "passlib==1.7.4",
        "bcrypt==4.1.2",
        "aiohttp==3.9.3",
        "httpx==0.27.0"
    )
    
    $depsStr = $deps -join " "
    Write-Info "安装核心依赖 (这可能需要几分钟)..."
    
    & $pip install $depsStr --quiet 2>&1 | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "部分依赖安装失败，尝试逐个安装..."
        foreach ($dep in $deps) {
            & $pip install $dep --quiet 2>$null
        }
    }
    
    Write-Success "Python 依赖安装完成"
    return $true
}

function Install-NodeDeps {
    Set-Step "安装前端依赖"
    
    Set-Location $Script:FrontendDir
    
    if (-not (Test-Path "package.json")) {
        Write-Err "package.json 不存在"
        Set-Location $Script:ProjectRoot
        return $false
    }
    
    if (-not (Test-Path "node_modules")) {
        Write-Info "安装 npm 依赖..."
        npm install 2>&1 | Out-Null
    }
    
    Set-Location $Script:ProjectRoot
    Write-Success "前端依赖安装完成"
    return $true
}

function Test-Port($port) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    return ($null -ne $conn -and $conn.Count -gt 0)
}

function Get-PortProcess($port) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conn) {
        return $conn[0].OwningProcess
    }
    return $null
}

function Stop-ProcessOnPort($port) {
    $pid = Get-PortProcess $port
    if ($pid) {
        Write-Warn "端口 $port 被占用，尝试关闭..."
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Start-Sleep 1
    }
}

function Start-Redis {
    param([string]$Mode = "none")
    
    if ($Mode -eq "none") {
        Write-Info "Redis: 禁用 (无缓存模式)"
        $env:REDIS_URL = "redis://127.0.0.1:6379"
        return $true
    }
    
    if (Test-Port 6379) {
        Write-Info "Redis: 已在运行"
        return $true
    }
    
    if ($Mode -eq "memurai") {
        Write-Info "启动 Memurai..."
        Start-Process -FilePath "memurai" -ArgumentList "server", "--maxmemory", "64mb", "--maxmemory-policy", "allkeys-lru" -WindowStyle Hidden -ErrorAction SilentlyContinue
    } else {
        Write-Info "启动 Redis..."
        Start-Process -FilePath "redis-server" -ArgumentList "--daemonize", "yes", "--port", "6379", "--maxmemory", "64mb", "--maxmemory-policy", "allkeys-lru" -WindowStyle Hidden -ErrorAction SilentlyContinue
    }
    
    Start-Sleep 2
    
    if (Test-Port 6379) {
        Write-Success "Redis 已启动"
        return $true
    } else {
        Write-Warn "Redis 启动失败，禁用缓存"
        return $true
    }
}

function Start-Backend {
    Set-Step "启动后端服务"
    
    if (Test-Port 8000) {
        Write-Warn "端口 8000 已被占用"
        Stop-ProcessOnPort 8000
    }
    
    $activate = Join-Path $Script:VenvDir "Scripts\Activate.ps1"
    if (-not (Test-Path $activate)) {
        Write-Err "虚拟环境未找到"
        return $false
    }
    
    $logFile = Join-Path $DataDir "logs\backend.log"
    if (-not (Test-Path (Split-Path $logFile))) {
        New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
    }
    
    Write-Info "启动 uvicorn (日志: $logFile)..."
    
    $python = Join-Path $Script:VenvDir "Scripts\python.exe"
    $script:BackendJob = Start-Job -ScriptBlock {
        param($python, $logFile, $root)
        
        $env:PYTHONDONTWRITEBYTECODE = "1"
        $env:DATABASE_URL = "sqlite+aiosqlite:///data/novel.db"
        $env:REDIS_URL = "redis://127.0.0.1:6379"
        $env:DATA_DIR = "./data"
        
        Set-Location $root
        
        & $python -m uvicorn main:app --host 0.0.0.0 --port 8000 2>&1 | Out-File -FilePath $logFile -Append
    } -ArgumentList $python, $logFile, $Script:BackendDir
    
    Write-Info "等待后端启动..."
    for ($i = 1; $i -le 30; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($resp.StatusCode -eq 200) {
                Write-Success "后端已就绪 (耗时 ${i}s)"
                return $true
            }
        } catch {}
        if ($i % 5 -eq 0) { Write-Info "仍在启动中... ($i/30)" }
        Start-Sleep 1
    }
    
    Write-Warn "后端启动超时，请检查日志: $logFile"
    return $false
}

function Start-Frontend {
    Set-Step "启动前端服务"
    
    if (Test-Port 8080) {
        Write-Warn "端口 8080 已被占用"
        Stop-ProcessOnPort 8080
    }
    
    Set-Location $Script:FrontendDir
    
    Write-Info "启动 Vite 开发服务器..."
    
    $logFile = Join-Path $DataDir "logs\frontend.log"
    
    $script:FrontendJob = Start-Job -ScriptBlock {
        param($dir, $logFile)
        
        Set-Location $dir
        npm run dev -- --host 0.0.0.0 --port 8080 2>&1 | Out-File -FilePath $logFile -Append
    } -ArgumentList $Script:FrontendDir, $logFile
    
    Write-Info "等待前端启动..."
    for ($i = 1; $i -le 60; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8080" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($resp.StatusCode -eq 200) {
                Write-Success "前端已就绪 (耗时 ${i}s)"
                Set-Location $Script:ProjectRoot
                return $true
            }
        } catch {}
        if ($i % 10 -eq 0) { Write-Info "仍在启动中... ($i/60)" }
        Start-Sleep 1
    }
    
    Write-Warn "前端启动超时，请检查日志: $logFile"
    Set-Location $Script:ProjectRoot
    return $false
}

function Stop-AllServices {
    Write-Step "停止所有服务"
    
    if ($script:BackendJob) {
        Stop-Job -Job $script:BackendJob -ErrorAction SilentlyContinue
        Remove-Job -Job $script:BackendJob -Force -ErrorAction SilentlyContinue
    }
    if ($script:FrontendJob) {
        Stop-Job -Job $script:FrontendJob -ErrorAction SilentlyContinue
        Remove-Job -Job $script:FrontendJob -Force -ErrorAction SilentlyContinue
    }
    
    Get-Job | Stop-Job -ErrorAction SilentlyContinue
    Get-Job | Remove-Job -Force -ErrorAction SilentlyContinue
    
    Get-CimInstance Win32_Process | Where-Object { $_.Name -match "uvicorn|vite" } | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
    
    Write-Success "所有服务已停止"
}

function Show-Menu {
    Write-Host ""
    Write-Host "═══════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Novel Reader 控制面板" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1. 启动服务" -ForegroundColor Green
    Write-Host "  2. 停止服务" -ForegroundColor Yellow
    Write-Host "  3. 重启服务" -ForegroundColor Cyan
    Write-Host "  4. 检查更新" -ForegroundColor Blue
    Write-Host "  5. 查看日志" -ForegroundColor Gray
    Write-Host "  6. 完整重装" -ForegroundColor Red
    Write-Host "  0. 退出" -ForegroundColor White
    Write-Host ""
    
    $choice = Read-Host "请输入选项"
    return $choice
}

function Update-Project {
    Write-Step "检查更新"
    
    Set-Location $Script:ProjectRoot
    
    Write-Info "拉取最新代码..."
    git fetch origin main 2>$null
    
    $local = git rev-parse HEAD 2>$null
    $remote = git rev-parse origin/main 2>$null
    
    if ($local -eq $remote) {
        Write-Success "已是最新版本"
        return $true
    }
    
    Write-Warn "发现新版本"
    Write-Host "本地:  $local"
    Write-Host "远程:  $remote"
    Write-Host ""
    
    $confirm = Read-Host "是否更新? (y/n)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        return $false
    }
    
    Write-Info "正在更新..."
    git pull origin main 2>&1
    
    Write-Success "更新完成，请重启服务"
    return $true
}

function Show-Logs {
    $backendLog = Join-Path $DataDir "logs\backend.log"
    $frontendLog = Join-Path $DataDir "logs\frontend.log"
    
    Write-Host ""
    Write-Host "═══ 后端日志 (最后 30 行) ═══" -ForegroundColor Cyan
    if (Test-Path $backendLog) {
        Get-Content $backendLog -Tail 30
    } else {
        Write-Host "(无日志)" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "═══ 前端日志 (最后 30 行) ═══" -ForegroundColor Cyan
    if (Test-Path $frontendLog) {
        Get-Content $frontendLog -Tail 30
    } else {
        Write-Host "(无日志)" -ForegroundColor Gray
    }
}

function Get-ServiceStatus {
    Write-Host ""
    Write-Host "═══ 服务状态 ═══" -ForegroundColor Cyan
    
    $backendOk = $false
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        $backendOk = ($resp.StatusCode -eq 200)
    } catch {}
    if ($backendOk) { Write-Success "后端 API: 运行中" } else { Write-Err "后端 API: 未运行" }
    
    $frontendOk = $false
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8080" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        $frontendOk = ($resp.StatusCode -eq 200)
    } catch {}
    if ($frontendOk) { Write-Success "前端页面: 运行中" } else { Write-Err "前端页面: 未运行" }
    
    if ((Test-Port 6379)) { Write-Success "Redis: 运行中" } else { Write-Info "Redis: 未运行 (无缓存)" }
}

function Start-FullInstall {
    Write-Step "Novel Reader 一键安装启动"
    
    Set-ExecutionPolicy-Bypass
    
    Initialize-Directories
    Initialize-EnvFile
    
    if (-not (Install-Python)) {
        Write-Err "Python 安装失败"
        return
    }
    
    if (-not (Install-Nodejs)) {
        Write-Err "Node.js 安装失败"
        return
    }
    
    $redisMode = Install-RedisOrSkip
    Start-Redis -Mode $redisMode
    
    if (-not (Install-PythonDeps)) {
        Write-Err "Python 依赖安装失败"
        return
    }
    
    if (-not (Install-NodeDeps)) {
        Write-Err "前端依赖安装失败"
        return
    }
    
    Write-Step "启动服务"
    
    Start-Redis -Mode $redisMode
    $backendOk = Start-Backend
    $frontendOk = Start-Frontend
    
    Write-Host ""
    Write-Host "═══════════════════════════════════" -ForegroundColor Green
    if ($backendOk -and $frontendOk) {
        Write-Host "  ✓ 服务已全部启动!" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ 部分服务启动异常" -ForegroundColor Yellow
    }
    Write-Host "═══════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "  📖 前端: http://localhost:8080" -ForegroundColor Cyan
    Write-Host "  🔧 API:  http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host ""
    
    Get-ServiceStatus
}

function Main {
    Clear-Host
    
    Set-Location $Script:ProjectRoot
    
    Write-Host ""
    Write-Host "╔═══════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║   Novel Reader 启动器 v1.0        ║" -ForegroundColor Cyan
    Write-Host "╚═══════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    
    if (-not $SkipUpdate) {
        Write-Info "检查更新..."
        try {
            git fetch origin main 2>$null
            $behind = git rev-list HEAD..origin/main --count 2>$null
            if ($behind -gt 0) {
                Write-Warn "发现 $behind 个更新"
                $u = Read-Host "是否更新? (y/n)"
                if ($u -eq "y" -or $u -eq "Y") {
                    Update-Project
                }
            }
        } catch {}
    }
    
    if ($Force) {
        Stop-AllServices
    }
    
    while ($true) {
        Get-ServiceStatus
        $choice = Show-Menu
        
        switch ($choice) {
            "1" { Start-FullInstall }
            "2" { Stop-AllServices; Write-Success "已停止" }
            "3" { Stop-AllServices; Start-Sleep 2; Start-FullInstall }
            "4" { Update-Project }
            "5" { Show-Logs }
            "6" {
                Write-Warn "即将删除所有依赖并重新安装..."
                $confirm = Read-Host "确认? (yes/no)"
                if ($confirm -eq "yes") {
                    Stop-AllServices
                    Remove-Item -Recurse -Force (Join-Path $Script:BackendDir "venv") -ErrorAction SilentlyContinue
                    Remove-Item -Recurse -Force (Join-Path $Script:FrontendDir "node_modules") -ErrorAction SilentlyContinue
                    Start-FullInstall
                }
            }
            "0" { Write-Host "再见!"; break }
            default { Write-Warn "无效选项" }
        }
        
        if ($choice -eq "0") { break }
    }
}

Main
