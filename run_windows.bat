@echo off
chcp 65001 >NUL
setlocal

REM 进入脚本所在目录
cd /d "%~dp0"

REM 启动 GUI
python gui_app.py

pause
endlocal

