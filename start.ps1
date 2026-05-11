# Novel Reader Windows Launcher
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
function Write-Sep($msg) { Write-Host ""; Write-Host "=== $msg ===" -ForegroundColor Cyan }

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
        Write-Info "Setting policy..."
        Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force -ErrorAction SilentlyContinue
    }
}

function Init-Dirs {
    @("books", "index", "static", "logs", "cache", "backups") | ForEach-Object {
        $p = Join-Path $DataDir $_
        if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
    }
}

function Init-Env {
    $p = Join-Path $Script:ProjectRoot ".env"
    if (-not (Test-Path $p)) {
        $key = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % { [char]$_ })
        @"
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
"@ | Out-File -FilePath $p -Encoding UTF8
        Write-OK ".env created"
    }
}

function Set-Mirrors {
    if ((Get-Region) -eq "china") {
        Write-Info "China detected, set mirrors..."
        $pipDir = "$env:APPDATA\pip"
        if (-not (Test-Path $pipDir)) { New-Item -ItemType Directory -Force -Path $pipDir | Out-Null }
        @"
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 120
[install]
trusted-host = mirrors.aliyun.com
"@ | Out-File -FilePath "$pipDir\pip.ini" -Encoding UTF8
        npm config set registry https://registry.npmmirror.com --location user 2>$null
        Write-OK "Mirrors set"
    }
}

function Test-Cmd($name) {
    return !!(Get-Command $name -ErrorAction SilentlyContinue)
}

function Install-Python {
    if (Test-Cmd "python") {
        $v = python --version 2>&1
        Write-Info "Python: $v"
        return $true
    }
    Write-Sep "Install Python"
    if (Test-Cmd "py") {
        Write-Info "Try py launcher..."
        py -3.11 -m pip --version 2>$null
        if ($?) { Write-OK "Using py launcher"; return $true }
    }
    Write-Warn "Python not found! Install from Microsoft Store or python.org"
    return $false
}

function Install-Nodejs {
    if (Test-Cmd "node") {
        $v = node --version
        Write-Info "Node: $v"
        return $true
    }
    Write-Sep "Install Node.js"
    Write-Warn "Node not found, install from https://nodejs.org"
    return $false
}

function Get-RedisMode {
    if (Test-Cmd "redis-server") { return "native" }
    if (Test-Cmd "memurai") { return "memurai" }
    Write-Warn "Redis not found, cache disabled"
    return "none"
}

function Install-PythonDeps {
    Write-Sep "Install Python dependencies"
    Set-Mirrors
    $venv = Join-Path $Script:BackendDir "venv"
    if (-not (Test-Path $venv)) {
        Write-Info "Creating venv in backend dir..."
        Set-Location $Script:BackendDir
        python -m venv venv
        if (-not $?) { Write-Err "Venv failed"; Set-Location $Script:ProjectRoot; return $false }
        Set-Location $Script:ProjectRoot
    }
    $pip = Join-Path $venv "Scripts\pip.exe"
    if (-not (Test-Path $pip)) {
        Write-Warn "Venv corrupt, recreating..."
        Remove-Item -Recurse -Force $venv -ErrorAction SilentlyContinue
        Set-Location $Script:BackendDir
        python -m venv venv
        Set-Location $Script:ProjectRoot
        $pip = Join-Path $venv "Scripts\pip.exe"
    }
    Write-Info "Upgrading pip..."
    & cmd /c "`"$pip`" install --upgrade pip" 2>$null
    $req = Join-Path $Script:BackendDir "requirements.txt"
    Write-Info "Installing from $req..."
    & cmd /c "`"$pip`" install -r `"$req`""
    Write-OK "Python deps installed"
    return $true
}

function Install-NodeDeps {
    Write-Sep "Install frontend dependencies"
    Set-Location $Script:FrontendDir
    if (-not (Test-Path "package.json")) { Write-Err "package.json missing"; Set-Location $Script:ProjectRoot; return $false }
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

function Kill-Port($port) {
    $pids = (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue).OwningProcess
    if ($pids) { $pids | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }; Start-Sleep 1 }
}

