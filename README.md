<div align="center">

# 小米笔记导出工具

从网页版小米笔记导出笔记为 Evernote ENEX 格式，支持命令行和 GUI 两种运行方式，支持批量导出、资源下载、容量估算和打包为 exe。

![Version](https://img.shields.io/badge/version-v1.0.6-2f6f5f)
![Platform](https://img.shields.io/badge/platform-Windows-c47f2c)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.8+-203a43)

</div>

---

## 文档导航

| 内容 | 说明 |
|------|------|
| [核心功能](#核心功能) | 批量导出、GUI 界面、容量估算、资源下载 |
| [快速开始](#快速开始) | 安装依赖、获取 cookies、基本使用 |
| [使用方式](#使用方式) | 命令行、GUI、打包 exe 三种方式 |
| [配置文件](#配置文件) | config.yaml 配置项说明 |
| [项目结构](#项目结构) | 代码目录和入口文件 |
| [打包说明](#打包说明) | PyInstaller 打包为 exe |
| [常见问题](#常见问题) | 登录失败、下载失败、内存不足等问题 |
| [更新日志](#更新日志) | v1.0.0 ~ v1.0.6 版本记录 |

---

## 核心功能

- **笔记导出**：将网页版小米笔记导出为 Evernote ENEX 格式，支持文本、图片、附件等资源。
- **批量处理**：支持分批导出大量笔记，避免内存溢出和请求超时。
- **GUI 界面**：基于 tkinter 的桌面 GUI，支持 cookies 验证、容量估算和导出进度显示。
- **容量估算**：导出前预估输出文件大小，支持根据容量自动调整分块大小。
- **并发下载**：使用线程池并发下载图片等资源文件，可配置工作线程数。
- **配置管理**：支持 YAML 配置文件，命令行参数可覆盖配置项。
- **日志系统**：多级别日志（DEBUG/INFO/WARNING/ERROR），同时输出到控制台和文件。
- **打包支持**：通过 PyInstaller 打包为独立 exe，无需安装 Python 环境。

---

## 快速开始

### 安装依赖

```bash
pip install requests PyYAML Pillow tqdm
```

或使用 requirements.txt：

```bash
pip install -r requirements.txt
```

### 获取 cookies

1. 打开浏览器登录 [i.mi.com](https://i.mi.com)（小米云服务网页版）。
2. 进入笔记页面。
3. 按 F12 打开开发者工具，切换到 Network 标签。
4. 刷新页面，找到任意请求，复制请求头中的 Cookie 值。
5. 运行命令时传入 cookies：

```bash
python xiaomi_export.py --cookies "你的cookies字符串"
```

程序也支持空 cookies 启动，会自动提示获取方式：

```bash
python xiaomi_export.py --cookies ""
```

---

## 使用方式

### 方式一：命令行模式

```bash
# 基本使用
python xiaomi_export.py --cookies "your_cookies_string"

# 完整参数
python xiaomi_export.py \
  --cookies "your_cookies_string" \
  --chunk-size 30 \
  --output-dir "my_notes" \
  --timeout 60 \
  --max-workers 8 \
  --log-level DEBUG \
  --no-progress

# 仅验证 cookies 和估算容量（不导出）
python xiaomi_export.py --cookies "your_cookies_string" --validate-only

# 生成默认配置文件
python xiaomi_export.py --create-config
```

### 方式二：GUI 模式

```bash
python xiaomi_export.py --gui
```

GUI 支持：
- cookies 输入和验证
- 容量估算
- 分块大小设置
- 实时导出进度显示

### 方式三：打包为 exe

参考 [打包说明](#打包说明) 使用 PyInstaller 打包。

---

## 配置文件

配置文件为 `config.yaml`，支持以下主要配置项：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `export.chunk_size` | `30` | 每批导出的笔记数量 |
| `export.output_dir` | `xiaomi_notes` | 输出目录 |
| `export.timeout` | `30` | 请求超时时间（秒） |
| `export.max_workers` | `5` | 并发下载线程数 |
| `logging.log_level` | `INFO` | 日志级别 |
| `logging.log_file` | `xiaomi_export.log` | 日志文件路径 |

命令行参数会覆盖配置文件中的对应设置。

---

## 项目结构

```text
.
├─ xiaomi_to_evernote.py      # 核心导出逻辑模块
├─ xiaomi_to_evernote_gui.py  # GUI 界面模块（tkinter）
├─ xiaomi_export.py           # 统一入口脚本（命令行 + GUI）
├─ xiaomi_export.spec         # PyInstaller 打包配置
├─ config.yaml                # 用户配置文件
├─ default_config.yaml        # 默认配置模板
├─ requirements.txt           # 依赖列表
├─ build.bat                  # Windows 打包脚本
├─ build.sh                   # Linux/macOS 打包脚本
├─ BUILD.md                   # 打包详细说明
├─ changelog.md               # 早期更新日志
├─ BUGFIX_REPORT.md           # Bug 修复报告
├─ FIXES_CHECKLIST.md         # 修复检查清单
├─ REPAIR_SUMMARY.md          # 修复汇总
├─ dist/                      # 打包输出目录
└─ build/                     # 构建临时目录
```

### 架构概览

```
┌──────────────────────────────────────────────────────────┐
│                     入口层                               │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              xiaomi_export.py                     │   │
│  │  命令行解析 → 模式选择 → 配置加载                  │   │
│  └────────┬─────────────────────┬───────────────────┘   │
│           │                     │                        │
│           ▼                     ▼                        │
│  ┌────────────────┐   ┌────────────────────────────┐    │
│  │ 命令行模式      │   │ GUI 模式                    │    │
│  │ 直接调用核心模块 │   │ tkinter 窗口 + 进度显示     │    │
│  └───────┬────────┘   └──────────┬─────────────────┘    │
│          │                       │                       │
├──────────┼───────────────────────┼───────────────────────┤
│          │         业务逻辑层     │                       │
│          ▼                       ▼                       │
│  ┌──────────────────────────────────────────────────┐   │
│  │         xiaomi_to_evernote.py                     │   │
│  │                                                    │   │
│  │  ┌──────────────────────────────────────────────┐ │   │
│  │  │  XiaomiNoteExporter                          │ │   │
│  │  │                                              │ │   │
│  │  │  validate_cookies()  → 登录验证               │ │   │
│  │  │  validate_and_estimate() → 容量估算            │ │   │
│  │  │  download_notes_list() → 获取笔记列表          │ │   │
│  │  │  export_notes() → 导出笔记 + 资源下载          │ │   │
│  │  │  save_enex() → 保存为 ENEX 格式               │ │   │
│  │  └──────────────────────────────────────────────┘ │   │
│  │                                                    │   │
│  │  ┌──────────────────────────────────────────────┐ │   │
│  │  │  辅助模块                                    │ │   │
│  │  │  - 配置管理 (YAML 加载/保存)                  │ │   │
│  │  │  - 日志系统 (多级别/多目标)                    │ │   │
│  │  │  - 异常处理 (自定义异常类)                     │ │   │
│  │  │  - 文件清理 (安全文件名)                      │ │   │
│  │  └──────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │         xiaomi_to_evernote_gui.py                 │   │
│  │                                                    │   │
│  │  tkinter GUI → cookies 输入 → 验证 → 容量估算      │   │
│  │             → 分块设置 → 导出进度 → 完成提示        │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                     外部依赖层                            │
│                                                          │
│  小米云服务 API ← requests → ENEX 文件 ← 文件系统        │
│  ThreadPoolExecutor → 并发下载图片/附件                  │
│  PyYAML → 配置读写    Pillow → 图片检测     tqdm → 进度   │
└──────────────────────────────────────────────────────────┘
```

### 导出流程

```
用户执行导出命令
    │
    ▼
① 配置加载: 读取 config.yaml → 合并命令行参数
    │
    ▼
② 登录验证: validate_cookies() → 检查 cookies 有效性
    │
    ▼
③ 容量估算: validate_and_estimate() → 预估输出大小
    │
    ▼
④ 获取列表: download_notes_list() → 递归获取所有笔记
    │
    ▼
⑤ 分批导出: export_notes() → 按 chunk_size 分批处理
    │
    ├─ 获取笔记内容（文本 + 资源列表）
    ├─ 并发下载图片/附件 (ThreadPoolExecutor)
    ├─ 转换为 ENEX XML 格式
    └─ 实时进度输出
    │
    ▼
⑥ 保存文件: save_enex() → 写入 .enex 文件
    │
    ▼
⑦ 完成: 显示统计信息（笔记数、文件大小、耗时）
```

---

## 打包说明

### Windows

```bash
# 使用打包脚本
build.bat

# 或直接使用 PyInstaller
pyinstaller xiaomi_export.spec --noconfirm
```

输出目录：`dist/`

详细说明参考 `BUILD.md`。

### Linux / macOS

```bash
chmod +x build.sh
./build.sh
```

---

## 常见问题

### 登录失败

- 检查 cookies 是否过期（小米云服务登录有时效性）
- 确认 cookies 字符串格式正确，包含完整的 `serviceToken` 字段
- 使用 `--log-level DEBUG` 查看详细错误信息

### 下载失败 / 超时

- 增加超时时间：`--timeout 120`
- 降低并发线程数：`--max-workers 3`
- 检查网络连接是否稳定

### 文件保存失败

- 检查输出目录是否有写入权限
- 确认磁盘空间充足
- 输出文件名已自动清理特殊字符，如有异常请检查日志

### 内存不足（大量笔记）

- 减小分块大小：`--chunk-size 15`
- 降低并发线程数
- 分批多次导出不同文件夹的笔记

### 非图片资源下载慢

v1.0.6 已优化：非图片资源（如 `application/json`）直接跳过，不再重试 3 次，显著提升导出速度。

---

## 更新日志

### v1.0.6 (2026-03-12)

- **Bug 修复**：修复 Git 合并冲突、方法名不一致、GUI 未定义 logger、`folder_id` 类型错误、缩进问题。
- **代码优化**：清理未使用的线程锁，使用 `raise ... from e` 保留异常链上下文。
- **性能改进**：非图片资源直接跳过，不再重试，显著提升导出速度。
- **代码重构**：整合 GUI 文件，统一入口，三个 Python 文件各司其职。
- **功能修正**：修复导出容量检测功能，正确显示 `.enex` 文件总大小。

### v1.0.5 (2025-12-20)

- **GUI 增强**：新增 cookies 验证和容量估算，优化进度显示，窗口默认 850x800，分块大小改为下拉框。
- **主程序增强**：新增 `--validate-only` 参数，实现 `validate_and_estimate()` 方法，结构化进度报告。
- **入口脚本完善**：支持命令行和 GUI 模式，自定义输出流捕获，PyInstaller 打包支持。

### v1.0.4 (2025-12-19)

- 修复错误日志未输出问题，确保日志文件自动生成。
- 程序报错后不再闪退，等待用户确认后退出。

### v1.0.3 (2025-12-19)

- 修复导出 400+ 笔记闪退问题，优化内存管理和正则表达式性能。

### v1.0.0 (2025-11-04)

- 完整重构，添加配置管理、错误处理、日志系统、并发支持和安全性改进。

---

## 依赖

| 依赖 | 用途 | 必需 |
|------|------|------|
| `requests` | HTTP 请求 | 是 |
| `PyYAML` | 配置文件读写 | 是 |
| `Pillow` | 图片尺寸检测 | 否（未安装自动跳过） |
| `tqdm` | 进度条显示 | 否（未安装使用简单进度显示） |

---

## 联系方式

- **项目主页**：[GitHub - herofox2024/xiaomi_to_evernote](https://github.com/herofox2024/xiaomi_to_evernote)
- **问题反馈**：[GitHub Issues](https://github.com/herofox2024/xiaomi_to_evernote/issues)
- **邮箱**：42845734@qq.com

---

## License

MIT License。详见 LICENSE 文件。

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=herofox2024/xiaomi_to_evernote&type=date&legend=top-left)](https://www.star-history.com/#herofox2024/xiaomi_to_evernote&type=date&legend=top-left)
