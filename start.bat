@echo off
chcp 65001 >nul 2>&1
powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1" -SkipUpdate
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start
    pause
)
