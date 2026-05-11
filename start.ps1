# Novel Reader Windows Launcher
# Encoding: UTF-8 with BOM
# Usage: .\start.ps1

param(
    [switch]$SkipUpdate,
    [switch]$Force,
    [switch]$Debug
)

$ErrorActionPreference = "Continue"
$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

$Script:ProjectRoot = $PSScriptRoot
$Script:BackendDir = Join-Path $Script:ProjectRoot "backend"
$Script:FrontendDir = Join-Path $Script:ProjectRoot "frontend"
$Script:DataDir = Join-Path $Script:ProjectRoot "data"
$Script:VenvDir = Join-Path $Script:BackendDir "venv"
$Script:PidsDir = Join-Path $Script:ProjectRoot ".pids"

$R = "Red"; $G = "Green"; $Y = "Yellow"; $B = "Cyan"; $C = "Cyan"

function W($msg) { Write-Host "[INFO] $msg" -ForegroundColor $B }
function S($msg) { Write-Host "[OK] $msg" -ForegroundColor $G }
function Wn($msg) { Write-Host "[WARN] $msg" -ForegroundColor $Y }
function E($msg) { Write-Host "[ERROR] $msg" -ForegroundColor $R }
function H($msg) {
    Write-Host ""
    Write-Host "=== $msg ===" -ForegroundColor $C
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
        W "Setting PowerShell policy..."
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
    if (-not (Test-Path $Script:PidsDir)) {
        New-Item -ItemType Directory -Force -Path $Script:PidsDir | Out-Null
    }
}

function Init-Env {
    $envPath = Join-Path $Script:ProjectRoot ".env"
    if (-not (Test-Path $envPath)) {
        W "Creating .env file..."
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
        S ".env created"
    }
}

function Set-Mirrors {
    $region = Get-Region
    if ($region -eq "china") {
        W "Detected China, setting up mirrors..."
        
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
        S "Mirrors configured"
    }
}

function Test-Cmd($cmd) {
    return !!(Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Install-Python {
    if (Test-Cmd "python") {
        $ver = python --version 2>&1
        W "Python: $ver"
        return $true
    }
    
    H "Install Python"
    
    if (Test-Cmd "py") {
        W "Try using py launcher..."
        py -3.11 -m pip --version 2>$null
        if ($?) {
            S "Using py launcher"
            return $true
        }
    }
    
    Wn "Python not found!"
    W "Please install Python from Microsoft Store or python.org"
    
    try {
        Start-Process "ms-windows-store://search/python"
    } catch {}
    
    return $false
}

function Install-Nodejs {
    if (Test-Cmd "node") {
        $ver = node --version
        W "Node.js: v$ver"
        return $true
    }
    
    H "Install Node.js"
    Wn "Node.js not found!"
    W "Please install from https://nodejs.org"
    
    try {
        Start-Process "https://nodejs.org"
    } catch {}
    
    return $false
}

function Get-RedisMode {
    if (Test-Cmd "redis-server") { return "native" }
    if (Test-Cmd "memurai") { return "memurai" }
    Wn "Redis not found, cache disabled"
    return "none"
}

function Install-PythonDeps {
    H "Install Python Dependencies"
    
    Set-Mirrors
    
    if (-not (Test-Path $Script:VenvDir)) {
        W "Creating venv..."
        python -m venv venv
        if (-not $?) {
            E "Venv creation failed"
            return $false
        }
    }
    
    $pip = Join-Path $Script:VenvDir "Scripts\pip.exe"
    if (-not (Test-Path $pip)) {
        Wn "Venv corrupted, recreating..."
        Remove-Item -Recurse -Force $Script:VenvDir -ErrorAction SilentlyContinue
        python -m venv venv
        $pip = Join-Path $Script:VenvDir "Scripts\pip.exe"
    }
    
    W "Upgrading pip..."
    & $pip install --upgrade pip --quiet 2>$null
    
    W "Installing dependencies..."
    
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
    W "Installing core packages (may take minutes)..."
    
    & $pip install $depsStr --quiet 2>&1 | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        Wn "Some deps failed, retry one by one..."
        foreach ($dep in $deps) {
            & $pip install $dep --quiet 2>$null
        }
    }
    
    S "Python deps installed"
    return $true
}

function Install-NodeDeps {
    H "Install Frontend Dependencies"
    
    Set-Location $Script:FrontendDir
    
    if (-not (Test-Path "package.json")) {
        E "package.json not found"
        Set-Location $Script:ProjectRoot
        return $false
    }
    
    if (-not (Test-Path "node_modules")) {
        W "Installing npm packages..."
        npm install 2>&1 | Out-Null
    }
    
    Set-Location $Script:ProjectRoot
    S "Node deps installed"
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
        Wn "Port $port in use, killing..."
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Start-Sleep 1
    }
}

