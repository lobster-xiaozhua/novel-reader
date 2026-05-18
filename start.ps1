# Novel Reader - Django 小说阅读器 (Windows PowerShell)
# 用法: .\start.ps1 [command]

param(
    [string]$Command = "start"
)

$VERSION = "1.0.0"

function Write-Log { param($type, $msg)
    $color = switch ($type) {
        "info" { "Cyan" }
        "success" { "Green" }
        "warning" { "Yellow" }
        "error" { "Red" }
        "step" { "Magenta" }
    }
    Write-Host "[$($type.ToUpper())] $msg" -ForegroundColor $color
}

function Show-Banner {
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════╗" -ForegroundColor Magenta
    Write-Host "║  Novel Reader - Django 小说阅读器               ║" -ForegroundColor Magenta
    Write-Host "╚═══════════════════════════════════════════════════╝" -ForegroundColor Magenta
    Write-Host ""
}

function Show-Help {
    Show-Banner
    @"
用法: .\start.ps1 [command]

命令:
  start           启动项目（默认）
  stop            停止服务
  restart         重启服务
  status          查看服务状态
  migrate         执行数据库迁移
  createsuperuser 创建超级用户
  shell           进入 Django shell
  help            显示此帮助

示例:
  .\start.ps1 start      启动服务
  .\start.ps1 stop       停止服务
  .\start.ps1 migrate    数据库迁移
"@
}

function Test-Environment {
    Write-Log "step" "检查环境..."
    try {
        $pyVersion = python --version 2>&1
        Write-Log "success" "Python: $pyVersion"
    } catch {
        Write-Log "error" "Python 未安装"
        exit 1
    }
}

function Install-Dependencies {
    Write-Log "step" "安装依赖..."
    if (-not (Test-Path "venv")) {
        python -m venv venv
        Write-Log "success" "虚拟环境已创建"
    }
    .\venv\Scripts\pip.exe install -q --upgrade pip
    .\venv\Scripts\pip.exe install -q -r requirements.txt
    Write-Log "success" "依赖安装完成"
}

function Invoke-Migrate {
    Write-Log "step" "执行数据库迁移..."
    .\venv\Scripts\python.exe manage.py migrate
    Write-Log "success" "数据库迁移完成"
}

function New-SuperUser {
    Write-Log "step" "创建超级用户..."
    $exists = .\venv\Scripts\python.exe manage.py shell -c "from django.contrib.auth.models import User; print(User.objects.filter(username='admin').exists())" 2>$null
    if ($exists -ne "True") {
        .\venv\Scripts\python.exe manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123'); print('Superuser created: admin / admin123')" 2>$null
        Write-Log "success" "超级用户已创建: admin / admin123"
    } else {
        Write-Log "info" "超级用户已存在"
    }
}

function Start-Server {
    Show-Banner
    Test-Environment
    Install-Dependencies
    Invoke-Migrate
    New-SuperUser

    Write-Log "step" "启动 Django 开发服务器..."
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  服务已启动!" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "  📖 访问地址:  http://localhost:8000" -ForegroundColor Green
    Write-Host "  🔧 Admin 后台: http://localhost:8000/admin" -ForegroundColor Green
    Write-Host "  👤 默认账号:  admin / admin123" -ForegroundColor Green
    Write-Host ""
    Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Yellow
    Write-Host ""

    .\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
}

function Stop-Server {
    Write-Log "step" "停止服务..."
    Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Log "success" "服务已停止"
}

function Get-Status {
    Write-Log "step" "服务状态"
    $proc = Get-Process python -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Log "success" "Django 服务: 运行中"
    } else {
        Write-Log "error" "Django 服务: 未运行"
    }
}

switch ($Command) {
    "start" { Start-Server }
    "stop" { Stop-Server }
    "restart" { Stop-Server; Start-Sleep -Seconds 1; Start-Server }
    "status" { Get-Status }
    "migrate" { Test-Environment; Install-Dependencies; Invoke-Migrate }
    "createsuperuser" { Test-Environment; Install-Dependencies; .\venv\Scripts\python.exe manage.py createsuperuser }
    "shell" { Test-Environment; Install-Dependencies; .\venv\Scripts\python.exe manage.py shell }
    "help" { Show-Help }
    default { Write-Log "error" "未知命令: $Command"; Show-Help }
}
