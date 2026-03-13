# 打包说明

## 一键打包

### Windows
双击运行 `build.bat` 或在命令行中执行：
```bash
build.bat
```

脚本会自动完成以下步骤：
1. 提示输入新版本号（直接回车使用当前版本）
2. 自动更新所有文件中的版本号（`xiaomi_to_evernote_gui.py`、`xiaomi_export.spec`、`build.bat`、`build.sh`）
3. 检查 Python 环境，自动安装 PyInstaller 和依赖
4. 清理旧的打包文件
5. 执行打包
6. 将生成的 exe 移动到当前目录并清理临时文件
7. 显示文件大小，询问是否立即运行

### Linux/macOS
```bash
chmod +x build.sh
./build.sh
```

脚本会自动完成以下步骤：
1. 检查 Python 环境（优先使用 `python3`，其次 `python`）
2. 自动安装 PyInstaller 和依赖
3. 清理旧的打包文件
4. 执行打包
5. 将生成的可执行文件移动到当前目录并清理临时文件
6. 询问是否立即运行

> **注意：** `build.sh` 不会自动更新版本号，打包前需手动修改 `build.sh` 中的 `VERSION` 变量。

## 手动打包

如果需要自定义打包选项，可以使用以下命令：

```bash
# 安装 PyInstaller 和依赖
pip install pyinstaller requests PyYAML Pillow tqdm

# 使用 spec 文件打包
pyinstaller xiaomi_export.spec --clean
```

打包完成后，可执行文件位于 `dist/` 目录中。

## 版本号更新

- **Windows（自动）：** 运行 `build.bat` 时会提示输入新版本号，脚本自动更新以下所有文件：
  1. `xiaomi_to_evernote_gui.py` - 窗口标题中的版本号
  2. `xiaomi_export.spec` - `VERSION` 变量
  3. `build.bat` - `CURRENT_VERSION` 变量
  4. `build.sh` - `VERSION` 变量

- **Linux/macOS（手动）：** 需要手动修改以上文件中的版本号。

## 输出文件

打包完成后，会在当前目录生成：
- Windows: `小米笔记导出工具v{版本号}.exe`
- Linux/macOS: `小米笔记导出工具v{版本号}`

## 必要文件

打包前请确保以下文件存在：
- `xiaomi_export.spec` - PyInstaller 打包配置
- `xiaomi_export.py` - 主程序入口

## 注意事项

1. 首次打包可能需要较长时间，请耐心等待
2. 如果打包失败，请检查是否有杀毒软件干扰
3. 建议在虚拟环境中打包，避免依赖冲突
