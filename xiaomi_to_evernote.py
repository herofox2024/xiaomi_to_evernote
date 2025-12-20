#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小米笔记导出为Evernote格式(.enex)的Python工具 - 优化版本
优化点：
- 完善的错误处理和日志系统
- 配置管理
- 代码结构优化
- 类型提示完善
- 安全性改进
- 进度显示
- 配置文件支持
"""

import requests
import xml.etree.ElementTree as ET
import hashlib
import base64
import re
import json
import os
import logging
import yaml
from datetime import datetime
from typing import Dict, List, Optional, TypedDict, Any, Union
from urllib.parse import urljoin
from io import BytesIO
from pathlib import Path
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


# 类型定义
class NoteEntry(TypedDict):
    """笔记条目类型定义"""
    id: str
    title: str
    content: str
    createDate: int
    modifyDate: int
    folderId: int
    extraInfo: str

class FolderInfo(TypedDict):
    """文件夹信息类型定义"""
    subject: str
    notes: List[str]

class ResourceData(TypedDict):
    """资源数据类型定义"""
    data: str
    hash: str
    width: int
    height: int
    mime: str

@dataclass
class ExportConfig:
    """导出配置"""
    chunk_size: int = 50
    output_dir: str = "exported_notes"
    timeout: int = 30
    max_retries: int = 3
    max_workers: int = 5
    log_level: str = "INFO"
    log_file: Optional[str] = "xiaomi_export.log"
    enable_progress_bar: bool = True
    progress_report: bool = False  # 输出结构化进度信息


class Logger:
    """日志管理器"""
    
    @staticmethod
    def setup_logger(config: ExportConfig) -> logging.Logger:
        """设置日志系统"""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, config.log_level.upper()))
        
        # 清除现有处理器
        logger.handlers.clear()
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, config.log_level.upper()))
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 文件处理器（如果指定）
        if config.log_file:
            # 确保日志文件路径是绝对路径
            log_file_path = os.path.abspath(config.log_file)
            try:
                file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
                file_handler.setLevel(getattr(logging, config.log_level.upper()))
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
                logger.debug(f"日志文件已配置: {log_file_path}")
                # 立即写入一条测试日志
                logger.info(f"日志系统初始化完成，日志文件: {log_file_path}")
            except Exception as e:
                # 如果文件创建失败，使用控制台输出错误
                logger.error(f"创建日志文件失败: {e}")
                # 确保根日志记录器也配置了文件输出
                root_logger = logging.getLogger()
                for handler in root_logger.handlers:
                    if isinstance(handler, logging.FileHandler):
                        root_logger.removeHandler(handler)
                try:
                    root_file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
                    root_file_handler.setLevel(getattr(logging, config.log_level.upper()))
                    root_file_handler.setFormatter(formatter)
                    root_logger.addHandler(root_file_handler)
                    logger.error(f"已为根日志记录器配置日志文件: {log_file_path}")
                except Exception as e2:
                    logger.error(f"为根日志记录器创建日志文件也失败: {e2}")
        
        return logger


class Config:
    """配置管理类"""
    
    BASE_URL = "https://i.mi.com/"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    DEFAULT_HEADERS = {
        'User-Agent': USER_AGENT,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Content-Type': 'application/json;charset=UTF-8',
    }
    
    @classmethod
    def load_from_file(cls, config_file: str) -> ExportConfig:
        """从配置文件加载设置"""
        config = ExportConfig()
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                # 更新配置
                for key, value in config_data.get('export', {}).items():
                    if hasattr(config, key):
                        setattr(config, key, value)
                        
                for key, value in config_data.get('logging', {}).items():
                    if hasattr(config, key):
                        # 确保日志文件始终被设置，即使配置文件中为null
                        if key == 'log_file' and value is None:
                            value = "xiaomi_export.log"
                        setattr(config, key, value)
                        
                # 处理progress_report参数
                if 'progress_report' in config_data.get('export', {}):
                    config.progress_report = config_data['export']['progress_report']
                        
            except Exception as e:
                logging.warning(f"配置文件加载失败: {e}，使用默认配置")
        
        return config
    
    @classmethod
    def save_to_file(cls, config: ExportConfig, config_file: str) -> None:
        """保存配置到文件"""
        config_data = {
            'export': {
                'chunk_size': config.chunk_size,
                'output_dir': config.output_dir,
                'timeout': config.timeout,
                'max_retries': config.max_retries,
                'max_workers': config.max_workers,
                'enable_progress_bar': config.enable_progress_bar,
                'progress_report': config.progress_report
            },
            'logging': {
                'log_level': config.log_level,
                'log_file': config.log_file
            }
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)


class ValidationError(Exception):
    """验证错误异常"""
    pass


class NetworkError(Exception):
    """网络错误异常"""
    pass


class XiaomiNoteExporter:
    """小米笔记导出器 - 优化版本"""
    
    def __init__(self, cookies_str: Optional[str] = None, config: Optional[ExportConfig] = None):
        self.config = config or ExportConfig()
        self.logger = Logger.setup_logger(self.config)
        
        self.base_url = Config.BASE_URL
        self.session = requests.Session()
        self.session.headers.update(Config.DEFAULT_HEADERS)
        
        # 创建输出目录
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        # 设置cookies
        if cookies_str:
            self.set_cookies_from_string(cookies_str)
        
        # 文件夹列表
        self.folder_list: Dict[int, FolderInfo] = {
            0: {"subject": "未分类", "notes": []},
            2: {"subject": "私密笔记", "notes": []}
        }
        
        # 线程锁（用于线程安全）
        self._lock = threading.Lock()
        
        self.logger.info("小米笔记导出器初始化完成")
    
    def __del__(self):
        """析构函数，释放资源"""
        try:
            self.session.close()
        except Exception as e:
            pass
    
    def set_cookies_from_string(self, cookies_str: str) -> None:
        """从字符串设置cookies"""
        try:
            self._validate_cookies(cookies_str)
            
            cookies_dict = {}
            for cookie in cookies_str.split(';'):
                if '=' in cookie:
                    key, value = cookie.strip().split('=', 1)
                    cookies_dict[key] = value
            
            self.session.cookies.update(cookies_dict)
            self.logger.info(f"已设置 {len(cookies_dict)} 个cookies")
            
        except ValidationError as e:
            self.logger.error(f"Cookies验证失败: {e}")
            raise
    
    def _validate_cookies(self, cookies_str: str) -> None:
        """验证cookies格式"""
        if not cookies_str or not isinstance(cookies_str, str):
            raise ValidationError("Cookies字符串不能为空")
        
        cookie_pairs = cookies_str.split(';')
        for cookie in cookie_pairs:
            if cookie.strip() and '=' not in cookie:
                raise ValidationError(f"无效的cookie格式: {cookie}")
    
    def check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            test_url = urljoin(self.base_url, "note/full/page/?limit=1")
            response = self.session.get(test_url, timeout=self.config.timeout)
            
            if response.status_code == 200:
                self.logger.info("登录状态检查成功")
                return True
            elif response.status_code == 401:
                self.logger.warning("登录状态无效，cookies已过期，请重新获取")
                return False
            else:
                self.logger.warning(f"登录状态检查失败，状态码: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            self.logger.error(f"网络请求失败: {e}")
            return False
        except Exception as e:
            self.logger.error(f"登录状态检查时发生未知错误: {e}")
            return False
    
    def to_time_string(self, timestamp: Union[int, float]) -> str:
        """转换时间为Evernote格式的时间字符串"""
        try:
            if timestamp > 10000000000:  # 如果是毫秒时间戳
                timestamp = timestamp / 1000
            
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y%m%dT%H%M%SZ")
        except (ValueError, OSError) as e:
            self.logger.warning(f"时间戳转换失败: {timestamp}, {e}")
            return datetime.now().strftime("%Y%m%dT%H%M%SZ")
    
    def sanitize_for_xml(self, content: str) -> str:
        """清理XML特殊字符"""
        if not content:
            return ""
        
        replacements = {
            '&': '&amp;',
            '<': '&lt;', 
            '>': '&gt;',
            '"': '&quot;',
            "'": '&apos;'
        }
        
        for old, new in replacements.items():
            content = content.replace(old, new)
        
        return content
    
    def md5_digest(self, data: bytes) -> str:
        """计算MD5哈希"""
        return hashlib.md5(data).hexdigest()
    
    def base64_encode(self, data: bytes) -> str:
        """Base64编码"""
        return base64.b64encode(data).decode('utf-8')
    
    def download_note(self, note_id: str) -> Dict[str, Any]:
        """下载单个笔记内容"""
        try:
            url = urljoin(self.base_url, f"note/note/{note_id}/")
            response = self.session.get(url, timeout=self.config.timeout)
            
            # 检查401错误，明确提示cookies过期
            if response.status_code == 401:
                error_msg = f"下载笔记 {note_id} 失败: 登录已过期，请重新获取cookies"
                self.logger.error(error_msg)
                raise NetworkError(error_msg)
            
            response.raise_for_status()
            
            data = response.json()
            self.logger.debug(f"笔记 {note_id} 下载成功")
            return data
            
        except requests.RequestException as e:
            self.logger.error(f"下载笔记 {note_id} 失败: {e}")
            # 区分401错误和其他网络错误
            if "401" in str(e):
                raise NetworkError(f"登录已过期，请重新获取cookies")
            raise NetworkError(f"下载笔记失败: {e}")
        except json.JSONDecodeError as e:
            self.logger.error(f"笔记 {note_id} JSON解析失败: {e}")
            raise NetworkError(f"JSON解析失败: {e}")
    
    def download_resource(self, url: str) -> ResourceData:
        """下载资源文件（图片等）"""
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            
            # 检查401错误，明确提示cookies过期
            if response.status_code == 401:
                error_msg = f"下载资源失败: 登录已过期，请重新获取cookies"
                self.logger.error(error_msg)
                raise NetworkError(error_msg)
            
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            raw_data = response.content
            
            if not content_type.startswith('image/'):
                raise ValueError(f"不支持的资源类型: {content_type}")
            
            # 处理图片
            width, height = 0, 0
            if HAS_PIL:
                try:
                    with Image.open(BytesIO(raw_data)) as img:
                        width, height = img.size
                except Exception as e:
                    self.logger.warning(f"图片尺寸检测失败: {e}")
            
            return {
                'data': self.base64_encode(raw_data),
                'hash': self.md5_digest(raw_data),
                'width': width,
                'height': height,
                'mime': content_type
            }
            
        except requests.RequestException as e:
            self.logger.error(f"下载资源失败: {e}")
            # 区分401错误和其他网络错误
            if "401" in str(e):
                raise NetworkError(f"登录已过期，请重新获取cookies")
            raise NetworkError(f"下载资源失败: {e}")
    
    def process_html_content(self, content: str) -> str:
        """处理HTML内容，转换为Evernote格式"""
        if not content:
            return ""
        
        # 基本的标签替换
        replacements = [
            (r'<text>(.*?)</text>', r'<div>\1</div>'),
            (r'<new-format>(.*?)</new-format>', r'\1'),
            (r'<delete>(.*?)</delete>', r'<s>\1</s>'),
            (r'<input type="checkbox" checked="([^"]*)"', r'<en-todo checked="\1"'),
            (r'<size>(.*?)</size>', r'<font style="font-size:18pt">\1</font>'),
            (r'<mid-size>(.*?)</mid-size>', r'<font style="font-size:16pt">\1</font>'),
            (r'<h3-size>(.*?)</h3-size>', r'<font style="font-size:14pt">\1</font>'),
            (r'<background color="([^"]*)">(.*?)</background>', 
             r'<span style="background-color:\1;-evernote-highlight:true;">\2</span>')
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # 替换换行符
        content = content.replace('\n', '\n\n')
        
        return content
    
    def create_enex_document(self) -> ET.ElementTree:
        """创建Evernote导出文档"""
        root = ET.Element("en-export")
        root.set("export-date", self.to_time_string(time.time()))
        root.set("application", "Evernote")
        root.set("version", "10.89.2")
        
        return ET.ElementTree(root)
    
    def download_notes_recursive(self, sync_tag: Optional[str] = None, 
                                note_collection: Optional[List] = None) -> List:
        """递归下载笔记列表"""
        if note_collection is None:
            note_collection = []
        
        url = urljoin(self.base_url, "note/full/page/")
        params = {"limit": 200}
        if sync_tag:
            params["syncTag"] = sync_tag
        
        self.logger.info(f"获取笔记列表，syncTag: {sync_tag}")
        
        try:
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            
            # 检查授权状态
            if response.status_code == 401:
                raise NetworkError("未授权访问，请检查cookies是否有效")
            
            response.raise_for_status()
            data = response.json()
            
            # 更新文件夹列表
            for folder in data.get('data', {}).get('folders', []):
                self.folder_list[folder['id']] = {
                    "subject": folder['subject'],
                    "notes": []
                }
            
            # 收集笔记
            entries = data.get('data', {}).get('entries', [])
            note_collection.extend(entries)
            
            self.logger.info(f"本次获取 {len(entries)} 条笔记，总共 {len(note_collection)} 条")
            
            if not entries:
                # 处理最终笔记分配
                for entry in note_collection:
                    folder = self.folder_list.get(entry.get('folderId'))
                    if folder:
                        folder['notes'].append(entry['id'])
                    else:
                        self.logger.warning(f"找不到文件夹ID {entry.get('folderId')} 对应的文件夹")
                
                return note_collection
            else:
                # 继续递归下载
                next_sync_tag = data.get('data', {}).get('syncTag')
                return self.download_notes_recursive(next_sync_tag, note_collection)
                
        except requests.RequestException as e:
            self.logger.error(f"获取笔记列表失败: {e}")
            raise NetworkError(f"获取笔记列表失败: {e}")
    
    def process_single_note(self, note_id: str, xml_root: ET.Element) -> bool:
        """处理单个笔记并添加到XML根节点"""
        try:
            note_data = self.download_note(note_id)
            note_entry = note_data.get('data', {}).get('entry', {})
            
            # 创建笔记元素
            note_elem = ET.SubElement(xml_root, "note")
            
            # 标题
            title_elem = ET.SubElement(note_elem, "title")
            extra_info = note_entry.get('extraInfo', '{}')
            title = "无标题笔记"
            try:
                title_json = json.loads(extra_info)
                title = title_json.get('title', '无标题笔记')
            except (json.JSONDecodeError, TypeError):
                pass
            
            title_elem.text = self.sanitize_for_xml(title)
            
            # 日期
            create_date = ET.SubElement(note_elem, "created")
            create_timestamp = note_entry.get('createDate', 0)
            create_date.text = self.to_time_string(create_timestamp)
            
            update_date = ET.SubElement(note_elem, "updated") 
            update_timestamp = note_entry.get('modifyDate', 0)
            update_date.text = self.to_time_string(update_timestamp)
            
            # 笔记属性
            note_attr = ET.SubElement(note_elem, "note-attributes")
            ET.SubElement(note_attr, "author")
            ET.SubElement(note_attr, "source")
            ET.SubElement(note_attr, "source-application")
            
            # 内容
            content_elem = ET.SubElement(note_elem, "content")
            original_content = note_entry.get('content', '')
            
            # 处理嵌入的资源（优化正则表达式性能）
            processed_content = original_content
            
            # 使用更高效的正则表达式，避免贪婪匹配
            img_pattern = re.compile(r'☺([^<]+?)<[^/]+/><[^/]*/>')
            img_matches = img_pattern.finditer(processed_content)
            
            # 收集所有匹配项，避免在循环中修改字符串
            replacements = []
            for match in img_matches:
                try:
                    file_id = match.group(1)
                    img_url = f"https://i.mi.com/file/full?type=note_img&fileid={file_id}"
                    
                    # 下载资源
                    resource_data = self.download_resource(img_url)
                    
                    # 创建资源元素
                    resource_elem = ET.SubElement(note_elem, "resource")
                    
                    data_elem = ET.SubElement(resource_elem, "data")
                    data_elem.set("encoding", "base64")
                    data_elem.text = resource_data['data']
                    
                    mime_elem = ET.SubElement(resource_elem, "mime")
                    mime_elem.text = resource_data['mime']
                    
                    # 图片尺寸
                    width_elem = ET.SubElement(resource_elem, "width")
                    width_elem.text = str(resource_data['width'])
                    height_elem = ET.SubElement(resource_elem, "height")
                    height_elem.text = str(resource_data['height'])
                    
                    # 资源属性
                    resource_attr = ET.SubElement(resource_elem, "resource-attributes")
                    ET.SubElement(resource_attr, "source-url")
                    
                    file_name_elem = ET.SubElement(resource_attr, "file-name")
                    major_type, sub_type = resource_data['mime'].split('/')
                    file_name_elem.text = f"minote_{resource_data['hash']}.{sub_type}"
                    
                    # 记录替换信息
                    replacement = f'<div><en-media type="{resource_data["mime"]}" hash="{resource_data["hash"]}"/></div>'
                    replacements.append((match.group(0), replacement))
                    
                except Exception as e:
                    self.logger.warning(f"处理资源 {file_id} 时出错: {e}")
                    continue
            
            # 执行所有替换
            for old, new in replacements:
                processed_content = processed_content.replace(old, new)
            
            # 处理HTML内容
            processed_content = self.process_html_content(processed_content)
            
            # 创建CDATA内容
            enex_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">
<en-note><div>{processed_content}</div></en-note>'''
            
            content_elem.text = enex_content
            
            self.logger.debug(f"笔记 {note_id} 处理成功")
            return True
            
        except Exception as e:
            self.logger.error(f"处理笔记 {note_id} 时出错: {e}", exc_info=True)
            return False
    
    def download_resources_batch(self, urls: List[str]) -> List[ResourceData]:
        """批量下载资源文件"""
        resources = []
        
        if not urls:
            return resources
        
        self.logger.info(f"开始批量下载 {len(urls)} 个资源文件")
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # 提交所有任务
            future_to_url = {
                executor.submit(self.download_resource, url): url 
                for url in urls
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    resource = future.result()
                    resources.append(resource)
                    self.logger.debug(f"资源下载成功: {url}")
                except Exception as e:
                    self.logger.warning(f"资源下载失败 {url}: {e}")
        
        self.logger.info(f"批量下载完成，成功 {len(resources)}/{len(urls)} 个")
        return resources
    
    def _save_chunk(self, xml_tree: ET.ElementTree, filename: str, chunk_info: Dict) -> None:
        """保存单个分块"""
        try:
            filepath = os.path.join(self.config.output_dir, filename)
            xml_tree.write(filepath, encoding='utf-8', xml_declaration=True)
            self.logger.info(f"已导出分块: {filepath} (包含 {chunk_info['count']} 条笔记)")
        except Exception as e:
            self.logger.error(f"保存分块失败 {filename}: {e}")
            raise
    
    def _get_progress_bar(self, total: int, desc: str = "处理进度") -> Any:
        """获取进度条"""
        if HAS_TQDM and self.config.enable_progress_bar:
            return tqdm(total=total, desc=desc)
        else:
            # 简单的进度显示
            class SimpleProgress:
                def __init__(self, total):
                    self.total = total
                    self.current = 0
                
                def update(self, n=1):
                    self.current += n
                    percentage = (self.current / self.total) * 100
                    print(f"\r{desc}: {self.current}/{self.total} ({percentage:.1f}%)", end='', flush=True)
                
                def close(self):
                    print()  # 换行
            
            return SimpleProgress(total)
    
    def handle_folder_export(self) -> None:
        """处理文件夹导出 - 优化版本"""
        total_exported = 0
        total_failed = 0
        
        for folder_id, folder in self.folder_list.items():
            if not folder['notes']:
                continue
            
            folder_name = folder['subject']
            notes_count = len(folder['notes'])
            self.logger.info(f"开始导出文件夹: {folder_name} (包含 {notes_count} 条笔记)")
            
            # 重置计数器
            successful_notes = 0
            current_chunk_notes = 0
            chunk_number = 1
            
            # 使用进度条
            progress = self._get_progress_bar(notes_count, f"导出 {folder_name}")
            
            # 为每个分块创建单独的XML文档
            xml_tree = self.create_enex_document()
            xml_root = xml_tree.getroot()
            
            for i, note_id in enumerate(folder['notes']):
                try:
                    # 每处理20条笔记检查一次登录状态
                    if i > 0 and i % 20 == 0:
                        self.logger.info(f"已处理 {i} 条笔记，检查登录状态...")
                        if not self.check_login_status():
                            raise NetworkError("登录已过期，请重新获取cookies")
                    
                    # 处理单个笔记
                    if self.process_single_note(note_id, xml_root):
                        successful_notes += 1
                        current_chunk_notes += 1
                        total_exported += 1
                    else:
                        total_failed += 1
                    
                    # 输出结构化进度信息
                    if self.config.progress_report:
                        progress_data = {
                            "type": "progress",
                            "current": i + 1,
                            "total": notes_count,
                            "folder": folder_name,
                            "successful": successful_notes,
                            "failed": total_failed,
                            "percentage": round((i + 1) / notes_count * 100, 2)
                        }
                        print(f"PROGRESS:{json.dumps(progress_data)}")
                    
                    # 达到分块大小时保存当前文件
                    if current_chunk_notes >= self.config.chunk_size and i < notes_count - 1:
                        # 保存当前分块
                        if current_chunk_notes > 0:
                            filename = f"{self._sanitize_filename(folder_name)}_part{chunk_number:02d}.enex"
                            chunk_info = {'count': current_chunk_notes}
                            self._save_chunk(xml_tree, filename, chunk_info)
                        
                        # 清理并创建新的XML文档用于下一分块
                        del xml_tree
                        del xml_root
                        
                        xml_tree = self.create_enex_document()
                        xml_root = xml_tree.getroot()
                        current_chunk_notes = 0
                        chunk_number += 1
                
                except Exception as e:
                    self.logger.error(f"处理笔记 {note_id} 时发生错误: {e}", exc_info=True)
                    total_failed += 1
                
                finally:
                    progress.update(1)
            
            progress.close()
            
            # 保存最后一个分块（或唯一的分块）
            if current_chunk_notes > 0:
                if notes_count > self.config.chunk_size:
                    filename = f"{self._sanitize_filename(folder_name)}_part{chunk_number:02d}.enex"
                else:
                    filename = f"{self._sanitize_filename(folder_name)}.enex"
                
                chunk_info = {'count': current_chunk_notes}
                self._save_chunk(xml_tree, filename, chunk_info)
            
            # 清理资源
            del xml_tree
            del xml_root
            
            self.logger.info(f"文件夹 {folder_name} 导出完成 (成功 {successful_notes}/{notes_count} 条笔记)")
        
        self.logger.info(f"所有文件夹导出完成！总共导出 {total_exported} 条笔记，失败 {total_failed} 条")
        self.logger.info(f"文件保存在: {os.path.abspath(self.config.output_dir)}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        # 移除或替换文件名中的非法字符
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        
        # 限制长度
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename.strip()
    
    def validate_and_estimate(self) -> None:
        """验证cookies并估算容量，不实际导出笔记"""
        self.logger.info("开始验证cookies并估算容量...")
        
        # 检查登录状态
        if not self.check_login_status():
            raise NetworkError("登录状态无效，请检查cookies")
        
        self.logger.info("登录状态检查成功")
        
        try:
            # 获取笔记列表
            note_list = self.download_notes_recursive()
            total_notes = len(note_list)
            self.logger.info(f"共获取到 {total_notes} 条笔记")
            
            # 改进容量估算：每条笔记平均200KB（根据用户反馈实际约146KB）
            avg_size_kb = 200
            estimated_size_kb = total_notes * avg_size_kb
            estimated_size_mb = round(estimated_size_kb / 1024, 1)
            
            self.logger.info(f"估算总容量: {estimated_size_mb} MB (每条笔记平均 {avg_size_kb} KB)")
            
            # 输出估算结果，格式便于GUI解析
            print(f"估算容量: {estimated_size_mb}MB")
            print(f"笔记数量: {total_notes}")
            
            self.logger.info("容量估算完成")
            
        except Exception as e:
            self.logger.error(f"验证和估算过程中出错: {e}")
            raise
    
    def export_notes(self) -> None:
        """主导出函数"""
        self.logger.info("开始导出小米笔记...")
        self.logger.info(f"分批大小: {self.config.chunk_size} 条笔记/文件")
        self.logger.info(f"输出目录: {self.config.output_dir}")
        
        # 输出初始进度
        if self.config.progress_report:
            progress_data = {
                "type": "progress",
                "current": 0,
                "total": 100,
                "folder": "准备中",
                "successful": 0,
                "failed": 0,
                "percentage": 0.0
            }
            print(f"PROGRESS:{json.dumps(progress_data)}")
        
        # 检查登录状态
        if not self.check_login_status():
            raise NetworkError("登录状态无效，请检查cookies")
        
        # 登录成功，更新进度
        if self.config.progress_report:
            progress_data = {
                "type": "progress",
                "current": 10,
                "total": 100,
                "folder": "准备中",
                "successful": 0,
                "failed": 0,
                "percentage": 10.0
            }
            print(f"PROGRESS:{json.dumps(progress_data)}")
        
        try:
            # 下载笔记列表
            self.logger.info("开始获取笔记列表...")
            self.download_notes_recursive()
            
            # 笔记列表获取完成，更新进度
            if self.config.progress_report:
                progress_data = {
                    "type": "progress",
                    "current": 30,
                    "total": 100,
                    "folder": "准备中",
                    "successful": 0,
                    "failed": 0,
                    "percentage": 30.0
                }
                print(f"PROGRESS:{json.dumps(progress_data)}")
            
            # 导出各个文件夹
            self.logger.info("开始导出文件夹...")
            self.handle_folder_export()
            
            # 导出完成，更新进度
            if self.config.progress_report:
                progress_data = {
                    "type": "progress",
                    "current": 100,
                    "total": 100,
                    "folder": "完成",
                    "successful": 0,
                    "failed": 0,
                    "percentage": 100.0
                }
                print(f"PROGRESS:{json.dumps(progress_data)}")
            
            self.logger.info("导出完成!")
            
        except Exception as e:
            self.logger.error(f"导出过程中出错: {e}")
            # 导出失败，更新进度
            if self.config.progress_report:
                progress_data = {
                    "type": "progress",
                    "current": 0,
                    "total": 100,
                    "folder": "失败",
                    "successful": 0,
                    "failed": 1,
                    "percentage": 0.0
                }
                print(f"PROGRESS:{json.dumps(progress_data)}")
            raise


def get_cookies_from_browser():
    """从浏览器获取cookies的说明"""
    print("""