function Start-Redis {
    param($Mode = "none")
    if ($Mode -eq "none") { Write-Info "Redis disabled"; return $true }
    if (Test-Port 6379) { Write-Info "Redis running"; return $true }
    Write-Info "Starting Redis..."
    if ($Mode -eq "memurai") { Start-Process -FilePath "memurai" -ArgumentList "server", "--maxmemory", "64mb" -WindowStyle Hidden -ErrorAction SilentlyContinue }
    else { Start-Process -FilePath "redis-server" -ArgumentList "--daemonize", "yes", "--port", "6379", "--maxmemory", "64mb", "--maxmemory-policy", "allkeys-lru" -WindowStyle Hidden -ErrorAction SilentlyContinue }
    Start-Sleep 2
    if (Test-Port 6379) { Write-OK "Redis started" } else { Write-Warn "Redis start failed" }
    return $true
}

function Start-Backend {
    Write-Sep "Start backend"
    if (Test-Port 8000) { Kill-Port 8000 }
    $venv = Join-Path $Script:BackendDir "venv"
    $py = Join-Path $venv "Scripts\python.exe"
    if (-not (Test-Path $py)) { Write-Err "Venv missing"; return $false }
    $log = Join-Path $DataDir "logs\backend.log"
    $logDir = Split-Path $log
    if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
    Write-Info "Starting uvicorn..."
    $Script:BackendJob = Start-Job -ScriptBlock {
        param($py, $log, $root)
        $env:PYTHONDONTWRITEBYTECODE = "1"
        Set-Location $root
        cmd /c "`"$py`" -m uvicorn main:app --host 0.0.0.0 --port 8000" 2>&1 | Out-File -FilePath $log -Append
    } -ArgumentList $py, $log, $Script:BackendDir
    Write-Info "Wait for backend..."
    for ($i = 1; $i -le 30; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($resp.StatusCode -eq 200) { Write-OK "Backend ready ($i s)"; return $true }
        } catch {}
        if ($i % 5 -eq 0) { Write-Info "Still starting ($i / 30)" }
        Start-Sleep 1
    }
    Write-Warn "Backend timeout"
    return $false
}

function Start-Frontend {
    Write-Sep "Start frontend"
    if (Test-Port 8080) { Kill-Port 8080 }
    Set-Location $Script:FrontendDir
    Write-Info "Starting vite..."
    $log = Join-Path $DataDir "logs\frontend.log"
    $Script:FrontendJob = Start-Job -ScriptBlock {
        param($dir, $log)
        Set-Location $dir
        npm run dev -- --host 0.0.0.0 --port 8080 2>&1 | Out-File -FilePath $log -Append
    } -ArgumentList $Script:FrontendDir, $log
    Write-Info "Wait for frontend..."
    for ($i = 1; $i -le 60; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8080" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($resp.StatusCode -eq 200) { Write-OK "Frontend ready ($i s)"; Set-Location $Script:ProjectRoot; return $true }
        } catch {}
        if ($i % 10 -eq 0) { Write-Info "Still starting ($i / 60)" }
        Start-Sleep 1
    }
    Write-Warn "Frontend timeout"
    Set-Location $Script:ProjectRoot
    return $false
}

function Stop-All {
    Write-Sep "Stop all"
    if ($Script:BackendJob) { Stop-Job $Script:BackendJob -ErrorAction SilentlyContinue; Remove-Job $Script:BackendJob -Force -ErrorAction SilentlyContinue }
    if ($Script:FrontendJob) { Stop-Job $Script:FrontendJob -ErrorAction SilentlyContinue; Remove-Job $Script:FrontendJob -Force -ErrorAction SilentlyContinue }
    Get-Job | Stop-Job -ErrorAction SilentlyContinue; Get-Job | Remove-Job -Force -ErrorAction SilentlyContinue
    Get-CimInstance Win32_Process | Where-Object { $_.Name -match "uvicorn|vite" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-OK "All stopped"
}

function Show-Menu {
    Write-Host ""
    Write-Host "===================================" -ForegroundColor Cyan
    Write-Host "    Novel Reader Control Panel     " -ForegroundColor Cyan
    Write-Host "===================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Start all services" -ForegroundColor Green
    Write-Host "2. Stop all services" -ForegroundColor Yellow
    Write-Host "3. Restart services" -ForegroundColor Cyan
    Write-Host "4. Check for updates" -ForegroundColor Blue
    Write-Host "5. View logs" -ForegroundColor Gray
    Write-Host "6. Clean install (reinstall all deps)" -ForegroundColor Red
    Write-Host "0. Exit" -ForegroundColor White
    Write-Host ""
    $choice = Read-Host "Select choice"
    return $choice
}

function Update-Project {
    Write-Sep "Check updates"
    Set-Location $Script:ProjectRoot
    try {
        git fetch origin main 2>$null
        $local = git rev-parse HEAD 2>$null
        $remote = git rev-parse origin/main 2>$null
        if ($local -eq $remote) { Write-OK "Already latest"; return $true }
        Write-Warn "Updates available! Local: $local, Remote: $remote"
        $confirm = Read-Host "Update now? (y/n)"
        if ($confirm -ne "y" -and $confirm -ne "Y") { return $false }
        git pull origin main 2>&1
        Write-OK "Updated! Restart services"
        return $true
    } catch {
        Write-Warn "Update failed: $_"
        return $false
    }
}

function Show-Logs {
    $bLog = Join-Path $DataDir "logs\backend.log"
    $fLog = Join-Path $DataDir "logs\frontend.log"
    Write-Host ""
    Write-Host "=== Backend log (last 30 lines) ===" -ForegroundColor Cyan
    if (Test-Path $bLog) { Get-Content $bLog -Tail 30 } else { Write-Host "(No log yet)" -ForegroundColor Gray }
    Write-Host ""
    Write-Host "=== Frontend log (last 30 lines) ===" -ForegroundColor Cyan
    if (Test-Path $fLog) { Get-Content $fLog -Tail 30 } else { Write-Host "(No log yet)" -ForegroundColor Gray }
}

function Get-Status {
    Write-Host ""
    Write-Host "=== Service status ===" -ForegroundColor Cyan
    $backendOk = $false
    try { $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue; $backendOk = ($r.StatusCode -eq 200) } catch {}
    if ($backendOk) { Write-OK "Backend: running" } else { Write-Err "Backend: stopped" }
    $frontendOk = $false
    try { $r = Invoke-WebRequest -Uri "http://127.0.0.1:8080" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue; $frontendOk = ($r.StatusCode -eq 200) } catch {}
    if ($frontendOk) { Write-OK "Frontend: running" } else { Write-Err "Frontend: stopped" }
    if (Test-Port 6379) { Write-OK "Redis: running" } else { Write-Info "Redis: not running" }
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
    Write-Sep "Start services"
    Start-Redis -Mode $redisMode
    $bOK = Start-Backend
    $fOK = Start-Frontend
    Write-Host ""
    Write-Host "===================================" -ForegroundColor Green
    if ($bOK -and $fOK) { Write-Host "      All services started!       " -ForegroundColor Green } else { Write-Host "      Some services failed        " -ForegroundColor Yellow }
    Write-Host "===================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Frontend: http://localhost:8080" -ForegroundColor Cyan
    Write-Host "  API docs: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host ""
    Get-Status
}

function Main {
    Clear-Host
    Set-Location $Script:ProjectRoot
    Write-Host ""
    Write-Host "===================================" -ForegroundColor Cyan
    Write-Host "   Novel Reader Launcher v1.0     " -ForegroundColor Cyan
    Write-Host "===================================" -ForegroundColor Cyan
    Write-Host ""
    if (-not $SkipUpdate) { Write-Info "Check updates..."; Update-Project }
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
                Write-Warn "Clean install (deletes venv/node_modules)?"
                $confirm = Read-Host "Confirm? (yes/no)"
                if ($confirm -eq "yes") {
                    Stop-All
                    Remove-Item -Recurse -Force (Join-Path $Script:BackendDir "venv") -ErrorAction SilentlyContinue
                    Remove-Item -Recurse -Force (Join-Path $Script:FrontendDir "node_modules") -ErrorAction SilentlyContinue
                    Full-Install
                }
            }
            "0" { Write-Host "Goodbye!"; break }
            default { Write-Warn "Invalid choice" }
        }
        if ($choice -eq "0") { break }
    }
}

Main