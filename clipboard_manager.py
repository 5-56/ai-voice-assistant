#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪贴板管理器
支持文本和图片的剪贴板操作
"""

import logging
import tempfile
import io
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Union
import tkinter as tk
from PIL import Image, ImageGrab, ImageTk

class ClipboardManager:
    """剪贴板管理器"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "ai_assistant_clipboard"
        self.temp_dir.mkdir(exist_ok=True)
        
        # 剪贴板历史
        self.clipboard_history = []
        self.max_history = 50
        
        logging.info("剪贴板管理器初始化成功")
    
    def get_text_from_clipboard(self) -> Optional[str]:
        """从剪贴板获取文本"""
        try:
            # 创建临时窗口来访问剪贴板
            temp_root = tk.Tk()
            temp_root.withdraw()
            
            try:
                text = temp_root.clipboard_get()
                temp_root.destroy()
                
                if text and text.strip():
                    # 添加到历史记录
                    self._add_to_history("text", text)
                    logging.info(f"从剪贴板获取文本: {len(text)} 字符")
                    return text.strip()
                
            except tk.TclError:
                # 剪贴板为空或不包含文本
                temp_root.destroy()
                return None
                
        except Exception as e:
            logging.error(f"获取剪贴板文本失败: {e}")
            return None
    
    def get_image_from_clipboard(self) -> Optional[Dict[str, Any]]:
        """从剪贴板获取图片"""
        try:
            # 使用PIL获取剪贴板图片
            image = ImageGrab.grabclipboard()
            
            if image is None:
                return None
            
            # 确保是PIL Image对象
            if not isinstance(image, Image.Image):
                return None
            
            # 生成临时文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_filename = f"clipboard_image_{timestamp}.png"
            temp_path = self.temp_dir / temp_filename
            
            # 保存图片
            image.save(temp_path, "PNG")
            
            # 获取图片信息
            width, height = image.size
            file_size = temp_path.stat().st_size
            
            image_info = {
                "type": "image",
                "path": str(temp_path),
                "filename": temp_filename,
                "width": width,
                "height": height,
                "file_size": file_size,
                "format": "PNG",
                "timestamp": datetime.now().isoformat()
            }
            
            # 添加到历史记录
            self._add_to_history("image", image_info)
            
            logging.info(f"从剪贴板获取图片: {width}x{height}, {file_size} bytes")
            
            return image_info
            
        except Exception as e:
            logging.error(f"获取剪贴板图片失败: {e}")
            return None
    
    def set_text_to_clipboard(self, text: str) -> bool:
        """设置文本到剪贴板"""
        try:
            temp_root = tk.Tk()
            temp_root.withdraw()
            
            temp_root.clipboard_clear()
            temp_root.clipboard_append(text)
            temp_root.update()
            temp_root.destroy()
            
            logging.info(f"文本已复制到剪贴板: {len(text)} 字符")
            return True
            
        except Exception as e:
            logging.error(f"设置剪贴板文本失败: {e}")
            return False
    
    def set_image_to_clipboard(self, image_path: str) -> bool:
        """设置图片到剪贴板"""
        try:
            image = Image.open(image_path)
            
            # 将图片复制到剪贴板
            output = io.BytesIO()
            image.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]  # 移除BMP文件头
            output.close()
            
            # 使用Windows API复制到剪贴板
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
            
            logging.info(f"图片已复制到剪贴板: {image_path}")
            return True
            
        except Exception as e:
            logging.error(f"设置剪贴板图片失败: {e}")
            return False
    
    def _add_to_history(self, content_type: str, content: Union[str, Dict[str, Any]]):
        """添加到剪贴板历史"""
        try:
            history_item = {
                "type": content_type,
                "content": content,
                "timestamp": datetime.now().isoformat()
            }
            
            self.clipboard_history.insert(0, history_item)
            
            # 限制历史记录数量
            if len(self.clipboard_history) > self.max_history:
                self.clipboard_history = self.clipboard_history[:self.max_history]
                
        except Exception as e:
            logging.error(f"添加剪贴板历史失败: {e}")
    
    def get_clipboard_history(self, content_type: str = None) -> list:
        """获取剪贴板历史"""
        try:
            if content_type:
                return [item for item in self.clipboard_history if item["type"] == content_type]
            return self.clipboard_history
            
        except Exception as e:
            logging.error(f"获取剪贴板历史失败: {e}")
            return []
    
    def clear_history(self):
        """清空剪贴板历史"""
        try:
            self.clipboard_history.clear()
            logging.info("剪贴板历史已清空")
            
        except Exception as e:
            logging.error(f"清空剪贴板历史失败: {e}")
    
    def has_text(self) -> bool:
        """检查剪贴板是否包含文本"""
        try:
            temp_root = tk.Tk()
            temp_root.withdraw()
            
            try:
                text = temp_root.clipboard_get()
                temp_root.destroy()
                return bool(text and text.strip())
            except tk.TclError:
                temp_root.destroy()
                return False
                
        except Exception as e:
            logging.error(f"检查剪贴板文本失败: {e}")
            return False
    
    def has_image(self) -> bool:
        """检查剪贴板是否包含图片"""
        try:
            image = ImageGrab.grabclipboard()
            return isinstance(image, Image.Image)
            
        except Exception as e:
            logging.error(f"检查剪贴板图片失败: {e}")
            return False
    
    def get_clipboard_content_type(self) -> Optional[str]:
        """获取剪贴板内容类型"""
        try:
            if self.has_image():
                return "image"
            elif self.has_text():
                return "text"
            else:
                return None
                
        except Exception as e:
            logging.error(f"获取剪贴板内容类型失败: {e}")
            return None
    
    def paste_to_widget(self, widget, content_type: str = "auto") -> bool:
        """粘贴内容到指定控件"""
        try:
            if content_type == "auto":
                content_type = self.get_clipboard_content_type()
            
            if content_type == "text":
                text = self.get_text_from_clipboard()
                if text and hasattr(widget, 'insert'):
                    # 获取当前光标位置
                    try:
                        cursor_pos = widget.index(tk.INSERT)
                        widget.insert(cursor_pos, text)
                        return True
                    except:
                        # 如果获取光标位置失败，插入到末尾
                        widget.insert(tk.END, text)
                        return True
            
            elif content_type == "image":
                # 对于图片，返回图片信息，由调用者处理
                image_info = self.get_image_from_clipboard()
                return image_info is not None
            
            return False
            
        except Exception as e:
            logging.error(f"粘贴到控件失败: {e}")
            return False
    
    def create_image_preview(self, image_path: str, size: tuple = (200, 200)) -> Optional[ImageTk.PhotoImage]:
        """创建图片预览"""
        try:
            image = Image.open(image_path)
            
            # 计算缩放比例，保持宽高比
            image.thumbnail(size, Image.Resampling.LANCZOS)
            
            # 转换为Tkinter可用的格式
            photo = ImageTk.PhotoImage(image)
            
            return photo
            
        except Exception as e:
            logging.error(f"创建图片预览失败: {e}")
            return None
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """清理临时文件"""
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            cleaned_count = 0
            
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        cleaned_count += 1
            
            if cleaned_count > 0:
                logging.info(f"清理了 {cleaned_count} 个临时文件")
            
            return cleaned_count
            
        except Exception as e:
            logging.error(f"清理临时文件失败: {e}")
            return 0
    
    def get_status(self) -> Dict[str, Any]:
        """获取剪贴板管理器状态"""
        return {
            "has_text": self.has_text(),
            "has_image": self.has_image(),
            "content_type": self.get_clipboard_content_type(),
            "history_count": len(self.clipboard_history),
            "temp_dir": str(self.temp_dir),
            "temp_files_count": len(list(self.temp_dir.iterdir()))
        }

# 全局剪贴板管理器实例
clipboard_manager = ClipboardManager()

def get_clipboard_manager() -> ClipboardManager:
    """获取剪贴板管理器实例"""
    return clipboard_manager
