# AOI复判系统V4.1 - 一键打包脚本
# 使用方法: .\build.ps1

$ErrorActionPreference = "Stop"
$version = "4.1.0"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " AOI复判系统 V$version 打包流程" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Step 1: 生成图标（如果没有）
if (-not (Test-Path "app_icon.ico")) {
    Write-Host "[1/4] 生成默认图标..." -ForegroundColor Yellow
    python -c "from PIL import Image; img=Image.new('RGBA',(256,256),(59,130,246,255)); img.save('app_icon.png'); img.save('app_icon.ico',format='ICO',sizes=[(256,256)])"
} else {
    Write-Host "[1/4] 使用已有图标 app_icon.ico" -ForegroundColor Yellow
}

# Step 2: Nuitka 打包
Write-Host "[2/4] Nuitka 打包 (预计 15-30 分钟)..." -ForegroundColor Yellow
python -m nuitka --standalone --windows-console-mode=disable --assume-yes-for-downloads `
    --enable-plugin=pyqt5 `
    --windows-icon-from-ico=app_icon.ico `
    --include-package=analytics `
    --include-package=auth `
    --include-package=config `
    --include-package=dashboard `
    --include-package=database `
    --include-package=editor `
    --include-package=modes `
    --include-package=review `
    --include-package=services `
    --include-package=ui `
    --include-package=utils `
    --include-data-dir=ui/web=ui/web `
    --include-data-dir=data=data `
    --include-data-dir=config=config `
    --follow-imports --lto=yes --python-flag=-OO `
    --output-dir=dist_nuitka --remove-output `
    main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Nuitka 打包失败!" -ForegroundColor Red
    exit 1
}
Write-Host "打包完成: dist_nuitka\main.dist\" -ForegroundColor Green

# Step 3: Inno Setup 安装包
Write-Host "[3/4] 生成安装包..." -ForegroundColor Yellow
$inno = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (Test-Path $inno) {
    & $inno setup_installer.iss
    Write-Host "安装包完成: installer_output\AOI复判系统V4.1_Setup.exe" -ForegroundColor Green
} else {
    Write-Host "未找到 Inno Setup，跳过安装包生成" -ForegroundColor Yellow
    Write-Host "请手动安装 Inno Setup: https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
}

# Step 4: 完成
Write-Host "" 
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 打包完成!" -ForegroundColor Cyan
Write-Host "  绿色版: dist_nuitka\main.dist\" -ForegroundColor Cyan
Write-Host "  安装包: installer_output\AOI复判系统V4.1_Setup.exe" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
