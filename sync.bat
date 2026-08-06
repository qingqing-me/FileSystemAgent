@echo off
chcp 65001 >nul
title GXU Agent - 增量同步

echo ============================================
echo   GXU 校园文件智能助手 - 增量同步
echo ============================================
echo.

cd /d "%~dp0"

REM ============ 读取账号配置 ============
REM 优先级: sync.conf 配置文件 > 环境变量 > 交互输入
set WJXT_USERNAME=
set WJXT_PASSWORD=

if exist "sync.conf" (
    echo [读取] 从 sync.conf 读取账号配置...
    for /f "usebackq delims=" %%a in ("sync.conf") do set "%%a"
    if defined WJXT_USERNAME if defined WJXT_PASSWORD echo [OK] 配置已读取
)

if not defined WJXT_USERNAME (
    echo [登录] 请输入学号:
    set /p WJXT_USERNAME="  学号: "
)

if not defined WJXT_PASSWORD (
    echo [登录] 请输入密码（将隐藏显示）:
    for /f "usebackq delims=" %%p in (`powershell -Command "$p = Read-Host -AsSecureString '  密码'; [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($p))"`) do set "WJXT_PASSWORD=%%p"
)

REM ============ 检查后端 ============
echo.
curl -s -o nul -w "%%{http_code}" http://localhost:8000/api/health > "%TEMP%\gxu_health.txt" 2>nul
set /p HEALTH=<"%TEMP%\gxu_health.txt"

if "%HEALTH%"=="200" (
    echo [OK] 后端已在运行
) else (
    echo [启动] 启动后端服务...
    start "GXU-Backend" cmd /c "cd /d %~dp0backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    echo       等待后端就绪（约 8 秒）...
    timeout /t 8 /nobreak >nul
)

REM ============ 执行同步 ============
echo.
echo [同步] 开始增量同步...
cd scripts
set BACKEND_URL=http://localhost:8000
npx tsx sync.ts

echo.
echo ============================================
echo   同步完成！浏览器访问 http://localhost:5173
echo ============================================
pause