function Start-Redis {
    param([string]$Mode = "none")
    
    if ($Mode -eq "none") {
        W "Redis: disabled (no-cache mode)"
        return $true
    }
    
    if (Test-Port 6379) {
        W "Redis: already running"
        return $true
    }
    
    if ($Mode -eq "memurai") {
        W "Starting Memurai..."
        Start-Process -FilePath "memurai" -ArgumentList "server", "--maxmemory", "64mb" -WindowStyle Hidden -ErrorAction SilentlyContinue
    } else {
        W "Starting Redis..."
        Start-Process -FilePath "redis-server" -ArgumentList "--daemonize", "yes", "--port", "6379", "--maxmemory", "64mb", "--maxmemory-policy", "allkeys-lru" -WindowStyle Hidden -ErrorAction SilentlyContinue
    }
    
    Start-Sleep 2
    
    if (Test-Port 6379) {
        S "Redis started"
        return $true
    } else {
        Wn "Redis start failed, continuing without cache"
        return $true
    }
}

function Start-Backend {
    H "Start Backend"
    
    if (Test-Port 8000) { Kill-Port 8000 }
    
    $activate = Join-Path $Script:VenvDir "Scripts\Activate.ps1"
    if (-not (Test-Path $activate)) {
        E "Venv not found, run install first"
        return $false
    }
    
    $logFile = Join-Path $DataDir "logs\backend.log"
    $logDir = Split-Path $logFile
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    }
    
    W "Starting uvicorn..."
    
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
    
    W "Waiting for backend..."
    for ($i = 1; $i -le 30; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($resp.StatusCode -eq 200) {
                S "Backend ready (${i}s)"
                return $true
            }
        } catch {}
        if ($i % 5 -eq 0) { W "Still starting... ($i/30)" }
        Start-Sleep 1
    }
    
    Wn "Backend timeout, check logs"
    return $false
}

function Start-Frontend {
    H "Start Frontend"
    
    if (Test-Port 8080) { Kill-Port 8080 }
    
    Set-Location $Script:FrontendDir
    
    W "Starting Vite..."
    $logFile = Join-Path $DataDir "logs\frontend.log"
    
    $script:FrontendJob = Start-Job -ScriptBlock {
        param($dir, $logFile)
        Set-Location $dir
        npm run dev -- --host 0.0.0.0 --port 8080 2>&1 | Out-File -FilePath $logFile -Append
    } -ArgumentList $Script:FrontendDir, $logFile
    
    W "Waiting for frontend..."
    for ($i = 1; $i -le 60; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8080" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($resp.StatusCode -eq 200) {
                S "Frontend ready (${i}s)"
                Set-Location $Script:ProjectRoot
                return $true
            }
        } catch {}
        if ($i % 10 -eq 0) { W "Still starting... ($i/60)" }
        Start-Sleep 1
    }
    
    Wn "Frontend timeout, check logs"
    Set-Location $Script:ProjectRoot
    return $false
}

