@echo off
chcp 936
setlocal

title 小米笔记导出工具打包
echo ============================================
echo 小米笔记导出工具 - 一键打包脚本
echo ============================================
echo.

cd /d "%~dp0"

:: 当前版本号（从文件读取）
set CURRENT_VERSION=1.0.6

:: 提示输入新版本号
echo 当前版本: %CURRENT_VERSION%
echo.
set /p NEW_VERSION=请输入新版本号 (直接回车使用当前版本): 

:: 如果没有输入，使用当前版本
if "%NEW_VERSION%"=="" (
    set NEW_VERSION=%CURRENT_VERSION%
    echo 使用当前版本: %NEW_VERSION%
)

echo.
echo ============================================
echo   版本号: %NEW_VERSION%
echo ============================================
echo.

:: 更新版本号到各文件
echo [步骤1] 更新版本号到各文件...

:: 1. 更新 xiaomi_to_evernote_gui.py
if exist "xiaomi_to_evernote_gui.py" (
    echo   - 更新 xiaomi_to_evernote_gui.py
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "(Get-Content 'xiaomi_to_evernote_gui.py') -replace 'v[0-9]+\.[0-9]+\.[0-9]+','v%NEW_VERSION%' | Set-Content 'xiaomi_to_evernote_gui.py'"
)

:: 2. 更新 xiaomi_export.spec
if exist "xiaomi_export.spec" (
    echo   - 更新 xiaomi_export.spec
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "(Get-Content 'xiaomi_export.spec') -replace 'VERSION = \"[0-9]+\.[0-9]+\.[0-9]+\"','VERSION = \"%NEW_VERSION%\"' | Set-Content 'xiaomi_export.spec'"
)

:: 3. 更新 build.bat 自身版本号
echo   - 更新 build.bat
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"(Get-Content 'build.bat') -replace 'set CURRENT_VERSION=[0-9]+\.[0-9]+\.[0-9]+','set CURRENT_VERSION=%NEW_VERSION%' | Set-Content 'build.bat'"

:: 4. 更新 build.sh（可选）
if exist "build.sh" (
    echo   - 更新 build.sh
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "(Get-Content 'build.sh') -replace 'VERSION=\"[0-9]+\.[0-9]+\.[0-9]+\"','VERSION=\"%NEW_VERSION%\"' | Set-Content 'build.sh'"
)

echo   - 版本号更新完成!
echo.

:: 设置应用名称
set APP_NAME=小米笔记导出工具v%NEW_VERSION%

echo [步骤2] 检查 Python 环境...

:: 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python
    goto :error_end
)

:: 检查 PyInstaller 是否已安装
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [信息] 正在安装 PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败
        goto :error_end
    )
)

:: 安装依赖
echo [信息] 检查并安装依赖...
pip install requests PyYAML Pillow tqdm -q

:: 检查必要文件
if not exist "xiaomi_export.spec" (
    echo [错误] 未找到 xiaomi_export.spec 文件
    goto :error_end
)

if not exist "xiaomi_export.py" (
    echo [错误] 未找到 xiaomi_export.py 文件
    goto :error_end
)

echo [步骤3] 清理旧的打包文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "%APP_NAME%.exe" del /f /q "%APP_NAME%.exe"

echo [步骤4] 开始打包 %APP_NAME%...
echo.

pyinstaller xiaomi_export.spec --clean
if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    goto :error_end
)

echo.
echo [步骤5] 整理输出文件...
if exist "dist\%APP_NAME%.exe" (
    move "dist\%APP_NAME%.exe" . >nul
    echo [成功] 已生成: %APP_NAME%.exe
) else (
    echo [错误] 未找到生成的 exe 文件
    goto :error_end
)

:: 清理临时文件
echo [步骤6] 清理临时文件...
rmdir /s /q "build" 2>nul
rmdir /s /q "dist" 2>nul
del /f /q "*.pyz" 2>nul

:: 显示文件大小
for %%A in ("%APP_NAME%.exe") do set FILE_SIZE=%%~zA
set /a FILE_SIZE_MB=%FILE_SIZE% / 1048576

echo.
echo ============================================
echo   打包完成！
echo   输出文件: %APP_NAME%.exe
echo   文件大小: %FILE_SIZE_MB% MB
echo ============================================
echo.

:: 询问是否运行
set /p RUN_NOW=是否立即运行？(Y/N): 
if /i "%RUN_NOW%"=="Y" (
    start "" "%APP_NAME%.exe"
)

goto :end

:error_end
echo.
echo ============================================
echo   打包过程中出现错误！
echo ============================================
echo.

:end
pause