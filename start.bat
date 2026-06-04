@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

:: ─── Colors (via PowerShell) ───
set "GREEN="
set "YELLOW="
set "RED="
set "BLUE="
set "DIM="
set "BOLD="
set "NC="
for /f "delims=" %%i in ('powershell -NoProfile -Command "[char]27 + '[0;32m'"') do set "GREEN=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "[char]27 + '[1;33m'"') do set "YELLOW=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "[char]27 + '[0;31m'"') do set "RED=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "[char]27 + '[0;34m'"') do set "BLUE=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "[char]27 + '[2m'"') do set "DIM=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "[char]27 + '[1m'"') do set "BOLD=%%i"
for /f "delims=" %%i in ('powershell -NoProfile -Command "[char]27 + '[0m'"') do set "NC=%%i"

set "STEP_NUM=0"
set "TOTAL_STEPS=8"

:: ─── Logging ───
:log_info
echo   %BLUE%E2%84%B9%NC% %~1
goto :eof

:log_success
echo   %GREEN%E2%9C%93%NC% %~1
goto :eof

:log_warn
echo   %YELLOW%E2%9A%A0%NC% %~1
goto :eof

:log_error
echo   %RED%E2%9C%97%NC% %~1
goto :eof

:log_detail
echo   %DIM%-> %~1%NC%
goto :eof

:log_step
set /a STEP_NUM+=1
echo.
echo %BOLD%%CYAN%[%STEP_NUM%/%TOTAL_STEPS%]%NC% %BOLD%%~1%NC%
set "_timer_start=%TIME%"
goto :eof

:step_done
echo   %GREEN%E2%9C%93%NC% %DIM%Done%NC%
goto :eof

:: ─── Banner ───
:print_banner
echo.
echo %MAGENTA%E2%95%94%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%97%NC%
echo %MAGENTA%E2%95%91%NC%  Novel Reader v2.0 - High-Performance Novel Reader    %MAGENTA%E2%95%91%NC%
echo %MAGENTA%E2%95%91%NC%  %DIM%PG + Redis + DiskCache + Liquid Glass UI%NC%       %MAGENTA%E2%95%91%NC%
echo %MAGENTA%E2%95%9A%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%9D%NC%
echo.
goto :eof

:: ─── Infrastructure ───
:ensure_pg
:: Check if PostgreSQL is running
net start > "%temp%\_pg_check.txt" 2>nul
findstr /i "postgresql" "%temp%\_pg_check.txt" >nul 2>&1
if %errorlevel%==0 (
    call :log_success "PostgreSQL is running"
    goto :eof
)

:: Try to start PostgreSQL service
call :log_info "PostgreSQL not running, attempting to start..."
for /f "tokens=2 delims=:" %%a in ('sc query state^= all ^| findstr /i "postgresql" ^| findstr "SERVICE_NAME"') do (
    set "pg_svc=%%a"
)
if defined pg_svc (
    call :log_info "Starting PostgreSQL service..."
    net start "%pg_svc%" >nul 2>&1
    timeout /t 3 /nobreak >nul
    net start > "%temp%\_pg_check2.txt" 2>nul
    findstr /i "postgresql" "%temp%\_pg_check2.txt" >nul 2>&1
    if %errorlevel%==0 (
        call :log_success "PostgreSQL started"
        call :setup_pg_user_db
        del "%temp%\_pg_check*.txt" 2>nul
        goto :eof
    )
)

:: PostgreSQL not installed - guide user
call :log_error "PostgreSQL is not installed or not running"
call :log_warn "This is a hard dependency, cannot fallback to SQLite"
echo.
echo   %BOLD%Please install PostgreSQL for Windows:%NC%
echo   %DIM%1. Download: https://www.postgresql.org/download/windows/%NC%
echo   %DIM%2. Install with default settings (port 5432)%NC%
echo   %DIM%3. Create user: novel_user, password: novel_pass%NC%
echo   %DIM%4. Run start.bat again%NC%
echo.
call :log_info "Or install via winget:"
echo   %DIM%winget install --id PostgreSQL.PostgreSQL --accept-source-agreements --accept-package-agreements%NC%
echo.
del "%temp%\_pg_check*.txt" 2>nul
exit /b 1

:setup_pg_user_db
:: Check and create user/database via psql
where psql >nul 2>&1
if %errorlevel% neq 0 goto :eof

call :log_info "Checking PostgreSQL user and database..."
:: Try to run psql commands (assumes postgres superuser available)
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

call :log_warn "Redis not available, falling back to DiskCache"
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

where python >nul 2>&1 || where python3 >nul 2>&1
if %errorlevel% neq 0 (
    call :log_error "Python is not installed"
    set /a env_errors+=1
) else (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do call :log_success "Python %%v"
)

where node >nul 2>&1
if %errorlevel% neq 0 (
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
echo %GREEN%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%NC%
echo %GREEN%  Server Started!%NC%
echo %GREEN%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%E2%95%90%NC%
echo.
echo   %GREEN%>%NC% Access:  %BOLD%http://localhost:8000%NC%
echo   %GREEN%>%NC% Admin:   http://localhost:8000/admin
echo   %GREEN%>%NC% API:     http://localhost:8000/api/v1/docs/
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
echo   %GREEN%>%NC% Frontend: %BOLD%http://localhost:5173%NC%
echo   %GREEN%>%NC% Backend:  http://localhost:8000
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