function Stop-All {
    H "Stop Services"
    
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
    
    S "All services stopped"
}

function Show-Menu {
    Write-Host ""
    Write-Host "===================================" -ForegroundColor $C
    Write-Host "  Novel Reader Control Panel" -ForegroundColor $C
    Write-Host "===================================" -ForegroundColor $C
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
    H "Check Updates"
    
    Set-Location $Script:ProjectRoot
    
    try {
        git fetch origin main 2>$null
        $local = git rev-parse HEAD 2>$null
        $remote = git rev-parse origin/main 2>$null
        
        if ($local -eq $remote) {
            S "Already up to date"
            return $true
        }
        
        Wn "Updates available"
        Write-Host "Local:  $local"
        Write-Host "Remote: $remote"
        Write-Host ""
        
        $confirm = Read-Host "Update? (y/n)"
        if ($confirm -ne "y" -and $confirm -ne "Y") { return $false }
        
        W "Updating..."
        git pull origin main 2>&1
        S "Update complete, restart services"
        return $true
    } catch {
        Wn "Update failed: $_"
        return $false
    }
}

function Show-Logs {
    $backendLog = Join-Path $DataDir "logs\backend.log"
    $frontendLog = Join-Path $DataDir "logs\frontend.log"
    
    Write-Host ""
    Write-Host "=== Backend Log (last 30 lines) ===" -ForegroundColor $C
    if (Test-Path $backendLog) {
        Get-Content $backendLog -Tail 30
    } else {
        Write-Host "(no log)" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "=== Frontend Log (last 30 lines) ===" -ForegroundColor $C
    if (Test-Path $frontendLog) {
        Get-Content $frontendLog -Tail 30
    } else {
        Write-Host "(no log)" -ForegroundColor Gray
    }
}

function Get-Status {
    Write-Host ""
    Write-Host "=== Service Status ===" -ForegroundColor $C
    
    $backendOk = $false
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        $backendOk = ($resp.StatusCode -eq 200)
    } catch {}
    if ($backendOk) { S "Backend API: Running" } else { E "Backend API: Stopped" }
    
    $frontendOk = $false
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8080" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        $frontendOk = ($resp.StatusCode -eq 200)
    } catch {}
    if ($frontendOk) { S "Frontend: Running" } else { E "Frontend: Stopped" }
    
    if (Test-Port 6379) { S "Redis: Running" } else { W "Redis: Not running" }
}

function Full-Install {
    H "Novel Reader Setup"
    
    Set-Policy
    Init-Dirs
    Init-Env
    
    if (-not (Install-Python)) { return }
    if (-not (Install-Nodejs)) { return }
    
    $redisMode = Get-RedisMode
    Start-Redis -Mode $redisMode
    
    if (-not (Install-PythonDeps)) { return }
    if (-not (Install-NodeDeps)) { return }
    
    H "Start Services"
    
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
        W "Checking updates..."
        try {
            git fetch origin main 2>$null
            $behind = git rev-list HEAD..origin/main --count 2>$null
            if ($behind -gt 0) {
                Wn "Found $behind update(s)"
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
            "2" { Stop-All; S "Stopped" }
            "3" { Stop-All; Start-Sleep 2; Full-Install }
            "4" { Update-Project }
            "5" { Show-Logs }
            "6" {
                Wn "Will delete all deps and reinstall..."
                $confirm = Read-Host "Confirm? (yes/no)"
                if ($confirm -eq "yes") {
                    Stop-All
                    Remove-Item -Recurse -Force (Join-Path $Script:BackendDir "venv") -ErrorAction SilentlyContinue
                    Remove-Item -Recurse -Force (Join-Path $Script:FrontendDir "node_modules") -ErrorAction SilentlyContinue
                    Full-Install
                }
            }
            "0" { Write-Host "Goodbye!"; break }
            default { Wn "Invalid option" }
        }
        
        if ($choice -eq "0") { break }
    }
}

Main
