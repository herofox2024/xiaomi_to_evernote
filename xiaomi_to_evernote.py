#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小米笔记导出为Evernote格式(.enex)的Python工具 - 修复分批导出覆盖问题
"""

import requests
import xml.etree.ElementTree as ET
import hashlib
import base64
import re
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin
from io import BytesIO

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("警告: 未安装PIL/Pillow，图片尺寸检测功能不可用")

class XiaomiNoteExporter:
    """小米笔记导出器 - 修复分批导出覆盖问题"""
    
    def __init__(self, cookies_str=None, chunk_size=50, output_dir="exported_notes"):
        self.base_url = "https://i.mi.com/"
        self.session = requests.Session()
        self.chunk_size = chunk_size  # 每批导出的笔记数量
        self.output_dir = output_dir
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 设置请求头，模拟浏览器
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Content-Type': 'application/json;charset=UTF-8',
        })
        
        # 如果有cookies，设置cookies
        if cookies_str:
            self.set_cookies_from_string(cookies_str)
        
        self.folder_list = {
            0: {"subject": "未分类", "notes": []},
            2: {"subject": "私密笔记", "notes": []}
        }
    
    def set_cookies_from_string(self, cookies_str):
        """从字符串设置cookies"""
        cookies_dict = {}
        for cookie in cookies_str.split(';'):
            if '=' in cookie:
                key, value = cookie.strip().split('=', 1)
                cookies_dict[key] = value
        
        # 更新session的cookies
        self.session.cookies.update(cookies_dict)
        print(f"已设置 {len(cookies_dict)} 个cookies")
    
    def check_login_status(self) -> bool:
        """检查登录状态"""
        try:
            test_url = urljoin(self.base_url, "note/full/page/?limit=1")
            response = self.session.get(test_url)
            return response.status_code == 200
        except:
            return False
    
    def to_time_string(self, timestamp: datetime) -> str:
        """转换时间为Evernote格式的时间字符串"""
        return timestamp.strftime("%Y%m%dT%H%M%SZ")
    
    def sanitize_for_xml(self, content: str) -> str:
        """清理XML特殊字符"""
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
    
    def download_note(self, note_id: str) -> Dict:
        """下载单个笔记内容"""
        url = urljoin(self.base_url, f"note/note/{note_id}/")
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
    
    def download_resource(self, url: str) -> Dict:
        """下载资源文件（图片等）"""
        response = self.session.get(url)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        raw_data = response.content
        
        if content_type.startswith('image/'):
            # 处理图片
            width, height = 0, 0
            if HAS_PIL:
                try:
                    with Image.open(BytesIO(raw_data)) as img:
                        width, height = img.size
                except:
                    pass
            
            return {
                'data': self.base64_encode(raw_data),
                'hash': self.md5_digest(raw_data),
                'width': width,
                'height': height,
                'mime': content_type
            }
        else:
            raise ValueError(f"不支持的资源类型: {content_type}")
    
    def process_html_content(self, content: str) -> str:
        """处理HTML内容，转换为Evernote格式"""
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
            content = re.sub(pattern, replacement, content)
        
        # 替换换行符
        content = content.replace('\n', '\n\n')
        
        return content
    
    def create_enex_document(self) -> ET.ElementTree:
        """创建Evernote导出文档"""
        root = ET.Element("en-export")
        root.set("export-date", self.to_time_string(datetime.utcnow()))
        root.set("application", "Evernote")
        root.set("version", "10.89.2")
        
        return ET.ElementTree(root)
    
    def download_notes_recursive(self, sync_tag: Optional[str] = None, 
                                note_collection: List = None) -> List:
        """递归下载笔记列表"""
        if note_collection is None:
            note_collection = []
        
        url = urljoin(self.base_url, "note/full/page/")
        params = {"limit": 200}
        if sync_tag:
            params["syncTag"] = sync_tag
        
        print(f"获取笔记列表，syncTag: {sync_tag}")
        response = self.session.get(url, params=params)
        
        # 检查授权状态
        if response.status_code == 401:
            raise Exception("未授权访问，请检查cookies是否有效")
        
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
        
        print(f"本次获取 {len(entries)} 条笔记，总共 {len(note_collection)} 条")
        
        if not entries:
            # 处理最终笔记分配
            for entry in note_collection:
                folder = self.folder_list.get(entry.get('folderId'))
                if folder:
                    folder['notes'].append(entry['id'])
                else:
                    print(f"警告: 找不到文件夹ID {entry.get('folderId')} 对应的文件夹")
            
            return note_collection
        else:
            # 继续递归下载
            next_sync_tag = data.get('data', {}).get('syncTag')
            return self.download_notes_recursive(next_sync_tag, note_collection)

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
            except:
                pass
            title_elem.text = title
            
            # 日期
            create_date = ET.SubElement(note_elem, "created")
            create_timestamp = note_entry.get('createDate', 0)
            if create_timestamp > 10000000000:  # 如果是毫秒时间戳
                create_timestamp = create_timestamp / 1000
            create_date.text = self.to_time_string(datetime.fromtimestamp(create_timestamp))
            
            update_date = ET.SubElement(note_elem, "updated") 
            update_timestamp = note_entry.get('modifyDate', 0)
            if update_timestamp > 10000000000:  # 如果是毫秒时间戳
                update_timestamp = update_timestamp / 1000
            update_date.text = self.to_time_string(datetime.fromtimestamp(update_timestamp))
            
            # 笔记属性
            note_attr = ET.SubElement(note_elem, "note-attributes")
            ET.SubElement(note_attr, "author")
            ET.SubElement(note_attr, "source")
            ET.SubElement(note_attr, "source-application")
            
            # 内容
            content_elem = ET.SubElement(note_elem, "content")
            original_content = note_entry.get('content', '')
            
            # 处理嵌入的资源
            pattern = r'☺.+?<[^/]+/><[^/]*/>'
            matches = re.findall(pattern, original_content)
            
            for img_tag in matches:
                try:
                    file_id = img_tag[2:img_tag.index("<")]
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
                    
                    # 替换内容中的占位符
                    replacement = f'<div><en-media type="{resource_data["mime"]}" hash="{resource_data["hash"]}"/></div>'
                    original_content = original_content.replace(img_tag, replacement)
                    
                except Exception as e:
                    print(f"处理资源时出错: {e}")
                    continue
            
            # 处理HTML内容
            processed_content = self.process_html_content(original_content)
            
            # 创建CDATA内容
            enex_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">
<en-note><div>{processed_content}</div></en-note>'''
            
            content_elem.text = enex_content
            return True
            
        except Exception as e:
            print(f"处理笔记 {note_id} 时出错: {e}")
            return False
    
    def handle_folder_export(self) -> None:
        """处理文件夹导出 - 修复分批导出覆盖问题"""
        total_exported = 0
        
        for folder_id, folder in self.folder_list.items():
            if not folder['notes']:
                continue
            
            folder_name = folder['subject']
            notes_count = len(folder['notes'])
            print(f"\n正在导出文件夹: {folder_name} (包含 {notes_count} 条笔记)")
            
            # 创建XML文档（整个文件夹共享一个文档）
            xml_tree = self.create_enex_document()
            xml_root = xml_tree.getroot()
            
            successful_notes = 0
            current_chunk_notes = 0
            chunk_number = 1
            
            for i, note_id in enumerate(folder['notes']):
                print(f"处理笔记 {i+1}/{notes_count}: {note_id}")
                
                # 处理单个笔记
                if self.process_single_note(note_id, xml_root):
                    successful_notes += 1
                    current_chunk_notes += 1
                    total_exported += 1
                
                # 达到分块大小时保存当前文件
                if current_chunk_notes >= self.chunk_size and i < notes_count - 1:
                    # 保存当前分块
                    if successful_notes > 0:
                        if notes_count > self.chunk_size:
                            filename = f"{folder_name}_part{chunk_number:02d}.enex"
                        else:
                            filename = f"{folder_name}.enex"
                        
                        filepath = os.path.join(self.output_dir, filename)
                        xml_tree.write(filepath, encoding='utf-8', xml_declaration=True)
                        print(f"已导出分块 {chunk_number}: {filepath} (包含 {current_chunk_notes} 条笔记)")
                    
                    # 创建新的XML文档用于下一分块
                    xml_tree = self.create_enex_document()
                    xml_root = xml_tree.getroot()
                    current_chunk_notes = 0
                    chunk_number += 1
            
            # 保存最后一个分块（或唯一的分块）
            if successful_notes > 0:
                if notes_count > self.chunk_size:
                    filename = f"{folder_name}_part{chunk_number:02d}.enex"
                else:
                    filename = f"{folder_name}.enex"
                
                filepath = os.path.join(self.output_dir, filename)
                xml_tree.write(filepath, encoding='utf-8', xml_declaration=True)
                print(f"已导出分块 {chunk_number}: {filepath} (包含 {current_chunk_notes} 条笔记)")
            
            print(f"文件夹 {folder_name} 导出完成 (成功 {successful_notes}/{notes_count} 条笔记)")
        
        print(f"\n所有文件夹导出完成！总共导出 {total_exported} 条笔记")
        print(f"文件保存在: {os.path.abspath(self.output_dir)}")
    
    def export_notes(self) -> None:
        """主导出函数"""
        print("开始导出小米笔记...")
        print(f"分批大小: {self.chunk_size} 条笔记/文件")
        print(f"输出目录: {self.output_dir}")
        
        # 检查登录状态
        if not self.check_login_status():
            print("错误: 登录状态无效，请检查cookies")
            return
        
        try:
            # 下载笔记列表
            self.download_notes_recursive()
            
            # 导出各个文件夹
            self.handle_folder_export()
            
            print("导出完成!")
            
        except Exception as e:
            print(f"导出过程中出错: {e}")
            raise

def get_cookies_from_browser():
    """从浏览器获取cookies的说明"""
    print("""
