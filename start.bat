@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1

cd /d "%~dp0"

set "RED=[31m"
set "GREEN=[32m"
set "YELLOW=[33m"
set "BLUE=[34m"
set "CYAN=[36m"
set "MAGENTA=[35m"
set "NC=[0m"
set "BOLD=[1m"
set "DIM=[2m"

goto :main

:print_banner
echo.
echo %MAGENTA%╔═══════════════════════════════════════════════════╗%NC%
echo %MAGENTA%║%NC%  %CYAN%Novel Reader v2.0 - 高性能小说阅读器%NC%        %MAGENTA%║%NC%
echo %MAGENTA%╚═══════════════════════════════════════════════════╝%NC%
echo.
goto :eof

:log_info
echo %BLUE%[INFO]%NC% %~1
goto :eof

:log_success
echo %GREEN%[✓]%NC% %~1
goto :eof

:log_warning
echo %YELLOW%[⚠]%NC% %~1
goto :eof

:log_error
echo %RED%[✗]%NC% %~1
goto :eof

:log_step
echo %CYAN%[→]%NC% %~1
goto :eof

:show_help
call :print_banner
echo 用法: start.bat [command]
echo.
echo 命令:
echo   start      启动项目（默认）
echo   stop       停止服务
echo   restart    重启服务
echo   status     查看服务状态
echo   migrate    执行数据库迁移
echo   build      构建前端
echo   dev        开发模式（前后端分离）
echo   help       显示此帮助
echo.
echo 示例:
echo   start.bat start          启动生产服务
echo   start.bat dev            开发模式
echo   start.bat build          构建前端
goto :eof

:check_env
call :log_step "检查环境..."
set "errors=0"

python --version >nul 2>&1
if errorlevel 1 (
    call :log_error "Python 未安装或未添加到 PATH"
    set /a errors+=1
) else (
    for /f "tokens=*" %%a in ('python --version 2^>^&1') do call :log_success "Python: %%a"
)

node --version >nul 2>&1
if errorlevel 1 (
    call :log_error "Node.js 未安装或未添加到 PATH"
    set /a errors+=1
) else (
    for /f %%a in ('node --version') do call :log_success "Node: %%a"
)

if !errors! gtr 0 (
    call :log_error "环境检查失败"
    exit /b 1
)
call :log_success "环境检查通过"
goto :eof

:draw_progress
set "pkg=%~1"
set "current=%~2"
set "total=%~3"
set "status=%~4"
set "width=30"
set /a filled=current*width/total
set /a empty=width-filled
set "bar="
for /l %%i in (1,1,!filled!) do set "bar=!bar!█"
for /l %%i in (1,1,!empty!) do set "bar=!bar!░"
set /a pct=current*100/total
if "!status!"=="done" (
    echo %GREEN%  ✓%NC% %-30s [%GREEN%!bar!%NC%] !pct!%% %DIM%已完成%NC%
) else (
    echo %CYAN%  →%NC% %-30s [%CYAN%!bar!%NC%] !pct!%% %YELLOW%下载中...%NC%
)
goto :eof

:install_python_deps
call :log_step "安装 Python 依赖..."
call :log_info "使用阿里云 PyPI 镜像..."
call venv\Scripts\activate.bat

pip install -q --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ >nul 2>&1

set "pkg_list=Django granian whitenoise django-environ django-unfold django-ninja pydantic redis celery requests beautifulsoup4 tenacity httpx orjson django-cors-headers pytest pytest-django pytest-cov ruff django-debug-toolbar"
set "pkg_total=0"
for %%p in (!pkg_list!) do set /a pkg_total+=1

set "pkg_idx=0"
set "pkg_failed=0"
for %%p in (!pkg_list!) do (
    set /a pkg_idx+=1
    call :draw_progress "%%p" !pkg_idx! !pkg_total! downloading
    pip install -q "%%p" -i https://mirrors.aliyun.com/pypi/simple/ >nul 2>&1
    if errorlevel 1 (
        call :log_error "  ✗ %%p 安装失败"
        set /a pkg_failed+=1
    ) else (
        call :draw_progress "%%p" !pkg_idx! !pkg_total! done
    )
)
if !pkg_failed! gtr 0 (
    call :log_warning "Python 依赖安装完成 (!pkg_total! 个包, !pkg_failed! 个失败)"
) else (
    call :log_success "Python 依赖安装完成 (!pkg_total! 个包)"
)
goto :eof

