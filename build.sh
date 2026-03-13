#!/bin/bash
# 小米笔记导出工具 - 一键打包脚本 (Linux/macOS)

echo "============================================"
echo "  小米笔记导出工具 - 一键打包脚本"
echo "============================================"
echo

# 设置版本号（与 spec 文件中的版本号保持一致）
VERSION="1.0.6"
APP_NAME="小米笔记导出工具v${VERSION}"

# 检查 Python 是否可用
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "[错误] 未找到 Python，请先安装 Python"
        exit 1
    fi
    PYTHON=python
else
    PYTHON=python3
fi

# 检查 PyInstaller 是否已安装
if ! $PYTHON -m pip show pyinstaller &> /dev/null; then
    echo "[信息] 正在安装 PyInstaller..."
    $PYTHON -m pip install pyinstaller
    if [ $? -ne 0 ]; then
        echo "[错误] PyInstaller 安装失败"
        exit 1
    fi
fi

# 安装依赖
echo "[信息] 检查并安装依赖..."
$PYTHON -m pip install requests PyYAML Pillow tqdm -q

# 清理旧的打包文件
echo "[信息] 清理旧的打包文件..."
rm -rf build dist "${APP_NAME}"*.exe "${APP_NAME}" 2>/dev/null

# 执行打包
echo "[信息] 开始打包 ${APP_NAME}..."
echo

$PYTHON -m PyInstaller xiaomi_export.spec --clean

if [ $? -ne 0 ]; then
    echo
    echo "[错误] 打包失败！"
    exit 1
fi

# 移动生成的文件
echo
echo "[信息] 整理输出文件..."
if [ -f "dist/${APP_NAME}" ]; then
    mv "dist/${APP_NAME}" .
    chmod +x "${APP_NAME}"
    echo "[成功] 已生成: ${APP_NAME}"
elif [ -f "dist/${APP_NAME}.exe" ]; then
    mv "dist/${APP_NAME}.exe" .
    echo "[成功] 已生成: ${APP_NAME}.exe"
else
    echo "[错误] 未找到生成的可执行文件"
    exit 1
fi

# 清理临时文件
echo "[信息] 清理临时文件..."
rm -rf build dist 2>/dev/null
rm -f *.pyz 2>/dev/null

echo
echo "============================================"
echo "  打包完成！"
echo "  输出文件: ${APP_NAME}*"
echo "============================================"
echo

# 询问是否运行
read -p "是否立即运行？(y/N): " RUN_NOW
if [ "$RUN_NOW" = "y" ] || [ "$RUN_NOW" = "Y" ]; then
    if [ -f "${APP_NAME}" ]; then
        ./"${APP_NAME}"
    elif [ -f "${APP_NAME}.exe" ]; then
        ./"${APP_NAME}.exe"
    fi
fi
