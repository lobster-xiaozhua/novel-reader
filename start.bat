@echo off
chcp 65001 >nul
echo.
echo ═══════════════════════════════════
echo   Novel Reader 启动器
echo ═══════════════════════════════════
echo.
echo 正在启动 PowerShell 脚本...
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1" -SkipUpdate

if errorlevel 1 (
    echo.
    echo [错误] 启动失败
    pause
)
