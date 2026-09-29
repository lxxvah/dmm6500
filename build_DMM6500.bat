@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================
REM  DMM6500 一键打包脚本
REM  流程：
REM    1. PyInstaller 打包 → dist\DMM6500\DMM6500.exe
REM    2. Inno Setup 编译 → Output\DMM6500_Setup_v1.0.0.exe
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

if not exist "DMM6500_Setup.iss" (
    echo [警告] 找不到 DMM6500_Setup.iss，将跳过安装包制作
    set SKIP_ISS=1
) else (
    echo [检查] ISS  OK: DMM6500_Setup.iss
    set SKIP_ISS=0
)

echo.

REM ============================================================
REM  第一步：PyInstaller 打包（多文件版本）
REM ============================================================

echo ------------------------------------------------------------
echo   步骤 1/2：PyInstaller 打包
echo ------------------------------------------------------------
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

echo.
echo ============================================================
echo   [成功] PyInstaller 打包完成
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

REM ============================================================
REM  第二步：Inno Setup 制作安装包
REM ============================================================

if "!SKIP_ISS!"=="1" (
    echo ------------------------------------------------------------
    echo   步骤 2/2：跳过（未找到 .iss）
    echo ------------------------------------------------------------
    goto :DONE
)

echo ------------------------------------------------------------
echo   步骤 2/2：Inno Setup 制作安装包
echo ------------------------------------------------------------
echo.

REM ---------- 找 ISCC.exe ----------
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
)

if "!ISCC!"=="" (
    echo [错误] 找不到 Inno Setup（ISCC.exe）
    echo        请安装：https://jrsoftware.org/isdl.php
    echo.
    echo   PyInstaller 输出已在 dist\DMM6500\ 中，可手动编译 .iss
    echo.
    goto :DONE
)

echo [找到] !ISCC!
echo.

REM ---------- 清理旧安装包 ----------
if exist "Output" (
    echo [清理] 删除旧 Output\ ...
    rmdir /s /q "Output"
)

echo.
echo [编译] 开始 Inno Setup ...
echo.

"!ISCC!" DMM6500_Setup.iss

if errorlevel 1 (
    echo.
    echo ============================================================
    echo   [失败] Inno Setup 编译出错
    echo ============================================================
    echo.
    pause
    exit /b 1
)

REM ---------- 校验安装包 ----------
if not exist "Output\DMM6500_Setup_*.exe" (
    echo.
    echo ============================================================
    echo   [失败] 未找到 Output\DMM6500_Setup_*.exe
    echo ============================================================
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   [成功] Inno Setup 安装包完成
echo ============================================================
echo.

for %%F in ("Output\DMM6500_Setup_*.exe") do (
    set /a ISS_MB=%%~zF / 1048576
    echo   安装包：%%~fF
    echo   大小：  !ISS_MB! MB
)
echo.

:DONE
echo ============================================================
echo   全部完成
echo ============================================================
echo.
echo   1) 便携版：%CD%\dist\DMM6500\DMM6500.exe
if exist "Output\DMM6500_Setup_*.exe" (
    for %%F in ("Output\DMM6500_Setup_*.exe") do (
        echo   2) 安装包：%%~fF
    )
) else (
    echo   2) 安装包：未生成
)
echo.
echo 按任意键退出 ...
pause >nul
endlocal