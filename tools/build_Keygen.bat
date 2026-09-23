@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================
REM  Keygen 一键打包脚本（放在 tools\ 里也能用）
REM  输出：<项目根>\dist\Keygen\Keygen.exe
REM ============================================================

REM ✅ 切到项目根目录（bat 在 tools\ 里，往上一级）
cd /d "%~dp0.."

echo ============================================================
echo   打包 Keygen
echo ============================================================
echo   CWD: %CD%
echo.

REM ---------- 前置检查 ----------
if not exist "tools\keygen_app.ico" (
    echo [错误] 找不到图标文件: tools\keygen_app.ico
    pause
    exit /b 1
)
echo [检查] 图标 OK: tools\keygen_app.ico

if not exist "tools\keygen_gui.py" (
    echo [错误] 找不到 tools\keygen_gui.py
    pause
    exit /b 1
)
echo [检查] 入口 OK: tools\keygen_gui.py

if not exist "tools\apps_config.py" (
    echo [错误] 找不到 tools\apps_config.py
    pause
    exit /b 1
)
echo [检查] 依赖 OK: tools\apps_config.py

if not exist "tools\private_key.pem" (
    echo [警告] 找不到 tools\private_key.pem
    echo        打包后需手动拷到 dist\Keygen\
)
echo.

REM ---------- 清理旧产物 ----------
if exist "dist\Keygen" (
    echo [清理] 删除旧 dist\Keygen ...
    rmdir /s /q "dist\Keygen"
)
if exist "build\Keygen" (
    echo [清理] 删除旧 build\Keygen ...
    rmdir /s /q "build\Keygen"
)

REM ---------- 打包 ----------
echo.
echo [打包] 开始 PyInstaller ...
echo.

pyinstaller ^
    --windowed ^
    --name Keygen ^
    --icon tools\keygen_app.ico ^
    --paths tools ^
    --hidden-import apps_config ^
    --hidden-import cryptography ^
    --hidden-import cryptography.hazmat.primitives.asymmetric.padding ^
    --hidden-import cryptography.hazmat.primitives.hashes ^
    --hidden-import cryptography.hazmat.primitives.serialization ^
    --exclude-module tkinter ^
    --exclude-module matplotlib ^
    --exclude-module PyQt6.QtWebEngineCore ^
    --exclude-module PyQt6.QtWebEngineWidgets ^
    --exclude-module PyQt6.QtMultimedia ^
    --exclude-module PyQt6.QtBluetooth ^
    --exclude-module PyQt6.QtNetworkAuth ^
    --exclude-module PyQt6.QtPositioning ^
    --exclude-module PyQt6.QtSql ^
    --exclude-module PyQt6.QtTest ^
    --exclude-module PyQt6.QtDesigner ^
    --exclude-module PyQt6.QtHelp ^
    --noconfirm ^
    tools\keygen_gui.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo   [失败] PyInstaller 打包出错
    echo ============================================================
    pause
    exit /b 1
)

REM ---------- 校验输出 ----------
if not exist "dist\Keygen\Keygen.exe" (
    echo.
    echo ============================================================
    echo   [失败] 未找到 dist\Keygen\Keygen.exe
    echo ============================================================
    pause
    exit /b 1
)

REM ---------- 拷贝私钥 ----------
if exist "tools\private_key.pem" (
    echo.
    echo [拷贝] private_key.pem -^> dist\Keygen\
    copy /Y "tools\private_key.pem" "dist\Keygen\private_key.pem" >nul
    echo [拷贝] 完成
) else (
    echo.
    echo [警告] 未找到 tools\private_key.pem
    echo        请手动拷到 dist\Keygen\ 才能运行
)

REM ---------- 报告 ----------
echo.
echo ============================================================
echo   [成功] 打包完成
echo ============================================================
echo.
echo   输出目录：%CD%\dist\Keygen
echo   主程序：  %CD%\dist\Keygen\Keygen.exe
echo.

for %%F in ("dist\Keygen\Keygen.exe") do (
    set /a SIZE_MB=%%~zF / 1048576
    echo   文件大小：!SIZE_MB! MB
)

echo.
echo 按任意键退出 ...
pause >nul
endlocal