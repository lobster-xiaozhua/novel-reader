# Novel Reader - Windows 部署脚本
param(
    [switch]$Docker,
    [switch]$WSL,
    [switch]$Native,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

function Write-Header {
    param([string]$Text)
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host " $Text" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
}

function Write-Success { param([string]$Text) Write-Host "[OK] $Text" -ForegroundColor Green }
function Write-Info { param([string]$Text) Write-Host "[INFO] $Text" -ForegroundColor Yellow }
function Write-Err { param([string]$Text) Write-Host "[ERROR] $Text" -ForegroundColor Red }

function Test-Command {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

function Deploy-Docker {
    Write-Header "使用 Docker Desktop 部署"
    if (-not (Test-Command "docker")) { Write-Err "Docker 未安装"; return $false }
    Write-Success "Docker: $(docker --version)"
    $composeCmd = if (Test-Command "docker compose") { "docker compose" } else { "docker-compose" }
    if (-not (Test-Path "$ProjectRoot\.env")) {
        $envExample = "$ProjectRoot\.env.example"
        if (Test-Path $envExample) { Copy-Item $envExample "$ProjectRoot\.env"; Write-Success "已创建 .env 文件" }
    }
    & $composeCmd up -d --build
    if ($LASTEXITCODE -eq 0) { Write-Success "服务启动成功!"; return $true }
    return $false
}

function Deploy-Native {
    Write-Header "原生 Python 部署"
    $pythonCmd = if (Test-Command "python3") { "python3" } else { "python" }
    if (-not (Test-Command $pythonCmd)) { Write-Err "Python 未安装"; return $false }
    Write-Success "Python: $(&$pythonCmd --version)"
    $venvPath = "$ProjectRoot\venv"
    if (-not (Test-Path $venvPath)) { & $pythonCmd -m venv $venvPath; Write-Success "虚拟环境已创建" }
    & "$venvPath\Scripts\Activate.ps1"
    python -m pip install --upgrade pip
    python -m pip install -r "$ProjectRoot\backend\requirements.txt"
    Write-Success "依赖安装完成"
    @("books", "index", "static", "logs", "cache") | ForEach-Object { New-Item -ItemType Directory -Path "$ProjectRoot\data\$_" -Force | Out-Null }
    return $true
}

function Main {
    Write-Host "`n  ╔═══════════════════════════════════╗" -ForegroundColor Magenta
    Write-Host "  ║   Novel Reader 部署脚本 (Windows)  ║" -ForegroundColor Magenta
    Write-Host "  ╚═══════════════════════════════════╝" -ForegroundColor Magenta
    if ($Help) { Write-Host @"
用法: .\deploy.ps1 [选项]
  -Docker    使用 Docker Desktop 部署
  -WSL       使用 WSL2 + Docker 部署
  -Native    原生 Python 部署
  -Help      显示帮助
"@; return }
    if (-not $Docker -and -not $WSL -and -not $Native) {
        if (Test-Command "docker") { $Docker = $true } else { $Native = $true }
    }
    if ($Docker) { $result = Deploy-Docker }
    elseif ($Native) { $result = Deploy-Native }
    if ($result) { Write-Header "部署完成!" } else { Write-Header "部署失败"; exit 1 }
}
Main
