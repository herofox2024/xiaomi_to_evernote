#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小米笔记导出工具 - 统一入口脚本
支持命令行模式和GUI模式
"""

import sys
import os

# 添加当前目录到模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 检查命令行参数
if len(sys.argv) == 1:
    # 没有命令行参数，启动GUI模式
    print("启动GUI模式...")
    try:
        # 导入GUI模块
        from xiaomi_to_evernote_gui import main
        main()
    except Exception as e:
        print(f"GUI启动失败: {e}")
        print("命令行模式需要参数才能运行")
        print("使用方法: python xiaomi_export.py --help")
        sys.exit(1)
else:
    # 有命令行参数，直接调用主程序的命令行入口
    print("启动命令行模式...")
    import xiaomi_to_evernote
    xiaomi_to_evernote.main()
