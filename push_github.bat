@echo off
:: 强制控制台使用 UTF-8 编码，防止乱码
chcp 65001 >nul
cd /d %~dp0

echo ==========================================
echo 正在自动分析 DMM6500 变更并推送到 GitHub...
echo ==========================================

git add .

:: 检查是否有实际变更
git diff --cached --quiet
if %errorlevel% equ 0 (
    echo 没有需要提交的更改，脚本退出。
    exit
)

set "MSG=Auto: Update DMM6500 "
set "HAS_PY=0"
set "HAS_ISS=0"
set "HAS_BAT=0"
set "HAS_UI=0"

:: 使用 findstr 静默检测各类文件变更
git diff --cached --name-only | findstr /i "\.py$" >nul && set "HAS_PY=1"
git diff --cached --name-only | findstr /i "\.iss$" >nul && set "HAS_ISS=1"
git diff --cached --name-only | findstr /i "\.bat$" >nul && set "HAS_BAT=1"
git diff --cached --name-only | findstr /i "ui\\" >nul && set "HAS_UI=1"

:: 拼接纯英文提交信息，彻底规避 CMD 传递中文给 Git 的乱码问题
if %HAS_PY% equ 1 set "MSG=%MSG%source "
if %HAS_ISS% equ 1 set "MSG=%MSG%installer "
if %HAS_BAT% equ 1 set "MSG=%MSG%scripts "
if %HAS_UI% equ 1 set "MSG=%MSG%UI "

:: 如果什么都没匹配到
if "%MSG%"=="Auto: Update DMM6500 " set "MSG=Auto: Update DMM6500 project files"

:: 加上时间戳，避免每次提交信息重复
set "MSG=%MSG% [%date:~0,10% %time:~0,8%]"

echo 分析完成，自动生成提交信息: %MSG%
git commit -m "%MSG%"

:: 推送到远程仓库
git push

if %errorlevel% neq 0 (
    echo.
    echo GitHub 推送失败，请检查网络或 Git 配置。
    pause
    exit /b %errorlevel%
)

echo.
echo GitHub 推送成功！
:: 成功后延迟1秒自动退出，让你看到成功提示
timeout /t 1 >nul
exit