请按以下步骤获取小米云笔记的cookies:

1. 在Chrome浏览器中登录 https://i.mi.com/note/h5#/
2. 按F12打开开发者工具
3. 切换到 Network (网络) 标签
4. 刷新页面
5. 找到imi.com的请求，点击查看标头(Headers)，在标头中找到Cookie字段
6. 复制Cookie字段的值，这就是所需的cookies字符串

或者直接在控制台运行:
document.cookie

然后将cookies字符串作为参数传递给程序。
    """)


def create_default_config(config_file: str = "config.yaml") -> None:
    """创建默认配置文件"""
    config = ExportConfig()
    Config.save_to_file(config, config_file)
    print(f"默认配置文件已创建: {config_file}")


def main():
    """主函数"""
    import sys
    import argparse
    
    # 版本信息
    VERSION = "1.0.5"
    
    print(f"小米笔记导出工具 - 优化版本 v{VERSION}")
    print("=" * 50)
    
    parser = argparse.ArgumentParser(
        description='小米笔记导出工具 - 将小米云笔记导出为Evernote格式(.enex)',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
    1. 基本使用:
       python xiaomi_to_evernote.py --cookies "your_cookies_string"
    
    2. 使用配置文件:
       python xiaomi_to_evernote.py --create-config  # 创建默认配置
       python xiaomi_to_evernote.py --cookies "your_cookies_string" --config my_config.yaml
    
    3. 自定义参数:
       python xiaomi_to_evernote.py \
           --cookies "your_cookies_string" \
           --chunk-size 20 \
           --output-dir my_notes \
           --log-level DEBUG
        """
    )
    
    parser.add_argument('--cookies', '-c', help='小米云笔记的cookies字符串，必填参数')
    parser.add_argument('--chunk-size', '-s', type=int, help='每批导出的笔记数量，默认: 50')
    parser.add_argument('--output-dir', '-o', help='输出目录，默认: exported_notes')
    parser.add_argument('--config', '-f', default='config.yaml', help='配置文件路径，默认: config.yaml')
    parser.add_argument('--create-config', action='store_true', help='创建默认配置文件')
    parser.add_argument('--timeout', '-t', type=int, help='请求超时时间（秒），默认: 30')
    parser.add_argument('--max-workers', '-w', type=int, help='并发下载工作线程数，默认: 5')
    parser.add_argument('--log-level', '-l', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       help='日志级别，默认: INFO')
    parser.add_argument('--no-progress', action='store_true', help='禁用进度条')
    parser.add_argument('--progress-report', action='store_true', help='输出结构化进度信息')
    parser.add_argument('--validate-only', action='store_true', help='仅验证cookies并估算容量，不实际导出')
    parser.add_argument('--version', '-v', action='version', version=f'%(prog)s v{VERSION}')
    
    args = parser.parse_args()
    
    # 日志配置
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 创建默认配置
    if args.create_config:
        print("创建默认配置文件...")
        create_default_config(args.config)
        print("配置文件已创建成功！")
        print(f"配置文件路径: {os.path.abspath(args.config)}")
        print("您可以编辑此文件自定义导出设置。")
        return
    
    # 加载配置
    print(f"加载配置文件: {args.config}...")
    try:
        config = Config.load_from_file(args.config)
        print("配置文件加载成功！")
        
        # 命令行参数覆盖配置文件
        if args.chunk_size:
            config.chunk_size = args.chunk_size
            print(f"  分块大小: {config.chunk_size} 条/文件")
        if args.output_dir:
            config.output_dir = args.output_dir
        if args.timeout:
            config.timeout = args.timeout
            print(f"  请求超时: {config.timeout} 秒")
        if args.max_workers:
            config.max_workers = args.max_workers
            print(f"  并发线程: {config.max_workers} 个")
        if args.log_level:
            config.log_level = args.log_level
            print(f"  日志级别: {config.log_level}")
        if args.no_progress:
            config.enable_progress_bar = False
            print(f"  进度条: 已禁用")
        
        # 处理进度报告参数
        config.progress_report = args.progress_report
        if args.progress_report:
            print(f"  进度报告: 已启用")
            
        print(f"  输出目录: {config.output_dir}")
        print(f"  日志文件: {'启用' if config.log_file else '仅控制台'}")
        
    except Exception as e:
        print(f"警告: 配置文件加载失败: {e}")
        print("将使用默认配置继续导出...")
        config = ExportConfig()
        # 确保进度报告参数被设置
        config.progress_report = args.progress_report
    
    # 获取cookies
    cookies_str = args.cookies
    if not cookies_str:
        print("\n[提示] 未提供cookies参数")
        get_cookies_from_browser()
        print("=" * 50)
        cookies_str = input("请输入cookies字符串: ").strip()
        if not cookies_str:
            print("错误: cookies不能为空")
            print("请重新运行程序并提供有效的cookies")
            input("\n按Enter键退出...")
            sys.exit(1)
    
    print("\n[开始导出]")
    print("=" * 50)
    
    try:
        # 创建导出器
        exporter = XiaomiNoteExporter(
            cookies_str=cookies_str,
            config=config
        )
        
        # 检查是否仅验证模式
        if args.validate_only:
            print("\n[验证模式] 开始验证cookies并估算容量...")
            try:
                # 只执行验证和容量估算
                exporter.validate_and_estimate()
            except Exception as e:
                print(f"\n验证失败: {e}")
                sys.exit(1)
            finally:
                print("\n验证模式完成")
                sys.exit(0)
        
        # 开始导出
        exporter.export_notes()
        
        print("\n" + "=" * 50)
        print("导出完成！")
        print(f"导出文件保存在: {os.path.abspath(config.output_dir)}")
        print("\n提示:")
        print("  1. 导出的.enex文件可以直接导入到Evernote或其他支持该格式的笔记应用")
        print("  2. 如果遇到问题，请查看日志文件获取详细信息")
        print("  3. 若cookies过期，请重新获取并再次运行程序")
        
    except (NetworkError, ValidationError) as e:
        print("\n" + "=" * 50)
        error_msg = f"错误: {e}"
        print(error_msg)
        logging.error(error_msg)
        print("\n解决建议:")
        if "过期" in str(e) or "401" in str(e):
            print("  - 请重新获取小米云笔记的cookies")
            print("  - 确保cookies包含完整的认证信息")
            print("  - 建议在获取cookies后立即运行导出程序")
        else:
            print("  - 检查网络连接是否正常")
            print("  - 确保cookies正确有效")
            print("  - 尝试减小分块大小和并发线程数")
        input("\n按Enter键退出...")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        print("导出已取消")
        input("\n按Enter键退出...")
        sys.exit(1)
    except Exception as e:
        print("\n" + "=" * 50)
        error_msg = f"未知错误: {e}"
        print(error_msg)
        logging.error(error_msg, exc_info=True)
        print("\n解决建议:")
        print("  - 查看日志文件获取详细错误信息")
        print("  - 尝试使用--log-level DEBUG获取更详细的日志")
        print("  - 检查命令行参数是否正确")
        print("  - 确保Python版本 >= 3.7")
        input("\n按Enter键退出...")
        sys.exit(1)


if __name__ == "__main__":
    main()