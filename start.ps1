# Novel Reader Windows Launcher
# No Unicode - Pure ASCII Only
# Usage: .\start.ps1

param(
    [switch]$SkipUpdate,
    [switch]$Force,
    [switch]$Debug
)

$ErrorActionPreference = "Continue"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Script:ProjectRoot = $PSScriptRoot
$Script:BackendDir = Join-Path $Script:ProjectRoot "backend"
$Script:FrontendDir = Join-Path $Script:ProjectRoot "frontend"
$Script:DataDir = Join-Path $Script:ProjectRoot "data"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-OK($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Write-Sep($msg) {
    Write-Host ""
    Write-Host "=== $msg ===" -ForegroundColor Cyan
}

function Get-Region {
    try {
        $r = Invoke-WebRequest -Uri "https://ipinfo.io/country" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($r.Content -eq "CN") { return "china" }
    } catch {}
    return "global"
}

function Set-Policy {
    $current = Get-ExecutionPolicy -Scope CurrentUser
    if ($current -eq "Restricted" -or $current -eq "Undefined") {
        Write-Info "Setting PowerShell policy..."
        Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force -ErrorAction SilentlyContinue
    }
}

function Init-Dirs {
    $dirs = @("books", "index", "static", "logs", "cache", "backups")
    foreach ($dir in $dirs) {
        $path = Join-Path $DataDir $dir
        if (-not (Test-Path $path)) {
            New-Item -ItemType Directory -Force -Path $path | Out-Null
        }
    }
}

function Init-Env {
    $envPath = Join-Path $Script:ProjectRoot ".env"
    if (-not (Test-Path $envPath)) {
        Write-Info "Creating .env file..."
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
        Write-OK ".env created"
    }
}

function Set-Mirrors {
    $region = Get-Region
    if ($region -eq "china") {
        Write-Info "China region detected, setting mirrors..."
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
        Write-OK "Mirrors configured"
    }
}

function Test-Cmd($cmd) {
    return !!(Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Install-Python {
    if (Test-Cmd "python") {
        $ver = python --version 2>&1
        Write-Info "Python: $ver"
        return $true
    }
    Write-Sep "Install Python"
    if (Test-Cmd "py") {
        Write-Info "Try using py launcher..."
        py -3.11 -m pip --version 2>$null
        if ($?) {
            Write-OK "Using py launcher"
            return $true
        }
    }
    Write-Warn "Python not found!"
    Write-Info "Please install Python from Microsoft Store or python.org"
    try {
        Start-Process "ms-windows-store://search/python"
    } catch {}
    return $false
}

function Install-Nodejs {
    if (Test-Cmd "node") {
        $ver = node --version
        Write-Info "Node.js: v$ver"
        return $true
    }
    Write-Sep "Install Node.js"
    Write-Warn "Node.js not found!"
    Write-Info "Please install from https://nodejs.org"
    try {
        Start-Process "https://nodejs.org"
    } catch {}
    return $false
}

function Get-RedisMode {
    if (Test-Cmd "redis-server") { return "native" }
    if (Test-Cmd "memurai") { return "memurai" }
    Write-Warn "Redis not found, cache disabled"
    return "none"
}

function Install-PythonDeps {
    Write-Sep "Install Python Dependencies"
    Set-Mirrors
    $venvPath = Join-Path $Script:BackendDir "venv"
    if (-not (Test-Path $venvPath)) {
        Write-Info "Creating venv in backend folder..."
        Set-Location $Script:BackendDir
        python -m venv venv
        if (-not $?) {
            Write-Err "Venv creation failed"
            Set-Location $Script:ProjectRoot
            return $false
        }
        Set-Location $Script:ProjectRoot
    }
    $pip = Join-Path $venvPath "Scripts\pip.exe"
    if (-not (Test-Path $pip)) {
        Write-Warn "Venv corrupted, recreating..."
        Remove-Item -Recurse -Force $venvPath -ErrorAction SilentlyContinue
        Set-Location $Script:BackendDir
        python -m venv venv
        Set-Location $Script:ProjectRoot
        $pip = Join-Path $venvPath "Scripts\pip.exe"
    }
    Write-Info "Upgrading pip..."
    cmd /c "`"$pip`" install --upgrade pip" 2>$null
    Write-Info "Installing dependencies..."
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
    Write-Info "Installing core packages (may take minutes)..."
    cmd /c "`"$pip`" install $depsStr" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Some deps failed, retry one by one..."
        foreach ($dep in $deps) {
            cmd /c "`"$pip`" install $dep" 2>$null
        }
    }
    Write-OK "Python deps installed"
    return $true
}

function Install-NodeDeps {
    Write-Sep "Install Frontend Dependencies"
    Set-Location $Script:FrontendDir
    if (-not (Test-Path "package.json")) {
        Write-Err "package.json not found"
        Set-Location $Script:ProjectRoot
        return $false
    }
    if (-not (Test-Path "node_modules")) {
        Write-Info "Installing npm packages..."
        npm install 2>&1 | Out-Null
    }
    Set-Location $Script:ProjectRoot
    Write-OK "Node deps installed"
    return $true
}

function Test-Port($port) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    return ($null -ne $conn -and $conn.Count -gt 0)
}

function Get-PortPID($port) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conn) { return $conn[0].OwningProcess }
    return $null
}

function Kill-Port($port) {
    $pid = Get-PortPID $port
    if ($pid) {
        Write-Warn "Port $port in use, killing..."
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Start-Sleep 1
    }
}

function Start-Redis {
    param([string]$Mode = "none")
    if ($Mode -eq "none") {
        Write-Info "Redis: disabled (no-cache mode)"
        return $true
    }
    if (Test-Port 6379) {
        Write-Info "Redis: already running"
        return $true
    }
    if ($Mode -eq "memurai") {
        Write-Info "Starting Memurai..."
        Start-Process -FilePath "memurai" -ArgumentList "server", "--maxmemory", "64mb" -WindowStyle Hidden -ErrorAction SilentlyContinue
    } else {
        Write-Info "Starting Redis..."
        Start-Process -FilePath "redis-server" -ArgumentList "--daemonize", "yes", "--port", "6379", "--maxmemory", "64mb", "--maxmemory-policy", "allkeys-lru" -WindowStyle Hidden -ErrorAction SilentlyContinue
    }
    Start-Sleep 2
    if (Test-Port 6379) {
        Write-OK "Redis started"
        return $true
    } else {
        Write-Warn "Redis start failed, continuing without cache"
        return $true
    }
}

function Start-Backend {
    Write-Sep "Start Backend"
    if (Test-Port 8000) { Kill-Port 8000 }
    $venvPath = Join-Path $Script:BackendDir "venv"
    $python = Join-Path $venvPath "Scripts\python.exe"
    if (-not (Test-Path $python)) {
        Write-Err "Venv not found, run install first"
        return $false
    }
    $logFile = Join-Path $DataDir "logs\backend.log"
    $logDir = Split-Path $logFile
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    }
    Write-Info "Starting uvicorn..."
    $script:BackendJob = Start-Job -ScriptBlock {
        param($python, $logFile, $root)
        $env:PYTHONDONTWRITEBYTECODE = "1"
        $env:DATABASE_URL = "sqlite+aiosqlite:///data/novel.db"
        $env:REDIS_URL = "redis://127.0.0.1:6379"
        $env:DATA_DIR = "./data"
        Set-Location $root
        cmd /c "`"$python`" -m uvicorn main:app --host 0.0.0.0 --port 8000" 2>&1 | Out-File -FilePath $logFile -Append
    } -ArgumentList $python, $logFile, $Script:BackendDir
    Write-Info "Waiting for backend..."
    for ($i = 1; $i -le 30; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($resp.StatusCode -eq 200) {
                Write-OK "Backend ready (${i}s)"
                return $true
            }
        } catch {}
        if ($i % 5 -eq 0) { Write-Info "Still starting... ($i/30)" }
        Start-Sleep 1
    }
    Write-Warn "Backend timeout, check logs"
    return $false
}

function Start-Frontend {
    Write-Sep "Start Frontend"
    if (Test-Port 8080) { Kill-Port 8080 }
    Set-Location $Script:FrontendDir
    Write-Info "Starting Vite..."
    $logFile = Join-Path $DataDir "logs\frontend.log"
    $script:FrontendJob = Start-Job -ScriptBlock {
        param($dir, $logFile)
        Set-Location $dir
        npm run dev -- --host 0.0.0.0 --port 8080 2>&1 | Out-File -FilePath $logFile -Append
    } -ArgumentList $Script:FrontendDir, $logFile
    Write-Info "Waiting for frontend..."
    for ($i = 1; $i -le 60; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8080" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($resp.StatusCode -eq 200) {
                Write-OK "Frontend ready (${i}s)"
                Set-Location $Script:ProjectRoot
                return $true
            }
        } catch {}
        if ($i % 10 -eq 0) { Write-Info "Still starting... ($i/60)" }
        Start-Sleep 1
    }
    Write-Warn "Frontend timeout, check logs"
    Set-Location $Script:ProjectRoot
    return $false
}

