#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小米笔记导出工具 - GUI版本
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import json
import os
import re
from pathlib import Path


class XiaomiNoteExporterGUI:
    """小米笔记导出工具GUI界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("小米笔记导出工具 - v1.0.5")
        self.root.geometry("600x500")
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
        
        # 调整窗口大小，增加高度，确保日志框有足够空间显示
        self.root.geometry("750x800")
        self.root.minsize(750, 800)
        
    def setup_ui(self):
        """设置UI界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="小米笔记导出工具", font=('Arial', 16, 'bold'))
        title_label.pack(pady=10)
        
        # 配置区域
        config_frame = ttk.LabelFrame(main_frame, text="导出配置", padding="10")
        config_frame.pack(fill=tk.X, pady=10)
        
        # cookies输入区域
        cookies_frame = ttk.Frame(config_frame)
        cookies_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(cookies_frame, text="Cookies:").pack(anchor=tk.W, padx=5, pady=5)
        
        self.cookies_text = tk.Text(cookies_frame, height=5, wrap=tk.WORD)
        self.cookies_text.pack(fill=tk.X, padx=5, pady=5)
        
        # 验证cookie按钮
        validate_frame = ttk.Frame(cookies_frame)
        validate_frame.pack(fill=tk.X, pady=5)
        
        self.validate_button = ttk.Button(validate_frame, text="验证Cookie并估算容量", command=self.validate_cookies)
        self.validate_button.pack(side=tk.LEFT, padx=5)
        
        # 容量估算结果显示
        self.capacity_result_var = tk.StringVar(value="")
        self.capacity_label = ttk.Label(validate_frame, textvariable=self.capacity_result_var, foreground="blue", font=('Arial', 10, 'bold'))
        self.capacity_label.pack(side=tk.RIGHT, padx=5)
        
        # 提示信息
        ttk.Label(cookies_frame, text="如何获取Cookies:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, padx=5, pady=5)
        
        cookie_hint = (
            "1. 在Chrome浏览器中登录 https://i.mi.com/note/h5#/\n"
            "2. 按F12打开开发者工具\n"
            "3. 切换到Network标签，刷新页面\n"
            "4. 找到imi.com的请求，复制Cookie字段的值"
        )
        ttk.Label(cookies_frame, text=cookie_hint, font=('Arial', 9), justify=tk.LEFT).pack(anchor=tk.W, padx=5, pady=5)
        
        # 导出配置区域
        export_config_frame = ttk.Frame(config_frame)
        export_config_frame.pack(fill=tk.X, pady=10)
        
        # 导出条数设置 - 初始禁用，验证cookie后启用
        ttk.Label(export_config_frame, text="每批导出条数:").pack(side=tk.LEFT, padx=5)
        
        self.chunk_size_var = tk.StringVar(value="50")
        self.chunk_size_combo = ttk.Combobox(export_config_frame, textvariable=self.chunk_size_var, width=10, state="disabled")
        self.chunk_size_combo['values'] = ["20", "30", "40", "50", "60", "70", "80", "90", "100"]
        self.chunk_size_combo.pack(side=tk.LEFT, padx=5)
        self.chunk_size_combo.bind("<<ComboboxSelected>>", self.on_chunk_size_change)
        
        # 导出按钮区域
        button_frame = ttk.Frame(config_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.export_button = ttk.Button(button_frame, text="开始导出", command=self.start_export, state=tk.DISABLED)
        self.export_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="停止导出", command=self.stop_export, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(button_frame, text="清空", command=self.clear_fields)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # 进度区域
        progress_frame = ttk.LabelFrame(main_frame, text="导出进度", padding="10")
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=10, anchor=tk.S)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=10)
        
        # 进度标签
        self.progress_label = ttk.Label(progress_frame, text="准备就绪", font=('Arial', 10, 'bold'))
        self.progress_label.pack(pady=5)
        
        # 日志输出区域
        log_frame = ttk.Frame(progress_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 日志输出
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, state=tk.DISABLED, font=('Arial', 9))
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    import yaml
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
        try:
            import yaml
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.default_config, f, default_flow_style=False, allow_unicode=True)
            
            self.add_log(f"配置文件保存成功: {self.config_file}")
        except Exception as e:
            self.add_log(f"配置文件保存失败: {e}")
    
    def on_chunk_size_change(self, event):
        """导出条数变化事件"""
        try:
            self.selected_chunk_size = int(self.chunk_size_var.get())
            self.add_log(f"已设置每批导出条数: {self.selected_chunk_size}")
            
            # 根据条数建议容量
            self.update_capacity_suggestion()
        except ValueError:
            self.add_log("无效的导出条数")
    
    def update_capacity_suggestion(self):
        """更新容量建议"""
        # 简单的容量估算
        estimated_size = self.selected_chunk_size * 5  # 每条笔记约5MB
        self.capacity_label.config(text=f"估算容量: {estimated_size}MB")
        
        # 如果图片容量超过5G，建议增加条数
        if self.total_images_size > 5 * 1024 * 1024 * 1024:  # 5GB
            self.capacity_label.config(text=f"图片总容量: {self.format_size(self.total_images_size)}，建议增加导出条数")
    
    def format_size(self, size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
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
        
        self.total_images_size = total_size
        self.add_log(f"检测到图片总容量: {self.format_size(total_size)}")
        self.update_capacity_suggestion()
    
    def start_export(self):
        """开始导出"""
        cookies = self.cookies_text.get(1.0, tk.END).strip()
        
        if not cookies:
            messagebox.showerror("错误", "请输入有效的Cookies")
            return
        
        if self.is_exporting:
            messagebox.showwarning("警告", "导出正在进行中")
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
        self.progress_var.set(0)
        self.progress_label.config(text="开始导出...")
        
        # 保存配置
        self.save_config()
        
        # 启动导出线程
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
            # 构建命令
            cmd = [
                'python', 'xiaomi_to_evernote.py',
                '--cookies', cookies,
                '--chunk-size', str(self.selected_chunk_size),
                '--log-level', 'INFO',
                '--progress-report'
            ]
            
            self.add_log(f"执行命令: {' '.join(cmd)}")
            
            # 执行命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # 读取输出
            line_count = 0
            for line in iter(process.stdout.readline, ''):
                if not self.is_exporting:
                    process.terminate()
                    break
                
                line = line.rstrip('\r\n')
                if line:
                    self.add_log(line)
                    line_count += 1
                    
                    # 检查是否是进度信息
                    if line.startswith("PROGRESS:"):
                        try:
                            # 确保只处理有效的JSON格式
                            if "{" in line and "}" in line:
                                progress_json = line[9:]
                                progress_data = json.loads(progress_json)
                                if isinstance(progress_data, dict) and progress_data.get("type") == "progress":
                                    percentage = progress_data.get("percentage", 0)
                                    self.progress_var.set(percentage)
                                    
                                    # 更新进度标签
                                    folder = progress_data.get('folder', '')
                                    current = progress_data.get('current', 0)
                                    total = progress_data.get('total', 0)
                                    
                                    if folder == "准备中":
                                        self.progress_label.config(text=f"{folder}: {current}%")
                                    elif folder == "完成":
                                        self.progress_label.config(text="导出成功完成！")
                                    elif folder == "失败":
                                        self.progress_label.config(text="导出失败")
                                    else:
                                        self.progress_label.config(
                                            text=f"正在导出 {folder}: {current}/{total} ({percentage}%)"
                                        )
                                    
                                    # 强制更新UI
                                    self.root.update_idletasks()
                        except json.JSONDecodeError as e:
                            self.add_log(f"解析进度信息失败: {line}, 错误: {e}")
                        except Exception as e:
                            self.add_log(f"处理进度信息时发生错误: {e}")
                        continue
                    
                    # 传统进度估算（备用）
                    if line_count % 10 == 0:
                        progress = min(95, line_count / 2)
                        self.progress_var.set(progress)
            
            process.wait()
            
            if process.returncode == 0:
                self.add_log("导出成功完成！")
                self.progress_var.set(100)
                self.progress_label.config(text="导出成功")
                
                # 检测图片容量
                self.detect_images_size()
            else:
                self.add_log(f"导出失败，返回码: {process.returncode}")
                self.progress_label.config(text="导出失败")
                
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
    
    def validate_cookies(self):
        """验证cookies并估算容量"""
        cookies = self.cookies_text.get(1.0, tk.END).strip()
        
        if not cookies:
            messagebox.showerror("错误", "请输入有效的Cookies")
            return
        
        # 禁用验证按钮，防止重复点击
        self.validate_button.config(state=tk.DISABLED)
        self.capacity_result_var.set("正在验证和估算容量...")
        
        # 启动验证线程
        validate_thread = threading.Thread(target=self.run_cookie_validation, args=(cookies,))
        validate_thread.daemon = True
        validate_thread.start()
    
    def run_cookie_validation(self, cookies):
        """运行cookies验证和容量估算"""
        try:
            import sys
            # 构建验证命令，使用专门的验证模式
            cmd = [
                sys.executable, "xiaomi_to_evernote.py",
                "--cookies", cookies,
                "--validate-only",
                "--log-level", "INFO"
            ]
            
            self.add_log(f"执行验证命令: {' '.join(cmd)}")
            
            # 执行命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # 读取输出
            notes_count = 0
            estimated_size = 0
            validation_success = False
            detailed_output = []
            
            for line in iter(process.stdout.readline, ''):
                line = line.rstrip('\r\n')
                if line:
                    self.add_log(line)
                    detailed_output.append(line)
                    
                    # 解析输出，寻找验证结果
                    if "登录状态检查成功" in line:
                        validation_success = True
                    elif "共获取到" in line:
                        # 提取笔记数量 - 验证模式的输出格式
                        match = re.search(r'共获取到 (\d+) 条笔记', line)
                        if match:
                            notes_count = int(match.group(1))
                    elif "估算容量" in line:
                        # 提取估算容量
                        match = re.search(r'估算容量: ([\d.]+[KMGT]B?)', line)
                        if match:
                            estimated_size = match.group(1)
                    elif "估算总容量" in line:
                        # 提取估算容量 - 验证模式的输出格式
                        match = re.search(r'估算总容量: ([\d.]+) (KB|MB|GB|TB)', line)
                        if match:
                            estimated_size = f"{match.group(1)}{match.group(2)}"
            
            # 显示详细的输出信息，便于调试
            if not validation_success:
                self.add_log("\n=== 验证失败详细信息 ===")
                for line in detailed_output:
                    self.add_log(line)
                self.add_log("=== 验证失败详细信息结束 ===")
            
            process.wait()
            
            if validation_success and notes_count > 0:
                # 计算建议的导出条数
                suggested_chunk_size = 50
                if estimated_size:
                    # 根据容量调整建议条数
                    size_value = float(estimated_size[:-2])
                    size_unit = estimated_size[-2:].upper()
                    
                    # 转换为MB
                    if size_unit == 'KB':
                        size_in_mb = size_value / 1024
                    elif size_unit == 'MB':
                        size_in_mb = size_value
                    elif size_unit == 'GB':
                        size_in_mb = size_value * 1024
                    elif size_unit == 'TB':
                        size_in_mb = size_value * 1024 * 1024
                    else:
                        size_in_mb = size_value
                    
                    # 根据容量调整建议的导出条数
                    if size_in_mb > 5000:  # 大于5GB
                        suggested_chunk_size = 20
                    elif size_in_mb > 3000:  # 大于3GB
                        suggested_chunk_size = 30
                    elif size_in_mb > 1000:  # 大于1GB
                        suggested_chunk_size = 40
                    else:
                        suggested_chunk_size = 50  # 小于等于1GB，建议50条
                
                # 更新UI，添加实际容量说明
                self.capacity_result_var.set(f"Cookies有效，共 {notes_count} 条笔记，估算容量: {estimated_size} (实际容量以导出笔记的容量为准)")
                
                # 启用导出配置
                self.chunk_size_combo.set(str(suggested_chunk_size))
                self.chunk_size_combo.config(state="readonly")
                
                # 启用导出按钮
                self.export_button.config(state=tk.NORMAL)
                
                self.add_log(f"Cookies验证成功，建议每批导出 {suggested_chunk_size} 条笔记")
            else:
                self.capacity_result_var.set("Cookies无效或无法获取笔记信息")
                messagebox.showerror("验证失败", "Cookies无效或无法获取笔记信息，请检查Cookies是否正确")
                
        except Exception as e:
            self.add_log(f"验证过程中发生错误: {e}")
            self.capacity_result_var.set(f"验证失败: {str(e)}")
            messagebox.showerror("验证失败", f"验证过程中发生错误: {str(e)}")
        finally:
            # 恢复验证按钮状态
            self.validate_button.config(state=tk.NORMAL)
    
    def clear_fields(self):
        """清空输入字段"""
        self.cookies_text.delete(1.0, tk.END)
        self.capacity_result_var.set("")
        # 禁用导出配置和按钮
        self.chunk_size_combo.config(state="disabled")
        self.export_button.config(state="disabled")
        self.add_log("输入字段已清空")
    
    def on_chunk_size_change(self, event):
        """导出条数变化事件"""
        try:
            self.selected_chunk_size = int(self.chunk_size_var.get())
            self.add_log(f"已设置每批导出条数: {self.selected_chunk_size}")
            
            # 更新配置
            self.default_config['export']['chunk_size'] = self.selected_chunk_size
            self.save_config()
            
        except ValueError:
            self.add_log("无效的导出条数")


def main():
    """主函数"""
    root = tk.Tk()
    app = XiaomiNoteExporterGUI(root)
    
    # 设置窗口关闭事件
    def on_closing():
        if app.is_exporting:
            if messagebox.askokcancel("确认关闭", "导出正在进行中，确定要关闭吗？"):
                app.stop_export()
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
