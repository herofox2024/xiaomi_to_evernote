#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小米笔记导出工具 - 统一入口脚本
支持命令行模式和GUI模式
"""

import sys
import os
import tkinter as tk

# 添加当前目录到模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 检查命令行参数
if len(sys.argv) == 1:
    # 没有命令行参数，启动GUI模式
    print("启动GUI模式...")
    try:
        # 直接导入并使用主程序的核心功能
        import xiaomi_to_evernote
        
        # 定义GUI类，直接集成主程序功能
        class XiaomiNoteExporterGUI:
            def __init__(self, root):
                self.root = root
                self.root.title("小米笔记导出工具 - v1.0.5")
                self.root.geometry("850x800")
                self.root.minsize(850, 800)
                self.root.resizable(True, True)
                
                # 配置文件路径
                self.config_file = "config.yaml"
                self.default_config = {
                    "export": {
                        "chunk_size": 50,
                        "output_dir": "exported_notes",
                        "timeout": 30,
                        "max_retries": 3,
                        "max_workers": 5
                    },
                    "logging": {
                        "log_level": "INFO",
                        "log_file": "xiaomi_export.log"
                    }
                }
                
                # 当前状态
                self.is_exporting = False
                self.selected_chunk_size = 50
                self.total_images_size = 0
                
                # 初始化界面
                self.setup_ui()
                
                # 加载配置
                self.load_config()
            
            def setup_ui(self):
                # 创建主框架
                main_frame = tk.Frame(self.root)
                main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
                
                # 标题
                title_label = tk.Label(main_frame, text="小米笔记导出工具", font=('Arial', 16, 'bold'))
                title_label.pack(pady=10)
                
                # 配置区域
                config_frame = tk.LabelFrame(main_frame, text="导出配置")
                config_frame.pack(fill=tk.X, pady=10, padx=0)
                
                # cookies输入区域
                cookies_frame = tk.Frame(config_frame)
                cookies_frame.pack(fill=tk.X, pady=5, padx=10)
                
                tk.Label(cookies_frame, text="Cookies:").pack(anchor=tk.W, padx=5, pady=5)
                
                self.cookies_text = tk.Text(cookies_frame, height=5, wrap=tk.WORD)
                self.cookies_text.pack(fill=tk.X, padx=5, pady=5)
                
                # 验证cookie按钮
                validate_frame = tk.Frame(cookies_frame)
                validate_frame.pack(fill=tk.X, pady=5)
                
                self.validate_button = tk.Button(validate_frame, text="验证Cookie并估算容量", command=self.validate_cookies)
                self.validate_button.pack(side=tk.LEFT, padx=5)
                
                # 容量估算结果显示
                self.capacity_result_var = tk.StringVar(value="")
                # 调整容量标签，设置宽度和自动换行
                self.capacity_label = tk.Label(validate_frame, textvariable=self.capacity_result_var, foreground="blue", font=('Arial', 10, 'bold'), 
                                              wraplength=600, justify=tk.LEFT, anchor=tk.W)
                self.capacity_label.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)
                
                # 提示信息
                tk.Label(cookies_frame, text="如何获取Cookies:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, padx=5, pady=5)
                
                cookie_hint = (
                    "1. 在Chrome浏览器中登录 https://i.mi.com/note/h5#/\n"
                    "2. 按F12打开开发者工具\n"
                    "3. 切换到Network标签，刷新页面\n"
                    "4. 找到imi.com的请求，复制Cookie字段的值"
                )
                tk.Label(cookies_frame, text=cookie_hint, font=('Arial', 9), justify=tk.LEFT).pack(anchor=tk.W, padx=5, pady=5)
                
                # 导出配置区域
                export_config_frame = tk.Frame(config_frame)
                export_config_frame.pack(fill=tk.X, pady=10, padx=10)
                
                # 导出条数设置 - 初始禁用，验证cookie后启用
                tk.Label(export_config_frame, text="每批导出条数:").pack(side=tk.LEFT, padx=5)
                
                self.chunk_size_var = tk.StringVar(value="50")
                # 绑定下拉框变化事件
                self.chunk_size_var.trace_add("write", self.on_chunk_size_change)
                # 创建下拉框组件
                self.chunk_size_combo = tk.OptionMenu(export_config_frame, self.chunk_size_var, "20", "30", "40", "50", "60", "70", "80", "90", "100")
                self.chunk_size_combo.config(width=8, state="disabled")
                self.chunk_size_combo.pack(side=tk.LEFT, padx=5)
                
                # 导出按钮区域
                button_frame = tk.Frame(config_frame)
                button_frame.pack(fill=tk.X, pady=10, padx=10)
                
                self.export_button = tk.Button(button_frame, text="开始导出", command=self.start_export, state=tk.DISABLED)
                self.export_button.pack(side=tk.LEFT, padx=5)
                
                self.stop_button = tk.Button(button_frame, text="停止导出", command=self.stop_export, state=tk.DISABLED)
                self.stop_button.pack(side=tk.LEFT, padx=5)
                
                self.clear_button = tk.Button(button_frame, text="清空", command=self.clear_fields)
                self.clear_button.pack(side=tk.LEFT, padx=5)
                
                # 进度区域
                progress_frame = tk.LabelFrame(main_frame, text="导出进度")
                progress_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=0)
                
                # 进度条
                self.progress_var = tk.DoubleVar()
                # 使用Frame和Label模拟进度条
                self.progress_bar_frame = tk.Frame(progress_frame, borderwidth=1, relief=tk.SUNKEN)
                self.progress_bar_frame.pack(fill=tk.X, pady=10, padx=10)
                
                self.progress_bar = tk.Frame(self.progress_bar_frame, background="blue", height=20)
                self.progress_bar.pack(side=tk.LEFT, fill=tk.Y)
                
                self.progress_percent = tk.Label(self.progress_bar_frame, text="0%", background="white")
                self.progress_percent.pack(side=tk.RIGHT, padx=5)
                
                # 进度标签
                self.progress_label = tk.Label(progress_frame, text="准备就绪", font=('Arial', 10, 'bold'))
                self.progress_label.pack(pady=5, padx=10)
                
                # 日志输出区域
                log_frame = tk.Frame(progress_frame)
                log_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
                
                # 日志输出
                self.log_text = tk.Text(log_frame, wrap=tk.WORD, state=tk.DISABLED, font=('Arial', 9))
                self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                # 滚动条
                scrollbar = tk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                self.log_text.configure(yscrollcommand=scrollbar.set)
            
            def load_config(self):
                """加载配置文件"""
                import yaml
                if os.path.exists(self.config_file):
                    try:
                        with open(self.config_file, 'r', encoding='utf-8') as f:
                            config = yaml.safe_load(f)
                        
                        if config and 'export' in config:
                            chunk_size = config['export'].get('chunk_size', 50)
                            self.chunk_size_var.set(str(chunk_size))
                            self.selected_chunk_size = chunk_size
                        
                        self.add_log(f"配置文件加载成功: {self.config_file}")
                    except Exception as e:
                        self.add_log(f"配置文件加载失败: {e}")
                        self.save_config()
                else:
                    self.save_config()
            
            def save_config(self):
                """保存配置文件"""
                import yaml
                try:
                    with open(self.config_file, 'w', encoding='utf-8') as f:
                        yaml.dump(self.default_config, f, default_flow_style=False, allow_unicode=True)
                except Exception as e:
                    self.add_log(f"配置文件保存失败: {e}")
            
            def on_chunk_size_change(self, *args):
                """导出条数变化事件"""
                try:
                    self.selected_chunk_size = int(self.chunk_size_var.get())
                    self.add_log(f"已设置每批导出条数: {self.selected_chunk_size}")
                except ValueError:
                    self.add_log("无效的导出条数")
            
            def start_export(self):
                """开始导出"""
                cookies = self.cookies_text.get(1.0, tk.END).strip()
                
                if not cookies:
                    tk.messagebox.showerror("错误", "请输入有效的Cookies")
                    return
                
                if self.is_exporting:
                    tk.messagebox.showwarning("警告", "导出正在进行中")
                    return
                
                # 更新按钮状态
                self.export_button.config(state=tk.DISABLED)
                self.stop_button.config(state=tk.NORMAL)
                self.is_exporting = True
                
                # 清空日志
                self.log_text.config(state=tk.NORMAL)
                self.log_text.delete(1.0, tk.END)
                self.log_text.config(state=tk.DISABLED)
                
                # 更新进度
                self.update_progress(0)
                self.progress_label.config(text="开始导出...")
                
                # 保存配置
                self.save_config()
                
                # 启动导出线程
                import threading
                export_thread = threading.Thread(target=self.run_export, args=(cookies,))
                export_thread.daemon = True
                export_thread.start()
            
            def stop_export(self):
                """停止导出"""
                if not self.is_exporting:
                    return
                
                self.is_exporting = False
                self.add_log("导出已停止")
                
                # 更新按钮状态
                self.export_button.config(state=tk.NORMAL)
                self.stop_button.config(state=tk.DISABLED)
                
                self.progress_label.config(text="导出已停止")
            
            def run_export(self, cookies):
                """运行导出命令"""
                try:
                    # 直接使用主程序的配置类
                    config = xiaomi_to_evernote.ExportConfig()
                    config.chunk_size = self.selected_chunk_size
                    config.progress_report = True
                    # 启用文件日志
                    config.log_file = "xiaomi_export.log"
                    
                    # 创建导出器实例
                    exporter = xiaomi_to_evernote.XiaomiNoteExporter(cookies_str=cookies, config=config)
                    
                    # 执行导出，并捕获输出
                    import sys
                    import io
                    import json
                    
                    # 创建自定义输出流，捕获并处理输出
                    class CustomStream(io.StringIO):
                        def __init__(self, callback):
                            super().__init__()
                            self.callback = callback
                        
                        def write(self, text):
                            super().write(text)
                            # 处理PROGRESS:开头的结构化进度信息
                            if "PROGRESS:" in text:
                                try:
                                    progress_json = text.split("PROGRESS:")[-1]
                                    progress_data = json.loads(progress_json)
                                    if isinstance(progress_data, dict) and progress_data.get("type") == "progress":
                                        percentage = progress_data.get("percentage", 0)
                                        folder = progress_data.get('folder', '')
                                        current = progress_data.get('current', 0)
                                        total = progress_data.get('total', 0)
                                        
                                        # 更新进度条
                                        self.callback.update_progress(percentage)
                                        # 更新进度标签
                                        if percentage < 100:
                                            self.callback.progress_label.config(text=f"{folder}: {current}/{total} ({percentage:.1f}%)")
                                        else:
                                            self.callback.progress_label.config(text="导出成功完成！")
                                except Exception as e:
                                    pass
                    
                    # 保存原始输出流
                    original_stdout = sys.stdout
                    original_stderr = sys.stderr
                    
                    # 创建自定义流
                    custom_stdout = CustomStream(self)
                    custom_stderr = CustomStream(self)
                    
                    try:
                        # 重定向输出流
                        sys.stdout = custom_stdout
                        sys.stderr = custom_stderr
                        
                        # 执行导出
                        exporter.export_notes()
                        
                        # 显示成功信息
                        self.add_log("导出成功完成！")
                        self.update_progress(100)
                        self.progress_label.config(text="导出成功")
                        
                        # 检测图片容量
                        self.detect_images_size()
                    finally:
                        # 恢复原始输出流
                        sys.stdout = original_stdout
                        sys.stderr = original_stderr
                except Exception as e:
                    self.add_log(f"导出过程中发生错误: {e}")
                    self.progress_label.config(text="导出出错")
                finally:
                    self.is_exporting = False
                    self.export_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
            
            def add_log(self, message):
                """添加日志信息"""
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, f"{message}\n")
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
                
                # 更新UI
                self.root.update_idletasks()
            
            def detect_images_size(self):
                """检测导出目录中图片的总大小"""
                exported_dir = self.default_config['export']['output_dir']
                total_size = 0
                
                if os.path.exists(exported_dir):
                    for root, dirs, files in os.walk(exported_dir):
                        for file in files:
                            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                                file_path = os.path.join(root, file)
                                total_size += os.path.getsize(file_path)
                
                def format_size(size_bytes):
                    """格式化文件大小"""
                    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                        if size_bytes < 1024.0:
                            return f"{size_bytes:.2f} {unit}"
                        size_bytes /= 1024.0
                    return f"{size_bytes:.2f} PB"
                
                self.add_log(f"检测到图片总容量: {format_size(total_size)}")
            
            def validate_cookies(self):
                """验证cookies并估算容量"""
                cookies = self.cookies_text.get(1.0, tk.END).strip()
                
                if not cookies:
                    tk.messagebox.showerror("错误", "请输入有效的Cookies")
                    return
                
                # 禁用验证按钮，防止重复点击
                self.validate_button.config(state=tk.DISABLED)
                self.capacity_result_var.set("正在验证和估算容量...")
                
                # 启动验证线程
                import threading
                validate_thread = threading.Thread(target=self.run_cookie_validation, args=(cookies,))
                validate_thread.daemon = True
                validate_thread.start()
            
            def run_cookie_validation(self, cookies):
                """运行cookies验证和容量估算"""
                try:
                    # 直接使用主程序的配置类
                    config = xiaomi_to_evernote.ExportConfig()
                    # 启用文件日志
                    config.log_file = "xiaomi_export.log"
                    
                    # 创建导出器实例
                    exporter = xiaomi_to_evernote.XiaomiNoteExporter(cookies_str=cookies, config=config)
                    
                    # 捕获验证和估算的输出
                    import sys
                    import io
                    
                    # 保存原始输出流
                    original_stdout = sys.stdout
                    original_stderr = sys.stderr
                    
                    # 创建字符串缓冲区捕获输出
                    output_buffer = io.StringIO()
                    error_buffer = io.StringIO()
                    
                    try:
                        # 重定向输出流
                        sys.stdout = output_buffer
                        sys.stderr = error_buffer
                        
                        # 执行验证和估算
                        exporter.validate_and_estimate()
                        
                        # 获取输出内容
                        output = output_buffer.getvalue()
                        error = error_buffer.getvalue()
                        
                        # 解析输出中的笔记数量和估算容量
                        notes_count = 0
                        estimated_size = 0
                        
                        for line in output.split('\n'):
                            if "笔记数量:" in line:
                                try:
                                    notes_count = int(line.split("笔记数量:")[-1].strip())
                                except ValueError:
                                    pass
                            elif "估算容量:" in line:
                                try:
                                    size_str = line.split("估算容量:")[-1].strip()
                                    if "MB" in size_str:
                                        estimated_size = float(size_str.replace("MB", "").strip())
                                except ValueError:
                                    pass
                        
                        # 显示成功信息，包含笔记数量和估算容量
                        result_text = f"Cookies验证成功，共有{notes_count}条笔记，估算容量是{estimated_size}MB（实际容量以导出的笔记容量为准）"
                        self.capacity_result_var.set(result_text)
                        self.chunk_size_var.set("50")
                        self.chunk_size_combo.config(state="normal")
                        self.export_button.config(state=tk.NORMAL)
                        self.add_log(f"Cookies验证成功，共有{notes_count}条笔记，估算容量{estimated_size}MB，建议每批导出50条笔记")
                    finally:
                        # 恢复原始输出流
                        sys.stdout = original_stdout
                        sys.stderr = original_stderr
                except Exception as e:
                    self.add_log(f"验证过程中发生错误: {e}")
                    self.capacity_result_var.set(f"验证失败: {str(e)}")
                    tk.messagebox.showerror("验证失败", f"验证过程中发生错误: {str(e)}")
                finally:
                    # 恢复验证按钮状态
                    self.validate_button.config(state=tk.NORMAL)
            
            def clear_fields(self):
                """清空输入字段"""
                self.cookies_text.delete(1.0, tk.END)
                self.capacity_result_var.set("")
                # 禁用导出配置和按钮
                self.chunk_size_combo.config(state="disabled")
                self.export_button.config(state=tk.DISABLED)
                self.add_log("输入字段已清空")
            
            def update_progress(self, value):
                """更新进度条"""
                self.progress_var.set(value)
                # 更新自定义进度条宽度
                self.root.after(100, lambda: self._update_progress_bar(value))
            
            def _update_progress_bar(self, value):
                """实际更新进度条的UI"""
                try:
                    # 获取进度条框架的宽度
                    frame_width = self.progress_bar_frame.winfo_width()
                    # 计算进度条宽度
                    bar_width = int((value / 100) * frame_width)
                    # 更新进度条宽度和百分比文本
                    self.progress_bar.config(width=bar_width)
                    self.progress_percent.config(text=f"{int(value)}%")
                except Exception as e:
                    # 如果获取宽度失败，忽略错误
                    pass
        
        # 创建GUI实例
        root = tk.Tk()
        app = XiaomiNoteExporterGUI(root)
        
        # 设置窗口关闭事件
        def on_closing():
            if app.is_exporting:
                if tk.messagebox.askokcancel("确认关闭", "导出正在进行中，确定要关闭吗？"):
                    app.stop_export()
                    root.destroy()
            else:
                root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()
    except Exception as e:
        print(f"GUI启动失败: {e}")
        print("命令行模式需要参数才能运行")
        print("使用方法: python xiaomi_export.py --help")
        # 在GUI模式下启动失败时，不自动回退到命令行模式
        # 因为命令行模式需要sys.stdin，而在某些环境下可能不可用
        import sys
        sys.exit(1)
else:
    # 有命令行参数，直接调用主程序的命令行入口
    print("启动命令行模式...")
    import xiaomi_to_evernote
    xiaomi_to_evernote.main()
