@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

cd /d "%~dp0"

:: ─── Colors (via PowerShell) ───
set "ESC="
for /f "delims=" %%i in ('powershell -NoProfile -Command "[char]27"') do set "ESC=%%i"

set "GREEN=!ESC![0;32m"
set "YELLOW=!ESC![1;33m"
set "RED=!ESC![0;31m"
set "BLUE=!ESC![0;34m"
set "CYAN=!ESC![0;36m"
set "MAGENTA=!ESC![0;35m"
set "DIM=!ESC![2m"
set "BOLD=!ESC![1m"
set "NC=!ESC![0m"

:: ─── Symbols (Unicode via PowerShell, ASCII fallback) ───
set "OK=[+]"
set "INFO=[i]"
set "WARN=[!]"
set "FAIL=[x]"
set "ARROW=->"
:: ─── Banner line (Unicode box drawing, ASCII fallback) ───
set "LINE============================================"
set "LCORNER=|"
set "RCORNER=|"
for /f "delims=" %%i in ('powershell -NoProfile -Command "([char]0x2550)*44" 2^>nul') do set "LINE=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "[char]0x2554" 2^>nul') do set "LCORNER=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "[char]0x2557" 2^>nul') do set "RCORNER=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "[char]0x2713" 2^>nul') do set "OK=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "[char]0x2139" 2^>nul') do set "INFO=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "[char]0x26A0" 2^>nul') do set "WARN=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "[char]0x2717" 2^>nul') do set "FAIL=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "[char]0x2192" 2^>nul') do set "ARROW=%%i"

set "STEP_NUM=0"
set "TOTAL_STEPS=8"

:: ─── Jump to main logic (skip subroutines) ───
goto :main_entry

:: ─── Logging ───
:log_info
echo   %BLUE%%INFO%%NC% %~1
goto :eof

:log_success
echo   %GREEN%%OK%%NC% %~1
goto :eof

:log_warn
echo   %YELLOW%%WARN%%NC% %~1
goto :eof

:log_error
echo   %RED%%FAIL%%NC% %~1
goto :eof

:log_detail
echo   %DIM%%ARROW% %~1%NC%
goto :eof

:log_step
set /a STEP_NUM+=1
echo.
echo %BOLD%%CYAN%[%STEP_NUM%/%TOTAL_STEPS%]%NC% %BOLD%%~1%NC%
set "_timer_start=%TIME%"
goto :eof

:step_done
echo   %GREEN%%OK%%NC% %DIM%Done%NC%
goto :eof

:: ─── Banner ───
:print_banner
echo.
echo %MAGENTA%!LCORNER!!LINE!!RCORNER!%NC%
echo %MAGENTA%^|%NC%  Novel Reader v2.0 - High-Performance Novel Reader    %MAGENTA%^|%NC%
echo %MAGENTA%^|%NC%  %DIM%PG + Redis + DiskCache + Liquid Glass UI%NC%       %MAGENTA%^|%NC%
echo %MAGENTA%!LCORNER!!LINE!!RCORNER!%NC%
echo.
goto :eof

:: ─── Infrastructure ───
:ensure_pg
:: 1. Check if PostgreSQL service is already running
net start > "%temp%\_pg_check.txt" 2>nul
findstr /i "postgresql" "%temp%\_pg_check.txt" >nul 2>&1
if %errorlevel%==0 (
    call :log_success "PostgreSQL is running"
    del "%temp%\_pg_check.txt" 2>nul
    goto :eof
)
del "%temp%\_pg_check.txt" 2>nul

:: 2. Try to find and start existing PostgreSQL service
call :log_info "PostgreSQL not running, searching for installation..."
set "pg_svc="
for /f "tokens=2 delims=:" %%a in ('sc query state^= all ^| findstr /i "postgresql" ^| findstr "SERVICE_NAME"') do (
    set "pg_svc=%%a"
)
if defined pg_svc (
    call :log_info "Starting PostgreSQL service..."
    net start "!pg_svc!" >nul 2>&1
    timeout /t 3 /nobreak >nul
    net start > "%temp%\_pg_check2.txt" 2>nul
    findstr /i "postgresql" "%temp%\_pg_check2.txt" >nul 2>&1
    del "%temp%\_pg_check2.txt" 2>nul
    if !errorlevel!==0 (
        call :log_success "PostgreSQL started"
        call :setup_pg_user_db
        goto :eof
    )
)