请按以下步骤获取小米云笔记的cookies:

1. 在Chrome浏览器中登录 https://i.mi.com/note/h5#/
2. 按F12打开开发者工具
3. 切换到 Network (网络) 标签
4. 刷新页面
5. 找到任意一个请求，右键选择 Copy → Copy as cURL
6. 从cURL命令中提取cookies字符串

或者直接在控制台运行:
document.cookie

然后将cookies字符串作为参数传递给程序。
    """)

def main():
    """主函数"""
    print("小米笔记导出工具 - 修复分批导出版")
    
    # 解析命令行参数
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='小米笔记导出工具')
    parser.add_argument('--cookies', '-c', help='cookies字符串')
    parser.add_argument('--chunk-size', '-s', type=int, default=50, 
                       help='每批导出的笔记数量 (默认: 50)')
    parser.add_argument('--output-dir', '-o', default='exported_notes',
                       help='输出目录 (默认: exported_notes)')
    
    args = parser.parse_args()
    
    # 获取cookies
    cookies_str = args.cookies
    if not cookies_str:
        print("未提供cookies参数")
        get_cookies_from_browser()
        cookies_str = input("请输入cookies字符串: ")
        if not cookies_str.strip():
            print("使用无cookies模式(可能会失败)")
            cookies_str = None
    
    # 创建导出器
    exporter = XiaomiNoteExporter(
        cookies_str=cookies_str,
        chunk_size=args.chunk_size,
        output_dir=args.output_dir
    )
    
    exporter.export_notes()

if __name__ == "__main__":
    main()