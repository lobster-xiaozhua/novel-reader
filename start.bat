@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

set RED=[91m
set GREEN=[92m
set YELLOW=[93m
set BLUE=[94m
set CYAN=[96m
set MAGENTA=[95m
set NC=[0m
set DIM=[2m
set BOLD=[1m

set STEP_NUM=0
set TOTAL_STEPS=6

:log_info
echo.   %BLUE%i %NC% %~1
goto :eof

:log_success
echo.   %GREEN%v %NC% %~1
goto :eof

:log_warn
echo.   %YELLOW%! %NC% %~1
goto :eof

:log_error
echo.   %RED%x %NC% %~1
goto :eof

:log_detail
echo.   %DIM%-> %~1%NC%
goto :eof

:log_step
set /a STEP_NUM+=1
echo.
echo %BOLD%%CYAN%[%STEP_NUM%/%TOTAL_STEPS%]%NC% %BOLD%%~1%NC%
goto :eof

:step_done
echo.   %GREEN%v %NC% %DIM%done%NC%
goto :eof

:print_banner
echo.
echo %MAGENTA%=========================================%NC%
echo %MAGENTA%%NC%  %CYAN%Novel Reader v2.0 - High Performance%NC%  %MAGENTA%%NC%
echo %MAGENTA%=========================================%NC%
goto :eof

:show_help
echo.
echo Usage: start.bat ^<command^>
echo.
echo Commands:
echo   start      Start the project (default)
echo   stop       Stop services
echo   restart    Restart services
echo   status     Show service status
echo   migrate    Run database migrations
echo   build      Build frontend
echo   dev        Development mode
echo   help       Show this help
goto :eof

:check_env
call :log_step "Environment check"
set errors=0

python --version >nul 2>&1
if errorlevel 1 (
    call :log_error "Python3 not installed"
    set /a errors+=1
) else (
    call :log_success "Python OK"
)

node --version >nul 2>&1
if errorlevel 1 (
    call :log_error "Node.js not installed"
    set /a errors+=1
) else (
    call :log_success "Node.js OK"
)

if %errors% gtr 0 (
    call :log_error "Environment check failed"
    exit /b 1
)
call :step_done
goto :eof

:install_python_deps
if not exist "requirements.txt" (
    call :log_error "requirements.txt not found"
    exit /b 1
)

if not exist "venv" (
    python -m venv venv
    call :log_success "Virtual environment created"
)

call venv\Scripts\activate.bat
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
if errorlevel 1 (
    call :log_error "pip install failed"
    exit /b 1
)
goto :eof

:install_node_deps
if not exist "frontend\package.json" (
    goto :eof
)
if exist "frontend\node_modules\react" (
    call :log_success "Node deps already installed"
    goto :eof
)
cd frontend
npm install --registry https://registry.npmmirror.com
if errorlevel 1 (
    cd ..
    call :log_error "npm install failed"
    exit /b 1
)
cd ..
goto :eof

:install_deps
call :log_step "Installing dependencies"
call :install_python_deps
call :install_node_deps
call :step_done
goto :eof

:migrate_db
call :log_step "Database migration"
call venv\Scripts\activate.bat
python manage.py migrate
if errorlevel 1 (
    call :log_error "Migration failed"
    exit /b 1
)
call :step_done
goto :eof

:create_superuser
call :log_step "Initialize admin"
call venv\Scripts\activate.bat
for /f "tokens=*" %%r in ('python manage.py shell -c "from django.contrib.auth.models import User; print('EXISTS' if User.objects.filter(username='admin').exists() else 'CREATE')" 2^>^&1') do set result=%%r
if "%result%"=="CREATE" (
    for /f "tokens=*" %%p in ('python -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16)))"') do set pwd=%%p
    python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', '%pwd%')"
    call :log_success "Admin: admin / %pwd%"
) else (
    call :log_success "Admin already exists"
)
call :step_done
goto :eof

:build_frontend
call :log_step "Building frontend"
if not exist "frontend\node_modules\react" (
    call :install_node_deps
)
cd frontend
npm run build
if errorlevel 1 (
    cd ..
    call :log_error "Frontend build failed"
    exit /b 1
)
cd ..
call :step_done
goto :eof

:start_server
set port=%~1
if "%port%"=="" set port=8000
call venv\Scripts\activate.bat
call :log_step "Starting server"
python manage.py collectstatic --noinput >nul 2>&1
echo.
echo %GREEN%=========================================%NC%
echo %GREEN%  Service started!%NC%
echo %GREEN%=========================================%NC%
echo   Visit: %BOLD%http://localhost:%port%%NC%
echo   Admin: http://localhost:%port%/admin
echo   API:   http://localhost:%port%/api/v1/docs/
echo.
granian novel_reader.asgi:application --host 0.0.0.0 --port %port% --interface asgi --workers 1
goto :eof

:cmd_start
call :print_banner
call :check_env
call :install_deps
call :migrate_db
call :create_superuser
call :build_frontend
call :start_server 8000
goto :eof

:cmd_dev
set TOTAL_STEPS=4
call :print_banner
call :check_env
call :install_deps
call :migrate_db
call :create_superuser
start "Django" cmd /k "call venv\Scripts\activate.bat && python manage.py runserver 0.0.0.0:8000"
cd frontend
npm run dev
goto :eof

:cmd_stop
call :log_step "Stopping services"
for /f "tokens=2" %%p in ('tasklist ^| findstr /i "python.exe node.exe"') do (
    taskkill /f /pid %%p >nul 2>&1
)
call :log_success "Services stopped"
goto :eof

:cmd_status
call :log_step "Service status"
tasklist | findstr /i "python.exe" >nul 2>&1
if not errorlevel 1 (
    call :log_success "Python services running"
) else (
    call :log_warn "No services running"
)
goto :eof

:cmd_migrate
set TOTAL_STEPS=3
call :check_env
call :install_deps
call :migrate_db
goto :eof

:cmd_build
set TOTAL_STEPS=3
call :check_env
call :install_deps
call :build_frontend
call venv\Scripts\activate.bat
python manage.py collectstatic --noinput
call :step_done
call :log_success "Build complete"
goto :eof

:main
set command=%~1
if "%command%"=="" set command=start

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

call :log_error "Unknown command: %command%"
goto :show_help

call :main %*
