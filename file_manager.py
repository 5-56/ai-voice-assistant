#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件管理器
支持文档、图片上传、预览和管理功能
"""

import os
import json
import logging
import shutil
import hashlib
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import io

# 知识库集成
try:
    from knowledge_base import get_knowledge_base
    KNOWLEDGE_BASE_AVAILABLE = True
except ImportError:
    KNOWLEDGE_BASE_AVAILABLE = False
    logging.warning("知识库模块不可用")

class FileManager:
    """文件管理器"""
    
    def __init__(self):
        self.upload_dir = Path("uploads")
        self.thumbnails_dir = Path("thumbnails")
        self.files_db_path = Path("files_database.json")
        
        # 支持的文件类型
        self.supported_documents = {
            '.pdf': 'PDF文档',
            '.doc': 'Word文档',
            '.docx': 'Word文档',
            '.txt': '文本文件',
            '.md': 'Markdown文档',
            '.rtf': 'RTF文档',
            '.odt': 'OpenDocument文档'
        }
        
        self.supported_images = {
            '.png': 'PNG图片',
            '.jpg': 'JPEG图片',
            '.jpeg': 'JPEG图片',
            '.gif': 'GIF图片',
            '.bmp': 'BMP图片',
            '.webp': 'WebP图片',
            '.tiff': 'TIFF图片',
            '.ico': 'ICO图标'
        }
        
        # 文件数据库
        self.files_db = {}
        
        # 初始化
        self._initialize()
    
    def _initialize(self):
        """初始化文件管理器"""
        try:
            # 创建目录
            self.upload_dir.mkdir(exist_ok=True)
            self.thumbnails_dir.mkdir(exist_ok=True)
            
            # 加载文件数据库
            self._load_files_database()
            
            logging.info("文件管理器初始化成功")
            
        except Exception as e:
            logging.error(f"文件管理器初始化失败: {e}")
    
    def _load_files_database(self):
        """加载文件数据库"""
        try:
            if self.files_db_path.exists():
                with open(self.files_db_path, 'r', encoding='utf-8') as f:
                    self.files_db = json.load(f)
            else:
                self.files_db = {
                    "files": {},
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                }
                self._save_files_database()
        except Exception as e:
            logging.error(f"加载文件数据库失败: {e}")
            self.files_db = {"files": {}}
    
    def _save_files_database(self):
        """保存文件数据库"""
        try:
            self.files_db["last_updated"] = datetime.now().isoformat()
            with open(self.files_db_path, 'w', encoding='utf-8') as f:
                json.dump(self.files_db, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"保存文件数据库失败: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希值"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logging.error(f"计算文件哈希失败: {e}")
            return ""
    
    def _generate_thumbnail(self, image_path: Path, size: Tuple[int, int] = (150, 150)) -> Optional[Path]:
        """生成图片缩略图"""
        try:
            thumbnail_path = self.thumbnails_dir / f"thumb_{image_path.stem}.png"
            
            with Image.open(image_path) as img:
                # 转换为RGB模式（处理RGBA等格式）
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # 生成缩略图
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(thumbnail_path, "PNG")
                
                return thumbnail_path
        except Exception as e:
            logging.error(f"生成缩略图失败: {e}")
            return None
    
    def upload_file(self, source_path: str, custom_name: str = None) -> Dict[str, Any]:
        """上传文件"""
        try:
            source_path = Path(source_path)
            
            if not source_path.exists():
                return {"success": False, "error": "文件不存在"}
            
            # 检查文件类型
            file_ext = source_path.suffix.lower()
            if file_ext not in {**self.supported_documents, **self.supported_images}:
                return {"success": False, "error": f"不支持的文件类型: {file_ext}"}
            
            # 生成文件ID和目标路径
            file_hash = self._calculate_file_hash(source_path)
            file_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_hash[:8]}"
            
            # 使用自定义名称或原始名称
            if custom_name:
                filename = f"{custom_name}{file_ext}"
            else:
                filename = source_path.name
            
            target_path = self.upload_dir / f"{file_id}_{filename}"
            
            # 复制文件
            shutil.copy2(source_path, target_path)
            
            # 确定文件类型
            is_image = file_ext in self.supported_images
            file_type = "image" if is_image else "document"
            
            # 生成缩略图（如果是图片）
            thumbnail_path = None
            if is_image:
                thumbnail_path = self._generate_thumbnail(target_path)
            
            # 获取文件信息
            file_stat = target_path.stat()
            
            # 保存到数据库
            file_info = {
                "id": file_id,
                "original_name": source_path.name,
                "custom_name": custom_name,
                "filename": filename,
                "file_path": str(target_path),
                "file_type": file_type,
                "file_extension": file_ext,
                "file_size": file_stat.st_size,
                "file_hash": file_hash,
                "thumbnail_path": str(thumbnail_path) if thumbnail_path else None,
                "mime_type": mimetypes.guess_type(str(target_path))[0],
                "upload_time": datetime.now().isoformat(),
                "description": ""
            }
            
            self.files_db["files"][file_id] = file_info
            self._save_files_database()

            # 添加到知识库（如果是文档类型）
            knowledge_base_result = None
            if KNOWLEDGE_BASE_AVAILABLE and file_type == "document":
                try:
                    kb = get_knowledge_base()
                    kb_result = kb.add_document(
                        file_id=file_id,
                        file_name=filename,
                        file_path=str(target_path),
                        tags=[],
                        category=""
                    )
                    knowledge_base_result = kb_result
                    if kb_result["success"]:
                        logging.info(f"文档已添加到知识库: {filename}")
                    else:
                        logging.warning(f"添加到知识库失败: {kb_result.get('error', '未知错误')}")
                except Exception as e:
                    logging.error(f"知识库集成失败: {e}")

            logging.info(f"文件上传成功: {filename}")

            result = {
                "success": True,
                "file_info": file_info,
                "message": f"文件 '{filename}' 上传成功"
            }

            # 添加知识库信息
            if knowledge_base_result:
                result["knowledge_base"] = knowledge_base_result

            return result
            
        except Exception as e:
            logging.error(f"文件上传失败: {e}")
            return {"success": False, "error": f"上传失败: {e}"}
    
    def get_file_list(self, file_type: str = None) -> List[Dict[str, Any]]:
        """获取文件列表"""
        try:
            files = list(self.files_db.get("files", {}).values())
            
            if file_type:
                files = [f for f in files if f.get("file_type") == file_type]
            
            # 按上传时间排序
            files.sort(key=lambda x: x.get("upload_time", ""), reverse=True)
            
            return files
            
        except Exception as e:
            logging.error(f"获取文件列表失败: {e}")
            return []
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        return self.files_db.get("files", {}).get(file_id)
    
    def delete_file(self, file_id: str) -> Dict[str, Any]:
        """删除文件"""
        try:
            file_info = self.get_file_info(file_id)
            if not file_info:
                return {"success": False, "error": "文件不存在"}
            
            # 删除文件
            file_path = Path(file_info["file_path"])
            if file_path.exists():
                file_path.unlink()
            
            # 删除缩略图
            if file_info.get("thumbnail_path"):
                thumbnail_path = Path(file_info["thumbnail_path"])
                if thumbnail_path.exists():
                    thumbnail_path.unlink()
            
            # 从数据库删除
            del self.files_db["files"][file_id]
            self._save_files_database()

            # 从知识库删除（如果是文档类型）
            if KNOWLEDGE_BASE_AVAILABLE and file_info.get("file_type") == "document":
                try:
                    kb = get_knowledge_base()
                    kb_result = kb.remove_document(file_id)
                    if kb_result["success"]:
                        logging.info(f"文档已从知识库移除: {file_info['filename']}")
                    else:
                        logging.warning(f"从知识库移除失败: {kb_result.get('error', '未知错误')}")
                except Exception as e:
                    logging.error(f"知识库移除失败: {e}")

            logging.info(f"文件删除成功: {file_info['filename']}")

            return {
                "success": True,
                "message": f"文件 '{file_info['filename']}' 删除成功"
            }
            
        except Exception as e:
            logging.error(f"文件删除失败: {e}")
            return {"success": False, "error": f"删除失败: {e}"}
    
    def rename_file(self, file_id: str, new_name: str) -> Dict[str, Any]:
        """重命名文件"""
        try:
            file_info = self.get_file_info(file_id)
            if not file_info:
                return {"success": False, "error": "文件不存在"}
            
            # 更新自定义名称
            old_name = file_info.get("custom_name") or file_info["original_name"]
            file_info["custom_name"] = new_name
            
            # 更新显示文件名
            file_ext = file_info["file_extension"]
            file_info["filename"] = f"{new_name}{file_ext}"
            
            self._save_files_database()
            
            logging.info(f"文件重命名成功: {old_name} -> {new_name}")
            
            return {
                "success": True,
                "message": f"文件重命名成功: '{old_name}' -> '{new_name}'"
            }
            
        except Exception as e:
            logging.error(f"文件重命名失败: {e}")
            return {"success": False, "error": f"重命名失败: {e}"}
    
    def update_file_description(self, file_id: str, description: str) -> Dict[str, Any]:
        """更新文件描述"""
        try:
            file_info = self.get_file_info(file_id)
            if not file_info:
                return {"success": False, "error": "文件不存在"}
            
            file_info["description"] = description
            self._save_files_database()
            
            return {"success": True, "message": "文件描述更新成功"}
            
        except Exception as e:
            logging.error(f"更新文件描述失败: {e}")
            return {"success": False, "error": f"更新失败: {e}"}
    
    def get_supported_formats(self) -> Dict[str, Dict[str, str]]:
        """获取支持的文件格式"""
        return {
            "documents": self.supported_documents,
            "images": self.supported_images
        }
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        try:
            total_files = len(self.files_db.get("files", {}))
            total_size = 0
            
            for file_info in self.files_db.get("files", {}).values():
                total_size += file_info.get("file_size", 0)
            
            # 计算目录大小
            upload_dir_size = sum(f.stat().st_size for f in self.upload_dir.rglob('*') if f.is_file())
            thumbnails_dir_size = sum(f.stat().st_size for f in self.thumbnails_dir.rglob('*') if f.is_file())
            
            return {
                "total_files": total_files,
                "total_size": total_size,
                "upload_dir_size": upload_dir_size,
                "thumbnails_dir_size": thumbnails_dir_size,
                "upload_dir": str(self.upload_dir),
                "thumbnails_dir": str(self.thumbnails_dir)
            }
            
        except Exception as e:
            logging.error(f"获取存储信息失败: {e}")
            return {}
    
    def cleanup_orphaned_files(self) -> Dict[str, Any]:
        """清理孤立文件"""
        try:
            cleaned_files = []
            
            # 检查数据库中的文件是否存在
            for file_id, file_info in list(self.files_db.get("files", {}).items()):
                file_path = Path(file_info["file_path"])
                if not file_path.exists():
                    del self.files_db["files"][file_id]
                    cleaned_files.append(file_info["filename"])
            
            # 检查目录中的孤立文件
            db_files = {Path(info["file_path"]).name for info in self.files_db.get("files", {}).values()}
            
            for file_path in self.upload_dir.iterdir():
                if file_path.is_file() and file_path.name not in db_files:
                    file_path.unlink()
                    cleaned_files.append(file_path.name)
            
            if cleaned_files:
                self._save_files_database()
            
            return {
                "success": True,
                "cleaned_files": cleaned_files,
                "message": f"清理了 {len(cleaned_files)} 个孤立文件"
            }
            
        except Exception as e:
            logging.error(f"清理孤立文件失败: {e}")
            return {"success": False, "error": f"清理失败: {e}"}

# 全局文件管理器实例
file_manager = FileManager()

def get_file_manager() -> FileManager:
    """获取文件管理器实例"""
    return file_manager