:: 3. Try to find PostgreSQL in common install paths and add to PATH
call :log_info "Searching PostgreSQL in common install paths..."
set "PG_FOUND=0"
for /d %%D in ("C:\Program Files\PostgreSQL\*\bin") do (
    if exist "%%D\psql.exe" (
        set "PG_BIN=%%D"
        set "PG_FOUND=1"
    )
)
if "!PG_FOUND!"=="1" (
    call :log_info "Found PostgreSQL at: !PG_BIN!"
    set "PATH=!PG_BIN!;!PATH!"
    call :log_info "Attempting to register and start service..."
    :: Try to register service if not already registered
    if exist "!PG_BIN!\pg_ctl.exe" (
        for /f "delims=" %%P in ("!PG_BIN:\bin=!") do set "PG_DATA_DIR=%%P\data"
        if exist "!PG_DATA_DIR!\postgresql.conf" (
            "!PG_BIN!\pg_ctl.exe" register -N postgresql -D "!PG_DATA_DIR!" >nul 2>&1
            net start postgresql >nul 2>&1
            timeout /t 3 /nobreak >nul
        )
    )
    where psql >nul 2>&1 && (
        call :log_success "PostgreSQL now available"
        call :setup_pg_user_db
        goto :eof
    )
)

:: 4. Auto install via winget
call :log_warn "PostgreSQL not found, attempting auto installation..."
call :log_info "This is a hard dependency, cannot fallback to SQLite"

where winget >nul 2>&1
if %errorlevel%==0 (
    call :log_info "Installing PostgreSQL via winget (this may take a while)..."
    winget install --id PostgreSQL.PostgreSQL.16 --silent --accept-source-agreements --accept-package-agreements 2>&1
    if !errorlevel!==0 (
        timeout /t 5 /nobreak >nul
        goto :check_pg_after_install
    ) else (
        call :log_warn "winget install failed, trying alternative versions..."
        winget install --id PostgreSQL.PostgreSQL.17 --silent --accept-source-agreements --accept-package-agreements 2>&1
        if !errorlevel!==0 (
            timeout /t 5 /nobreak >nul
            goto :check_pg_after_install
        )
        call :log_error "winget installation failed"
    )
)

:: 5. Try Chocolatey
where choco >nul 2>&1
if %errorlevel%==0 (
    call :log_info "Installing PostgreSQL via Chocolatey..."
    choco install postgresql -y --force 2>&1
    if !errorlevel!==0 (
        timeout /t 5 /nobreak >nul
        goto :check_pg_after_install
    )
)

call :log_error "Cannot auto-install PostgreSQL"
call :log_info "Please install manually:"
call :log_info "  1. winget install PostgreSQL.PostgreSQL.16"
call :log_info "  2. Or download from: https://www.postgresql.org/download/windows/"
call :log_info "  3. Then re-run start.bat"
echo.
pause
exit /b 1

:check_pg_after_install
:: Scan common install paths and APPEND to existing PATH (never replace)
call :log_info "Verifying PostgreSQL installation..."

set "PG_FOUND=0"
for /d %%D in ("C:\Program Files\PostgreSQL\*\bin") do (
    if exist "%%D\psql.exe" (
        set "PG_BIN=%%D"
        set "PG_FOUND=1"
    )
)
if "!PG_FOUND!"=="1" (
    call :log_info "Found PostgreSQL at: !PG_BIN!"
    set "PATH=!PG_BIN!;!PATH!"
)

where psql >nul 2>&1
if %errorlevel%==0 (
    call :log_success "PostgreSQL is now available"
    call :setup_pg_user_db
    goto :eof
)

call :log_error "PostgreSQL installed but not accessible"
call :log_info "Please restart your terminal and re-run start.bat"
pause
exit /b 1

