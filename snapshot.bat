@echo off
chcp 65001 >nul
title GXU Agent - 数据快照

cd /d "%~dp0"

if "%~1"=="" (
    echo ============================================
    echo   GXU 数据快照工具
    echo ============================================
    echo.
    echo   用法:
    echo     snapshot.bat export    导出快照
    echo     snapshot.bat publish   导出并发布到 GitHub Release
    echo     snapshot.bat import    下载并恢复最新快照
    echo     snapshot.bat list      列出已发布的快照
    echo     snapshot.bat info      查看当前数据状态
    echo.
    pause
    exit /b 0
)

REM 发布/下载需要访问 GitHub，走代理
if "%~1"=="publish" set HTTPS_PROXY=http://127.0.0.1:7890
if "%~1"=="publish" set HTTP_PROXY=http://127.0.0.1:7890
if "%~1"=="import"  set HTTPS_PROXY=http://127.0.0.1:7890
if "%~1"=="import"  set HTTP_PROXY=http://127.0.0.1:7890
if "%~1"=="list"    set HTTPS_PROXY=http://127.0.0.1:7890
if "%~1"=="list"    set HTTP_PROXY=http://127.0.0.1:7890

python scripts/snapshot.py %*

echo.
pause
