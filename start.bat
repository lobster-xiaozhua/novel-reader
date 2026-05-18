@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "VERSION=1.0.0"
set "PROJECT_NAME=Novel Reader"

cd /d "%~dp0"

:: Colors
call :init_colors

:main
    if "%~1"=="" goto :cmd_start
    if /i "%~1"=="start" goto :cmd_start
    if /i "%~1"=="stop" goto :cmd_stop
    if /i "%~1"=="restart" goto :cmd_restart
    if /i "%~1"=="status" goto :cmd_status
    if /i "%~1"=="migrate" goto :cmd_migrate
    if /i "%~1"=="createsuperuser" goto :cmd_createsuperuser
    if /i "%~1"=="shell" goto :cmd_shell
    if /i "%~1"=="help" goto :show_help
    if /i "%~1"=="--help" goto :show_help
    if /i "%~1"=="-h" goto :show_help
    call :log_error "未知命令: %~1"
    goto :show_help

:show_help
    call :print_banner
    echo.
    echo 用法: start.bat [command]
    echo.
    echo 命令:
    echo   start           启动项目（默认）
    echo   stop            停止服务
    echo   restart         重启服务
    echo   status          查看服务状态
    echo   migrate         执行数据库迁移
    echo   createsuperuser 创建超级用户
    echo   shell           进入 Django shell
    echo   help            显示此帮助
    echo.
    echo 示例:
    echo   start.bat start     启动服务
    echo   start.bat stop      停止服务
    echo   start.bat migrate   数据库迁移
    echo.
    goto :eof

:print_banner
    echo.
    echo %MAGENTA%╔═══════════════════════════════════════════════════╗%RESET%
    echo %MAGENTA%║%RESET%  %CYAN%Novel Reader - Django 小说阅读器%RESET%                %MAGENTA%║%RESET%
    echo %MAGENTA%╚═══════════════════════════════════════════════════╝%RESET%
    echo.
    goto :eof

:cmd_start
    call :print_banner
    call :check_env
    call :install_deps
    call :migrate_db
    call :create_superuser

    call :log_step "启动 Django 开发服务器..."
    echo.
    echo %GREEN%═══════════════════════════════════════════════════%RESET%
    echo %GREEN%  服务已启动!%RESET%
    echo %GREEN%═══════════════════════════════════════════════════%RESET%
    echo.
    echo   %GREEN%📖%RESET% 访问地址:  http://localhost:8000
    echo   %GREEN%🔧%RESET% Admin 后台: http://localhost:8000/admin
    echo   %GREEN%👤%RESET% 默认账号:  admin / admin123
    echo.
    echo %YELLOW%按 Ctrl+C 停止服务%RESET%
    echo.

    venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
    goto :eof

:cmd_stop
    call :log_step "停止服务..."
    taskkill /F /IM python.exe 2>nul
    call :log_success "服务已停止"
    goto :eof

:cmd_restart
    call :cmd_stop
    timeout /t 1 /nobreak >nul
    call :cmd_start
    goto :eof

:cmd_status
    call :log_step "服务状态"
    tasklist /FI "IMAGENAME eq python.exe" 2>nul | findstr "python.exe" >nul
    if %errorlevel%==0 (
        call :log_success "Django 服务: 运行中"
    ) else (
        call :log_error "Django 服务: 未运行"
    )
    goto :eof

:cmd_migrate
    call :check_env
    call :install_deps
    call :migrate_db
    goto :eof

:cmd_createsuperuser
    call :check_env
    call :install_deps
    venv\Scripts\python.exe manage.py createsuperuser
    goto :eof

:cmd_shell
    call :check_env
    call :install_deps
    venv\Scripts\python.exe manage.py shell
    goto :eof

:check_env
    call :log_step "检查环境..."
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        call :log_error "Python 未安装"
        exit /b 1
    )
    call :log_success "Python 已安装"
    goto :eof

:install_deps
    call :log_step "安装依赖..."
    if not exist "venv" (
        python -m venv venv
        call :log_success "虚拟环境已创建"
    )
    venv\Scripts\pip.exe install -q --upgrade pip
    venv\Scripts\pip.exe install -q -r requirements.txt
    call :log_success "依赖安装完成"
    goto :eof

:migrate_db
    call :log_step "执行数据库迁移..."
    venv\Scripts\python.exe manage.py migrate
    call :log_success "数据库迁移完成"
    goto :eof

:create_superuser
    call :log_step "创建超级用户..."
    venv\Scripts\python.exe manage.py shell -c "from django.contrib.auth.models import User; import sys; sys.exit(0 if User.objects.filter(username='admin').exists() else 1)" 2>nul
    if %errorlevel% neq 0 (
        venv\Scripts\python.exe manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123'); print('Superuser created: admin / admin123')" 2>nul
        call :log_success "超级用户已创建: admin / admin123"
    ) else (
        call :log_info "超级用户已存在"
    )
    goto :eof

:init_colors
    set "RED=[31m"
    set "GREEN=[32m"
    set "YELLOW=[33m"
    set "BLUE=[34m"
    set "CYAN=[36m"
    set "MAGENTA=[35m"
    set "RESET=[0m"
    goto :eof

:log_info
    echo %BLUE%[INFO]%RESET% %~1
    goto :eof

:log_success
    echo %GREEN%[✓]%RESET% %~1
    goto :eof

:log_warning
    echo %YELLOW%[⚠]%RESET% %~1
    goto :eof

:log_error
    echo %RED%[✗]%RESET% %~1
    goto :eof

:log_step
    echo %CYAN%[→]%RESET% %~1
    goto :eof
