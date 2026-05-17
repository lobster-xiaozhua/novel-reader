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
        $dbPath = Join-Path $DataDir "novel.db"
        $content = @"
SECRET_KEY=$key
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///$dbPath
REDIS_URL=redis://127.0.0.1:6379
DATA_DIR=$DataDir
BOOKS_DIR=$DataDir\books
INDEX_DIR=$DataDir\index
STATIC_DIR=$DataDir\static
LOGS_DIR=$DataDir\logs
CACHE_DIR=$DataDir\cache
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
    Write-Info "Installing dependencies from requirements.txt..."
    $reqFile = Join-Path $Script:BackendDir "requirements.txt"
    $region = Get-Region
    $extraArgs = ""
    if ($region -eq "china") {
        $extraArgs = "--timeout 120 --retries 5 -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com"
    } else {
        $extraArgs = "--timeout 60 --retries 3"
    }
    cmd /c "`"$pip`" install -r `"$reqFile`" $extraArgs"
    Write-OK "Python deps installed"
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
        Start-Process -FilePath "redis-server" -ArgumentList "--port", "6379", "--maxmemory", "64mb", "--maxmemory-policy", "allkeys-lru" -WindowStyle Hidden -ErrorAction SilentlyContinue
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
    $dbPath = Join-Path $DataDir "novel.db"
    Write-Info "Starting uvicorn..."
    $script:BackendJob = Start-Job -ScriptBlock {
        param($python, $logFile, $root, $dbPath, $dataDir)
        $env:PYTHONDONTWRITEBYTECODE = "1"
        $env:DATABASE_URL = "sqlite+aiosqlite:///$dbPath"
        $env:REDIS_URL = "redis://127.0.0.1:6379"
        $env:DATA_DIR = $dataDir
        $env:BOOKS_DIR = "$dataDir\books"
        $env:INDEX_DIR = "$dataDir\index"
        $env:STATIC_DIR = "$dataDir\static"
        $env:LOGS_DIR = "$dataDir\logs"
        $env:CACHE_DIR = "$dataDir\cache"
        Set-Location $root
        cmd /c "`"$python`" -m uvicorn main:app --host 0.0.0.0 --port 8000" 2>&1 | Out-File -FilePath $logFile -Append
    } -ArgumentList $python, $logFile, $Script:BackendDir, $dbPath, $DataDir
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

function Stop-All {
    Write-Sep "Stop Services"
    if ($script:BackendJob) {
        Stop-Job -Job $script:BackendJob -ErrorAction SilentlyContinue
        Remove-Job -Job $script:BackendJob -Force -ErrorAction SilentlyContinue
    }
    Get-Job | Stop-Job -ErrorAction SilentlyContinue
    Get-Job | Remove-Job -Force -ErrorAction SilentlyContinue
    Get-CimInstance Win32_Process | Where-Object { $_.Name -match "uvicorn" } | ForEach-Object {
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
    Write-Host "  1. Start all services" -ForegroundColor Green
    Write-Host "  2. Stop all services" -ForegroundColor Yellow
    Write-Host "  3. Restart services" -ForegroundColor Cyan
    Write-Host "  4. Check for updates" -ForegroundColor Blue
    Write-Host "  5. View logs" -ForegroundColor Gray
    Write-Host "  6. Clean install (reinstall all deps)" -ForegroundColor Red
    Write-Host "  0. Exit" -ForegroundColor White
    Write-Host ""
    $choice = Read-Host "Select choice"
    return $choice
}

function Invoke-GitPull {
    param([int]$MaxRetries = 3, [int]$TimeoutSec = 30)
    $attempt = 1
    while ($attempt -le $MaxRetries) {
        Write-Info "Pull attempt $attempt/$MaxRetries (timeout: ${TimeoutSec}s)..."
        try {
            $job = Start-Job -ScriptBlock {
                param($dir)
                Set-Location $dir
                git pull origin main 2>&1
            } -ArgumentList $Script:ProjectRoot
            $result = Wait-Job -Job $job -Timeout $TimeoutSec
            if ($result) {
                $output = Receive-Job -Job $job 2>&1
                Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
                if ($LASTEXITCODE -eq 0 -or $output -notmatch "error|fatal|failed") {
                    return $true
                }
                Write-Warn "Pull returned errors"
            } else {
                Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
                Write-Warn "Pull timed out after ${TimeoutSec}s"
            }
        } catch {
            Write-Warn "Pull exception: $_"
        }
        $attempt++
        if ($attempt -le $MaxRetries) {
            Write-Info "Retrying in 3s..."
            Start-Sleep 3
        }
    }
    return $false
}

function Update-Project {
    Write-Sep "Check Updates"
    Set-Location $Script:ProjectRoot

    # Set git timeout settings
    git config --global http.lowSpeedLimit 1000 2>$null
    git config --global http.lowSpeedTime 10 2>$null

    # Setup mirror for China
    $region = Get-Region
    if ($region -eq "china") {
        Write-Info "China detected, using GitHub mirror..."
        git config --global url."https://ghproxy.com/https://github.com/".insteadOf "https://github.com/" 2>$null
    }

    try {
        Write-Info "Fetching remote info..."
        $fetchJob = Start-Job -ScriptBlock {
            param($dir)
            Set-Location $dir
            git fetch origin main 2>&1
        } -ArgumentList $Script:ProjectRoot
        $fetchResult = Wait-Job -Job $fetchJob -Timeout 30
        if (-not $fetchResult) {
            Remove-Job -Job $fetchJob -Force -ErrorAction SilentlyContinue
            Write-Warn "Fetch timed out, trying mirror..."
            git config --global url."https://ghproxy.com/https://github.com/".insteadOf "https://github.com/" 2>$null
            $fetchJob2 = Start-Job -ScriptBlock {
                param($dir)
                Set-Location $dir
                git fetch origin main 2>&1
            } -ArgumentList $Script:ProjectRoot
            $fetchResult2 = Wait-Job -Job $fetchJob2 -Timeout 30
            Remove-Job -Job $fetchJob2 -Force -ErrorAction SilentlyContinue
            if (-not $fetchResult2) {
                Write-Err "Cannot reach GitHub, check network"
                return $false
            }
        } else {
            Remove-Job -Job $fetchJob -Force -ErrorAction SilentlyContinue
        }

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
        if (Invoke-GitPull) {
            Write-OK "Update complete, restart services"
            return $true
        }

        # Fallback: try mirror if not already using it
        if ($region -ne "china") {
            Write-Warn "Direct pull failed, trying GitHub mirror..."
            git config --global url."https://ghproxy.com/https://github.com/".insteadOf "https://github.com/" 2>$null
            if (Invoke-GitPull -MaxRetries 2) {
                Write-OK "Updated via mirror"
                return $true
            }
        }

        # Last resort: fetch + reset
        Write-Warn "Trying fetch + reset..."
        $resetJob = Start-Job -ScriptBlock {
            param($dir)
            Set-Location $dir
            git fetch origin main 2>&1
            git reset --hard origin/main 2>&1
        } -ArgumentList $Script:ProjectRoot
        $resetResult = Wait-Job -Job $resetJob -Timeout 30
        Remove-Job -Job $resetJob -Force -ErrorAction SilentlyContinue
        if ($resetResult) {
            Write-OK "Updated via fetch+reset"
            return $true
        }

        Write-Err "All methods failed. Try manually:"
        Write-Info '  git config --global url."https://ghproxy.com/https://github.com/".insteadOf "https://github.com/"'
        Write-Info "  git pull origin main"
        return $false
    } catch {
        Write-Warn "Update failed: $_"
        return $false
    }
}

function Show-Logs {
    $backendLog = Join-Path $DataDir "logs\backend.log"
    Write-Host ""
    Write-Host "=== Backend log (last 30 lines) ===" -ForegroundColor Cyan
    if (Test-Path $backendLog) {
        Get-Content $backendLog -Tail 30
    } else {
        Write-Host "(no log)" -ForegroundColor Gray
    }
}

function Get-Status {
    Write-Host ""
    Write-Host "=== Service status ===" -ForegroundColor Cyan
    $backendOk = $false
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        $backendOk = ($resp.StatusCode -eq 200)
    } catch {}
    if ($backendOk) { Write-OK "Backend: running" } else { Write-Err "Backend: stopped" }
    if (Test-Port 6379) { Write-OK "Redis: running" } else { Write-Info "Redis: not running" }
}

function Full-Install {
    Write-Sep "Novel Reader Setup"
    Set-Policy
    Init-Dirs
    Init-Env
    if (-not (Install-Python)) { return }
    $redisMode = Get-RedisMode
    Start-Redis -Mode $redisMode
    if (-not (Install-PythonDeps)) { return }
    Write-Sep "Start Services"
    Start-Redis -Mode $redisMode
    $backendOk = Start-Backend
    Write-Host ""
    Write-Host "===================================" -ForegroundColor Green
    if ($backendOk) {
        Write-Host "  All services started!" -ForegroundColor Green
    } else {
        Write-Host "      Some services failed" -ForegroundColor Yellow
    }
    Write-Host "===================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  App: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "  API docs: http://localhost:8000/docs" -ForegroundColor Cyan
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
            git config --global http.lowSpeedLimit 1000 2>$null
            git config --global http.lowSpeedTime 10 2>$null
            $fetchJob = Start-Job -ScriptBlock {
                param($dir)
                Set-Location $dir
                git fetch origin main 2>&1
            } -ArgumentList $Script:ProjectRoot
            $fetchDone = Wait-Job -Job $fetchJob -Timeout 15
            Remove-Job -Job $fetchJob -Force -ErrorAction SilentlyContinue
            if ($fetchDone) {
                $behind = git rev-list HEAD..origin/main --count 2>$null
                if ($behind -gt 0) {
                    Write-Warn "Found $behind update(s)"
                    $u = Read-Host "Update now? (y/n)"
                    if ($u -eq "y" -or $u -eq "Y") { Update-Project }
                }
            } else {
                Write-Warn "Update check timed out, skipping"
            }
        } catch {
            Write-Warn "Update check failed, skipping"
        }
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
