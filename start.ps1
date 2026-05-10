# Novel Reader 一键启动脚本 (Windows PowerShell)
param([string]$Command = "")

$Red="Red";$Green="Green";$Yellow="Yellow";$Blue="Cyan";$Cyan="Cyan"

function Print-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor $Blue }
function Print-Success($msg) { Write-Host "[OK] $msg" -ForegroundColor $Green }
function Print-Warning($msg) { Write-Host "[WARN] $msg" -ForegroundColor $Yellow }
function Print-Error($msg) { Write-Host "[ERROR] $msg" -ForegroundColor $Red }
function Print-Header($msg) {
    Write-Host ""
    Write-Host "════════════════════════════════════════════" -ForegroundColor $Cyan
    Write-Host "  $msg" -ForegroundColor $Cyan
    Write-Host "════════════════════════════════════════════" -ForegroundColor $Cyan
}

function Get-Region {
    try {
        $r = Invoke-WebRequest -Uri "https://ipinfo.io/country" -UseBasicParsing -TimeoutSec 3
        if ($r.Content -eq "CN") { return "china" }
    } catch {}
    return "global"
}

function Set-Mirrors {
    Print-Header "配置镜像源"
    $region = Get-Region
    
    if ($region -eq "china") {
        Print-Info "检测到中国地区，配置国内镜像源..."
        
        Print-Info "━━━ Python pip ━━━"
        $pipDir = "$env:APPDATA\pip"
        if (-not (Test-Path $pipDir)) { New-Item -ItemType Directory -Force -Path $pipDir | Out-Null }
        @"
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
timeout = 60
[install]
trusted-host = mirrors.aliyun.com
"@ | Out-File -Path "$pipDir\pip.ini" -Encoding UTF8
        Print-Success "pip 镜像: 阿里云"
        
        Print-Info "━━━ Node.js npm ━━━"
        npm config set registry https://registry.npmmirror.com
        Print-Success "npm 镜像: 淘宝镜像"
        
        Print-Info "━━━ Docker ━━━"
        $dockerDir = "$env:USERPROFILE\.docker"
        if (-not (Test-Path $dockerDir)) { New-Item -ItemType Directory -Force -Path $dockerDir | Out-Null }
        @"
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
"@ | Out-File -Path "$dockerDir\daemon.json" -Encoding UTF8
        Print-Success "Docker 镜像加速已配置"
        Print-Info "请在 Docker Desktop 中重启 Docker"
    } else {
        Print-Info "检测到海外地区，使用官方源"
    }
    Print-Success "镜像源配置完成"
}

function New-DataDirectories {
    Print-Info "创建数据目录..."
    @("books","index","static","logs","cache") | % { New-Item -ItemType Directory -Force -Path "data\$_" | Out-Null }
    Print-Success "目录创建完成"
}

function Test-EnvFile {
    if (-not (Test-Path ".env")) {
        $key = -join ((65..90)+(97..122)+(48..57) | Get-Random -Count 32 | % { [char]$_ })
        @"
SECRET_KEY=$key
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://redis:6379
"@ | Out-File -FilePath ".env" -Encoding UTF8
        Print-Success ".env 文件已创建"
    }
}

function Start-All {
    Print-Header "启动 Novel Reader"
    New-DataDirectories
    Test-EnvFile
    docker-compose up -d redis,backend,frontend
    Print-Header "服务已启动"
    Write-Host "  📖 前端: http://localhost" -ForegroundColor $Green
    Write-Host "  🔧 API: http://localhost:8000/docs" -ForegroundColor $Green
}

function Stop-Services {
    Print-Header "停止服务"
    docker-compose down
    Print-Success "所有服务已停止"
}

function Set-Mirror { Set-Mirrors }
function Install-AllDeps {
    Print-Header "安装依赖"
    Set-Mirrors
    Print-Success "依赖安装完成"
}

switch ($Command) {
    "stop" { Stop-Services }
    "restart" { Stop-Services; Start-All }
    "mirror" { Set-Mirrors }
    "deps" { Install-AllDeps }
    "help" { Write-Host "命令: stop|restart|mirror|deps|help" }
    "" { Start-All }
    default { Print-Error "未知命令: $Command" }
}