:setup_pg_user_db
:: Check and create user/database via psql
where psql >nul 2>&1
if %errorlevel% neq 0 goto :eof

call :log_info "Checking PostgreSQL user and database..."
set "PG_USER=novel_user"
set "PG_PASS=novel_pass"
set "PG_DB=novel_reader"

:: Check if user exists
psql -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='%PG_USER%'" 2>nul | findstr "1" >nul
if %errorlevel% neq 0 (
    call :log_info "Creating user: %PG_USER%"
    psql -U postgres -c "CREATE USER %PG_USER% WITH PASSWORD '%PG_PASS%' CREATEDB;" 2>nul
)

:: Check if database exists
psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='%PG_DB%'" 2>nul | findstr "1" >nul
if %errorlevel% neq 0 (
    call :log_info "Creating database: %PG_DB%"
    psql -U postgres -c "CREATE DATABASE %PG_DB% OWNER %PG_USER%;" 2>nul
)

call :log_success "PostgreSQL user and database ready"
goto :eof

:ensure_redis
:: Check if Redis is running
redis-cli ping >nul 2>&1
if %errorlevel%==0 (
    call :log_success "Redis is running"
    goto :eof
)

:: Try to start Redis service
net start > "%temp%\_redis_check.txt" 2>nul
findstr /i "redis" "%temp%\_redis_check.txt" >nul 2>&1
if %errorlevel%==0 (
    call :log_info "Starting Redis..."
    for /f "tokens=2 delims=:" %%a in ('sc query state^= all ^| findstr /i "redis" ^| findstr "SERVICE_NAME"') do (
        net start "%%a" >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
    redis-cli ping >nul 2>&1 && (
        call :log_success "Redis started"
        del "%temp%\_redis_check.txt" 2>nul
        goto :eof
    )
)

:: Try standalone redis-server
where redis-server >nul 2>&1
if %errorlevel%==0 (
    call :log_info "Starting Redis standalone..."
    start /b redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru >nul 2>&1
    timeout /t 2 /nobreak >nul
    redis-cli ping >nul 2>&1 && (
        call :log_success "Redis started"
        del "%temp%\_redis_check.txt" 2>nul
        goto :eof
    )
)

call :log_warn "Redis not available, attempting auto install..."

where winget >nul 2>&1
if %errorlevel%==0 (
    call :log_info "Attempting to install Redis via winget..."
    winget install --id Memurai.MemuraiDeveloper --silent --accept-source-agreements --accept-package-agreements 2>nul || ^
    winget install --id Microsoft.Rdis --silent --accept-source-agreements --accept-package-agreements 2>nul
    if %errorlevel%==0 (
        timeout /t 3 /nobreak >nul
        redis-cli ping >nul 2>&1 && (
            call :log_success "Redis installed and started"
            del "%temp%\_redis_check.txt" 2>nul
            goto :eof
        )
    )
)

where choco >nul 2>&1
if %errorlevel%==0 (
    call :log_info "Attempting to install Redis via Chocolatey..."
    choco install redis-64 -y --force 2>nul
    if %errorlevel%==0 (
        timeout /t 3 /nobreak >nul
        redis-cli ping >nul 2>&1 && (
            call :log_success "Redis installed and started"
            del "%temp%\_redis_check.txt" 2>nul
            goto :eof
        )
    )
)

call :log_warn "Cannot auto-install Redis, falling back to DiskCache"
call :log_info "Optional: winget install Memurai.MemuraiDeveloper"
del "%temp%\_redis_check.txt" 2>nul
goto :eof

:start_infra
call :log_step "Starting Infrastructure"
call :ensure_pg || (
    call :log_error "Cannot start PostgreSQL, system cannot run"
    pause
    exit /b 1
)
call :ensure_redis
call :step_done
goto :eof

:: ─── Environment Check ───
:check_env
call :log_step "Environment Check"
set "env_errors=0"

:: Python: try python, python3, and Windows Store alias
set "PYTHON_FOUND=0"
where python >nul 2>&1 && set "PYTHON_FOUND=1"
if "!PYTHON_FOUND!"=="0" where python3 >nul 2>&1 && set "PYTHON_FOUND=1"
if "!PYTHON_FOUND!"=="0" (
    :: Check Windows Store Python alias
    if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" set "PYTHON_FOUND=1"
    if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe" set "PYTHON_FOUND=1"
)
if "!PYTHON_FOUND!"=="0" (
    :: Check common install paths
    for /d %%D in ("C:\Python3*\Scripts" "C:\Python3*" "%LOCALAPPDATA%\Programs\Python\Python3*\Scripts") do (
        if exist "%%~D\python.exe" (
            set "PYTHON_FOUND=1"
            set "PATH=%%~D;!PATH!"
        )
    )
)
if "!PYTHON_FOUND!"=="0" (
    call :log_error "Python is not installed"
    set /a env_errors+=1
) else (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do call :log_success "Python %%v"
)

:: Node.js: try node, and common install paths
set "NODE_FOUND=0"
where node >nul 2>&1 && set "NODE_FOUND=1"
if "!NODE_FOUND!"=="0" (
    if exist "C:\Program Files\nodejs\node.exe" (
        set "NODE_FOUND=1"
        set "PATH=C:\Program Files\nodejs;!PATH!"
    )
)
if "!NODE_FOUND!"=="0" (
    call :log_error "Node.js is not installed"
    set /a env_errors+=1
) else (
    for /f %%v in ('node --version 2^>^&1') do call :log_success "Node %%v"
)

if %env_errors% gtr 0 (
    call :log_error "Environment check failed"
    pause
    exit /b 1
)
call :step_done
goto :eof

:: ─── Python Dependencies ───
:install_python_deps
call :venv_activate

python -c "import django, ninja, granian" 2>nul
if %errorlevel%==0 (
    call :log_success "Python dependencies already installed"
    goto :eof
)

if not exist "requirements.txt" (
    call :log_error "requirements.txt not found"
    exit /b 1
)

call :log_info "Installing from PyPI mirror..."
call :pip_install || (
    call :log_error "pip install failed"
    exit /b 1
)

python -c "import django" 2>nul || (
    call :log_error "Python dependencies verification failed"
    exit /b 1
)
goto :eof

:pip_install
pip install -r requirements.txt ^
    -i https://mirrors.aliyun.com/pypi/simple/ ^
    --trusted-host mirrors.aliyun.com
goto :eof

:venv_activate
if not exist "venv\Scripts\activate.bat" (
    python -m venv venv
    call :log_success "Virtual environment created"
)
call venv\Scripts\activate.bat
goto :eof

:: ─── Node Dependencies ───
:install_node_deps
if not exist "frontend\package.json" goto :eof

if exist "frontend\node_modules\react" (
    call :log_success "Node dependencies already installed"
    goto :eof
)

call :log_info "Installing from npm mirror..."
cd frontend
call npm install --registry https://registry.npmmirror.com
cd ..

if not exist "frontend\node_modules\react" (
    call :log_error "Node dependencies installation failed"
    exit /b 1
)
goto :eof

:install_deps
call :log_step "Installing Dependencies"
call :install_python_deps
call :install_node_deps
call :step_done
goto :eof

:: ─── Database Migration ───
:migrate_db
call :log_step "Database Migration"
call :venv_activate

python manage.py migrate 2>&1
if %errorlevel% neq 0 (
    call :log_error "Database migration failed"
    exit /b 1
)
call :step_done
goto :eof

:: ─── Build Frontend ───
:build_frontend
call :log_step "Building Frontend"

if exist "frontend\dist\index.html" (
    call :log_success "Frontend already built, skipping"
    goto :eof
)

if not exist "frontend\node_modules\react" call :install_node_deps

cd frontend
call npx vite build
set "build_exit=%errorlevel%"
cd ..

if %build_exit% neq 0 (
    call :log_error "Frontend build failed"
    exit /b 1
)
call :step_done
goto :eof

:: ─── Start Server ───
:start_server
call :log_step "Starting Server"
call :venv_activate

call :log_info "Collecting static files..."
python manage.py collectstatic --noinput --clear >nul 2>&1

call :log_info "Initializing engines..."
python manage.py init_engines 2>nul

echo.
echo %GREEN%%LINE%%NC%
echo %GREEN%  Server Started!%NC%
echo %GREEN%%LINE%%NC%
echo.
echo   %GREEN%^>%NC% Access:  %BOLD%http://localhost:8000%NC%
echo   %GREEN%^>%NC% Admin:   http://localhost:8000/admin
echo   %GREEN%^>%NC% API:     http://localhost:8000/api/v1/docs/
echo.
echo   %DIM%Press Ctrl+C to stop%NC%
echo.

:: Start Granian
call granian novel_reader.asgi:application --host 0.0.0.0 --port 8000 --interface asginl --workers 1
goto :eof

:: ─── Commands ───
:cmd_start
call :print_banner
set "TOTAL_STEPS=8"
call :start_infra
call :check_env
call :install_deps
call :migrate_db
call :start_server
goto :eof

:cmd_dev
call :print_banner
set "TOTAL_STEPS=5"
call :start_infra
call :check_env
call :install_deps
call :migrate_db

call :log_info "Starting development servers..."
echo.
echo   %GREEN%^>%NC% Frontend: %BOLD%http://localhost:5173%NC%
echo   %GREEN%^>%NC% Backend:  http://localhost:8000
echo.

call :venv_activate
start "Django" python manage.py runserver 0.0.0.0:8000
cd frontend
call npm run dev
goto :eof

:cmd_stop
call :log_step "Stopping Services"
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
taskkill /f /im granian.exe >nul 2>&1
call :log_success "Services stopped"
goto :eof

:cmd_status
call :log_step "Service Status"

:: PostgreSQL
net start > "%temp%\_status.txt" 2>nul
findstr /i "postgresql" "%temp%\_status.txt" >nul 2>&1 && (
    call :log_success "PostgreSQL: Running"
) || (
    call :log_warn "PostgreSQL: Not Running"
)

:: Redis
redis-cli ping >nul 2>&1 && (
    call :log_success "Redis: Running"
) || (
    call :log_warn "Redis: Not Running"
)

:: App
tasklist /fi "imagename eq python.exe" 2>nul | findstr /i "python" >nul && (
    call :log_success "App Service: Running"
) || (
    call :log_warn "App Service: Not Running"
)

del "%temp%\_status.txt" 2>nul
goto :eof

:cmd_migrate
set "TOTAL_STEPS=4"
call :print_banner
call :start_infra
call :check_env
call :install_deps
call :migrate_db
goto :eof

:cmd_build
set "TOTAL_STEPS=4"
call :print_banner
call :check_env
call :install_deps
call :build_frontend
call :log_success "Build complete"
goto :eof

:cmd_services
set "TOTAL_STEPS=1"
call :print_banner
call :start_infra
goto :eof

:show_help
call :print_banner
echo Usage: start.bat ^<command^>
echo.
echo Commands:
echo   start      Start production server (default)
echo   stop       Stop services
echo   restart    Restart services
echo   status     Check service status
echo   migrate    Run database migrations
echo   build      Build frontend
echo   dev        Development mode
echo   services   Start infrastructure only
echo   help       Show this help
goto :eof

:: ─── Main ───
:main_entry
set "CMD=%~1"
if "%CMD%"=="" set "CMD=start"

if /i "%CMD%"=="start"     goto cmd_start
if /i "%CMD%"=="stop"      goto cmd_stop
if /i "%CMD%"=="restart"   call :cmd_stop & timeout /t 2 /nobreak >nul & goto cmd_start
if /i "%CMD%"=="status"    goto cmd_status
if /i "%CMD%"=="migrate"   goto cmd_migrate
if /i "%CMD%"=="build"     goto cmd_build
if /i "%CMD%"=="dev"       goto cmd_dev
if /i "%CMD%"=="services"  goto cmd_services
if /i "%CMD%"=="help"      goto show_help
if /i "%CMD%"=="--help"    goto show_help
if /i "%CMD%"=="-h"        goto show_help

call :log_error "Unknown command: %CMD%"
goto show_help
