@echo off
chcp 65001 >nul
echo Presentation Director 安装程序
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
echo.
pause
