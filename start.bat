@echo off
chcp 65001 >nul 2>&1
set PSDefaultParameterValues=@{Out-File:Encoding='utf8'}
powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1" -SkipUpdate
pause
