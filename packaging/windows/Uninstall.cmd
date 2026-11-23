@echo off
chcp 65001 >nul
echo 卸载 Presentation Director（你做的演示文稿会保留）
powershell -NoProfile -ExecutionPolicy Bypass -File "%LOCALAPPDATA%\PresentationDirector\uninstall.ps1"
echo.
pause