:install_node_deps
call :log_step "安装 Node 依赖..."
call :log_info "使用阿里云 npm 镜像..."
cd frontend

if exist "node_modules" (
    cd ..
    call :log_success "Node 依赖已存在，跳过安装"
    goto :eof
)

set "pkg_list=@tailwindcss/vite @tanstack/react-query axios lucide-react react react-dom react-markdown react-router-dom react-syntax-highlighter recharts rehype-highlight remark-gfm tailwindcss zustand @eslint/js @types/node @types/react @types/react-dom @types/react-syntax-highlighter @vitejs/plugin-react eslint eslint-plugin-react-hooks eslint-plugin-react-refresh globals typescript typescript-eslint vite"
set "pkg_total=0"
for %%p in (!pkg_list!) do set /a pkg_total+=1

set "pkg_idx=0"
set "pkg_failed=0"
for %%p in (!pkg_list!) do (
    set /a pkg_idx+=1
    call :draw_progress "%%p" !pkg_idx! !pkg_total! downloading
    npm install "%%p" --registry https://registry.npmmirror.com --no-save --no-package-lock >nul 2>&1
    if errorlevel 1 (
        call :log_error "  ✗ %%p 安装失败"
        set /a pkg_failed+=1
    ) else (
        call :draw_progress "%%p" !pkg_idx! !pkg_total! done
    )
)
cd ..
if !pkg_failed! gtr 0 (
    call :log_warning "Node 依赖安装完成 (!pkg_total! 个包, !pkg_failed! 个失败)"
) else (
    call :log_success "Node 依赖安装完成 (!pkg_total! 个包)"
)
goto :eof

:install_deps
call :log_step "安装依赖..."
if not exist "venv" (
    python -m venv venv
    call :log_success "虚拟环境已创建"
)
call :install_python_deps
if exist "frontend\package.json" (
    call :install_node_deps
)
goto :eof

:migrate_db
call :log_step "执行数据库迁移..."
call venv\Scripts\activate.bat
python manage.py migrate
call :log_success "数据库迁移完成"
goto :eof

:create_superuser
call :log_step "创建超级用户..."
call venv\Scripts\activate.bat
python -c "import pathlib;p=pathlib.Path('create_superuser_tmp.py');p.write_text('from django.contrib.auth.models import User\nimport secrets,string\nif not User.objects.filter(username=\"admin\").exists():\n    pwd=\"\".join(secrets.choice(string.ascii_letters+string.digits) for _ in range(16))\n    User.objects.create_superuser(\"admin\",\"admin@example.com\",pwd)\n    print(f\"Superuser created: admin / {pwd}\")\n    print(\"请妥善保存此密码！\")\nelse:\n    print(\"Superuser admin already exists\")\n');print('ok')"
if exist "create_superuser_tmp.py" (
    python manage.py shell create_superuser_tmp.py 2>nul || (
        call :log_warning "超级用户创建跳过"
    )
    del create_superuser_tmp.py 2>nul
) else (
    call :log_warning "超级用户创建跳过"
)
goto :eof

:build_frontend
call :log_step "构建前端..."
cd frontend
call npm run build
cd ..
call :log_success "前端构建完成"
goto :eof

:cmd_start
call :print_banner
call :check_env
call :install_deps
call :migrate_db
call :create_superuser
call :build_frontend

call venv\Scripts\activate.bat
python manage.py collectstatic --noinput 2>nul || (
    call :log_warning "静态文件收集跳过"
)

call :log_step "启动 Granian ASGI 服务器..."
echo.
echo %GREEN%═══════════════════════════════════════════════════%NC%
echo %GREEN%  服务已启动!%NC%
echo %GREEN%═══════════════════════════════════════════════════%NC%
echo.
echo   %GREEN%📖%NC% 访问地址:  http://localhost:8000
echo   %GREEN%🔧%NC% Admin 后台: http://localhost:8000/admin
echo   %GREEN%📋%NC% API 文档:   http://localhost:8000/api/v1/docs/
echo.
echo %YELLOW%按 Ctrl+C 停止服务%NC%
echo.

