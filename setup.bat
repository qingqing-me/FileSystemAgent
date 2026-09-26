@echo off
chcp 65001 >nul
title GXU Agent - 一键初始化

cd /d "%~dp0"

REM 自动检测 Clash 代理（访问 GitHub 下载数据快照需要）
netstat -an | findstr ":7890" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    set HTTPS_PROXY=http://127.0.0.1:7890
    set HTTP_PROXY=http://127.0.0.1:7890
    echo [代理] 检测到 127.0.0.1:7890，已启用
) else (
    echo [代理] 未检测到代理，直连
)
echo.

python scripts/setup.py %*

pause
