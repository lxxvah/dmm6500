@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================
REM  DMM6500 一键打包脚本
REM  输出：dist\DMM6500\DMM6500.exe
REM ============================================================

cd /d "%~dp0"

echo ============================================================
echo   打包 DMM6500
echo ============================================================
echo.

REM ---------- 前置检查 ----------
if not exist "DMM6500_app.ico" (
    echo [错误] 找不到图标文件: DMM6500_app.ico
    echo        请把图标放到: %CD%
    echo.
    pause
    exit /b 1
)
echo [检查] 图标 OK: DMM6500_app.ico

if not exist "licensing\public_key.pem" (
    echo [错误] 找不到公钥文件: licensing\public_key.pem
    echo.
    pause
    exit /b 1
)
echo [检查] 公钥 OK: licensing\public_key.pem

if not exist "main.py" (
    echo [错误] 找不到 main.py
    echo.
    pause
    exit /b 1
)
echo [检查] 入口 OK: main.py

echo.

REM ---------- 清理旧产物 ----------
if exist "dist\DMM6500" (
    echo [清理] 删除旧 dist\DMM6500 ...
    rmdir /s /q "dist\DMM6500"
)
if exist "build\DMM6500" (
    echo [清理] 删除旧 build\DMM6500 ...
    rmdir /s /q "build\DMM6500"
)

REM ---------- 打包 ----------
echo.
echo [打包] 开始 PyInstaller ...
echo.

pyinstaller ^
    --windowed ^
    --name DMM6500 ^
    --icon DMM6500_app.ico ^
    --add-data "licensing/public_key.pem;licensing" ^
    --hidden-import cryptography ^
    --hidden-import cryptography.hazmat.primitives.asymmetric.padding ^
    --hidden-import cryptography.hazmat.primitives.hashes ^
    --hidden-import cryptography.hazmat.primitives.serialization ^
    --hidden-import pyvisa ^
    --hidden-import pyvisa_py ^
    --hidden-import pyqtgraph ^
    --exclude-module tkinter ^
    --exclude-module matplotlib ^
    --exclude-module tools ^
    --exclude-module tests ^
    --noconfirm ^
    main.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo   [失败] PyInstaller 打包出错
    echo ============================================================
    echo.
    pause
    exit /b 1
)

REM ---------- 校验输出 ----------
if not exist "dist\DMM6500\DMM6500.exe" (
    echo.
    echo ============================================================
    echo   [失败] 未找到输出文件 dist\DMM6500\DMM6500.exe
    echo ============================================================
    echo.
    pause
    exit /b 1
)

REM ---------- 报告 ----------
echo.
echo ============================================================
echo   [成功] 打包完成
echo ============================================================
echo.
echo   输出目录：%CD%\dist\DMM6500
echo   主程序：  %CD%\dist\DMM6500\DMM6500.exe
echo.

for %%F in ("dist\DMM6500\DMM6500.exe") do (
    set /a SIZE_MB=%%~zF / 1048576
    echo   文件大小：!SIZE_MB! MB
)

echo.
echo 按任意键退出 ...
pause >nul
endlocal