granian novel_reader.asgi:application --host 0.0.0.0 --port 8000 --interface asgi --workers 1
goto :eof

:cmd_dev
call :print_banner
call :check_env
call :install_deps
call :migrate_db
call :create_superuser

for /f "tokens=3" %%m in ('systeminfo ^| findstr /C:"可用的物理内存" /C:"Available Physical Memory" 2^>nul') do (
    for /f "tokens=1" %%v in ("%%m") do set "mem_mb=%%v"
)
if defined mem_mb (
    set "mem_mb=!mem_mb:,=!"
    set "mem_mb=!mem_mb: =!"
    if !mem_mb! lss 1500 (
        call :log_warning "可用内存 !mem_mb!MB，不足同时运行 Django + Vite"
        call :log_step "切换为低内存模式：构建前端 → 启动后端"
        call :build_frontend
        call venv\Scripts\activate.bat
        python manage.py collectstatic --noinput 2>nul || (
            call :log_warning "静态文件收集跳过"
        )

        echo.
        echo %GREEN%═══════════════════════════════════════════════════%NC%
        echo %GREEN%  低内存开发模式启动!%NC%
        echo %GREEN%═══════════════════════════════════════════════════%NC%
        echo.
        echo   %GREEN%📖%NC% 访问地址: http://localhost:8000
        echo   %YELLOW%⚠%NC%  前端变更需重新 %CYAN%start.bat build%NC%
        echo.

        granian novel_reader.asgi:application --host 0.0.0.0 --port 8000 --interface asgi --workers 1
        goto :eof
    )
)

call :log_step "启动开发模式..."
echo.
echo %GREEN%═══════════════════════════════════════════════════%NC%
echo %GREEN%  开发模式启动!%NC%
echo %GREEN%═══════════════════════════════════════════════════%NC%
echo.
echo   %GREEN%📖%NC% 前端: http://localhost:5173
echo   %GREEN%🔧%NC% 后端: http://localhost:8000
echo.

start /b cmd /c "call venv\Scripts\activate.bat && python manage.py runserver 0.0.0.0:8000"
cd frontend && npm run dev
goto :eof

:cmd_stop
call :log_step "停止服务..."
taskkill /F /IM "granian.exe" 2>nul
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq *manage.py*" 2>nul
taskkill /F /IM "node.exe" /FI "WINDOWTITLE eq *vite*" 2>nul
call :log_success "服务已停止"
goto :eof

:cmd_status
call :log_step "服务状态"
tasklist /FI "IMAGENAME eq granian.exe" 2>nul | find "granian.exe" >nul
if not errorlevel 1 (
    call :log_success "Granian 服务: 运行中"
    for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq granian.exe" /NH') do echo   PID: %%a
    echo   地址: http://localhost:8000
) else (
    tasklist /FI "WINDOWTITLE eq *manage.py*" 2>nul | find "python.exe" >nul
    if not errorlevel 1 (
        call :log_success "Django 开发服务器: 运行中"
        echo   地址: http://localhost:8000
    ) else (
        call :log_error "服务: 未运行"
    )
)
goto :eof

:cmd_migrate
call :check_env
call :install_deps
call :migrate_db
goto :eof

:cmd_build
call :check_env
call :install_deps
call :build_frontend
call venv\Scripts\activate.bat
python manage.py collectstatic --noinput 2>nul || (
    call :log_warning "静态文件收集跳过"
)
call :log_success "构建完成"
goto :eof

:main
set "command=%~1"
if "%command%"=="" set "command=start"

if "%command%"=="start" goto :cmd_start
if "%command%"=="dev" goto :cmd_dev
if "%command%"=="stop" goto :cmd_stop
if "%command%"=="restart" (
    call :cmd_stop
    timeout /t 1 /nobreak >nul
    goto :cmd_start
)
if "%command%"=="status" goto :cmd_status
if "%command%"=="migrate" goto :cmd_migrate
if "%command%"=="build" goto :cmd_build
if "%command%"=="help" goto :show_help
if "%command%"=="--help" goto :show_help
if "%command%"=="-h" goto :show_help

call :log_error "未知命令: %command%"
call :show_help
exit /b 1