function Stop-All {
    Write-Sep "Stop Services"
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
    Write-OK "All services stopped"
}

function Show-Menu {
    Write-Host ""
    Write-Host "===================================" -ForegroundColor Cyan
    Write-Host "  Novel Reader Control Panel" -ForegroundColor Cyan
    Write-Host "===================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1. Start Services" -ForegroundColor Green
    Write-Host "  2. Stop Services" -ForegroundColor Yellow
    Write-Host "  3. Restart Services" -ForegroundColor Cyan
    Write-Host "  4. Check Updates" -ForegroundColor Blue
    Write-Host "  5. View Logs" -ForegroundColor Gray
    Write-Host "  6. Clean Reinstall" -ForegroundColor Red
    Write-Host "  0. Exit" -ForegroundColor White
    Write-Host ""
    $choice = Read-Host "Select option"
    return $choice
}

function Update-Project {
    Write-Sep "Check Updates"
    Set-Location $Script:ProjectRoot
    try {
        git fetch origin main 2>$null
        $local = git rev-parse HEAD 2>$null
        $remote = git rev-parse origin/main 2>$null
        if ($local -eq $remote) {
            Write-OK "Already up to date"
            return $true
        }
        Write-Warn "Updates available"
        Write-Host "Local:  $local"
        Write-Host "Remote: $remote"
        Write-Host ""
        $confirm = Read-Host "Update? (y/n)"
        if ($confirm -ne "y" -and $confirm -ne "Y") { return $false }
        Write-Info "Updating..."
        git pull origin main 2>&1
        Write-OK "Update complete, restart services"
        return $true
    } catch {
        Write-Warn "Update failed: $_"
        return $false
    }
}

