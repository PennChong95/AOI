@echo off
chcp 65001 >nul
title AOI复判系统V4.1 - 一键打包脚本
cd /d "%~dp0"

echo ============================================
echo  AOI复判系统V4.1 - 打包+安装包生成
echo ============================================
echo.

REM ─── 第一步：PyInstaller 打包 ───
echo [1/4] 安装依赖...
pip install -r requirements.txt -q 2>&1 | findstr /V "already satisfied"
pip install pyinstaller -q 2>&1 | findstr /V "already satisfied"

echo [2/4] 清理旧文件...
if exist dist_pyinstaller rmdir /s /q dist_pyinstaller >nul 2>&1
if exist installer_output rmdir /s /q installer_output >nul 2>&1

echo [3/4] PyInstaller 打包（约 3-10 分钟）...
echo.
pyinstaller pyinstaller.spec --clean
if %errorlevel% neq 0 (
    echo [错误] PyInstaller 打包失败！
    pause
    exit /b 1
)

REM 确认 exe 生成
if not exist "dist\main\main.exe" (
    echo [错误] 未找到 main.exe，打包可能未成功
    dir dist\main\ /b
    pause
    exit /b 1
)

echo.
echo [4/4] 生成安装包（Inno Setup）...
echo.

REM 检查 Inno Setup 编译器路径
set ISCC_PATH=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC_PATH="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set ISCC_PATH="C:\Program Files\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" set ISCC_PATH="C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
if exist "C:\Program Files\Inno Setup 5\ISCC.exe" set ISCC_PATH="C:\Program Files\Inno Setup 5\ISCC.exe"

if defined ISCC_PATH (
    %ISCC_PATH% setup_installer.iss
    if %errorlevel% equ 0 (
        echo.
        echo ============================================
        echo  [完成] 安装包已生成！
        echo  目录: installer_output\
        for %%f in (installer_output\*.exe) do echo  文件: %%f
        echo ============================================
    ) else (
        echo [警告] Inno Setup 编译失败，但 PyInstaller 打包已完成
    echo  输出目录: dist\main\
    echo  手动运行 ISCC setup_installer.iss 可重新生成安装包
    )
) else (
    echo [提示] 未找到 Inno Setup 编译器
    echo  如需生成安装包，请安装 Inno Setup 6（https://jrsoftware.org/isdl.php）
    echo  安装后再次运行本脚本即可
    echo.
    echo  PyInstaller 打包已完成，可直接运行:
    echo    dist_pyinstaller\main\main.exe
)

echo.
pause
