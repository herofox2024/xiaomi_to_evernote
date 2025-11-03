# xiaomi_to_evernote
# 小米笔记导出工具

一个用于将小米云笔记导出为 Evernote 格式 (.enex) 的 Python 工具，方便将笔记迁移到其他笔记应用。

## 功能特性

- ✅ 导出小米云笔记为 Evernote 格式 (.enex)
- ✅ 支持分批导出，避免导入时文件过大
- ✅ 保留图片、复选框、字体样式等格式
- ✅ 自动处理 XML 特殊字符
- ✅ 支持多个文件夹分类导出

## 支持的内容格式

- ✅ 文本内容
- ✅ 图片（手机上传、手写）
- ✅ 复选框
- ✅ 字体样式（加粗、斜体、下划线）
- ✅ 字体大小
- ✅ 背景高亮
- ✅ 删除线

## 系统要求

- Python 3.6+
- 网络连接（用于访问小米云服务）
- 有效的小米账号

## 安装依赖

```bash
pip install requests pillow
```

## 使用方法

### 1. 获取 Cookies

首先需要获取小米云笔记的登录 cookies：

1. 在 Chrome 浏览器中登录：https://i.mi.com/note/h5#/
2. 按 F12 打开开发者工具
3. 切换到 Console (控制台) 标签
4. 输入以下命令并复制输出结果：
```javascript
document.cookie
```

### 2. 运行导出工具

#### 基本用法：
```bash
python xiaomi_to_evernote.py --cookies "你的cookies字符串"
```

#### 自定义分批大小：
```bash
python xiaomi_to_evernote.py --cookies "cookies" --chunk-size 30
```

#### 自定义输出目录：
```bash
python xiaomi_to_evernote.py --cookies "cookies" --output-dir "我的笔记"
```

#### 交互式输入 cookies：
```bash
python xiaomi_to_evernote.py
```

### 3. 命令行参数

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--cookies` | `-c` | 无 | 小米云笔记的 cookies 字符串 |
| `--chunk-size` | `-s` | 50 | 每批导出的笔记数量 |
| `--output-dir` | `-o` | exported_notes | 输出文件目录 |

## 输出文件

导出的文件将保存在指定的输出目录中，格式为：

- `文件夹名称.enex` - 如果笔记数量小于分块大小
- `文件夹名称_part01.enex` - 分批导出的文件
- `文件夹名称_part02.enex` - 后续分块文件

## 导入到其他笔记应用

### 导入到 Obsidian

1. 安装 Obsidian Importer 插件
2. 使用插件导入 `.enex` 文件
3. **建议**：分批导入，每次导入一个分块文件

### 导入到 Evernote/印象笔记

1. 直接导入 `.enex` 文件
2. 文件 → 导入 → Evernote 导出文件 (.enex)

### 使用 Yarle 转换（推荐）

对于更好的 Obsidian 兼容性，建议使用 Yarle 工具：

```bash
# 安装 Yarle
npm install -g yarle

# 转换 .enex 文件
yarle --input 导出的enex文件 --output 输出文件夹
```

## 故障排除

### 常见问题

1. **401 未授权错误**
   - 检查 cookies 是否有效
   - 重新登录小米云笔记获取新的 cookies

2. **导入 Obsidian 时内容不全**
   - 减小 `--chunk-size` 参数（建议 30-50）
   - 使用 Yarle 工具进行转换

3. **图片导出失败**
   - 确保网络连接稳定
   - 检查 PIL/Pillow 库是否正确安装

### 错误信息

- `401 Client Error: Unauthorized` - Cookies 无效或已过期
- `ModuleNotFoundError: No module named 'PIL'` - 需要安装 Pillow 库
- `ConnectionError` - 网络连接问题

## 技术细节

- 使用 `requests.Session` 保持会话状态
- 递归分页获取所有笔记（每页200条）
- 自动处理时间戳格式转换
- 使用 XML ElementTree 生成标准 Evernote 格式

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 免责声明

本工具仅用于个人数据迁移目的，请遵守小米云服务的使用条款。使用者应对自己的行为负责，作者不承担任何责任。