function Show-Logs {
    $backendLog = Join-Path $DataDir "logs\backend.log"
    $frontendLog = Join-Path $DataDir "logs\frontend.log"
    Write-Host ""
    Write-Host "=== Backend Log (last 30 lines) ===" -ForegroundColor Cyan
    if (Test-Path $backendLog) {
        Get-Content $backendLog -Tail 30
    } else {
        Write-Host "(no log)" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "=== Frontend Log (last 30 lines) ===" -ForegroundColor Cyan
    if (Test-Path $frontendLog) {
        Get-Content $frontendLog -Tail 30
    } else {
        Write-Host "(no log)" -ForegroundColor Gray
    }
}

function Get-Status {
    Write-Host ""
    Write-Host "=== Service Status ===" -ForegroundColor Cyan
    $backendOk = $false
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        $backendOk = ($resp.StatusCode -eq 200)
    } catch {}
    if ($backendOk) { Write-OK "Backend API: Running" } else { Write-Err "Backend API: Stopped" }
    $frontendOk = $false
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8080" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        $frontendOk = ($resp.StatusCode -eq 200)
    } catch {}
    if ($frontendOk) { Write-OK "Frontend: Running" } else { Write-Err "Frontend: Stopped" }
    if (Test-Port 6379) { Write-OK "Redis: Running" } else { Write-Info "Redis: Not running" }
}

function Full-Install {
    Write-Sep "Novel Reader Setup"
    Set-Policy
    Init-Dirs
    Init-Env
    if (-not (Install-Python)) { return }
    if (-not (Install-Nodejs)) { return }
    $redisMode = Get-RedisMode
    Start-Redis -Mode $redisMode
    if (-not (Install-PythonDeps)) { return }
    if (-not (Install-NodeDeps)) { return }
    Write-Sep "Start Services"
    Start-Redis -Mode $redisMode
    $backendOk = Start-Backend
    $frontendOk = Start-Frontend
    Write-Host ""
    Write-Host "===================================" -ForegroundColor Green
    if ($backendOk -and $frontendOk) {
        Write-Host "  All services started!" -ForegroundColor Green
    } else {
        Write-Host "  Some services failed" -ForegroundColor Yellow
    }
    Write-Host "===================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Frontend: http://localhost:8080" -ForegroundColor Cyan
    Write-Host "  API:       http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host ""
    Get-Status
}

function Main {
    Clear-Host
    Set-Location $Script:ProjectRoot
    Write-Host ""
    Write-Host "===================================" -ForegroundColor Cyan
    Write-Host "   Novel Reader Launcher v1.0" -ForegroundColor Cyan
    Write-Host "===================================" -ForegroundColor Cyan
    Write-Host ""
    if (-not $SkipUpdate) {
        Write-Info "Checking updates..."
        try {
            git fetch origin main 2>$null
            $behind = git rev-list HEAD..origin/main --count 2>$null
            if ($behind -gt 0) {
                Write-Warn "Found $behind update(s)"
                $u = Read-Host "Update now? (y/n)"
                if ($u -eq "y" -or $u -eq "Y") { Update-Project }
            }
        } catch {}
    }
    if ($Force) { Stop-All }
    while ($true) {
        Get-Status
        $choice = Show-Menu
        switch ($choice) {
            "1" { Full-Install }
            "2" { Stop-All; Write-OK "Stopped" }
            "3" { Stop-All; Start-Sleep 2; Full-Install }
            "4" { Update-Project }
            "5" { Show-Logs }
            "6" {
                Write-Warn "Will delete all deps and reinstall..."
                $confirm = Read-Host "Confirm? (yes/no)"
                if ($confirm -eq "yes") {
                    Stop-All
                    $venvPath = Join-Path $Script:BackendDir "venv"
                    Remove-Item -Recurse -Force $venvPath -ErrorAction SilentlyContinue
                    Remove-Item -Recurse -Force (Join-Path $Script:FrontendDir "node_modules") -ErrorAction SilentlyContinue
                    Full-Install
                }
            }
            "0" { Write-Host "Goodbye!"; break }
            default { Write-Warn "Invalid option" }
        }
        if ($choice -eq "0") { break }
    }
}

Main
